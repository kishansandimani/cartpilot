from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Product, User
from ..schemas import CompareIn
from ..services.product_service import product_to_dict

router = APIRouter(prefix="/api/compare", tags=["compare"])


def build_comparison(products: list[dict]) -> dict:
    """Side-by-side table built only from stored provider data. Missing values stay None (shown as 'not listed')."""
    rows = [
        {"label": "Price", "values": [f"{p['currency']} {p['price']}" for p in products]},
        {"label": "Merchant", "values": [p["merchant"] for p in products]},
        {"label": "Brand", "values": [p["brand"] for p in products]},
        {"label": "Category", "values": [p["category"] for p in products]},
        {"label": "Rating", "values": [p["rating"] for p in products]},
        {"label": "Availability", "values": [p["availability"] for p in products]},
    ]
    keys: list[str] = []
    for p in products:
        for k in (p["specs"] or {}):
            if k not in keys:
                keys.append(k)
    rows += [{"label": k, "values": [(p["specs"] or {}).get(k) for p in products]} for k in keys]
    same_cur = len({p["currency"] for p in products}) == 1
    cheapest = min(products, key=lambda p: float(p["price"]))["id"] if same_cur else None
    return {"products": products, "rows": rows, "cheapest_id": cheapest, "comparable_prices": same_cur}


@router.post("")
def compare(body: CompareIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = list(dict.fromkeys(body.product_ids))
    prods = [db.get(Product, i) for i in ids]
    if any(p is None for p in prods) or len(prods) < 2:
        raise HTTPException(404, "One or more products were not found")
    return build_comparison([product_to_dict(p) for p in prods])
