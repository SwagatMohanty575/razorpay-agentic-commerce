from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.connection import Base


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=True, index=True)
    spec_summary: Mapped[str] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)

    cpu: Mapped[str] = mapped_column(String, nullable=True)
    gpu: Mapped[str] = mapped_column(String, nullable=True)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=True)
    storage: Mapped[str] = mapped_column(String, nullable=True)
    refresh_rate_hz: Mapped[int] = mapped_column(Integer, nullable=True)

    return_days: Mapped[int] = mapped_column(Integer, default=7)
    warranty_years: Mapped[int] = mapped_column(Integer, default=1)
    delivery_days: Mapped[int] = mapped_column(Integer, default=3)


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    offer_id: Mapped[str] = mapped_column(String, nullable=True)
    session_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    shipping_address: Mapped[str] = mapped_column(String, nullable=True)  # JSON string
    status: Mapped[str] = mapped_column(String, default="active")

    items: Mapped[list["CartItemModel"]] = relationship(back_populates="cart")


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id"))
    product_id: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_at_add: Mapped[float] = mapped_column(Float)

    cart: Mapped["CartModel"] = relationship(back_populates="items")


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cart_id: Mapped[str] = mapped_column(String)
    payment_id: Mapped[str] = mapped_column(String)
    final_amount: Mapped[float] = mapped_column(Float)
    shipping_address: Mapped[str] = mapped_column(String)  # JSON string
    created_at: Mapped[str] = mapped_column(String)

class OfferModel(Base):
    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # offer_id
    session_id: Mapped[str] = mapped_column(String, nullable=True)
    product_id: Mapped[str] = mapped_column(String)
    base_price: Mapped[float] = mapped_column(Float)
    addons_json: Mapped[str] = mapped_column(String, default="[]")
    expires_at: Mapped[str] = mapped_column(String)

class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cart_id: Mapped[str] = mapped_column(String)
    razorpay_order_id: Mapped[str] = mapped_column(String, nullable=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="INR")
    status: Mapped[str] = mapped_column(String, default="initiated")
    failure_reason: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String)


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="INR")
    issued_at: Mapped[str] = mapped_column(String)


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String)
    session_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    input_summary: Mapped[str] = mapped_column(String)
    decision: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    policy_evaluated: Mapped[str] = mapped_column(String, nullable=True)
    financial_amount: Mapped[float] = mapped_column(Float, nullable=True)
    related_entity_id: Mapped[str] = mapped_column(String, nullable=True)
    result: Mapped[str] = mapped_column(String)