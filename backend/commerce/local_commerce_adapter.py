import uuid
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.connection import async_session
from backend.database.models import ProductModel, CartModel, CartItemModel, OrderModel
from backend.commerce.commerce_service import CommerceService


class LocalCommerceAdapter(CommerceService):
    """Our own lightweight commerce backend, backed by SQLite.
    Plays the exact role Medusa would have — agents never know the difference."""

    async def search_products(self, category: str, max_price: float, filters: dict) -> list[dict]:
        async with async_session() as session:
            type: AsyncSession
            query = select(ProductModel)
            if category:
                query = query.where(ProductModel.category == category)
            if max_price:
                query = query.where(ProductModel.price <= max_price)
            result = await session.execute(query)
            products = result.scalars().all()
            return [self._to_dict(p) for p in products]

    async def get_product(self, product_id: str) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(ProductModel).where(ProductModel.id == product_id)
            )
            product = result.scalar_one_or_none()
            return self._to_dict(product) if product else None

    async def check_inventory(self, product_id: str) -> int:
        product = await self.get_product(product_id)
        return product["stock"] if product else 0

    async def create_cart(self, product_id: str, quantity: int) -> dict:
        async with async_session() as session:
            product = await self.get_product(product_id)
            cart_id = str(uuid.uuid4())
            cart = CartModel(id=cart_id)
            session.add(cart)
            await session.flush()

            item = CartItemModel(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
                unit_price_at_add=product["price"],
            )
            session.add(item)
            await session.commit()
            return await self.get_cart(cart_id)

    async def get_cart(self, cart_id: str) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(CartModel).where(CartModel.id == cart_id)
            )
            cart = result.scalar_one_or_none()
            if not cart:
                return None
            items_result = await session.execute(
                select(CartItemModel).where(CartItemModel.cart_id == cart_id)
            )
            items = items_result.scalars().all()
            return {
                "cart_id": cart.id,
                "session_id": cart.session_id,
                "status": cart.status,
                "shipping_address": json.loads(cart.shipping_address) if cart.shipping_address else None,
                "items": [
                    {
                        "product_id": i.product_id,
                        "quantity": i.quantity,
                        "unit_price": i.unit_price_at_add,
                    }
                    for i in items
                ],
            }

    async def add_line_item(self, cart_id: str, product_id: str, quantity: int) -> dict:
        async with async_session() as session:
            product = await self.get_product(product_id)
            item = CartItemModel(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
                unit_price_at_add=product["price"],
            )
            session.add(item)
            await session.commit()
            return await self.get_cart(cart_id)

    async def create_cart_with_frozen_price(self, product_id: str, quantity: int, unit_price: float, session_id: str | None = None) -> dict:
        async with async_session() as session:
            cart_id = str(uuid.uuid4())
            cart = CartModel(id=cart_id, session_id=session_id)
            session.add(cart)
            await session.flush()
            item = CartItemModel(
                cart_id=cart_id, product_id=product_id,
                quantity=quantity, unit_price_at_add=unit_price,
            )
            session.add(item)
            await session.commit()
            return await self.get_cart(cart_id)

        
    async def add_line_item_frozen_price(self, cart_id: str, product_id: str, quantity: int, unit_price: float) -> dict:
        async with async_session() as session:
            item = CartItemModel(
                cart_id=cart_id, product_id=product_id,
                quantity=quantity, unit_price_at_add=unit_price,
            )
            session.add(item)
            await session.commit()
            return await self.get_cart(cart_id)

    async def set_shipping_address(self, cart_id: str, address: dict) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(CartModel).where(CartModel.id == cart_id)
            )
            cart = result.scalar_one_or_none()
            cart.shipping_address = json.dumps(address)
            await session.commit()
            return await self.get_cart(cart_id)

    async def complete_cart(self, cart_id: str) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(CartModel).where(CartModel.id == cart_id)
            )
            cart = result.scalar_one_or_none()
            cart.status = "completed"
            await session.commit()
            return {"cart_id": cart_id, "status": "completed"}

    def _to_dict(self, p: ProductModel) -> dict:
        if not p:
            return None
        return {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "brand": p.brand,
            "spec_summary": p.spec_summary,
            "price": p.price,
            "stock": p.stock,
            "cpu": p.cpu,
            "gpu": p.gpu,
            "ram_gb": p.ram_gb,
            "storage": p.storage,
            "refresh_rate_hz": p.refresh_rate_hz,
            "return_days": p.return_days,
            "warranty_years": p.warranty_years,
            "delivery_days": p.delivery_days,

        }