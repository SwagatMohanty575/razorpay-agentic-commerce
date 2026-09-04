from backend.commerce.local_commerce_adapter import LocalCommerceAdapter
from backend.schemas.merchant import RecommendedAddon, BundleSuggestion, UpsellSuggestion, OfferDiscount
from backend.schemas.audit import GrowthDecision
from backend.growth_engine.analytics_data import (
    CO_PURCHASE_RATES, DISCOUNT_CONVERSION_MODEL, gpu_rank,
)
from backend.schemas.buyer import NO_BUDGET_LIMIT


class GrowthEngine:
    """Legitimate merchant revenue optimization. Every recommendation comes
    with a reason the merchant agent (and later the audit trail) can point
    to. Nothing here overrides customer budget — that's independently
    re-checked by the Buyer Agent regardless of what's proposed here."""

    def __init__(self):
        self.commerce = LocalCommerceAdapter()

    async def recommend_addons(
        self, product: dict, session_id: str, top_n: int = 3
    ) -> tuple[list[RecommendedAddon], list[GrowthDecision]]:
        co_purchase = CO_PURCHASE_RATES.get(product["category"], [])
        addons, decisions = [], []

        for entry in sorted(co_purchase, key=lambda x: x["rate"], reverse=True)[:top_n]:
            candidates = await self.commerce.search_products(
                category=entry["addon_category"], max_price=float("inf"), filters={}
            )
            in_stock = [c for c in candidates if c["stock"] > 0]
            if not in_stock:
                continue
            best = min(in_stock, key=lambda x: x["price"])

            reason = (
                f"{int(entry['rate'] * 100)}% of {product['category']} buyers "
                f"also purchase a {entry['addon_category'].replace('_', ' ')}"
            )

            addons.append(RecommendedAddon(
                product_id=best["id"], name=best["name"], price=best["price"],
                stock=best["stock"], reason=reason,
            ))
            decisions.append(GrowthDecision(
                session_id=session_id, product_id=best["id"],
                decision_type="cross_sell", reason=reason,
            ))

        return addons, decisions

    def build_bundle(
        self, base_price: float, budget_max: float, addons: list[RecommendedAddon]
    ) -> BundleSuggestion | None:
        """Greedily fills remaining budget with the highest-co-purchase-rate
        addons first (addons is already rate-sorted), never exceeding budget."""
        if budget_max >= NO_BUDGET_LIMIT:
            remaining = None
        else:
            remaining = budget_max - base_price
            if remaining <= 0:
                return None

        picked, running_total = [], 0.0
        for addon in addons:
            if remaining is not None and (running_total + addon.price) > remaining:
                continue
            picked.append(addon)
            running_total += addon.price

        if not picked:
            return None

        return BundleSuggestion(
            addon_ids=[a.product_id for a in picked],
            items=picked,
            bundle_total=round(running_total, 2),
            combined_total=round(base_price + running_total, 2),
            reason=f"Adds {len(picked)} frequently co-purchased item(s) while staying within your budget",
        )

    async def find_upsell(
        self, base_product: dict, budget_max: float, session_id: str
    ) -> tuple[UpsellSuggestion | None, GrowthDecision | None]:
        """Only suggests a pricier alternative if it's within budget AND a
        genuinely better GPU tier — never upsells on price alone."""
        candidates = await self.commerce.search_products(
            category=base_product["category"], max_price=budget_max, filters={}
        )
        base_rank = gpu_rank(base_product.get("gpu"))

        better_options = [
            c for c in candidates
            if c["id"] != base_product["id"]
            and c["price"] > base_product["price"]
            and gpu_rank(c.get("gpu")) > base_rank
            and c["stock"] > 0
        ]
        if not better_options:
            return None, None

        best = min(better_options, key=lambda x: x["price"])
        price_diff = round(best["price"] - base_product["price"], 2)
        reason = (
            f"{best['gpu']} offers better performance than "
            f"{base_product.get('gpu', 'the base option')}, still within your budget for ₹{price_diff:.0f} more"
        )

        suggestion = UpsellSuggestion(
            product_id=best["id"], name=best["name"], price=best["price"],
            price_diff=price_diff, reason=reason,
        )
        decision = GrowthDecision(
            session_id=session_id, product_id=best["id"],
            decision_type="upsell", reason=reason,
        )
        return suggestion, decision

    def score_promotion(
        self, price: float, session_id: str, product_id: str
    ) -> tuple[OfferDiscount | None, GrowthDecision | None]:
        """Picks the discount tier that maximizes EXPECTED revenue
        (price × (1-discount) × assumed conversion probability), not the
        deepest available discount. Fully deterministic — no LLM involved."""
        baseline_revenue = price * DISCOUNT_CONVERSION_MODEL[0.0]
        best_tier, best_expected_revenue = 0.0, baseline_revenue

        for discount, conversion_prob in DISCOUNT_CONVERSION_MODEL.items():
            expected_revenue = price * (1 - discount) * conversion_prob
            if expected_revenue > best_expected_revenue:
                best_expected_revenue, best_tier = expected_revenue, discount

        if best_tier == 0.0:
            return None, None

        discount_amount = round(price * best_tier, 2)
        reason = (
            f"{int(best_tier*100)}% discount maximizes expected revenue "
            f"(₹{best_expected_revenue:.0f} expected vs ₹{baseline_revenue:.0f} with no discount)"
        )

        offer = OfferDiscount(type="coupon", bank=None, discount=discount_amount, min_amount=None, valid_until=None)
        decision = GrowthDecision(session_id=session_id, product_id=product_id, decision_type="promotion", reason=reason)
        return offer, decision