import uuid
from datetime import datetime, timezone
from backend.database.connection import async_session
from backend.database.models import InvoiceModel


async def create_invoice_record(order_id: str, amount: float) -> dict:
    invoice_id = f"INV-{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    async with async_session() as session:
        record = InvoiceModel(id=invoice_id, order_id=order_id, amount=amount, currency="INR", issued_at=now)
        session.add(record)
        await session.commit()
    return {"invoice_id": invoice_id, "order_id": order_id, "amount": amount, "currency": "INR", "issued_at": now}