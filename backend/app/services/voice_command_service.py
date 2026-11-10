"""Understands voice/text commands and executes them.

parse_command()  - pure Python, no database. Decides WHAT the user wants.
execute_command() - runs it against the database and tells the frontend what to do.

Safety rules baked in:
 * Every command needs a logged-in user (the route requires a JWT).
 * "buy / checkout" NEVER creates or captures a payment. It only returns the order summary and asks the user
   to confirm on screen; PayPal approval happens in the PayPal popup.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .voice_service import detect_language, page_name, t

NAV_TARGETS: list[tuple[str, str, list[str]]] = [
    # (target, path, keywords) - longer phrases first so they win
    ("platforms", "/platforms", ["connected platforms", "platforms", "integrations", "प्लेटफॉर्म", "प्लेटफ़ॉर्म", "ಪ್ಲಾಟ್‌ಫಾರ್ಮ್"]),
    ("assistant", "/assistant", ["shopping assistant", "ai assistant", "assistant", "copilot", "असिस्टेंट", "सहायक", "ಸಹಾಯಕ"]),
    ("memory", "/memory", ["shopping memory", "memory", "preferences", "मेमोरी", "ಮೆಮೊರಿ"]),
    ("insights", "/insights", ["spending insights", "insights", "analytics", "इनसाइट", "ಒಳನೋಟ"]),
    ("discover", "/discover", ["discover products", "discover", "browse products", "डिस्कवर"]),
    ("compare", "/compare", ["compare products", "comparison page", "compare"]),
    ("orders", "/orders", ["shopping history", "purchase history", "order history", "orders", "order", "purchases", "ऑर्डर", "आर्डर", "ಆರ್ಡರ್"]),
    ("profile", "/settings", ["my profile", "profile", "settings", "my account", "प्रोफाइल", "प्रोफ़ाइल", "सेटिंग", "ಪ್ರೊಫೈಲ್", "ಸೆಟ್ಟಿಂಗ್"]),
    ("cart", "/cart", ["my cart", "cart", "basket", "कार्ट", "ಕಾರ್ಟ್"]),
    ("overview", "/", ["overview", "dashboard", "home page", "home", "ओवरव्यू", "ಅವಲೋಕನ"]),
]
NAV_VERBS = ["open", "go to", "goto", "take me to", "navigate", "switch to", "show me", "show my", "show", "खोलो", "खोलें", "खोल", "दिखाओ", "दिखाएं", "दिखाइए", "जाओ", "ತೆರೆ", "ತೋರಿಸು", "ಹೋಗು"]
PLATFORMS = {"amazon": ["amazon", "अमेज़न", "अमेजन", "ಅಮೆಜಾನ್"], "flipkart": ["flipkart", "फ्लिपकार्ट", "ಫ್ಲಿಪ್‌ಕಾರ್ಟ್"],
             "myntra": ["myntra", "मिंत्रा"], "ajio": ["ajio", "अजियो"], "cartpilot": ["cartpilot", "cart pilot"]}
CART_WORDS = ["cart", "basket", "कार्ट", "ಕಾರ್ಟ್"]
ORDINALS = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "fourth": 3, "4th": 3, "fifth": 4, "5th": 4,
            "last": -1, "पहला": 0, "पहले": 0, "पहली": 0, "दूसरा": 1, "दूसरे": 1, "तीसरा": 2, "तीसरे": 2,
            "ಮೊದಲ": 0, "ಮೊದಲನೇ": 0, "ಎರಡನೇ": 1, "ಮೂರನೇ": 2}


@dataclass
class ParsedCommand:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    language: str = "en"
    original: str = ""


def normalize(text: str) -> str:
    text = text.lower().replace("₹", " rs ")
    text = re.sub(r"[^\w\s\u0900-\u097F\u0C80-\u0CFF\u200c\u200d.-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has(text: str, words: list[str]) -> bool:
    for w in words:
        if re.search(r"[^\x00-\x7f]", w):
            if w in text:
                return True
        elif re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text):
            return True
    return False


def _ordinals(text: str) -> list[int]:
    found: list[tuple[int, int]] = []
    for word, idx in ORDINALS.items():
        for m in re.finditer(re.escape(word), text):
            found.append((m.start(), idx))
    for m in re.finditer(r"(?:number|no\.?|item|product)\s*(\d)", text):
        found.append((m.start(), int(m.group(1)) - 1))
    return [i for _, i in sorted(found)]


def _nav_target(text: str) -> Optional[tuple[str, str]]:
    for target, path, words in NAV_TARGETS:
        if _has(text, words):
            return target, path
    return None


def parse_command(text: str, language_hint: str = "en") -> ParsedCommand:
    original = text.strip()
    lang = detect_language(original, language_hint)
    n = normalize(original)
    P = lambda intent, **params: ParsedCommand(intent, params, lang, original)  # noqa: E731
    if not n:
        return P("empty")

    # 1) BUY - always only a request for confirmation
    if re.search(r"\b(buy|checkout|check out|pay for|place (?:the |my )?order|order this|purchase this|pay now)\b", n) \
            or any(w in n for w in ["खरीद", "ಖರೀದಿ"]):
        return P("buy")

    has_cart = _has(n, CART_WORDS)
    ords = _ordinals(n)

    # 2) remove from cart
    if _has(n, ["remove", "delete", "हटा", "हटाओ", "ತೆಗೆ"]) and has_cart:
        m = re.search(r"(?:remove|delete)\s+(?:the\s+|my\s+)?(.+?)\s+from", n)
        name = m.group(1).strip() if m else None
        if name in ("it", "this", "that", "item"):
            name = None
        return P("remove_from_cart", name=name, index=ords[0] if ords else None)

    # 3) add to cart
    if (_has(n, ["add", "जोड़", "जोड़ो", "ಸೇರಿಸು"]) and (has_cart or "to cart" in n)):
        return P("add_to_cart", index=ords[0] if ords else None)

    # 4) cart total
    if has_cart and _has(n, ["total", "value", "how much", "worth", "कुल", "ಒಟ್ಟು"]):
        return P("cart_total")

    # 5) spending
    if _has(n, ["spend", "spent", "spending", "खर्च", "ಖರ್ಚು"]) or "how much did" in n:
        period = "month" if _has(n, ["month", "महीन", "महीने", "ತಿಂಗಳ"]) else "year" if _has(n, ["year", "साल", "ವರ್ಷ"]) else "all"
        return P("spending", period=period)

    # 6) track order
    if _has(n, ["track", "ट्रैक", "ಟ್ರ್ಯಾಕ್"]):
        return P("track_order")

    # 7) platform purchases ("show my amazon purchases")
    for platform, words in PLATFORMS.items():
        if _has(n, words) and _has(n, ["order", "orders", "purchase", "purchases", "bought", "ऑर्डर", "ಆರ್ಡರ್", "history"]):
            return P("navigate", target="orders", path=f"/orders?platform={platform}")

    # 8) compare
    if _has(n, ["compare", "comparison", "तुलना", "ಹೋಲಿಸ"]):
        refs = _has(n, ["these", "this", "them", "both", "two", "vs", "versus", "with", "first", "second", "third"]) or len(ords) >= 2
        nav_verb = _has(n, NAV_VERBS)
        if not (nav_verb and not refs):
            return P("compare", indexes=ords)

    # 9) cheaper alternatives
    if _has(n, ["cheaper", "less expensive", "alternative", "alternatives", "सस्ता", "सस्ते", "ಅಗ್ಗ"]):
        return P("cheaper", index=ords[0] if ords else None)

    # 10) explain recommendation
    if re.search(r"\b(why did you recommend|why recommend|explain why|explain this|why this)\b", n) or _has(n, ["क्यों", "ಏಕೆ"]):
        return P("explain", index=ords[0] if ords else None)

    # 11) navigation
    target = _nav_target(n)
    short = len(n.split()) <= 3
    if target and (_has(n, NAV_VERBS) or short):
        return P("navigate", target=target[0], path=target[1])

    # 12) search / suggestions
    if _has(n, ["find", "search", "look for", "looking for", "get me", "show me", "i need", "i want", "suggest", "recommend",
                "खोज", "ढूंढ", "ढूँढ", "चाहिए", "ಹುಡುಕ", "ಬೇಕು"]):
        return P("search_products", query=original)

    # 13) anything else goes to the AI assistant as a normal chat message
    return P("chat", query=original)


# ------------------------------------------------------------------ execution
def execute_command(db, user, parsed: ParsedCommand, context: dict) -> dict:
    """Returns {"intent","language","speech","action","requires_confirmation"}. `action` tells the frontend what to do."""
    from decimal import Decimal

    from sqlalchemy import select

    from ..models import AIRecommendation, Product
    from . import cart_service
    from .analytics_service import apply_filters, compute_analytics
    from .order_service import load_unified_orders

    lang = parsed.language
    last_ids: list[int] = [int(i) for i in (context.get("last_product_ids") or []) if str(i).isdigit()]

    def pick(index: Optional[int]) -> Optional[int]:
        if index is None:
            return last_ids[0] if len(last_ids) == 1 else (context.get("selected_product_id") or None)
        try:
            return last_ids[index]
        except IndexError:
            return None

    def done(speech: str, action: Optional[dict] = None, confirm: bool = False) -> dict:
        return {"intent": parsed.intent, "language": lang, "speech": speech, "action": action or {"type": "none"},
                "requires_confirmation": confirm}

    it = parsed.intent
    if it == "empty":
        return done("")
    if it == "navigate":
        page = page_name(parsed.params["target"], lang)
        return done(t("navigate", lang, page=page), {"type": "navigate", "path": parsed.params["path"]})
    if it in ("search_products", "chat"):
        return done(t("searching" if it == "search_products" else "thinking", lang),
                    {"type": "assistant_query", "query": parsed.params["query"], "path": "/assistant"})

    if it == "add_to_cart":
        pid = pick(parsed.params.get("index"))
        product = db.get(Product, pid) if pid else None
        if product is None:
            return done(t("need_product", lang))
        cart_service.add_product(db, user.id, product.id, 1)
        return done(t("added", lang, title=product.title[:60]), {"type": "cart_updated"})

    if it == "remove_from_cart":
        cart = cart_service.get_or_create_cart(db, user.id)
        name, idx = parsed.params.get("name"), parsed.params.get("index")
        target = None
        if name:
            words = [w for w in name.split() if len(w) > 2]
            target = next((i for i in cart.items if all(w.rstrip("s") in i.product.title.lower() for w in words)), None) \
                or next((i for i in cart.items if any(w.rstrip("s") in i.product.title.lower() for w in words)), None)
        elif idx is not None and cart.items:
            try:
                target = cart.items[idx]
            except IndexError:
                target = None
        elif len(cart.items) == 1:
            target = cart.items[0]
        if target is None:
            return done(t("not_in_cart", lang))
        title = target.product.title[:60]
        db.delete(target)
        db.commit()
        return done(t("removed", lang, title=title), {"type": "cart_updated"})

    if it == "cart_total":
        s = cart_service.cart_summary(cart_service.get_or_create_cart(db, user.id))
        if not s["item_count"]:
            return done(t("cart_empty", lang))
        total = f"{s['currency']} {s['total']}" if s["currency"] else ", ".join(f"{c} {v}" for c, v in s["totals"].items())
        return done(t("cart_total", lang, total=total, count=s["item_count"]), {"type": "navigate", "path": "/cart"})

    if it == "buy":
        s = cart_service.cart_summary(cart_service.get_or_create_cart(db, user.id))
        if not s["item_count"]:
            return done(t("cart_empty", lang))
        total = f"{s['currency']} {s['total']}" if s["currency"] else "mixed currencies"
        # NO payment is created here. The cart page shows the summary + explicit confirm button.
        return done(t("confirm_purchase", lang, total=total),
                    {"type": "confirm_purchase", "path": "/cart?review=1"}, confirm=True)

    if it == "spending":
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        period = parsed.params.get("period", "all")
        orders = load_unified_orders(db, user.id)
        label = {"month": "this month", "year": "this year", "all": "in total"}[period]
        if period == "month":
            orders = apply_filters(orders, date_from=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
        elif period == "year":
            orders = apply_filters(orders, date_from=now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
        stats = compute_analytics(orders, now)["by_currency"]
        if not stats:
            return done(t("no_spend", lang, period=label), {"type": "navigate", "path": "/insights"})
        amount = ", ".join(f"{cur} {Decimal(v['total']):,.2f}" for cur, v in stats.items())
        return done(t("spent", lang, amount=amount, period=label), {"type": "navigate", "path": "/insights"})

    if it == "track_order":
        orders = load_unified_orders(db, user.id)
        latest = apply_filters(orders)[:1]
        if not latest:
            return done(t("no_orders", lang))
        o = latest[0]
        tracking = f"Tracking: {o.tracking_info}." if o.tracking_info else "No verified tracking information is available."
        return done(t("track", lang, platform=o.platform, product=o.product_name[:60], status=o.status or "unknown", tracking=tracking),
                    {"type": "navigate", "path": "/orders"})

    if it == "compare":
        idxs = parsed.params.get("indexes") or []
        ids = [last_ids[i] for i in idxs if -len(last_ids) <= i < len(last_ids)] if idxs else last_ids[:3]
        if len(ids) < 2:
            return done(t("need_two", lang))
        return done(t("compare", lang), {"type": "navigate", "path": "/compare?ids=" + ",".join(map(str, ids))})

    if it == "cheaper":
        pid = pick(parsed.params.get("index")) or (last_ids[0] if last_ids else None)
        product = db.get(Product, pid) if pid else None
        if product is None:
            return done(t("need_product", lang))
        q = f"cheaper alternatives to {product.title} under {product.currency} {product.price}"
        return done(t("cheaper", lang), {"type": "assistant_query", "query": q, "path": "/assistant"})

    if it == "explain":
        pid = pick(parsed.params.get("index")) or (last_ids[0] if last_ids else None)
        rec = db.scalar(select(AIRecommendation).where(AIRecommendation.user_id == user.id,
                                                       AIRecommendation.product_id == pid)
                        .order_by(AIRecommendation.id.desc())) if pid else None
        if rec is None or not rec.reason:
            return done(t("no_reason", lang))
        return done(rec.reason, {"type": "none"})

    return done(t("thinking", lang), {"type": "assistant_query", "query": parsed.original, "path": "/assistant"})
