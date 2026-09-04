import re
import uuid
from backend.agents.llm_client import LLMClient
from backend.schemas.buyer import BuyerIntent, ConstraintSet, NO_BUDGET_LIMIT

SYSTEM_PROMPT = """You are the intent-understanding module of a shopping buyer agent.
Convert the customer's natural-language shopping request into structured JSON.

Rules:
- Only extract what the customer EXPLICITLY said as hard_constraints (category, budget).
- Do NOT invent technical specs (CPU, GPU, RAM, refresh rate) as hard constraints unless
  the customer explicitly named them in the query.
- If the customer's phrasing implies a general need (e.g. "heavy-duty", "for gaming",
  "for programming", "lightweight"), translate that into soft_preferences as plain-English
  phrases — never as invented hard specs.
- budget_max must be a number in INR, or null if the customer stated no budget.
- category should be "laptop" unless the query clearly names a different product type.

Respond with ONLY this JSON shape, no other text, no markdown formatting:
{
  "category": "laptop",
  "budget_max": <number or null>,
  "use_case": "<short phrase or null>",
  "hard_constraints": ["<string>", ...],
  "soft_preferences": ["<string>", ...]
}
"""


class BuyerAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def understand_intent(self, raw_query: str, session_id: str | None = None) -> BuyerIntent:
        session_id = session_id or str(uuid.uuid4())

        try:
            parsed = await self.llm.generate_json(SYSTEM_PROMPT, raw_query)
            constraints = self._build_constraints(parsed)
        except Exception:
            # Deterministic fallback so a flaky/offline LLM never breaks the demo.
            constraints = self._fallback_constraints(raw_query)

        return BuyerIntent(
            raw_query=raw_query,
            constraints=constraints,
            session_id=session_id,
        )

    def _build_constraints(self, parsed: dict) -> ConstraintSet:
        budget = parsed.get("budget_max")
        hard = list(parsed.get("hard_constraints") or [])
        category = parsed.get("category") or "laptop"

        # Budget arithmetic/comparisons are always deterministic — we only ever
        # trust the LLM to extract the number, never to reason about it.
        if budget:
            hard.append(f"budget <= {budget}")

        return ConstraintSet(
            category=category,
            budget_max=float(budget) if budget else NO_BUDGET_LIMIT,
            use_case=parsed.get("use_case"),
            hard_constraints=hard,
            soft_preferences=list(parsed.get("soft_preferences") or []),
        )

    def _fallback_constraints(self, raw_query: str) -> ConstraintSet:
        """Used only if the LLM call fails entirely (Ollama not running, etc.)
        so the demo never hard-crashes. Extracts a budget number via regex,
        defaults everything else to safe/empty."""
        cleaned = raw_query.replace(",", "")
        numbers = re.findall(r"\d{4,}", cleaned)
        budget = float(numbers[0]) if numbers else None

        hard = [f"budget <= {budget}"] if budget else []

        return ConstraintSet(
            category="laptop",
            budget_max=budget or NO_BUDGET_LIMIT,
            use_case=None,
            hard_constraints=hard,
            soft_preferences=[],
        )

    def evaluate_offer(self, offer: dict, constraints: ConstraintSet) -> dict:
        """Independently checks every merchant suggestion — addons, bundle,
        upsell — against the customer's actual budget. Nothing the merchant
        proposes is accepted just because it was proposed."""
        base_price = offer["base_price"]
        budget = constraints.budget_max

        accepted_addons, rejected_addons = [], []
        for addon in offer.get("recommended_addons", []):
            if budget < NO_BUDGET_LIMIT and (base_price + addon["price"]) > budget:
                rejected_addons.append({**addon, "rejection_reason": "Exceeds stated budget when combined with base product"})
            else:
                accepted_addons.append(addon)

        bundle = offer.get("bundle_suggestion")
        bundle_accepted = None
        if bundle:
            bundle_accepted = budget >= NO_BUDGET_LIMIT or bundle["combined_total"] <= budget

        upsell = offer.get("upsell_suggestion")
        upsell_accepted = None
        if upsell:
            upsell_accepted = budget >= NO_BUDGET_LIMIT or upsell["price"] <= budget

        return {
            "offer_id": offer["offer_id"],
            "base_product_within_budget": budget >= NO_BUDGET_LIMIT or base_price <= budget,
            "accepted_addons": accepted_addons,
            "rejected_addons": rejected_addons,
            "bundle_accepted": bundle_accepted,
            "upsell_accepted": upsell_accepted,
        }