"""
Baseline vs AI-assisted revenue evaluation. Every number below comes from
running synthetic buyer queries through the REAL MerchantAgent + GrowthEngine
against your seeded catalog — nothing is fabricated.

Two documented assumptions fill gaps where no real order history exists yet:
  1. Addon attach probability = the same co-purchase rate the Growth Engine
     itself cites to justify the recommendation (analytics_data.py).
  2. Upsell acceptance probability = 15% (UPSELL_ACCEPTANCE_RATE below) —
     a conservative placeholder since there's no real upsell history yet.
     Change this constant if you want to defend a different number.

Run from project root:
    python -m backend.evaluation.evaluate_growth_engine
"""
import asyncio
from backend.agents.merchant_agent import MerchantAgent
from backend.commerce.local_commerce_adapter import LocalCommerceAdapter
from backend.growth_engine.analytics_data import CO_PURCHASE_RATES, DISCOUNT_CONVERSION_MODEL
from backend.schemas.buyer import ConstraintSet

UPSELL_ACCEPTANCE_RATE = 0.15
BASELINE_CONVERSION = DISCOUNT_CONVERSION_MODEL[0.0]

# Fixed synthetic buyer population so results are reproducible run to run.
SYNTHETIC_BUYERS = [
    ConstraintSet(category="laptop", budget_max=b, hard_constraints=[f"budget <= {b}"], soft_preferences=p)
    for b, p in [
        (50000, []), (55000, ["gaming"]), (60000, []), (65000, ["high performance"]),
        (70000, ["heavy-duty"]), (75000, []), (80000, ["gaming"]), (90000, []),
        (100000, ["high performance"]), (120000, []), (45000, []), (52000, []),
        (68000, ["gaming"]), (72000, []), (95000, []), (58000, ["heavy-duty"]),
        (63000, []), (110000, []), (47000, []), (85000, ["gaming"]),
    ]
]


async def addon_attach_rate(addon_product_id: str) -> float:
    commerce = LocalCommerceAdapter()
    product = await commerce.get_product(addon_product_id)
    if not product:
        return 0.0
    for entry in CO_PURCHASE_RATES.get("laptop", []):
        if entry["addon_category"] == product["category"]:
            return entry["rate"]
    return 0.0


async def evaluate():
    merchant_agent = MerchantAgent()

    baseline_total = ai_assisted_total = total_discount_cost = 0.0
    orders_evaluated = cross_sell_offered = upsell_offered = 0

    for i, constraints in enumerate(SYNTHETIC_BUYERS):
        offers, _ = await merchant_agent.generate_offers(constraints, session_id=f"eval-{i}")
        if not offers:
            continue

        top_offer = offers[0]  # highest fit_score — what the buyer agent would actually pick
        orders_evaluated += 1

        # Baseline: no growth engine, flat conversion, base price only.
        baseline_total += top_offer.base_price * BASELINE_CONVERSION

        # AI-assisted: promotion-adjusted conversion + expected cross-sell + expected upsell.
        promo_conversion = BASELINE_CONVERSION
        discount_cost = 0.0
        for discount in top_offer.offers:
            if discount.type == "coupon":
                tier = round(discount.discount / top_offer.base_price, 2) if top_offer.base_price else 0.0
                promo_conversion = DISCOUNT_CONVERSION_MODEL.get(tier, BASELINE_CONVERSION)
                discount_cost = discount.discount * promo_conversion
                total_discount_cost += discount_cost

        product_revenue = (top_offer.base_price * promo_conversion) - discount_cost

        addon_revenue = 0.0
        for addon in top_offer.recommended_addons:
            rate = await addon_attach_rate(addon.product_id)
            addon_revenue += addon.price * rate
            if rate > 0:
                cross_sell_offered += 1

        upsell_revenue = 0.0
        if top_offer.upsell_suggestion:
            upsell_revenue = top_offer.upsell_suggestion.price_diff * UPSELL_ACCEPTANCE_RATE
            upsell_offered += 1

        ai_assisted_total += product_revenue + addon_revenue + upsell_revenue

    baseline_aov = baseline_total / orders_evaluated if orders_evaluated else 0
    ai_aov = ai_assisted_total / orders_evaluated if orders_evaluated else 0
    uplift_pct = ((ai_assisted_total - baseline_total) / baseline_total * 100) if baseline_total else 0

    print("=" * 60)
    print("GROWTH ENGINE EVALUATION")
    print("=" * 60)
    print(f"Synthetic buyers evaluated: {orders_evaluated}")
    print(f"Cross-sell recommendations with real co-purchase data: {cross_sell_offered}")
    print(f"Upsell recommendations offered: {upsell_offered}")
    print("-" * 60)
    print(f"Baseline expected revenue (no growth engine): Rs.{baseline_total:,.0f}")
    print(f"AI-assisted expected revenue:                 Rs.{ai_assisted_total:,.0f}")
    print(f"Expected discount cost given out:             Rs.{total_discount_cost:,.0f}")
    print(f"Net incremental revenue:                      Rs.{ai_assisted_total - baseline_total:,.0f}")
    print("-" * 60)
    print(f"Baseline AOV:    Rs.{baseline_aov:,.0f}")
    print(f"AI-assisted AOV: Rs.{ai_aov:,.0f}")
    print(f"Revenue uplift:  {uplift_pct:+.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(evaluate())