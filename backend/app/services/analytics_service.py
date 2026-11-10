"""Pure functions (no database) that filter and summarise orders. Easy to unit-test."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

CANCELLED = {"cancelled", "canceled", "returned", "refunded", "failed", "pending_payment"}


@dataclass
class UnifiedOrder:
    source: str                 # "cartpilot" | "external"
    row_id: int
    platform: str               # cartpilot | amazon | flipkart | myntra | ajio | other
    order_id: str
    order_date: datetime
    amount: Decimal
    currency: str
    status: Optional[str]
    payment_method: Optional[str]
    tracking_info: Optional[str]
    import_source: str          # paypal_checkout | manual | receipt_upload | email
    items: list[dict] = field(default_factory=list)   # {title, image_url, category, price, quantity}

    @property
    def product_name(self) -> str:
        if not self.items:
            return "(no item details)"
        extra = len(self.items) - 1
        return self.items[0]["title"] + (f" + {extra} more" if extra else "")

    @property
    def image_url(self) -> Optional[str]:
        return self.items[0].get("image_url") if self.items else None

    def counts_as_spend(self) -> bool:
        return (self.status or "").lower() not in CANCELLED


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def apply_filters(orders: list[UnifiedOrder], *, platform: Optional[str] = None, q: Optional[str] = None,
                  date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> list[UnifiedOrder]:
    out = []
    for o in orders:
        if platform and platform != "all" and o.platform != platform:
            continue
        if date_from and _aware(o.order_date) < _aware(date_from):
            continue
        if date_to and _aware(o.order_date) > _aware(date_to):
            continue
        if q:
            needle = q.lower()
            hay = " ".join([o.order_id, o.platform, *(i["title"] for i in o.items)]).lower()
            if needle not in hay:
                continue
        out.append(o)
    return sorted(out, key=lambda o: _aware(o.order_date), reverse=True)


def _category_split(o: UnifiedOrder) -> dict[str, Decimal]:
    priced = [(i.get("category") or "Uncategorized", Decimal(str(i["price"])) * i.get("quantity", 1))
              for i in o.items if i.get("price") is not None]
    if not priced:
        cat = (o.items[0].get("category") if o.items else None) or "Uncategorized"
        return {cat: o.amount}
    res: dict[str, Decimal] = defaultdict(Decimal)
    for cat, amt in priced:
        res[cat] += amt
    leftover = o.amount - sum(res.values())
    if leftover > Decimal("0.01"):
        res["Uncategorized"] += leftover
    return dict(res)


def compute_analytics(orders: list[UnifiedOrder], now: Optional[datetime] = None) -> dict:
    """Totals are kept per currency because we never convert currencies with invented rates."""
    now = now or datetime.now(timezone.utc)
    this_month = now.strftime("%Y-%m")
    by_cur: dict[str, dict] = {}
    for o in orders:
        if not o.counts_as_spend():
            continue
        d = by_cur.setdefault(o.currency, {"total": Decimal("0"), "this_month": Decimal("0"), "order_count": 0,
                                           "monthly": defaultdict(Decimal), "by_platform": defaultdict(Decimal),
                                           "by_category": defaultdict(Decimal)})
        month = _aware(o.order_date).strftime("%Y-%m")
        d["total"] += o.amount
        d["order_count"] += 1
        d["monthly"][month] += o.amount
        d["by_platform"][o.platform] += o.amount
        if month == this_month:
            d["this_month"] += o.amount
        for cat, amt in _category_split(o).items():
            d["by_category"][cat] += amt

    def fmt(d: dict) -> dict:
        return {
            "total": str(d["total"]), "this_month": str(d["this_month"]), "order_count": d["order_count"],
            "monthly": [{"month": m, "amount": str(a)} for m, a in sorted(d["monthly"].items())],
            "by_platform": [{"platform": p, "amount": str(a)} for p, a in sorted(d["by_platform"].items(), key=lambda x: -x[1])],
            "by_category": [{"category": c, "amount": str(a)} for c, a in sorted(d["by_category"].items(), key=lambda x: -x[1])],
        }

    recent = sorted(orders, key=lambda o: _aware(o.order_date), reverse=True)[:5]
    return {
        "by_currency": {cur: fmt(d) for cur, d in by_cur.items()},
        "recent": [{"platform": o.platform, "order_id": o.order_id, "product_name": o.product_name,
                    "amount": str(o.amount), "currency": o.currency, "order_date": o.order_date.isoformat()} for o in recent],
        "total_orders": len(orders),
    }
