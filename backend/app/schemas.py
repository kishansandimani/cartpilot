from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

PLATFORMS = ("amazon", "flipkart", "myntra", "ajio", "other")


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    preferred_language: str
    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    preferred_language: Optional[str] = Field(default=None, pattern="^(en|hi|kn)$")


class PreferenceIn(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    value: str = Field(min_length=1, max_length=500)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = None


class CartAddIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=20)


class CartUpdateIn(BaseModel):
    quantity: int = Field(ge=1, le=20)


class CompareIn(BaseModel):
    product_ids: list[int] = Field(min_length=2, max_length=4)


class CreateOrderIn(BaseModel):
    confirmed: bool = False  # the user must explicitly confirm the order summary


class CaptureIn(BaseModel):
    paypal_order_id: str = Field(min_length=5, max_length=64)


class VoiceCommandIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    language: str = Field(default="en", pattern="^(en|hi|kn)$")
    context: dict[str, Any] = Field(default_factory=dict)


class ExplainIn(BaseModel):
    product_id: int


class ManualOrderIn(BaseModel):
    platform: str
    external_order_id: str = Field(min_length=3, max_length=128)
    order_date: date
    total: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    product_name: str = Field(min_length=1, max_length=500)
    category: Optional[str] = Field(default=None, max_length=120)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=40)
    payment_method: Optional[str] = Field(default=None, max_length=60)
    tracking_info: Optional[str] = Field(default=None, max_length=255)
    receipt_import_id: Optional[int] = None

    @field_validator("platform")
    @classmethod
    def _platform(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in PLATFORMS:
            raise ValueError(f"platform must be one of {', '.join(PLATFORMS)}")
        return v

    @field_validator("currency")
    @classmethod
    def _cur(cls, v: str) -> str:
        return v.upper()

    @field_validator("external_order_id")
    @classmethod
    def _oid(cls, v: str) -> str:
        return v.strip()


class ReceiptTextIn(BaseModel):
    text: str = Field(min_length=10, max_length=200_000)
