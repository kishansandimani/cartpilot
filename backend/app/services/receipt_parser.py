"""Best-effort receipt text parser. It only EXTRACTS what is written in the receipt; every field
that is not found stays None, and the user reviews the result before anything is saved."""
import html
import re
from datetime import datetime
from typing import Optional

PLATFORM_HINTS = {
    "amazon": ["amazon.in", "amazon.com", "amazon"],
    "flipkart": ["flipkart"],
    "myntra": ["myntra"],
    "ajio": ["ajio"],
}
CURRENCY_MAP = {"₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR", "$": "USD", "usd": "USD", "€": "EUR"}

AMOUNT_RE = re.compile(
    r"(?:grand\s*total|order\s*total|total\s*amount|amount\s*paid|total\s*paid|total)\s*[:\-]?\s*"
    r"(₹|rs\.?|inr|\$|usd|€)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
ORDER_ID_RES = [
    re.compile(r"\b(\d{3}-\d{7}-\d{7})\b"),  # Amazon style
    re.compile(r"order\s*(?:id|no\.?|number|#)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_]{5,30})", re.I),
]
TRACKING_RE = re.compile(r"(?:tracking|awb|consignment)\s*(?:id|no\.?|number)?\s*[:#\-]?\s*([A-Z0-9]{8,25})", re.I)
ITEM_RE = re.compile(r"(?:item|product|items?\s*ordered)\s*[:\-]\s*(.+)", re.I)
DATE_FORMATS = ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b, %Y"]
DATE_RES = [
    re.compile(r"\b(\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})\b"),
    re.compile(r"\b([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b"),
]


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"[ \t]+", " ", html.unescape(raw))


def _parse_date(text: str) -> Optional[str]:
    for rx in DATE_RES:
        for m in rx.finditer(text):
            candidate = m.group(1).replace(",", ", ").replace("  ", " ") if "," in m.group(1) and ", " not in m.group(1) else m.group(1)
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(candidate.strip(), fmt).date().isoformat()
                except ValueError:
                    continue
    return None


def detect_platform(text: str) -> Optional[str]:
    low = text.lower()
    for platform, hints in PLATFORM_HINTS.items():
        if any(h in low for h in hints):
            return platform
    return None


def parse_receipt_text(text: str) -> dict:
    text = html_to_text(text) if "<" in text and ">" in text else text
    result = {"platform": detect_platform(text), "external_order_id": None, "order_date": None, "total": None,
              "currency": None, "product_name": None, "tracking_info": None}
    for rx in ORDER_ID_RES:
        m = rx.search(text)
        if m:
            result["external_order_id"] = m.group(1)
            break
    amounts = AMOUNT_RE.findall(text)
    if amounts:
        cur, num = amounts[-1]  # the last "Total"-like line is usually the grand total
        try:
            result["total"] = float(num.replace(",", ""))
            result["currency"] = CURRENCY_MAP.get(cur.lower()) if cur else None
        except ValueError:
            pass
    result["order_date"] = _parse_date(text)
    m = TRACKING_RE.search(text)
    if m:
        result["tracking_info"] = m.group(1)
    m = ITEM_RE.search(text)
    if m:
        result["product_name"] = m.group(1).strip()[:300]
    found = sum(1 for k in ("external_order_id", "order_date", "total", "product_name") if result[k])
    result["confidence"] = "high" if found >= 4 else "medium" if found >= 2 else "low"
    return result
