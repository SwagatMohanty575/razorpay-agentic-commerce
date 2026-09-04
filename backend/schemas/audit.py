from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditEvent(BaseModel):
    timestamp: datetime
    session_id: str
    request_id: str
    agent: str
    action: str
    input_summary: str
    decision: str
    reason: str
    policy_evaluated: Optional[str] = None
    financial_amount: Optional[float] = None
    related_entity_id: Optional[str] = None
    result: str


class GrowthDecision(BaseModel):
    session_id: str
    product_id: str
    decision_type: str
    reason: str
    accepted_by_buyer: Optional[bool] = None