from fastapi import APIRouter, HTTPException
from app.agent.session_store import SessionStore

router = APIRouter(prefix="/agent", tags=["sessions"])


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    store = SessionStore()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "ok": True,
        "data": {
            "id": session.id,
            "project_id": session.project_id,
            "runtime_provider": session.runtime_provider,
            "status": session.status,
            "created_at": session.created_at,
        }
    }
