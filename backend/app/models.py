"""Database tables. One class = one table."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation", order_by="ChatMessage.id",
                                                         cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Product(Base):
    """A product returned by a provider. Prices are copied from the provider, never invented."""
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(500))
    brand: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merchant: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8))
    availability: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    specs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Order(Base):
    """A CartPilot purchase paid through PayPal."""
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending_payment")  # pending_payment|paid|failed|cancelled|refunded
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    merchant: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(16), default="paypal")
    paypal_order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    paypal_capture_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="created")  # created|completed|failed|refunded|denied
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    order: Mapped[Order] = relationship(back_populates="payment")


class WebhookEvent(Base):
    """Remembers PayPal webhook event ids so the same event is never processed twice."""
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    event_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    integration_type: Mapped[str] = mapped_column(String(32))  # manual_receipts | official_api | email
    status: Mapped[str] = mapped_column(String(24), default="active")
    permissions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    encrypted_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Fernet-encrypted, never plain text
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReceiptImport(Base):
    __tablename__ = "receipt_imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(24), default="upload")
    status: Mapped[str] = mapped_column(String(16), default="parsed")  # parsed | confirmed
    parsed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExternalOrder(Base):
    """An order made on another store (Amazon, Flipkart...). Imported by the user, never scraped."""
    __tablename__ = "external_orders"
    __table_args__ = (UniqueConstraint("user_id", "platform", "external_order_id", name="uq_external_order"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    external_order_id: Mapped[str] = mapped_column(String(128))
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    tracking_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    import_source: Mapped[str] = mapped_column(String(24), default="manual")  # manual | receipt_upload | email
    receipt_import_id: Mapped[Optional[int]] = mapped_column(ForeignKey("receipt_imports.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    items: Mapped[list["ExternalOrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class ExternalOrderItem(Base):
    __tablename__ = "external_order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("external_orders.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    order: Mapped[ExternalOrder] = relationship(back_populates="items")


class ShoppingEvent(Base):
    __tablename__ = "shopping_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pros: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    cons: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
