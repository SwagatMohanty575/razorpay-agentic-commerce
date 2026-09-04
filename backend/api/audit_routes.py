from fastapi import APIRouter
from backend.audit.audit_logger import get_audit_trail

router = APIRouter()


@router.get("/trail/{session_id}")
async def get_trail(session_id: str):
    events = await get_audit_trail(session_id)
    return {"session_id": session_id, "event_count": len(events), "events": events}