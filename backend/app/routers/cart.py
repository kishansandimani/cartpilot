from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CartItem, Product, ShoppingEvent, User
from ..schemas import CartAddIn, CartUpdateIn
from ..services import cart_service
from ..services.product_service import product_to_dict

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _out(cart) -> dict:
    s = cart_service.cart_summary(cart)
    return {"items": [{"id": i.id, "quantity": i.quantity, "product": product_to_dict(i.product)} for i in s["items"]],
            "totals": s["totals"], "currency": s["currency"], "total": s["total"],
            "mixed_currencies": s["mixed_currencies"], "item_count": s["item_count"]}


@router.get("")
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(cart_service.get_or_create_cart(db, user.id))


@router.post("/items", status_code=201)
def add_item(body: CartAddIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(Product, body.product_id) is None:
        raise HTTPException(404, "Product not found")
    cart_service.add_product(db, user.id, body.product_id, body.quantity)
    db.add(ShoppingEvent(user_id=user.id, event_type="add_to_cart", payload={"product_id": body.product_id}))
    db.commit()
    return _out(cart_service.get_or_create_cart(db, user.id))


def _own_item(db: Session, user: User, item_id: int) -> CartItem:
    cart = cart_service.get_or_create_cart(db, user.id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(404, "Cart item not found")
    return item


@router.patch("/items/{item_id}")
def update_item(item_id: int, body: CartUpdateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _own_item(db, user, item_id).quantity = body.quantity
    db.commit()
    return _out(cart_service.get_or_create_cart(db, user.id))


@router.delete("/items/{item_id}")
def remove_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_own_item(db, user, item_id))
    db.commit()
    return _out(cart_service.get_or_create_cart(db, user.id))


@router.delete("")
def clear_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = cart_service.get_or_create_cart(db, user.id)
    for i in list(cart.items):
        db.delete(i)
    db.commit()
    return _out(cart_service.get_or_create_cart(db, user.id))
