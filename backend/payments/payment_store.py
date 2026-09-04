import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from backend.database.connection import async_session
from backend.database.models import PaymentModel


async def create_payment_record(cart_id: str, amount: float, razorpay_order_id: str) -> str:
    payment_id = f"PAY-{uuid.uuid4().hex[:10]}"
    async with async_session() as session:
        record = PaymentModel(
            id=payment_id, cart_id=cart_id, razorpay_order_id=razorpay_order_id,
            amount=amount, currency="INR", status="initiated",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(record)
        await session.commit()
    return payment_id


async def update_payment_status(
    payment_id: str, status: str, razorpay_payment_id: str | None = None, failure_reason: str | None = None
) -> dict | None:
    async with async_session() as session:
        result = await session.execute(select(PaymentModel).where(PaymentModel.id == payment_id))
        record = result.scalar_one_or_none()
        if not record:
            return None
        record.status = status
        if razorpay_payment_id:
            record.razorpay_payment_id = razorpay_payment_id
        if failure_reason:
            record.failure_reason = failure_reason
        await session.commit()
        return await get_payment(payment_id)


async def get_payment(payment_id: str) -> dict | None:
    async with async_session() as session:
        result = await session.execute(select(PaymentModel).where(PaymentModel.id == payment_id))
        record = result.scalar_one_or_none()
        if not record:
            return None
        return {
            "payment_id": record.id, "cart_id": record.cart_id,
            "razorpay_order_id": record.razorpay_order_id,
            "razorpay_payment_id": record.razorpay_payment_id,
            "amount": record.amount, "currency": record.currency,
            "status": record.status, "failure_reason": record.failure_reason,
        }