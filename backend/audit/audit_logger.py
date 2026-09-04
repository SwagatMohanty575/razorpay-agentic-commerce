import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from backend.database.connection import async_session
from backend.database.models import AuditEventModel


async def log_event(
    session_id: str, agent: str, action: str, input_summary: str,
    decision: str, reason: str, result: str,
    policy_evaluated: str | None = None,
    financial_amount: float | None = None,
    related_entity_id: str | None = None,
) -> dict:
    """Writes one audit event. Every agent/service that makes a decision
    calls this — it's the queryable record behind the judges' audit view."""
    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    async with async_session() as session:
        record = AuditEventModel(
            timestamp=timestamp, session_id=session_id or "unknown", request_id=request_id,
            agent=agent, action=action, input_summary=input_summary,
            decision=decision, reason=reason, policy_evaluated=policy_evaluated,
            financial_amount=financial_amount, related_entity_id=related_entity_id,
            result=result,
        )
        session.add(record)
        await session.commit()

    return {"timestamp": timestamp, "session_id": session_id, "request_id": request_id, "agent": agent, "action": action, "result": result}


async def get_audit_trail(session_id: str) -> list[dict]:
    async with async_session() as session:
        result = await session.execute(
            select(AuditEventModel).where(AuditEventModel.session_id == session_id).order_by(AuditEventModel.id.asc())
        )
        events = result.scalars().all()
        return [
            {
                "timestamp": e.timestamp, "session_id": e.session_id, "request_id": e.request_id,
                "agent": e.agent, "action": e.action, "input_summary": e.input_summary,
                "decision": e.decision, "reason": e.reason,
                "policy_evaluated": e.policy_evaluated, "financial_amount": e.financial_amount,
                "related_entity_id": e.related_entity_id, "result": e.result,
            }
            for e in events
        ]