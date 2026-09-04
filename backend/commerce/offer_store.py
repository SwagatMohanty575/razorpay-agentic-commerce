import json
from datetime import datetime, timezone
from sqlalchemy import select
from backend.database.connection import async_session
from backend.database.models import OfferModel
from backend.schemas.merchant import MerchantOffer


async def save_offer(offer: MerchantOffer, session_id: str | None = None) -> None:
    async with async_session() as session:
        addons = [
            {"product_id": a.product_id, "name": a.name, "price": a.price}
            for a in offer.recommended_addons
        ]
        record = OfferModel(
            id=offer.offer_id,
            session_id=session_id,
            product_id=offer.product.id,
            base_price=offer.base_price,
            addons_json=json.dumps(addons),
            expires_at=offer.expires_at.isoformat(),
        )
        session.add(record)
        await session.commit()


async def get_offer(offer_id: str) -> dict | None:
    async with async_session() as session:
        result = await session.execute(select(OfferModel).where(OfferModel.id == offer_id))
        record = result.scalar_one_or_none()
        if not record:
            return None
        expires_at = datetime.fromisoformat(record.expires_at)
        is_expired = datetime.now(timezone.utc) > expires_at
        return {
            "offer_id": record.id,
            "product_id": record.product_id,
            "base_price": record.base_price,
            "addons": json.loads(record.addons_json),
            "expires_at": record.expires_at,
            "is_expired": is_expired,
        }