from pydantic import BaseModel
from datetime import datetime


class Order(BaseModel):
    order_id: str
    cart_id: str
    payment_id: str
    items: list[dict]
    final_amount: float
    currency: str = "INR"
    shipping_address: dict
    created_at: datetime


class Invoice(BaseModel):
    invoice_id: str
    order_id: str
    amount: float
    currency: str = "INR"
    issued_at: datetime