from pydantic import BaseModel, Field
from typing import Optional


class CartItem(BaseModel):
    product_id: str
    name: str
    unit_price: float
    quantity: int = 1


class Cart(BaseModel):
    cart_id: str
    offer_id: str
    items: list[CartItem]
    subtotal: float
    shipping_cost: float = 0
    tax: float = 0
    discount: float = 0
    final_amount: float
    currency: str = "INR"
    shipping_address: Optional[dict] = None


class CartValidationResult(BaseModel):
    valid: bool
    reason: Optional[str] = None
    price_changed: bool = False
    original_price: Optional[float] = None
    current_price: Optional[float] = None
    out_of_stock_items: list[str] = Field(default_factory=list)