"""Tests that need no database or network."""
from datetime import datetime, timezone
from decimal import Decimal

from app.services.analytics_service import UnifiedOrder, apply_filters, compute_analytics
from app.services.receipt_parser import parse_receipt_text
from app.services.voice_command_service import parse_command


def mk(platform, amount, date, status="delivered", cat=None, cur="INR", title="Item"):
    return UnifiedOrder(source="external", row_id=1, platform=platform, order_id=f"{platform}-{amount}-{date}", order_date=date,
                        amount=Decimal(amount), currency=cur, status=status, payment_method=None, tracking_info=None,
                        import_source="manual", items=[{"title": title, "image_url": None, "category": cat, "price": Decimal(amount), "quantity": 1}])


def test_analytics_totals_monthly_platform_category():
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    orders = [mk("amazon", "1000", datetime(2026, 11, 2), cat="Electronics"), mk("flipkart", "500", datetime(2026, 10, 5), cat="Fashion"),
              mk("amazon", "250", datetime(2026, 11, 8), cat="Electronics"), mk("amazon", "9999", datetime(2026, 11, 9), status="cancelled"),
              mk("cartpilot", "20", datetime(2026, 11, 3), cur="USD")]
    r = compute_analytics(orders, now)["by_currency"]
    assert r["INR"]["total"] == "1750" and r["INR"]["this_month"] == "1250" and r["INR"]["order_count"] == 3
    assert {m["month"]: m["amount"] for m in r["INR"]["monthly"]} == {"2026-10": "500", "2026-11": "1250"}
    assert r["INR"]["by_platform"][0] == {"platform": "amazon", "amount": "1250"}
    assert {c["category"]: c["amount"] for c in r["INR"]["by_category"]} == {"Electronics": "1250", "Fashion": "500"}
    assert r["USD"]["total"] == "20"  # currencies are never mixed


def test_filters_search_and_dates():
    orders = [mk("amazon", "10", datetime(2026, 1, 1), title="Blue Mouse"), mk("myntra", "20", datetime(2026, 6, 1), title="Red Shirt")]
    assert [o.platform for o in apply_filters(orders, platform="myntra")] == ["myntra"]
    assert [o.platform for o in apply_filters(orders, q="mouse")] == ["amazon"]
    assert [o.platform for o in apply_filters(orders, date_from=datetime(2026, 3, 1))] == ["myntra"]
    assert len(apply_filters(orders, platform="all")) == 2


def test_receipt_parser_extracts_only_what_is_present():
    r = parse_receipt_text("Your Amazon.in order\nOrder # 402-1234567-7654321\nOrdered on 5 October 2026\nGrand Total: Rs. 1,499.00\nTracking ID: TBA123456789")
    assert (r["platform"], r["external_order_id"], r["total"], r["currency"], r["order_date"]) == ("amazon", "402-1234567-7654321", 1499.0, "INR", "2026-10-05")
    assert r["tracking_info"] == "TBA123456789"
    empty = parse_receipt_text("hello there, nothing useful in this text at all")
    assert empty["external_order_id"] is None and empty["total"] is None and empty["confidence"] == "low"


def test_voice_parser_core_commands():
    cases = {"Open shopping assistant": "/assistant", "open my cart": "/cart", "Show my orders": "/orders",
             "Go to my profile": "/settings", "Open connected platforms": "/platforms", "Show my Amazon purchases": "/orders?platform=amazon"}
    for text, path in cases.items():
        p = parse_command(text)
        assert p.intent == "navigate" and p.params["path"] == path, text
    assert parse_command("Add the second product to my cart").params["index"] == 1
    assert parse_command("Remove the headphones from my cart").params["name"] == "headphones"
    assert parse_command("Compare these two laptops").intent == "compare"
    assert parse_command("How much did I spend this month?").params["period"] == "month"
    assert parse_command("Buy this product").intent == "buy"
    assert parse_command("कार्ट खोलो").language == "hi" and parse_command("ಕಾರ್ಟ್ ತೆರೆ").language == "kn"
