"""Builds the unified order list (CartPilot + imported external orders) from the database."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import ExternalOrder, Order
from .analytics_service import UnifiedOrder


def load_unified_orders(db: Session, user_id: int) -> list[UnifiedOrder]:
    out: list[UnifiedOrder] = []
    orders = db.scalars(select(Order).where(Order.user_id == user_id, Order.status != "pending_payment")
                        .options(selectinload(Order.items), selectinload(Order.payment))).all()
    for o in orders:
        out.append(UnifiedOrder(
            source="cartpilot", row_id=o.id, platform="cartpilot", order_id=f"CP-{o.id}",
            order_date=o.paid_at or o.created_at, amount=o.total, currency=o.currency, status=o.status,
            payment_method="PayPal", tracking_info=None, import_source="paypal_checkout",
            items=[{"title": i.title, "image_url": i.image_url, "category": i.category,
                    "price": i.unit_price, "quantity": i.quantity} for i in o.items]))
    ext = db.scalars(select(ExternalOrder).where(ExternalOrder.user_id == user_id)
                     .options(selectinload(ExternalOrder.items))).all()
    for e in ext:
        out.append(UnifiedOrder(
            source="external", row_id=e.id, platform=e.platform, order_id=e.external_order_id,
            order_date=e.order_date, amount=e.total, currency=e.currency, status=e.status,
            payment_method=e.payment_method, tracking_info=e.tracking_info, import_source=e.import_source,
            items=[{"title": i.title, "image_url": i.image_url, "category": i.category,
                    "price": i.price, "quantity": i.quantity} for i in e.items]))
    return out


def unified_to_dict(o: UnifiedOrder) -> dict:
    return {"source": o.source, "id": o.row_id, "platform": o.platform, "order_id": o.order_id,
            "product_name": o.product_name, "image_url": o.image_url, "order_date": o.order_date.isoformat(),
            "amount": str(o.amount), "currency": o.currency, "status": o.status,
            "payment_method": o.payment_method, "tracking_info": o.tracking_info,
            "import_source": o.import_source, "items": [{**i, "price": str(i["price"]) if i.get("price") is not None else None} for i in o.items]}
