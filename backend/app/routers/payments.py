"""PayPal checkout. The browser never decides whether a payment succeeded - only PayPal's server response does."""
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Order, OrderItem, Payment, ShoppingEvent, User, WebhookEvent, utcnow
from ..schemas import CaptureIn, CreateOrderIn
from ..services import cart_service, paypal_service
from ..services.paypal_service import PayPalError
from ..services.product_provider import ProviderError, get_provider
from ..services.product_service import upsert_product

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _paypal_http(e: PayPalError) -> HTTPException:
    return HTTPException(e.status_code, str(e))


@router.get("/config")
def config(user: User = Depends(get_current_user)):
    s = get_settings()
    return {"client_id": s.paypal_client_id or None, "currency": s.paypal_currency, "env": s.paypal_env,
            "configured": bool(s.paypal_client_id and s.paypal_client_secret)}


@router.post("/create-order")
def create_order(body: CreateOrderIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not body.confirmed:
        raise HTTPException(400, "The order must be explicitly confirmed by the user.")
    s = get_settings()
    cart = cart_service.get_or_create_cart(db, user.id)
    if not cart.items:
        raise HTTPException(400, "Your cart is empty.")
    try:
        provider = get_provider()
    except ProviderError as e:
        raise HTTPException(502, str(e))

    # 1) Re-check every product with the provider so the price cannot be tampered with or stale.
    for item in cart.items:
        p = item.product
        if p.provider != provider.name:
            raise HTTPException(409, f"'{p.title}' came from a different product source. Please remove it and search again.")
        if s.paypal_env == "live" and p.is_fixture:
            raise HTTPException(409, "Development fixture products cannot be bought in live mode.")
        try:
            fresh = provider.get(p.external_id)
        except ProviderError as e:
            raise HTTPException(502, f"Could not verify current prices: {e}")
        if fresh is None or (fresh.availability or "InStock") == "OutOfStock":
            raise HTTPException(409, f"'{p.title}' is no longer available.")
        upsert_product(db, fresh)
    db.flush()
    db.refresh(cart)
    for item in cart.items:
        db.refresh(item.product)

    summary = cart_service.cart_summary(cart)
    if summary["mixed_currencies"] or summary["currency"] != s.paypal_currency:
        raise HTTPException(400, f"Checkout is configured for {s.paypal_currency}, but your cart is priced in "
                                 f"{', '.join(summary['totals'])}. CartPilot does not guess exchange rates.")
    total = Decimal(summary["total"])

    # 2) Cancel any older unpaid order, then create a fresh one.
    for old in db.scalars(select(Order).where(Order.user_id == user.id, Order.status == "pending_payment")):
        old.status = "cancelled"
    order = Order(user_id=user.id, status="pending_payment", total=total, currency=s.paypal_currency)
    for item in cart.items:
        p = item.product
        order.items.append(OrderItem(product_id=p.id, title=p.title, merchant=p.merchant, image_url=p.image_url,
                                     category=p.category, unit_price=p.price, quantity=item.quantity))
    db.add(order)
    db.flush()

    # 3) Ask PayPal to create the order. Amounts come from OUR database only.
    try:
        pp = paypal_service.create_order(
            local_order_id=order.id, total=total, currency=s.paypal_currency,
            items=[{"name": i.title, "unit_price": i.unit_price, "quantity": i.quantity} for i in order.items])
    except PayPalError as e:
        db.rollback()
        raise _paypal_http(e)
    db.add(Payment(order_id=order.id, paypal_order_id=pp["id"], amount=total, currency=s.paypal_currency, status="created"))
    db.commit()
    return {"order_id": order.id, "paypal_order_id": pp["id"], "total": str(total), "currency": s.paypal_currency}


@router.post("/capture")
def capture(body: CaptureIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payment = db.scalar(select(Payment).join(Order, Order.id == Payment.order_id)
                        .where(Payment.paypal_order_id == body.paypal_order_id, Order.user_id == user.id))
    if payment is None:
        raise HTTPException(404, "Payment not found")
    order = payment.order
    if payment.status == "completed":  # idempotent: calling twice never charges twice
        return {"status": "completed", "order_id": order.id, "already_processed": True}
    if order.status in ("cancelled",):
        raise HTTPException(409, "This order was cancelled. Please start checkout again.")

    try:
        current = paypal_service.get_order(body.paypal_order_id)
        if current.get("status") == "APPROVED":       # buyer approved in the PayPal popup -> now we may capture
            result = paypal_service.capture_order(body.paypal_order_id)
        elif current.get("status") == "COMPLETED":     # already captured (e.g. by a retry)
            result = current
        else:
            raise HTTPException(409, f"The buyer has not approved this payment yet (PayPal status: {current.get('status')}).")
    except PayPalError as e:
        raise _paypal_http(e)

    ok, reason, capture_id = paypal_service.verify_capture(
        result, expected_total=order.total, expected_currency=order.currency, expected_local_order_id=order.id)
    if not ok:
        payment.paypal_capture_id = capture_id
        payment.status = "needs_review" if capture_id else "failed"
        order.status = "needs_review" if capture_id else "failed"
        db.commit()
        raise HTTPException(422, f"Payment could not be verified: {reason}")

    payment.status, payment.paypal_capture_id = "completed", capture_id
    order.status, order.paid_at = "paid", utcnow()
    cart = cart_service.get_or_create_cart(db, user.id)
    for i in list(cart.items):
        db.delete(i)
    db.add(ShoppingEvent(user_id=user.id, event_type="purchase", payload={"order_id": order.id, "total": str(order.total)}))
    db.commit()
    return {"status": "completed", "order_id": order.id, "total": str(order.total), "currency": order.currency}


@router.get("/{order_id}/status")
def status(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    return {"order_id": order.id, "order_status": order.status,
            "payment_status": order.payment.status if order.payment else None}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """PayPal -> CartPilot notifications. Signature is verified with PayPal before anything is trusted."""
    raw = await request.body()
    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Invalid JSON")
    try:
        if not paypal_service.verify_webhook_signature(dict(request.headers), event):
            raise HTTPException(400, "Webhook signature verification failed")
    except PayPalError as e:
        raise _paypal_http(e)

    event_id = event.get("id")
    if not event_id:
        raise HTTPException(400, "Missing event id")
    try:
        db.add(WebhookEvent(event_id=event_id, event_type=event.get("event_type", "")))
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    res = event.get("resource") or {}
    capture_id = res.get("id")
    pp_order_id = ((res.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id")
    payment = None
    if pp_order_id:
        payment = db.scalar(select(Payment).where(Payment.paypal_order_id == pp_order_id))
    if payment is None and capture_id:
        payment = db.scalar(select(Payment).where(Payment.paypal_capture_id == capture_id))
    if payment is not None:
        etype, order = event.get("event_type", ""), payment.order
        if etype == "PAYMENT.CAPTURE.COMPLETED":
            amt = res.get("amount") or {}
            if (payment.status != "completed" and amt.get("currency_code") == payment.currency
                    and Decimal(str(amt.get("value", "0"))) == payment.amount.quantize(Decimal("0.01"))):
                payment.status, payment.paypal_capture_id = "completed", capture_id
                order.status, order.paid_at = "paid", order.paid_at or utcnow()
        elif etype in ("PAYMENT.CAPTURE.DENIED", "PAYMENT.CAPTURE.DECLINED"):
            payment.status, order.status = "failed", "failed"
        elif etype in ("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"):
            payment.status, order.status = "refunded", "refunded"
    db.commit()
    return {"status": "ok"}
