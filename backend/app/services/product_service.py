from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Product, utcnow
from .product_provider import ProductData


def upsert_product(db: Session, data: ProductData) -> Product:
    p = db.scalar(select(Product).where(Product.provider == data.provider, Product.external_id == data.external_id))
    if p is None:
        p = Product(provider=data.provider, external_id=data.external_id)
        db.add(p)
    p.title, p.brand, p.category = data.title, data.brand, data.category
    p.image_url, p.product_url, p.merchant = data.image_url, data.product_url, data.merchant
    p.price, p.currency, p.availability = data.price, data.currency, data.availability
    p.rating, p.specs, p.is_fixture, p.fetched_at = data.rating, data.specs, data.is_fixture, utcnow()
    db.flush()
    return p


def product_to_dict(p: Product) -> dict:
    return {"id": p.id, "title": p.title, "brand": p.brand, "category": p.category, "image_url": p.image_url,
            "product_url": p.product_url, "merchant": p.merchant, "price": str(p.price), "currency": p.currency,
            "availability": p.availability, "rating": p.rating, "specs": p.specs or {}, "is_fixture": p.is_fixture}


def budget_for_provider(req: dict) -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    """Returns (max_price, min_price, note) in the PRODUCT provider's currency. Never invents an exchange rate."""
    s = get_settings()
    mx, mn, cur = req.get("max_price"), req.get("min_price"), (req.get("currency") or s.product_currency).upper()
    if mx is None and mn is None:
        return None, None, None
    if cur == s.product_currency.upper():
        return mx, mn, None
    if cur == "INR" and s.product_currency.upper() == "USD" and s.inr_per_usd:
        rate = Decimal(str(s.inr_per_usd))
        return (mx / rate if mx is not None else None), (mn / rate if mn is not None else None), \
            f"Budget converted from INR to {s.product_currency} at your configured rate of {rate} INR per USD."
    return None, None, (f"Your budget is in {cur} but results are priced in {s.product_currency} and no exchange rate is "
                        f"configured, so I could not apply the budget filter. Prices below are in {s.product_currency}.")
