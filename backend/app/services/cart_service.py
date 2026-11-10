from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Cart, CartItem, Product


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items).selectinload(CartItem.product)))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_product(db: Session, user_id: int, product_id: int, quantity: int = 1) -> CartItem:
    product = db.get(Product, product_id)
    if product is None:
        raise ValueError("Product not found")
    cart = get_or_create_cart(db, user_id)
    item = next((i for i in cart.items if i.product_id == product_id), None)
    if item:
        item.quantity = min(item.quantity + quantity, 20)
    else:
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=min(quantity, 20))
        db.add(item)
    db.commit()
    return item


def cart_summary(cart: Cart) -> dict:
    """Totals per currency; a cart mixing currencies cannot be checked out (no invented FX rates)."""
    totals: dict[str, Decimal] = {}
    for i in cart.items:
        totals[i.product.currency] = totals.get(i.product.currency, Decimal("0")) + i.product.price * i.quantity
    currencies = list(totals)
    return {
        "items": cart.items,
        "totals": {c: str(t) for c, t in totals.items()},
        "currency": currencies[0] if len(currencies) == 1 else None,
        "total": str(totals[currencies[0]]) if len(currencies) == 1 else None,
        "mixed_currencies": len(currencies) > 1,
        "item_count": sum(i.quantity for i in cart.items),
    }
