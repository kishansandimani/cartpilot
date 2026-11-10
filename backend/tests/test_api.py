"""End-to-end API tests (registration -> search -> cart -> voice -> PayPal -> orders -> analytics)."""
from decimal import Decimal


def search_and_add(client, headers, q="laptop", n=1):
    r = client.get("/api/products/search", params={"q": q}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["is_fixture_data"] is True
    prods = r.json()["products"]
    for p in prods[:n]:
        assert client.post("/api/cart/items", json={"product_id": p["id"], "quantity": 1}, headers=headers).status_code == 201
    return prods


def test_register_login_and_auth_required(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 201
    assert client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"}).json()["email"] == "a@example.com"
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/cart", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_password_too_short_rejected(client):
    assert client.post("/api/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422


def test_search_budget_and_compare(client, auth):
    headers, _ = auth
    r = client.get("/api/products/search", params={"q": "laptop", "max_price": "400"}, headers=headers)
    prods = r.json()["products"]
    assert prods and all(Decimal(p["price"]) <= 400 for p in prods)
    allp = client.get("/api/products/search", params={"q": "laptop"}, headers=headers).json()["products"]
    ids = [p["id"] for p in allp[:2]]
    cmp = client.post("/api/compare", json={"product_ids": ids}, headers=headers)
    assert cmp.status_code == 200
    body = cmp.json()
    assert body["cheapest_id"] in ids and any(row["label"] == "Price" for row in body["rows"])
    assert client.post("/api/compare", json={"product_ids": [ids[0], 999999]}, headers=headers).status_code == 404


def test_cart_operations_and_isolation(client, auth):
    headers, _ = auth
    prods = search_and_add(client, headers, "laptop", 2)
    cart = client.get("/api/cart", headers=headers).json()
    assert cart["item_count"] == 2
    item = cart["items"][0]
    up = client.patch(f"/api/cart/items/{item['id']}", json={"quantity": 3}, headers=headers).json()
    assert up["item_count"] == 4
    expected = sum(Decimal(i["product"]["price"]) * i["quantity"] for i in up["items"])
    assert Decimal(up["total"]) == expected
    # another user cannot touch this cart item
    other = client.post("/api/auth/register", json={"email": "other-cart@example.com", "password": "password123"}).json()
    oh = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.delete(f"/api/cart/items/{item['id']}", headers=oh).status_code == 404
    assert client.delete(f"/api/cart/items/{item['id']}", headers=headers).json()["item_count"] == 1
    assert client.delete("/api/cart", headers=headers).json()["item_count"] == 0


def test_voice_commands_and_safe_buy(client, auth, fake_paypal):
    headers, _ = auth
    prods = client.get("/api/products/search", params={"q": "headphones"}, headers=headers).json()["products"]
    ctx = {"last_product_ids": [p["id"] for p in prods]}

    def say(text, lang="en"):
        r = client.post("/api/voice/command", json={"text": text, "language": lang, "context": ctx}, headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    assert say("open my cart")["action"] == {"type": "navigate", "path": "/cart"}
    assert say("कार्ट खोलो", "hi")["action"]["path"] == "/cart"
    assert say("Show my orders")["action"]["path"] == "/orders"
    r = say("add the second product to my cart")
    assert r["action"]["type"] == "cart_updated"
    assert client.get("/api/cart", headers=headers).json()["items"][0]["product"]["id"] == prods[1]["id"]
    assert "cart total" in say("show my total cart value")["speech"].lower()
    r = say("Buy this product")
    assert r["requires_confirmation"] is True and r["action"]["type"] == "confirm_purchase"
    # VERY IMPORTANT: saying "buy" must never create a payment
    assert client.get("/api/payments/1/status", headers=headers).status_code == 404
    assert fake_paypal["orders"] == {}
    assert say("remove the earbuds from my cart")["action"]["type"] in ("cart_updated", "none")
    assert client.post("/api/voice/command", json={"text": "open cart"}).status_code == 401


def test_paypal_flow_verification_and_idempotency(client, auth, fake_paypal):
    headers, _ = auth
    search_and_add(client, headers, "laptop", 2)
    # must explicitly confirm
    assert client.post("/api/payments/create-order", json={"confirmed": False}, headers=headers).status_code == 400
    created = client.post("/api/payments/create-order", json={"confirmed": True}, headers=headers)
    assert created.status_code == 200, created.text
    ppid, order_id = created.json()["paypal_order_id"], created.json()["order_id"]
    cart_total = Decimal(client.get("/api/cart", headers=headers).json()["total"])
    assert Decimal(created.json()["total"]) == cart_total
    # buyer has not approved yet -> cannot capture
    assert client.post("/api/payments/capture", json={"paypal_order_id": ppid}, headers=headers).status_code == 409
    # another user cannot capture my payment
    other = client.post("/api/auth/register", json={"email": "thief@example.com", "password": "password123"}).json()
    oh = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/api/payments/capture", json={"paypal_order_id": ppid}, headers=oh).status_code == 404
    fake_paypal["approve"](ppid)
    cap = client.post("/api/payments/capture", json={"paypal_order_id": ppid}, headers=headers)
    assert cap.status_code == 200 and cap.json()["status"] == "completed"
    again = client.post("/api/payments/capture", json={"paypal_order_id": ppid}, headers=headers)
    assert again.json()["already_processed"] is True
    assert client.get("/api/cart", headers=headers).json()["item_count"] == 0
    assert client.get(f"/api/payments/{order_id}/status", headers=headers).json() == {
        "order_id": order_id, "order_status": "paid", "payment_status": "completed"}
    unified = client.get("/api/orders/unified", params={"platform": "cartpilot"}, headers=headers).json()
    assert len(unified) == 1 and unified[0]["payment_method"] == "PayPal" and unified[0]["tracking_info"] is None


def test_paypal_amount_mismatch_is_rejected(client, auth, fake_paypal):
    headers, _ = auth
    search_and_add(client, headers, "headphones", 1)
    c = client.post("/api/payments/create-order", json={"confirmed": True}, headers=headers).json()
    fake_paypal["approve"](c["paypal_order_id"])
    fake_paypal["tamper_amount"] = True
    r = client.post("/api/payments/capture", json={"paypal_order_id": c["paypal_order_id"]}, headers=headers)
    assert r.status_code == 422
    assert client.get(f"/api/payments/{c['order_id']}/status", headers=headers).json()["order_status"] == "needs_review"


def test_external_orders_duplicates_and_receipts(client, auth):
    headers, _ = auth
    body = {"platform": "amazon", "external_order_id": "402-1234567-7654321", "order_date": "2026-10-05",
            "total": "1499.00", "currency": "INR", "product_name": "USB-C cable", "category": "Electronics"}
    assert client.post("/api/external-orders", json=body, headers=headers).status_code == 201
    dup = client.post("/api/external-orders", json=body, headers=headers)
    assert dup.status_code == 409
    assert client.post("/api/external-orders", json={**body, "platform": "flipkart"}, headers=headers).status_code == 201
    assert client.post("/api/external-orders", json={**body, "platform": "walmart", "external_order_id": "x-1234"}, headers=headers).status_code == 422
    text = "Thank you for shopping at Flipkart\nOrder ID: OD123456789012\nOrder Date: 12 Oct 2026\nItem: Cotton T-shirt\nTotal Amount: ₹ 799.00"
    parsed = client.post("/api/external-orders/receipts/parse-text", json={"text": text}, headers=headers).json()
    assert parsed["parsed"]["platform"] == "flipkart" and parsed["parsed"]["total"] == 799.0
    up = client.post("/api/external-orders/receipts/parse", files={"file": ("r.txt", text.encode(), "text/plain")}, headers=headers)
    assert up.status_code == 200
    assert client.post("/api/external-orders/receipts/parse", files={"file": ("r.exe", b"x", "application/octet-stream")}, headers=headers).status_code == 415
    imp = client.post("/api/external-orders", json={"platform": "flipkart", "external_order_id": "OD123456789012", "order_date": "2026-10-12",
                                                    "total": "799", "currency": "INR", "product_name": "Cotton T-shirt",
                                                    "receipt_import_id": parsed["receipt_import_id"]}, headers=headers)
    assert imp.status_code == 201
    rows = client.get("/api/orders/unified", params={"platform": "flipkart"}, headers=headers).json()
    assert {r["import_source"] for r in rows} == {"manual", "receipt_upload"}
    assert all(r["tracking_info"] is None for r in rows)  # never invented
    assert len(client.get("/api/orders/unified", params={"q": "cotton"}, headers=headers).json()) == 1


def test_integrations_are_honest(client, auth):
    headers, _ = auth
    data = client.get("/api/integrations", headers=headers).json()
    amazon = next(p for p in data["platforms"] if p["platform"] == "amazon")
    assert amazon["status"] == "not_connected" and amazon["official_api"]["available"] is False
    assert data["email_import"]["available"] is False
    assert client.post("/api/integrations/amazon/connect", headers=headers).status_code == 201
    assert client.post("/api/integrations/amazon/connect", headers=headers).status_code == 409
    assert client.delete("/api/integrations/amazon", headers=headers).status_code == 204


def test_analytics_summary_endpoint(client, auth):
    headers, _ = auth
    for i, (plat, amt) in enumerate([("amazon", "1000"), ("flipkart", "500")]):
        client.post("/api/external-orders", json={"platform": plat, "external_order_id": f"ORD-{i}-{plat}", "order_date": "2026-11-02",
                                                  "total": amt, "currency": "INR", "product_name": "Thing"}, headers=headers)
    s = client.get("/api/analytics/summary", headers=headers).json()
    inr = s["by_currency"]["INR"]
    assert Decimal(inr["total"]) == 1500 and {p["platform"] for p in inr["by_platform"]} == {"amazon", "flipkart"}


def test_chat_with_mocked_gemini(client, auth, monkeypatch):
    from app.services import gemini_service as g
    headers, _ = auth
    calls = {"n": 0}

    def fake_extract(history, msg, prefs):
        calls["n"] += 1
        if "laptop" not in msg:
            return {"needs_clarification": True, "clarifying_question": "What product?", "search_query": None, "max_price": None,
                    "min_price": None, "currency": None, "brand": None, "category": None, "must_have": [], "preferences": [], "wants_comparison": False}
        return {"needs_clarification": False, "clarifying_question": None, "search_query": "laptop", "max_price": Decimal("600"),
                "min_price": None, "currency": "USD", "brand": None, "category": "Laptops", "must_have": [], "preferences": [], "wants_comparison": False}

    monkeypatch.setattr(g, "extract_requirements", fake_extract)
    monkeypatch.setattr(g, "rank_products", lambda msg, req, products: {
        "summary": "Best matches", "recommendations": [{"product_id": products[0]["id"], "why": "Fits budget", "pros": ["cheap"], "cons": []}]})
    r1 = client.post("/api/chat", json={"message": "hello"}, headers=headers).json()
    assert r1["needs_clarification"] is True and r1["products"] == []
    r2 = client.post("/api/chat", json={"message": "laptop under 600 dollars", "conversation_id": r1["conversation_id"]}, headers=headers).json()
    assert r2["products"] and r2["products"][0]["recommendation"]["why"] == "Fits budget"
    assert all(Decimal(p["price"]) <= 600 for p in r2["products"])
    conv = client.get(f"/api/chat/conversations/{r1['conversation_id']}", headers=headers).json()
    assert len(conv["messages"]) == 4
    prefs = {p["key"]: p["value"] for p in client.get("/api/users/me/preferences", headers=headers).json()}
    assert prefs["last_category"] == "Laptops"
    # explanation of a stored recommendation
    pid = r2["products"][0]["id"]
    monkeypatch.setattr(g, "explain_recommendation", lambda *a, **k: "Because it fits your budget.")
    assert client.post("/api/recommendations/explain", json={"product_id": pid}, headers=headers).json()["explanation"]
