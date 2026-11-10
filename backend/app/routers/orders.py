from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Order, User
from ..services.analytics_service import apply_filters
from ..services.order_service import load_unified_orders, unified_to_dict

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/unified")
def unified(platform: Optional[str] = None, q: Optional[str] = Query(None, max_length=100),
            date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orders = apply_filters(load_unified_orders(db, user.id), platform=platform, q=q, date_from=date_from, date_to=date_to)
    return [unified_to_dict(o) for o in orders]


@router.get("")
def list_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [unified_to_dict(o) for o in apply_filters(load_unified_orders(db, user.id), platform="cartpilot")]


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = db.get(Order, order_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(404, "Order not found")
    return {"id": o.id, "status": o.status, "total": str(o.total), "currency": o.currency,
            "created_at": o.created_at.isoformat(), "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "payment_status": o.payment.status if o.payment else None,
            "items": [{"title": i.title, "merchant": i.merchant, "unit_price": str(i.unit_price), "quantity": i.quantity,
                       "image_url": i.image_url} for i in o.items]}
