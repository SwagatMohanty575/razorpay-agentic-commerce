from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PaymentStatus(str, Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class AuthorizationLevel(str, Enum):
    AUTO_APPROVED = "auto_approved"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
    EXPLICIT_AUTH_REQUIRED = "explicit_auth_required"
    DENIED = "denied"


class Authorization(BaseModel):
    cart_id: str
    amount: float
    level: AuthorizationLevel
    approved: bool
    reason: str


class Payment(BaseModel):
    payment_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    cart_id: str
    amount: float
    currency: str = "INR"
    status: PaymentStatus
    failure_reason: Optional[str] = None