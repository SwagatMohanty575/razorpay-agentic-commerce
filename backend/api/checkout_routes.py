from fastapi import APIRouter
from pydantic import BaseModel
from backend.commerce.local_commerce_adapter import LocalCommerceAdapter
from backend.commerce.offer_store import get_offer
from backend.commerce.order_store import create_order_record
from backend.commerce.invoice_store import create_invoice_record
from backend.policy.policy_engine import PolicyEngine
from backend.payments.razorpay_adapter import RazorpayAdapter
from backend.payments.payment_store import create_payment_record, update_payment_status, get_payment
from backend.audit.audit_logger import log_event
from backend.schemas.cart import CartValidationResult
from backend.schemas.buyer import ShippingAddress
from backend.config import settings
from sqlalchemy import select
from backend.database.connection import async_session
from backend.database.models import OrderModel, InvoiceModel, CartItemModel, ProductModel
import json

router = APIRouter()
commerce = LocalCommerceAdapter()
policy_engine = PolicyEngine()
razorpay_adapter = RazorpayAdapter()


class CreateCartRequest(BaseModel):
    offer_id: str
    session_id: str
    selected_addon_ids: list[str] = []
    shipping_address: ShippingAddress


@router.post("/cart")
async def create_cart(request: CreateCartRequest):
    offer = await get_offer(request.offer_id)
    if not offer:
        return {"error": "Offer not found."}
    if offer["is_expired"]:
        await log_event(
            request.session_id, "system", "CART_CREATION_BLOCKED",
            f"offer_id={request.offer_id}", "blocked", "Offer expired before cart creation", "blocked",
            related_entity_id=request.offer_id,
        )
        return {"error": "Offer has expired. Please request a fresh quote.", "expired_at": offer["expires_at"]}

    cart = await commerce.create_cart_with_frozen_price(
        offer["product_id"], quantity=1, unit_price=offer["base_price"], session_id=request.session_id
    )
    cart_id = cart["cart_id"]

    for addon in offer["addons"]:
        if addon["product_id"] in request.selected_addon_ids:
            await commerce.add_line_item_frozen_price(cart_id, addon["product_id"], quantity=1, unit_price=addon["price"])

    await commerce.set_shipping_address(cart_id, request.shipping_address.model_dump())
    final_cart = await commerce.get_cart(cart_id)

    await log_event(
        request.session_id, "system", "CART_CREATED",
        f"offer_id={request.offer_id}, addons={request.selected_addon_ids}",
        "created", f"Cart created with {len(final_cart['items'])} item(s)", "success",
        related_entity_id=cart_id,
    )
    return final_cart


async def _validate_cart_internal(cart_id: str):
    cart = await commerce.get_cart(cart_id)
    if not cart:
        return None, {"error": "Cart not found."}

    out_of_stock = []
    price_changed = False
    original_total, current_total = 0.0, 0.0

    for item in cart["items"]:
        product = await commerce.get_product(item["product_id"])
        if not product or product["stock"] < item["quantity"]:
            out_of_stock.append(item["product_id"])

        original_total += item["unit_price"] * item["quantity"]
        current_price = product["price"] if product else item["unit_price"]
        current_total += current_price * item["quantity"]

        if product and product["price"] != item["unit_price"]:
            price_changed = True

    valid = not out_of_stock and not price_changed
    result = CartValidationResult(
        valid=valid,
        reason=None if valid else _build_invalid_reason(price_changed, out_of_stock, original_total, current_total),
        price_changed=price_changed,
        original_price=round(original_total, 2) if price_changed else None,
        current_price=round(current_total, 2) if price_changed else None,
        out_of_stock_items=out_of_stock,
    )
    return result, None


def _build_invalid_reason(price_changed, out_of_stock, original_total, current_total) -> str:
    parts = []
    if price_changed:
        parts.append(f"Price changed from ₹{original_total:.0f} to ₹{current_total:.0f}")
    if out_of_stock:
        parts.append(f"Out of stock: {', '.join(out_of_stock)}")
    return "; ".join(parts)


