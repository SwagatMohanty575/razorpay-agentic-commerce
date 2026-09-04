import uuid
from datetime import datetime, timedelta, timezone
from backend.commerce.local_commerce_adapter import LocalCommerceAdapter
from backend.growth_engine.growth_engine import GrowthEngine
from backend.schemas.buyer import ConstraintSet
from backend.schemas.audit import GrowthDecision
from backend.schemas.merchant import (
    MerchantOffer, Product, ProductSpecs,
    OfferDiscount, PaymentOptions, MerchantReasoning,
)
from backend.commerce.offer_store import save_offer
from backend.schemas.buyer import ConstraintSet, NO_BUDGET_LIMIT
OFFER_TTL_MINUTES = 15

ASSUMED_MARGIN = {
    "laptop": 0.12, "mouse": 0.35, "bag": 0.40,
    "cooling_pad": 0.30, "keyboard": 0.35, "headphones": 0.30, "warranty": 0.60,
}


class MerchantAgent:
    def __init__(self):
        self.commerce = LocalCommerceAdapter()
        self.growth_engine = GrowthEngine()

    async def generate_offers(
        self, constraints: ConstraintSet, session_id: str | None = None, top_n: int = 8
    ) -> tuple[list[MerchantOffer], list[GrowthDecision]]:
        session_id = session_id or str(uuid.uuid4())

        candidates = await self.commerce.search_products(
            category=constraints.category, max_price=constraints.budget_max, filters={},
        )
        if not candidates:
            return [], []

        max_stock = max((p["stock"] for p in candidates), default=1) or 1
        scored = [(self._fit_score(p, constraints), p) for p in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = scored[:top_n]

        offers, all_decisions = [], []
        for fit_score, product in top_candidates:
            offer, decisions = await self._build_offer(product, fit_score, max_stock, constraints, session_id)
            offers.append(offer)
            all_decisions.extend(decisions)

        return offers, all_decisions

    def _fit_score(self, product: dict, constraints: ConstraintSet) -> float:
        score = 0.0
        if constraints.budget_max and constraints.budget_max < NO_BUDGET_LIMIT:
            utilization = product["price"] / constraints.budget_max
            score += min(utilization, 1.0) * 0.5

        text_blob = " ".join(filter(None, [
            product.get("name", ""), product.get("cpu", ""),
            product.get("gpu", ""), product.get("storage", ""),
        ])).lower()

        pref_matches = 0
        for pref in constraints.soft_preferences:
            pref_words = pref.lower().split()
            if any(word in text_blob for word in pref_words if len(word) > 3):
                pref_matches += 1

        if constraints.soft_preferences:
            score += (pref_matches / len(constraints.soft_preferences)) * 0.5

        return round(score, 3)

    async def _build_offer(
        self, product: dict, fit_score: float, max_stock: int,
        constraints: ConstraintSet, session_id: str,
    ) -> tuple[MerchantOffer, list[GrowthDecision]]:
        now = datetime.now(timezone.utc)
        decisions = []

        addons, addon_decisions = await self.growth_engine.recommend_addons(product, session_id)
        decisions.extend(addon_decisions)

        bundle = self.growth_engine.build_bundle(product["price"], constraints.budget_max, addons)

        upsell, upsell_decision = await self.growth_engine.find_upsell(product, constraints.budget_max, session_id)
        if upsell_decision:
            decisions.append(upsell_decision)

        promo, promo_decision = self.growth_engine.score_promotion(product["price"], session_id, product["id"])
        if promo_decision:
            decisions.append(promo_decision)

        offers_list = self._eligible_bank_discounts(product["price"])
        if promo:
            offers_list.append(promo)

        offer = MerchantOffer(
            offer_id=f"OFR-{uuid.uuid4().hex[:10]}",
            generated_at=now,
            expires_at=now + timedelta(minutes=OFFER_TTL_MINUTES),
            currency="INR",
            product=Product(
                id=product["id"], name=product["name"], category=product["category"],
                specs=ProductSpecs(
                    cpu=product.get("cpu"), gpu=product.get("gpu"),
                    ram_gb=product.get("ram_gb"), storage=product.get("storage"),
                    refresh_rate_hz=product.get("refresh_rate_hz"),
                ),
            ),
            base_price=product["price"],
            available_stock=product["stock"],
            fit_score=fit_score,
            delivery_estimated_days=product.get("delivery_days", 3),
            return_days=product.get("return_days", 7),
            warranty_years=product.get("warranty_years", 1),
            recommended_addons=addons,
            payment_options=self._payment_options(product["price"]),
            offers=offers_list,
            merchant_reasoning=MerchantReasoning(
                customer_fit=fit_score,
                inventory_priority=round(product["stock"] / max_stock, 2),
                margin_score=ASSUMED_MARGIN.get(product["category"], 0.20),
            ),
            bundle_suggestion=bundle,
            upsell_suggestion=upsell,
        )
        await save_offer(offer, session_id)
        return offer, decisions

    def _eligible_bank_discounts(self, price: float) -> list[OfferDiscount]:
        discounts = []
        if price >= 50000:
            discounts.append(OfferDiscount(type="bank", bank="HDFC", discount=2000, min_amount=50000))
        if price >= 30000:
            discounts.append(OfferDiscount(type="bank", bank="ICICI", discount=1000, min_amount=30000))
        return discounts

    def _payment_options(self, price: float) -> PaymentOptions:
        emi_terms = []
        if price >= 15000:
            emi_terms = ["3M", "6M"]
        if price >= 40000:
            emi_terms = ["3M", "6M", "9M", "12M"]
        return PaymentOptions(upi=True, card=True, netbanking=True, emi=emi_terms)