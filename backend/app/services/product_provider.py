"""Product discovery adapters.

Channel3 integration follows https://docs.trychannel3.com :
  POST {base}/v1/search   header: x-api-key   body: {"query", "limit", "filters": {"price": {...}}}
  GET  {base}/v1/products/{id}
Prices and buy links live in product["offers"][] (not on the product itself).
To add another authorized provider, subclass ProductProvider and register it in get_provider().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

from ..config import get_settings


class ProviderError(Exception):
    """Raised when the product provider cannot be used (missing key, network error...)."""


@dataclass
class ProductData:
    external_id: str
    title: str
    price: Decimal
    currency: str
    provider: str
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    merchant: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    specs: dict = field(default_factory=dict)
    is_fixture: bool = False


class ProductProvider(ABC):
    name = "base"

    @abstractmethod
    def search(self, query: str, *, max_price: Optional[Decimal] = None, min_price: Optional[Decimal] = None,
               brand: Optional[str] = None, limit: int = 8) -> list[ProductData]: ...

    @abstractmethod
    def get(self, external_id: str) -> Optional[ProductData]: ...


# ---------------------------------------------------------------- Channel3
def _to_decimal(value: Any) -> Optional[Decimal]:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def parse_channel3_product(p: dict) -> Optional[ProductData]:
    """Turns one Channel3 product JSON object into ProductData. Returns None if it has no usable price."""
    offers = p.get("offers") or []
    best = None
    for offer in offers:
        price_obj = offer.get("price") or {}
        # docs show both {"amount": ..} and {"price": ..}; accept either
        amount = _to_decimal(price_obj.get("amount", price_obj.get("price")))
        if amount is None:
            continue
        in_stock = (offer.get("availability") or "InStock") == "InStock"
        key = (not in_stock, amount)  # prefer in-stock, then cheapest
        if best is None or key < best[0]:
            best = (key, offer, amount, price_obj.get("currency"))
    if best is None or not p.get("id") or not p.get("title"):
        return None
    _, offer, amount, currency = best

    image = p.get("image_url")
    images = p.get("images") or p.get("image_urls") or []
    if not image and images:
        first = images[0]
        image = first.get("url") if isinstance(first, dict) else first

    brand = p.get("brand_name")
    if not brand and isinstance(p.get("brand"), dict):
        brand = p["brand"].get("name")

    category = None
    cats = p.get("categories") or []
    if cats:
        c = cats[-1]
        category = c.get("title") if isinstance(c, dict) else str(c)

    specs: dict = {}
    if p.get("key_features"):
        specs["Key features"] = "; ".join(str(x) for x in p["key_features"][:6])
    if p.get("materials"):
        specs["Materials"] = ", ".join(str(x) for x in p["materials"])
    if p.get("description"):
        specs["Description"] = str(p["description"])[:400]

    return ProductData(
        external_id=str(p["id"]), title=p["title"], price=amount,
        currency=(currency or get_settings().product_currency).upper(), provider="channel3",
        brand=brand, category=category, image_url=image, product_url=offer.get("url"),
        merchant=offer.get("domain"), availability=offer.get("availability"),
        rating=None,  # Channel3 does not provide ratings; we never invent one
        specs=specs,
    )


class Channel3Provider(ProductProvider):
    name = "channel3"

    def __init__(self):
        s = get_settings()
        if not s.channel3_api_key:
            raise ProviderError("CHANNEL3_API_KEY is not set. Add it to backend/.env (or set PRODUCT_PROVIDER=fixtures for dev data).")
        self.base = s.channel3_base_url.rstrip("/")
        self.headers = {"x-api-key": s.channel3_api_key, "Content-Type": "application/json"}

    def search(self, query, *, max_price=None, min_price=None, brand=None, limit=8):
        body: dict = {"query": f"{brand} {query}".strip() if brand else query, "limit": limit}
        price = {}
        if min_price is not None:
            price["min_price"] = float(min_price)
        if max_price is not None:
            price["max_price"] = float(max_price)
        if price:
            body["filters"] = {"price": price}
        try:
            r = httpx.post(f"{self.base}/v1/search", json=body, headers=self.headers, timeout=25)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"Channel3 search failed: {e}") from e
        out = []
        for raw in r.json().get("products", []):
            parsed = parse_channel3_product(raw)
            if parsed:
                out.append(parsed)
        return out

    def get(self, external_id):
        try:
            r = httpx.get(f"{self.base}/v1/products/{external_id}", headers=self.headers, timeout=25)
            if r.status_code == 404:
                return None
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ProviderError(f"Channel3 product lookup failed: {e}") from e
        return parse_channel3_product(r.json())


# ---------------------------------------------------------------- Dev fixtures
_FIXTURES = [
    ("fx-laptop-1", "DEV FIXTURE Laptop A (16GB RAM, 512GB SSD)", "FixtureBrand", "Laptops", "499.00", {"RAM": "16 GB", "Storage": "512 GB SSD"}),
    ("fx-laptop-2", "DEV FIXTURE Laptop B (8GB RAM, 256GB SSD)", "FixtureBrand", "Laptops", "349.00", {"RAM": "8 GB", "Storage": "256 GB SSD"}),
    ("fx-laptop-3", "DEV FIXTURE Laptop C (32GB RAM, 1TB SSD)", "OtherBrand", "Laptops", "899.00", {"RAM": "32 GB", "Storage": "1 TB SSD"}),
    ("fx-phones-1", "DEV FIXTURE Phone A (128GB)", "FixtureBrand", "Phones", "299.00", {"Storage": "128 GB"}),
    ("fx-phones-2", "DEV FIXTURE Phone B (256GB)", "OtherBrand", "Phones", "449.00", {"Storage": "256 GB"}),
    ("fx-audio-1", "DEV FIXTURE Wireless Headphones", "FixtureBrand", "Headphones", "39.00", {"Type": "Over-ear, Bluetooth"}),
    ("fx-audio-2", "DEV FIXTURE Wireless Earbuds", "OtherBrand", "Headphones", "24.00", {"Type": "In-ear, Bluetooth"}),
]


class FixtureProvider(ProductProvider):
    """Clearly-labelled fake data for development ONLY. Titles start with 'DEV FIXTURE'."""
    name = "fixtures"

    def _all(self) -> list[ProductData]:
        cur = get_settings().product_currency
        return [ProductData(external_id=i, title=t, price=Decimal(p), currency=cur, provider="fixtures", brand=b,
                            category=c, merchant="DEV FIXTURE (not a real merchant)", availability="InStock",
                            product_url=None, image_url=None, specs=s, is_fixture=True)
                for i, t, b, c, p, s in _FIXTURES]

    def search(self, query, *, max_price=None, min_price=None, brand=None, limit=8):
        words = [w for w in query.lower().split() if len(w) > 2]
        res = []
        for p in self._all():
            hay = f"{p.title} {p.category} {p.brand}".lower()
            if words and not any(w.rstrip("s") in hay for w in words):
                continue
            if max_price is not None and p.price > max_price:
                continue
            if min_price is not None and p.price < min_price:
                continue
            if brand and brand.lower() not in (p.brand or "").lower():
                continue
            res.append(p)
        return res[:limit]

    def get(self, external_id):
        return next((p for p in self._all() if p.external_id == external_id), None)


def get_provider() -> ProductProvider:
    name = get_settings().product_provider.lower()
    if name == "fixtures":
        return FixtureProvider()
    if name == "channel3":
        return Channel3Provider()
    raise ProviderError(f"Unknown PRODUCT_PROVIDER '{name}'")
