import json
import uuid
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import AgentTurn, AgentEvent
from app.agent.session_store import SessionStore
from app.agent.context_builder import ContextBuilder
from app.agent.prompt_composer import PromptComposer
from app.agent.claude_adapter import MockClaudeRuntimeAdapter


class MessageRuntime:
    def __init__(self):
        self.session_store = SessionStore()
        self.context_builder = ContextBuilder()
        self.prompt_composer = PromptComposer()
        self.adapter = MockClaudeRuntimeAdapter()
        self._event_buffers: dict[str, list[dict]] = {}

    def handle_message(self, project_id: str, session_id: Optional[str], message: str, ui_context: dict | None = None) -> dict:
        db = get_session()
        try:
            session = self.session_store.get_or_create_session(project_id, session_id, provider="mock")
            session_id = session.id

            if session_id not in self._event_buffers:
                self._event_buffers[session_id] = []

            turn = AgentTurn(
                id=f"turn_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                project_id=project_id,
                user_message=message,
                status="running",
                created_at=datetime.now().isoformat(),
            )
            db.add(turn)
            db.commit()
            db.refresh(turn)

            context = self.context_builder.build(project_id, ui_context)

            prompt = self.prompt_composer.compose(context, message)

            for event in self.adapter.send_message(session_id, prompt, context):
                event["turn_id"] = turn.id
                self._event_buffers[session_id].append(event)

                agent_event = AgentEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    turn_id=turn.id,
                    project_id=project_id,
                    type=event["type"],
                    payload_json=json.dumps(event, ensure_ascii=False),
                    created_at=datetime.now().isoformat(),
                )
                db.add(agent_event)

            turn.status = "completed"
            turn.completed_at = datetime.now().isoformat()
            db.commit()

            return {
                "turn_id": turn.id,
                "session_id": session_id,
                "status": "running",
                "event_stream_url": f"/api/agent/sessions/{session_id}/events",
            }
        finally:
            db.close()

    def get_events(self, session_id: str) -> list[dict]:
        events = self._event_buffers.get(session_id, [])
        self._event_buffers[session_id] = []
        return events

    def interrupt(self, session_id: str) -> None:
        self.adapter.interrupt(session_id)
        self.session_store.update_session(session_id, status="interrupted")


_message_runtime: Optional[MessageRuntime] = None


def get_message_runtime() -> MessageRuntime:
    global _message_runtime
    if _message_runtime is None:
        _message_runtime = MessageRuntime()
    return _message_runtime