@router.post("/validate/{cart_id}")
async def validate_cart(cart_id: str):
    cart = await commerce.get_cart(cart_id)
    if not cart:
        return {"error": "Cart not found."}
    result, error = await _validate_cart_internal(cart_id)
    if error:
        return error

    await log_event(
        cart["session_id"], "system", "CART_VALIDATED",
        f"cart_id={cart_id}", "valid" if result.valid else "invalid",
        result.reason or "Cart matches quoted price and available stock",
        "success" if result.valid else "failure",
        related_entity_id=cart_id,
    )
    return result


class AuthorizeRequest(BaseModel):
    cart_id: str


@router.post("/authorize")
async def authorize(request: AuthorizeRequest):
    cart = await commerce.get_cart(request.cart_id)
    if not cart:
        return {"error": "Cart not found."}

    validation, error = await _validate_cart_internal(request.cart_id)
    if error:
        return error
    if not validation.valid:
        await log_event(
            cart["session_id"], "policy_engine", "AUTHORIZATION_BLOCKED",
            f"cart_id={request.cart_id}", "blocked", validation.reason, "blocked",
            related_entity_id=request.cart_id,
        )
        return {"error": "Cart failed revalidation — cannot authorize payment.", "validation": validation}

    final_amount = round(sum(item["unit_price"] * item["quantity"] for item in cart["items"]), 2)
    auth = policy_engine.evaluate(request.cart_id, final_amount)

    await log_event(
        cart["session_id"], "policy_engine", "AUTHORIZATION_EVALUATED",
        f"cart_id={request.cart_id}, amount={final_amount}",
        auth.level.value, auth.reason, "success" if auth.approved else "blocked",
        policy_evaluated="amount_threshold_policy", financial_amount=final_amount,
        related_entity_id=request.cart_id,
    )
    return auth


class ConfirmRequest(BaseModel):
    cart_id: str
    user_confirmed: bool


@router.post("/confirm")
async def confirm(request: ConfirmRequest):
    cart = await commerce.get_cart(request.cart_id)
    if not cart:
        return {"error": "Cart not found."}
    final_amount = round(sum(item["unit_price"] * item["quantity"] for item in cart["items"]), 2)
    auth = policy_engine.confirm(request.cart_id, final_amount, request.user_confirmed)

    await log_event(
        cart["session_id"], "system", "USER_AUTHORIZATION",
        f"cart_id={request.cart_id}, user_confirmed={request.user_confirmed}",
        auth.level.value, auth.reason, "success" if auth.approved else "blocked",
        financial_amount=final_amount, related_entity_id=request.cart_id,
    )
    return auth


class InitiatePaymentRequest(BaseModel):
    cart_id: str


@router.post("/initiate-payment")
async def initiate_payment(request: InitiatePaymentRequest):
    cart = await commerce.get_cart(request.cart_id)
    if not cart:
        return {"error": "Cart not found."}

    validation, error = await _validate_cart_internal(request.cart_id)
    if error:
        return error
    if not validation.valid:
        return {"error": "Cart failed revalidation — cannot initiate payment.", "validation": validation}

    final_amount = round(sum(item["unit_price"] * item["quantity"] for item in cart["items"]), 2)
    razorpay_order = razorpay_adapter.create_order(final_amount, receipt=request.cart_id)
    payment_id = await create_payment_record(request.cart_id, final_amount, razorpay_order["id"])

    await log_event(
        cart["session_id"], "system", "PAYMENT_INITIATED",
        f"cart_id={request.cart_id}, amount={final_amount}",
        "initiated", f"Razorpay order {razorpay_order['id']} created for ₹{final_amount}", "success",
        financial_amount=final_amount, related_entity_id=razorpay_order["id"],
    )

    return {
        "payment_id": payment_id,
        "razorpay_order_id": razorpay_order["id"],
        "amount": final_amount,
        "amount_paise": razorpay_order["amount"],
        "currency": "INR",
        "razorpay_key_id": settings.razorpay_key_id,
    }


class VerifyPaymentRequest(BaseModel):
    payment_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/verify-payment")
