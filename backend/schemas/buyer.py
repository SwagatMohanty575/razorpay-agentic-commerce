from pydantic import BaseModel, Field
from typing import Optional


NO_BUDGET_LIMIT = 10_000_000  
# ₹1 crore — safely above the whole catalog; used instead of
# float("inf") because infinity isn't valid JSON and crashes
# # response serialization.


class ConstraintSet(BaseModel):
    category: str
    budget_max: float
    currency: str = "INR"
    use_case: Optional[str] = None
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)


class BuyerIntent(BaseModel):
    raw_query: str
    constraints: ConstraintSet
    session_id: str


class ShippingAddress(BaseModel):
    name: str
    address_line: str
    city: str
    state: str
    pincode: str
    country: str = "IN"