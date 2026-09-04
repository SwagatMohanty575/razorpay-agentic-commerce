import json
import uuid
from datetime import datetime, timezone
from backend.database.connection import async_session
from backend.database.models import OrderModel


async def create_order_record(
    cart_id: str, payment_id: str, items: list[dict], final_amount: float, shipping_address: dict
) -> dict:
    order_id = f"ORD-{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    async with async_session() as session:
        record = OrderModel(
            id=order_id, cart_id=cart_id, payment_id=payment_id,
            final_amount=final_amount, shipping_address=json.dumps(shipping_address),
            created_at=now,
        )
        session.add(record)
        await session.commit()
    return {
        "order_id": order_id, "cart_id": cart_id, "payment_id": payment_id,
        "items": items, "final_amount": final_amount,
        "shipping_address": shipping_address, "created_at": now,
    }