from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.agents.buyer_agent import BuyerAgent
from backend.agents.merchant_agent import MerchantAgent
from backend.schemas.buyer import ConstraintSet
from backend.audit.audit_logger import log_event
from sqlalchemy import select
from backend.database.connection import async_session
from backend.database.models import OrderModel, CartItemModel, ProductModel, AuditEventModel
from backend.policy.guardrails import check_query

router = APIRouter()
buyer_agent = BuyerAgent()
merchant_agent = MerchantAgent()


class OffersRequest(BaseModel):
    query: Optional[str] = None
    constraints: Optional[ConstraintSet] = None
    session_id: Optional[str] = None


@router.post("/offers")
async def get_offers(request: OffersRequest):
    if request.constraints:
        constraints = request.constraints
    elif request.query:
        allowed, reason = check_query(request.query)
        if not allowed:
            return {"blocked": True, "reason": reason}
        intent = await buyer_agent.understand_intent(request.query, request.session_id)
        constraints = intent.constraints
        request.session_id = intent.session_id
    else:
        return {"error": "Provide either 'query' or 'constraints'."}

    offers, growth_decisions = await merchant_agent.generate_offers(constraints, session_id=request.session_id)

    session_id = request.session_id or "unknown"
    await log_event(
        session_id, "merchant_agent", "PRODUCTS_SHORTLISTED",
        f"category={constraints.category}, budget_max={constraints.budget_max}",
        "shortlisted", f"{len(offers)} offer(s) generated within constraints", "success",
    )
    for gd in growth_decisions:
        await log_event(
            session_id, "growth_engine", "GROWTH_RECOMMENDATION_CREATED",
            f"product_id={gd.product_id}", gd.decision_type, gd.reason, "success",
            related_entity_id=gd.product_id,
        )

    return {
        "session_id": session_id,
        "constraints_used": constraints,
        "offer_count": len(offers),
        "offers": offers,
        "growth_decisions": growth_decisions,
    }

@router.get("/dashboard")
async def merchant_dashboard():
    """Read-only merchant view. Baseline AOV = base product revenue only;
    actual AOV includes everything the Growth Engine added. The gap is the
    measured uplift, computed from real orders — not projected."""
    async with async_session() as session:
        orders_result = await session.execute(
            select(OrderModel).order_by(OrderModel.created_at.desc())
        )
        orders = orders_result.scalars().all()

        order_count = len(orders)
        total_revenue = sum(o.final_amount for o in orders)
        aov = total_revenue / order_count if order_count else 0.0

        base_revenue = addon_revenue = 0.0
        orders_with_addons = 0
        recent = []

        for idx, o in enumerate(orders):
            items_result = await session.execute(
                select(CartItemModel).where(CartItemModel.cart_id == o.cart_id)
            )
            items = items_result.scalars().all()

            order_base = order_addon = 0.0
            detail = []
            for it in items:
                p_result = await session.execute(
                    select(ProductModel).where(ProductModel.id == it.product_id)
                )
                p = p_result.scalar_one_or_none()
                line = it.unit_price_at_add * it.quantity
                is_base = bool(p and p.category == "laptop")
                if is_base:
                    order_base += line
                else:
                    order_addon += line
                detail.append({
                    "name": p.name if p else it.product_id,
                    "category": p.category if p else "unknown",
                    "line_total": round(line, 2),
                    "is_addon": not is_base,
                })

            base_revenue += order_base
            addon_revenue += order_addon
            if order_addon > 0:
                orders_with_addons += 1

            if idx < 10:
                recent.append({
                    "order_id": o.id,
                    "created_at": o.created_at,
                    "final_amount": round(o.final_amount, 2),
                    "base_revenue": round(order_base, 2),
                    "addon_revenue": round(order_addon, 2),
                    "items": detail,
                })

        ge_result = await session.execute(
            select(AuditEventModel).where(
                AuditEventModel.action == "GROWTH_RECOMMENDATION_CREATED"
            )
        )
        ge_events = ge_result.scalars().all()

        blocked_result = await session.execute(
            select(AuditEventModel).where(AuditEventModel.result == "blocked")
        )
        blocked_count = len(blocked_result.scalars().all())

        baseline_aov = (base_revenue / order_count) if order_count else 0.0
        aov_uplift = ((aov - baseline_aov) / baseline_aov * 100) if baseline_aov else 0.0

        return {
            "order_count": order_count,
            "total_revenue": round(total_revenue, 2),
            "aov": round(aov, 2),
            "baseline_aov": round(baseline_aov, 2),
            "aov_uplift_pct": round(aov_uplift, 1),
            "base_revenue": round(base_revenue, 2),
            "addon_revenue": round(addon_revenue, 2),
            "attach_rate_pct": round(orders_with_addons / order_count * 100, 1) if order_count else 0.0,
            "growth_recommendations": {
                "cross_sell": sum(1 for e in ge_events if e.decision == "cross_sell"),
                "upsell": sum(1 for e in ge_events if e.decision == "upsell"),
                "promotion": sum(1 for e in ge_events if e.decision == "promotion"),
                "total": len(ge_events),
            },
            "blocked_actions": blocked_count,
            "recent_orders": recent,
        }