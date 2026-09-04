from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.database.connection import init_db
from backend.commerce.local_commerce_adapter import LocalCommerceAdapter
from backend.api import buyer_routes, merchant_routes, checkout_routes, audit_routes

app = FastAPI(title="Agentic Commerce — Merchant & Buyer Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(buyer_routes.router, prefix="/buyer", tags=["buyer"])
app.include_router(merchant_routes.router, prefix="/merchant", tags=["merchant"])
app.include_router(checkout_routes.router, prefix="/checkout", tags=["checkout"])
app.include_router(audit_routes.router, prefix="/audit", tags=["audit"])


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/commerce")
async def health_commerce():
    adapter = LocalCommerceAdapter()
    products = await adapter.search_products(category="", max_price=float("inf"), filters={})
    return {"commerce_reachable": True, "product_count": len(products)}


@app.get("/debug/products")
async def debug_products(category: str = "", max_price: float = 10000000):
    adapter = LocalCommerceAdapter()
    products = await adapter.search_products(category=category, max_price=max_price, filters={})
    return {"count": len(products), "products": products}


class ProductUpdateRequest(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None


@app.patch("/debug/products/{product_id}")
async def debug_update_product(product_id: str, request: ProductUpdateRequest):
    from sqlalchemy import select
    from backend.database.connection import async_session
    from backend.database.models import ProductModel

    async with async_session() as session:
        result = await session.execute(select(ProductModel).where(ProductModel.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            return {"error": "Product not found"}
        if request.price is not None:
            product.price = request.price
        if request.stock is not None:
            product.stock = request.stock
        await session.commit()
        return {"updated": product_id, "price": product.price, "stock": product.stock}