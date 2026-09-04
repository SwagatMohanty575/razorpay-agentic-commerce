from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductSpecs(BaseModel):
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    ram_gb: Optional[int] = None
    storage: Optional[str] = None
    refresh_rate_hz: Optional[int] = None


class Product(BaseModel):
    id: str
    name: str
    category: str
    specs: ProductSpecs = Field(default_factory=ProductSpecs)


class RecommendedAddon(BaseModel):
    product_id: str
    name: str
    price: float
    stock: int
    reason: str

class BundleSuggestion(BaseModel):
    addon_ids: list[str]
    items: list[RecommendedAddon]
    bundle_total: float
    combined_total: float
    reason: str


class UpsellSuggestion(BaseModel):
    product_id: str
    name: str
    price: float
    price_diff: float
    reason: str


class OfferDiscount(BaseModel):
    type: str
    bank: Optional[str] = None
    discount: float
    min_amount: Optional[float] = None
    valid_until: Optional[str] = None


class PaymentOptions(BaseModel):
    upi: bool = True
    card: bool = True
    netbanking: bool = True
    emi: list[str] = Field(default_factory=list)


class MerchantReasoning(BaseModel):
    customer_fit: float
    inventory_priority: float
    margin_score: float


class MerchantOffer(BaseModel):
    offer_id: str
    generated_at: datetime
    expires_at: datetime
    currency: str = "INR"
    product: Product
    base_price: float
    available_stock: int
    fit_score: float
    delivery_estimated_days: int
    return_days: int
    warranty_years: int
    recommended_addons: list[RecommendedAddon] = Field(default_factory=list)
    payment_options: PaymentOptions
    offers: list[OfferDiscount] = Field(default_factory=list)
    merchant_reasoning: Optional[MerchantReasoning] = None
    bundle_suggestion: Optional[BundleSuggestion] = None
    upsell_suggestion: Optional[UpsellSuggestion] = None

