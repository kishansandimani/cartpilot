"""PayPal REST (Orders v2) wrapper. Sandbox <-> Live is just PAYPAL_ENV + credentials.

Docs: https://developer.paypal.com/docs/api/orders/v2/
"""
import time
from decimal import Decimal
from typing import Any

import httpx

from ..config import get_settings


class PayPalError(Exception):
    def __init__(self, message: str, status_code: int = 502, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


_token_cache: dict = {"token": None, "expires": 0.0}


def _ensure_configured():
    s = get_settings()
    if not (s.paypal_client_id and s.paypal_client_secret):
        raise PayPalError("PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in backend/.env.", 503)
    return s


def _access_token() -> str:
    s = _ensure_configured()
    if _token_cache["token"] and _token_cache["expires"] > time.time() + 30:
        return _token_cache["token"]
    try:
        r = httpx.post(f"{s.paypal_base_url}/v1/oauth2/token", data={"grant_type": "client_credentials"},
                       auth=(s.paypal_client_id, s.paypal_client_secret), timeout=20)
    except httpx.HTTPError as e:
        raise PayPalError(f"Could not reach PayPal: {e}") from e
    if r.status_code != 200:
        raise PayPalError("PayPal rejected the credentials (check client id/secret and PAYPAL_ENV).", 502, r.text)
    data = r.json()
    _token_cache.update(token=data["access_token"], expires=time.time() + int(data.get("expires_in", 300)))
    return data["access_token"]


def _request(method: str, path: str, *, json: dict | None = None, request_id: str | None = None) -> httpx.Response:
    s = _ensure_configured()
    headers = {"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"}
    if request_id:
        headers["PayPal-Request-Id"] = request_id  # makes the call idempotent on PayPal's side
    try:
        return httpx.request(method, f"{s.paypal_base_url}{path}", json=json, headers=headers, timeout=30)
    except httpx.HTTPError as e:
        raise PayPalError(f"Could not reach PayPal: {e}") from e


def money(value: Decimal) -> str:
    return f"{Decimal(value):.2f}"


def create_order(*, local_order_id: int, items: list[dict], total: Decimal, currency: str) -> dict:
    """items: [{"name","unit_price"(Decimal),"quantity"}]. Amounts are computed by the backend only."""
    purchase_items = [{
        "name": it["name"][:127], "quantity": str(it["quantity"]),
        "unit_amount": {"currency_code": currency, "value": money(it["unit_price"])},
    } for it in items]
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": f"cartpilot-{local_order_id}",
            "custom_id": str(local_order_id),
            "invoice_id": f"CP-{local_order_id}",
            "items": purchase_items,
            "amount": {"currency_code": currency, "value": money(total),
                       "breakdown": {"item_total": {"currency_code": currency, "value": money(total)}}},
        }],
        "application_context": {"user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING"},
    }
    r = _request("POST", "/v2/checkout/orders", json=body, request_id=f"cartpilot-create-{local_order_id}")
    if r.status_code not in (200, 201):
        raise PayPalError("PayPal could not create the order.", 502, r.text)
    return r.json()


def get_order(paypal_order_id: str) -> dict:
    r = _request("GET", f"/v2/checkout/orders/{paypal_order_id}")
    if r.status_code != 200:
        raise PayPalError("PayPal order not found.", 404, r.text)
    return r.json()


def capture_order(paypal_order_id: str) -> dict:
    r = _request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture", json={},
                 request_id=f"cartpilot-capture-{paypal_order_id}")
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 422 and "ORDER_ALREADY_CAPTURED" in r.text:
        return get_order(paypal_order_id)
    raise PayPalError("PayPal could not capture the payment.", 502, r.text)


def verify_capture(paypal_order: dict, *, expected_total: Decimal, expected_currency: str,
                   expected_local_order_id: int) -> tuple[bool, str, str | None]:
    """Returns (ok, reason, capture_id). Never trusts the browser - only PayPal's own response."""
    if paypal_order.get("status") != "COMPLETED":
        return False, f"PayPal order status is {paypal_order.get('status')}", None
    units = paypal_order.get("purchase_units") or []
    if not units:
        return False, "No purchase unit in PayPal response", None
    unit = units[0]
    if str(unit.get("custom_id")) != str(expected_local_order_id):
        return False, "PayPal order does not belong to this CartPilot order", None
    captures = (unit.get("payments") or {}).get("captures") or []
    if not captures:
        return False, "No capture in PayPal response", None
    cap = captures[0]
    if cap.get("status") != "COMPLETED":
        return False, f"Capture status is {cap.get('status')}", cap.get("id")
    amount = cap.get("amount") or {}
    if amount.get("currency_code") != expected_currency:
        return False, "Captured currency does not match the order", cap.get("id")
    try:
        if Decimal(str(amount.get("value"))) != Decimal(expected_total).quantize(Decimal("0.01")):
            return False, "Captured amount does not match the order total", cap.get("id")
    except Exception:
        return False, "Captured amount is not a valid number", cap.get("id")
    return True, "ok", cap.get("id")


def verify_webhook_signature(headers: dict, event: dict) -> bool:
    """Asks PayPal to verify the webhook signature (needs PAYPAL_WEBHOOK_ID)."""
    s = _ensure_configured()
    if not s.paypal_webhook_id:
        raise PayPalError("PAYPAL_WEBHOOK_ID is not set, so webhooks cannot be verified.", 503)
    h = {k.lower(): v for k, v in headers.items()}
    body = {
        "auth_algo": h.get("paypal-auth-algo"), "cert_url": h.get("paypal-cert-url"),
        "transmission_id": h.get("paypal-transmission-id"), "transmission_sig": h.get("paypal-transmission-sig"),
        "transmission_time": h.get("paypal-transmission-time"), "webhook_id": s.paypal_webhook_id,
        "webhook_event": event,
    }
    if not all(body[k] for k in ("auth_algo", "cert_url", "transmission_id", "transmission_sig", "transmission_time")):
        return False
    r = _request("POST", "/v1/notifications/verify-webhook-signature", json=body)
    return r.status_code == 200 and r.json().get("verification_status") == "SUCCESS"
