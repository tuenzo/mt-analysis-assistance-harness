import json
import uuid
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import AgentTurn, AgentEvent, ToolCall
from app.agent.session_store import SessionStore
from app.agent.context_builder import ContextBuilder
from app.agent.prompt_composer import PromptComposer
from app.agent.claude_agent_sdk_adapter import get_claude_adapter
from app.tools.gateway import get_gateway
from app.core.permissions import PermissionLevel
from app.core.config import get_agent_runtime_config


class MessageRuntime:
    def __init__(self):
        self.session_store = SessionStore()
        self.context_builder = ContextBuilder()
        self.prompt_composer = PromptComposer()
        config = get_agent_runtime_config()
        self.adapter = get_claude_adapter(config)
        self._event_buffers: dict[str, list[dict]] = {}
        self._turn_sequences: dict[str, int] = {}  # track which turn events belong to
        self._last_confirmed_turn: dict[str, int] = {}  # last turn_id confirmed by client

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

                if event["type"] == "tool_call_started":
                    action = event.get("action", "")
                    tool_name = event.get("tool", "business_analysis")
                    payload = event.get("payload", {})

                    tc = ToolCall(
                        id=f"tc_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        turn_id=turn.id,
                        project_id=project_id,
                        tool_name=tool_name,
                        action=action,
                        payload_json=json.dumps(payload, ensure_ascii=False),
                        payload_hash=f"sha256:{uuid.uuid4().hex}",
                        status="pending",
                        permission_level=PermissionLevel.SAFE_COMPUTE,
                        created_at=datetime.now().isoformat(),
                    )
                    db.add(tc)
                    db.commit()
                    db.refresh(tc)

                    gateway = get_gateway()
                    result = gateway.execute(
                        tool_call_id=tc.id,
                        project_id=project_id,
                        action_str=action,
                        payload=payload,
                        reason="",
                        session_id=session_id,
                        turn_id=turn.id,
                        user_permission_level=PermissionLevel.SAFE_COMPUTE,
                    )

                    tool_result_event = {
                        "type": "tool_call_finished" if result.ok else "tool_call_failed",
                        "turn_id": turn.id,
                        "tool": tool_name,
                        "action": action,
                        "ok": result.ok,
                        "summary": result.summary,
                        "approval_required": not result.ok and "需要用户审批" in result.summary,
                    }
                    self._event_buffers[session_id].append(tool_result_event)

                    tc.result_json = json.dumps(result.model_dump(), ensure_ascii=False)
                    if result.ok:
                        tc.status = "succeeded" if "需要用户审批" not in result.summary else "waiting_approval"
                    else:
                        tc.status = "failed"
                    tc.completed_at = datetime.now().isoformat()
                    db.commit()

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

    def get_events(self, session_id: str, after_turn_id: str | None = None) -> list[dict]:
        """
        Get buffered events for session, optionally filtering by turn_id.
        If after_turn_id is provided, returns events for the specified turn
        and any turns after it (including subsequent turns).
        This allows reconnecting clients to resume receiving events for the
        current turn without missing subsequent events.
        Clears returned events from buffer to prevent duplicate delivery.
        """
        events = self._event_buffers.get(session_id, [])

        if after_turn_id:
            # Include the specified turn and any turns after it.
            # Use >= so that events within the same turn are not dropped
            # on reconnect (turn_id string comparison is best-effort for UUIDs).
            filtered_events = []
            remaining_events = []
            for event in events:
                event_turn_id = event.get("turn_id", "")
                if event_turn_id and event_turn_id >= after_turn_id:
                    filtered_events.append(event)
                else:
                    remaining_events.append(event)
            self._event_buffers[session_id] = remaining_events
            return filtered_events

        # No filter - return all events and clear buffer
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
