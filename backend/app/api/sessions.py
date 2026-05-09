from fastapi import APIRouter, HTTPException
from app.agent.session_store import SessionStore
from app.core.database import get_session as get_db_session
from app.projects.models import AgentTurn

router = APIRouter(prefix="/agent", tags=["sessions"])


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    store = SessionStore()
    session = store.get_session_summary(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "ok": True,
        "data": session,
    }


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    store = SessionStore()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db = get_db_session()
    try:
        turns = (
            db.query(AgentTurn)
            .filter(AgentTurn.session_id == session_id)
            .order_by(AgentTurn.created_at.asc(), AgentTurn.id.asc())
            .all()
        )
        messages = []
        for turn in turns:
            messages.append({
                "id": f"{turn.id}_user",
                "turn_id": turn.id,
                "role": "user",
                "content": turn.user_message,
                "created_at": turn.created_at,
            })
            if turn.assistant_message:
                messages.append({
                    "id": f"{turn.id}_assistant",
                    "turn_id": turn.id,
                    "role": "assistant",
                    "content": turn.assistant_message,
                    "created_at": turn.completed_at or turn.created_at,
                })
        return {"ok": True, "data": messages}
    finally:
        db.close()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    store = SessionStore()
    result = store.delete_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "data": result}
