from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Product, ShoppingEvent, User
from ..services.product_provider import ProviderError, get_provider
from ..services.product_service import product_to_dict, upsert_product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=200), max_price: Optional[Decimal] = None,
           min_price: Optional[Decimal] = None, brand: Optional[str] = None, category: Optional[str] = None,
           limit: int = Query(12, ge=1, le=30), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        provider = get_provider()
        found = provider.search(f"{category} {q}".strip() if category else q, max_price=max_price,
                                min_price=min_price, brand=brand, limit=limit)
    except ProviderError as e:
        raise HTTPException(502, str(e))
    products = [upsert_product(db, d) for d in found]
    db.add(ShoppingEvent(user_id=user.id, event_type="search", payload={"q": q, "results": len(products)}))
    db.commit()
    return {"provider": provider.name, "is_fixture_data": provider.name == "fixtures",
            "products": [product_to_dict(p) for p in products]}


@router.get("/{product_id}")
def detail(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return product_to_dict(p)
