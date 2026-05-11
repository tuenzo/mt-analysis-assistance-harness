import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import json
from app.projects.schemas import AgentMessageRequest, AgentMessageResponse
from app.agent.message_runtime import get_message_runtime
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/runtime")
def get_agent_runtime_metadata():
    return {
        "ok": True,
        "data": {
            "runtime_provider": settings.agent_runtime_provider,
            "model": os.environ.get("ANTHROPIC_API_MODEL") or settings.anthropic_api_model,
        },
        "error": None,
    }


@router.post("/messages", response_model=AgentMessageResponse)
def send_message(body: AgentMessageRequest):
    runtime = get_message_runtime()
    result = runtime.handle_message(body.project_id, body.session_id, body.message, body.ui_context)
    return result


@router.get("/sessions/{session_id}/events")
async def stream_events(session_id: str, after_turn_id: str | None = None):
    runtime = get_message_runtime()

    async def event_generator():
        import asyncio
        while True:
            events = runtime.get_events(session_id, after_turn_id)
            has_terminal = False
            for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") in ("final_answer", "error", "runtime_error"):
                    has_terminal = True
            if has_terminal:
                break
            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/sessions/{session_id}/interrupt")
def interrupt_session(session_id: str):
    runtime = get_message_runtime()
    runtime.interrupt(session_id)
    return {"ok": True, "message": "Session interrupted"}
