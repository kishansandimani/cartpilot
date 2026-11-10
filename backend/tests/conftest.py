"""Test setup: uses a throw-away SQLite file, fixture products, and fake PayPal/Gemini (no network)."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "JWT_SECRET": "test-secret-not-for-production-0123456789",
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "PRODUCT_PROVIDER": "fixtures", "PRODUCT_CURRENCY": "USD", "PAYPAL_CURRENCY": "USD",
    "PAYPAL_CLIENT_ID": "test-client", "PAYPAL_CLIENT_SECRET": "test-secret", "GEMINI_API_KEY": "test-key",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


_counter = {"n": 0}


@pytest.fixture()
def auth(client):
    """Registers a brand-new user and returns (headers, user_json)."""
    _counter["n"] += 1
    r = client.post("/api/auth/register", json={"email": f"user{_counter['n']}@example.com", "password": "password123", "full_name": "Test User"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture()
def fake_paypal(monkeypatch):
    """Replaces the PayPal network calls with an in-memory fake that behaves like PayPal Orders v2."""
    from app.services import paypal_service as pp
    state = {"orders": {}, "tamper_amount": False}

    def create_order(*, local_order_id, items, total, currency):
        oid = f"PP-ORDER-{local_order_id}-{len(state['orders'])}"
        state["orders"][oid] = {"status": "CREATED", "custom_id": str(local_order_id), "total": total, "currency": currency}
        return {"id": oid, "status": "CREATED"}

    def _full(oid):
        o = state["orders"][oid]
        amount = "0.01" if state["tamper_amount"] else f"{o['total']:.2f}"
        out = {"id": oid, "status": o["status"], "purchase_units": [{"custom_id": o["custom_id"], "payments": {"captures": []}}]}
        if o["status"] == "COMPLETED":
            out["purchase_units"][0]["payments"]["captures"] = [{"id": "CAP-" + oid, "status": "COMPLETED",
                                                                  "amount": {"currency_code": o["currency"], "value": amount}}]
        return out

    monkeypatch.setattr(pp, "create_order", create_order)
    monkeypatch.setattr(pp, "get_order", lambda oid: _full(oid))

    def capture_order(oid):
        state["orders"][oid]["status"] = "COMPLETED"
        return _full(oid)

    monkeypatch.setattr(pp, "capture_order", capture_order)
    state["approve"] = lambda oid: state["orders"][oid].update(status="APPROVED")
    return state