async def verify_payment(request: VerifyPaymentRequest):
    payment = await get_payment(request.payment_id)
    if not payment:
        return {"success": False, "reason": "Payment record not found."}

    cart = await commerce.get_cart(payment["cart_id"])
    session_id = cart["session_id"] if cart else "unknown"

    is_valid = razorpay_adapter.verify_signature(
        request.razorpay_order_id, request.razorpay_payment_id, request.razorpay_signature
    )

    if not is_valid:
        await update_payment_status(request.payment_id, status="failed", failure_reason="Signature verification failed")
        await log_event(
            session_id, "system", "PAYMENT_VERIFIED",
            f"payment_id={request.payment_id}", "failed",
            "Signature verification failed — payment cannot be trusted, no order created", "failure",
            related_entity_id=request.payment_id,
        )
        return {"success": False, "reason": "Signature verification failed. No order was created."}

    await update_payment_status(request.payment_id, status="success", razorpay_payment_id=request.razorpay_payment_id)
    await log_event(
        session_id, "system", "PAYMENT_VERIFIED",
        f"payment_id={request.payment_id}", "success", "Signature verified successfully", "success",
        financial_amount=payment["amount"], related_entity_id=request.payment_id,
    )

    await commerce.complete_cart(payment["cart_id"])
    order = await create_order_record(
        cart_id=payment["cart_id"], payment_id=request.payment_id,
        items=cart["items"], final_amount=payment["amount"],
        shipping_address=cart["shipping_address"],
    )
    await log_event(
        session_id, "system", "ORDER_CREATED",
        f"cart_id={payment['cart_id']}", "created", f"Order {order['order_id']} created", "success",
        financial_amount=payment["amount"], related_entity_id=order["order_id"],
    )

    invoice = await create_invoice_record(order["order_id"], payment["amount"])
    await log_event(
        session_id, "system", "INVOICE_GENERATED",
        f"order_id={order['order_id']}", "generated", f"Invoice {invoice['invoice_id']} issued", "success",
        financial_amount=payment["amount"], related_entity_id=invoice["invoice_id"],
    )

    itemized = []
    for item in order["items"]:
        product = await commerce.get_product(item["product_id"])
        itemized.append({
            "product_id": item["product_id"],
            "name": product["name"] if product else item["product_id"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "line_total": round(item["unit_price"] * item["quantity"], 2),
        })

    return {
        "success": True,
        "order": order,
        "invoice": {**invoice, "items": itemized},
    }


class PaymentFailedRequest(BaseModel):
    payment_id: str
    reason: str = "Payment declined at bank/checkout step."


@router.post("/payment-failed")
async def payment_failed(request: PaymentFailedRequest):
    updated = await update_payment_status(request.payment_id, status="failed", failure_reason=request.reason)
    if not updated:
        return {"error": "Payment record not found."}

    cart = await commerce.get_cart(updated["cart_id"])
    session_id = cart["session_id"] if cart else "unknown"

    await log_event(
        session_id, "system", "PAYMENT_FAILED",
        f"payment_id={request.payment_id}", "failed", request.reason, "failure",
        financial_amount=updated["amount"], related_entity_id=request.payment_id,
    )

    return {
        "success": False,
        "payment_id": request.payment_id,
        "status": "failed",
        "message": "Payment did not go through. No order was created. You can try again or choose a different payment method.",
    }



@router.get("/orders")
async def list_orders():
    async with async_session() as session:
        result = await session.execute(select(OrderModel).order_by(OrderModel.created_at.desc()))
        orders = result.scalars().all()

        out = []
        for o in orders:
            inv_res = await session.execute(select(InvoiceModel).where(InvoiceModel.order_id == o.id))
            inv = inv_res.scalar_one_or_none()

            items_res = await session.execute(select(CartItemModel).where(CartItemModel.cart_id == o.cart_id))
            items = []
            for it in items_res.scalars().all():
                p_res = await session.execute(select(ProductModel).where(ProductModel.id == it.product_id))
                p = p_res.scalar_one_or_none()
                items.append({
                    "product_id": it.product_id,
                    "name": p.name if p else it.product_id,
                    "quantity": it.quantity,
                    "unit_price": it.unit_price_at_add,
                    "line_total": round(it.unit_price_at_add * it.quantity, 2),
                })

            out.append({
                "order_id": o.id,
                "created_at": o.created_at,
                "final_amount": o.final_amount,
                "shipping_address": json.loads(o.shipping_address) if o.shipping_address else {},
                "items": items,
                "invoice": {
                    "invoice_id": inv.id if inv else None,
                    "amount": inv.amount if inv else o.final_amount,
                    "issued_at": inv.issued_at if inv else o.created_at,
                    "items": items,
                },
            })
        return {"count": len(out), "orders": out}