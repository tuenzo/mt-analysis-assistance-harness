import json
import uuid
from datetime import datetime
from typing import Optional

from app.agent.claude_agent_sdk_adapter import get_claude_adapter
from app.agent.context_builder import ContextBuilder
from app.agent.prompt_composer import PromptComposer
from app.agent.session_store import SessionStore
from app.core.config import get_agent_runtime_config
from app.core.database import get_session
from app.core.permissions import PermissionLevel, action_to_permission_level
from app.projects.models import AgentEvent, AgentTurn, ApprovalRequest, ToolCall
from app.tools.gateway import get_gateway
from app.tools.schemas import BusinessAnalysisAction


class MessageRuntime:
    def __init__(self):
        self.session_store = SessionStore()
        self.context_builder = ContextBuilder()
        self.prompt_composer = PromptComposer()
        config = get_agent_runtime_config()
        self.runtime_config = config
        self.runtime_provider = config.get("provider", "mock")
        self.adapter = get_claude_adapter(config)
        self._event_buffers: dict[str, list[dict]] = {}
        self._turn_order: dict[str, list[str]] = {}
        self._last_confirmed_turn: dict[str, int] = {}

    def handle_message(
        self,
        project_id: str,
        session_id: Optional[str],
        message: str,
        ui_context: dict | None = None,
    ) -> dict:
        db = get_session()
        try:
            session = self._get_or_create_runtime_session(project_id, session_id)
            session_id = session.id

            if session_id not in self._event_buffers:
                self._event_buffers[session_id] = []
            self._turn_order.setdefault(session_id, [])

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
            self._turn_order[session_id].append(turn.id)

            context = self.context_builder.build(project_id, ui_context)
            context["runtime_session_id"] = session_id
            context["runtime_turn_id"] = turn.id

            prompt = self.prompt_composer.compose(context, message)

            for event in self.adapter.send_message(session.external_session_id or session_id, prompt, context):
                if event.get("type") == "external_session_updated":
                    self.session_store.update_session(
                        session_id,
                        external_session_id=event.get("external_session_id"),
                    )
                    continue

                if event.get("type") in ("tool_call_finished", "tool_call_failed") and not event.get("sdk_executed"):
                    continue

                event["turn_id"] = turn.id
                self._event_buffers[session_id].append(event)

                if event["type"] == "tool_call_started" and not event.get("sdk_executed"):
                    self._execute_mock_tool_event(db, session_id, turn.id, project_id, event)

                db.add(
                    AgentEvent(
                        id=f"evt_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        turn_id=turn.id,
                        project_id=project_id,
                        type=event["type"],
                        payload_json=json.dumps(event, ensure_ascii=False),
                        created_at=datetime.now().isoformat(),
                    )
                )

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

    def _execute_mock_tool_event(self, db, session_id: str, turn_id: str, project_id: str, event: dict) -> None:
        action = event.get("action", "")
        tool_name = event.get("tool", "business_analysis")
        payload = event.get("payload", {})
        try:
            required_permission = action_to_permission_level(BusinessAnalysisAction(action))
        except ValueError:
            required_permission = PermissionLevel.SAFE_COMPUTE

        tc = ToolCall(
            id=f"tc_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            turn_id=turn_id,
            project_id=project_id,
            tool_name=tool_name,
            action=action,
            payload_json=json.dumps(payload, ensure_ascii=False),
            payload_hash=f"sha256:{uuid.uuid4().hex}",
            status="pending",
            permission_level=required_permission,
            created_at=datetime.now().isoformat(),
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)

        result = get_gateway().execute(
            tool_call_id=tc.id,
            project_id=project_id,
            action_str=action,
            payload=payload,
            reason="",
            session_id=session_id,
            turn_id=turn_id,
            user_permission_level=PermissionLevel.EXTERNAL_SYNC,
        )
        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.tool_call_id == tc.id, ApprovalRequest.status == "pending")
            .first()
        )
        if approval:
            self._event_buffers[session_id].append(
                {
                    "type": "approval_requested",
                    "turn_id": turn_id,
                    "approval_id": approval.id,
                    "action": approval.action,
                    "reason": approval.reason or "",
                    "risk_level": approval.risk_level,
                }
            )

        self._event_buffers[session_id].append(
            {
                "type": "tool_call_finished" if result.ok else "tool_call_failed",
                "turn_id": turn_id,
                "tool": tool_name,
                "action": action,
                "ok": result.ok,
                "summary": result.summary,
                "approval_required": bool(approval),
            }
        )

        tc.result_json = json.dumps(result.model_dump(), ensure_ascii=False)
        tc.status = "waiting_approval" if approval else ("succeeded" if result.ok else "failed")
        tc.completed_at = datetime.now().isoformat()
        db.commit()

    def get_events(self, session_id: str, after_turn_id: str | None = None) -> list[dict]:
        """
        Get buffered events for a session.

        If after_turn_id is provided, return buffered events for that turn and any later
        turns according to runtime insertion order, then clear only returned buffered events.
        """
        events = self._event_buffers.get(session_id, [])

        if after_turn_id:
            turn_order = self._turn_order.get(session_id, [])
            try:
                allowed_turns = set(turn_order[turn_order.index(after_turn_id):])
            except ValueError:
                return self._replay_turn_events_from_db(session_id, after_turn_id)

            filtered_events = []
            remaining_events = []
            for event in events:
                event_turn_id = event.get("turn_id", "")
                if not event_turn_id or event_turn_id in allowed_turns:
                    filtered_events.append(event)
                else:
                    remaining_events.append(event)
            self._event_buffers[session_id] = remaining_events
            if not filtered_events:
                return self._replay_turn_events_from_db(session_id, after_turn_id)
            return filtered_events

        self._event_buffers[session_id] = []
        return events

    def _replay_turn_events_from_db(self, session_id: str, turn_id: str) -> list[dict]:
        db = get_session()
        try:
            rows = (
                db.query(AgentEvent)
                .filter(AgentEvent.session_id == session_id, AgentEvent.turn_id == turn_id)
                .order_by(AgentEvent.created_at.asc(), AgentEvent.id.asc())
                .all()
            )
            replayed = []
            for row in rows:
                try:
                    replayed.append(json.loads(row.payload_json))
                except json.JSONDecodeError:
                    replayed.append(
                        {
                            "type": "error",
                            "turn_id": turn_id,
                            "error": "Stored agent event could not be decoded.",
                        }
                    )
            return replayed
        finally:
            db.close()

    def publish_events(self, session_id: str, project_id: str, turn_id: str, events: list[dict]) -> None:
        if not events:
            return

        self._event_buffers.setdefault(session_id, [])
        turn_order = self._turn_order.setdefault(session_id, [])
        if turn_id and turn_id not in turn_order:
            turn_order.append(turn_id)

        db = get_session()
        try:
            for event in events:
                event.setdefault("turn_id", turn_id)
                self._event_buffers[session_id].append(event)
                db.add(
                    AgentEvent(
                        id=f"evt_{uuid.uuid4().hex[:12]}",
                        session_id=session_id,
                        turn_id=turn_id,
                        project_id=project_id,
                        type=event["type"],
                        payload_json=json.dumps(event, ensure_ascii=False),
                        created_at=datetime.now().isoformat(),
                    )
                )
            db.commit()
        finally:
            db.close()

    def interrupt(self, session_id: str) -> None:
        session = self.session_store.get_session(session_id)
        external_session_id = session.external_session_id if session else session_id
        self.adapter.interrupt(external_session_id or session_id)
        self.session_store.update_session(session_id, status="interrupted")

    def _get_or_create_runtime_session(self, project_id: str, session_id: Optional[str]):
        if session_id:
            session = self.session_store.get_session(session_id)
            if session and session.project_id == project_id:
                external_session_id = session.external_session_id
                if external_session_id:
                    self.adapter.resume_session(external_session_id, project_id)
                else:
                    external_session_id = self.adapter.create_session(project_id)
                    self.session_store.update_session(session.id, external_session_id=external_session_id)
                    session.external_session_id = external_session_id
                return session

        external_session_id = self.adapter.create_session(project_id)
        return self.session_store.create_session(
            project_id,
            provider=self.runtime_provider,
            external_session_id=external_session_id,
        )


_message_runtime: Optional[MessageRuntime] = None


def get_message_runtime() -> MessageRuntime:
    global _message_runtime
    if _message_runtime is None:
        _message_runtime = MessageRuntime()
    return _message_runtime
