from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.agents.buyer_agent import BuyerAgent
from backend.schemas.buyer import ConstraintSet
from backend.schemas.merchant import MerchantOffer
from backend.audit.audit_logger import log_event
from backend.policy.guardrails import check_query

router = APIRouter()
buyer_agent = BuyerAgent()


class IntentRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@router.post("/intent")
async def parse_intent(request: IntentRequest):
    import uuid as _uuid
    allowed, reason = check_query(request.query)
    if not allowed:
        sid = request.session_id or str(_uuid.uuid4())
        await log_event(
            sid, "guardrail", "REQUEST_REJECTED",
            request.query[:120], "blocked", reason, "blocked",
            policy_evaluated="input_guardrail",
        )
        return {"blocked": True, "reason": reason, "session_id": sid}

    intent = await buyer_agent.understand_intent(request.query, request.session_id)

    await log_event(
        intent.session_id, "guardrail", "REQUEST_ACCEPTED",
        request.query[:120], "passed", "Request is a valid product enquiry", "success",
        policy_evaluated="input_guardrail",
    )
    await log_event(
        intent.session_id, "buyer_agent", "INTENT_RECEIVED",
        request.query, "parsed", "Converted natural-language query to intent", "success",
    )
    await log_event(
        intent.session_id, "buyer_agent", "CONSTRAINTS_CREATED",
        f"hard={intent.constraints.hard_constraints}, soft={intent.constraints.soft_preferences}",
        "constraints_built",
        f"category={intent.constraints.category}, budget_max={intent.constraints.budget_max}",
        "success",
    )
    return intent


class EvaluateOfferRequest(BaseModel):
    offer: MerchantOffer
    constraints: ConstraintSet
    session_id: str


@router.post("/evaluate-offer")
async def evaluate_offer(request: EvaluateOfferRequest):
    evaluation = buyer_agent.evaluate_offer(request.offer.model_dump(), request.constraints)

    await log_event(
        request.session_id, "buyer_agent", "OFFER_EVALUATED",
        f"offer_id={request.offer.offer_id}",
        "accepted" if evaluation["base_product_within_budget"] else "rejected",
        f"{len(evaluation['accepted_addons'])} addon(s) accepted, {len(evaluation['rejected_addons'])} rejected",
        "success",
        related_entity_id=request.offer.offer_id,
    )
    return evaluation