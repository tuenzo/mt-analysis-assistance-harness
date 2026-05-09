import json
import threading
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
        self._event_lock = threading.RLock()
        self._turn_workers: dict[str, threading.Thread] = {}

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

            with self._event_lock:
                if session_id not in self._event_buffers:
                    self._event_buffers[session_id] = []
                self._turn_order.setdefault(session_id, [])

            active_turn = self._active_running_turn(db, session_id)
            if active_turn:
                return self._complete_busy_turn(
                    db,
                    session_id=session_id,
                    project_id=project_id,
                    message=message,
                    active_turn_id=active_turn.id,
                )

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
            with self._event_lock:
                self._turn_order[session_id].append(turn.id)

            context = self.context_builder.build(project_id, ui_context)
            context["runtime_session_id"] = session_id
            context["runtime_turn_id"] = turn.id
            context["runtime_provider"] = self.runtime_provider
            context["user_message"] = message

            prompt = self.prompt_composer.compose(context, message)
            context["composed_prompt"] = prompt

            self._append_event(
                db,
                session_id,
                turn.id,
                project_id,
                self._thought_event(
                    "Reading project context and preparing the agent turn.",
                    phase="context",
                    source="message_runtime",
                ),
            )
            db.commit()

            external_session_id = session.external_session_id or session_id
            worker = threading.Thread(
                target=self._run_turn_worker,
                args=(session_id, external_session_id, turn.id, project_id, message, context),
                name=f"agent-turn-{turn.id}",
                daemon=True,
            )
            with self._event_lock:
                self._turn_workers[turn.id] = worker
            worker.start()

            return {
                "turn_id": turn.id,
                "session_id": session_id,
                "status": "running",
                "event_stream_url": f"/api/agent/sessions/{session_id}/events",
            }
        finally:
            db.close()

    def _run_turn_worker(
        self,
        session_id: str,
        external_session_id: str,
        turn_id: str,
        project_id: str,
        message: str,
        context: dict,
    ) -> None:
        db = get_session()
        final_answer = ""
        failed_error = ""
        try:
            self._append_event(
                db,
                session_id,
                turn_id,
                project_id,
                self._thought_event(
                    "Agent runtime started. Waiting for model planning or tool activity.",
                    phase="runtime",
                    source=self.runtime_provider,
                ),
            )
            db.commit()

            for raw_event in self.adapter.send_message(external_session_id, message, context):
                event = dict(raw_event)
                if event.get("type") == "external_session_updated":
                    self.session_store.update_session(
                        session_id,
                        external_session_id=event.get("external_session_id"),
                        runtime_provider=self.runtime_provider,
                    )
                    continue

                if event.get("type") in ("tool_call_finished", "tool_call_failed") and not event.get("sdk_executed"):
                    continue

                event["turn_id"] = turn_id
                if event.get("type") == "assistant_thought_delta":
                    event.setdefault("phase", "thinking")
                    event.setdefault("visibility", "public")
                    event.setdefault("source", self.runtime_provider)
                elif event.get("type") == "tool_call_started":
                    self._append_event(
                        db,
                        session_id,
                        turn_id,
                        project_id,
                        self._thought_event(
                            f"Preparing tool call: {event.get('action', event.get('tool', 'unknown'))}.",
                            phase="tool_planning",
                            source=self.runtime_provider,
                        ),
                    )

                if event.get("type") == "final_answer":
                    final_answer = event.get("message", "")
                if event.get("type") in ("error", "runtime_error"):
                    failed_error = event.get("error", "Agent runtime failed.")

                self._append_event(db, session_id, turn_id, project_id, event)
                db.commit()

                if event["type"] == "tool_call_started" and not event.get("sdk_executed"):
                    self._execute_mock_tool_event(db, session_id, turn_id, project_id, event)

                if event.get("type") in ("tool_call_finished", "tool_call_failed"):
                    self._append_event(
                        db,
                        session_id,
                        turn_id,
                        project_id,
                        self._thought_event(
                            f"Tool returned: {event.get('action', event.get('tool', 'unknown'))}.",
                            phase="tool_result",
                            source=self.runtime_provider,
                        ),
                    )
                    db.commit()

            self._finish_turn(db, turn_id, final_answer=final_answer, failed_error=failed_error)
        except Exception as exc:
            failed_error = str(exc)
            self._append_event(
                db,
                session_id,
                turn_id,
                project_id,
                {"type": "runtime_error", "turn_id": turn_id, "error": failed_error},
            )
            self._finish_turn(db, turn_id, failed_error=failed_error)
        finally:
            db.close()
            with self._event_lock:
                if self._turn_workers.get(turn_id) is threading.current_thread():
                    self._turn_workers.pop(turn_id, None)

    def _finish_turn(
        self,
        db,
        turn_id: str,
        *,
        final_answer: str = "",
        failed_error: str = "",
    ) -> None:
        turn = db.query(AgentTurn).filter(AgentTurn.id == turn_id).first()
        if not turn:
            db.commit()
            return

        turn.status = "failed" if failed_error else "completed"
        if final_answer:
            turn.assistant_message = final_answer
        if failed_error:
            turn.error_message = failed_error
        turn.completed_at = datetime.now().isoformat()
        db.commit()

    @staticmethod
    def _thought_event(delta: str, *, phase: str, source: str) -> dict:
        return {
            "type": "assistant_thought_delta",
            "delta": delta,
            "phase": phase,
            "visibility": "public",
            "source": source,
        }

    def _active_running_turn(self, db, session_id: str) -> AgentTurn | None:
        turn = (
            db.query(AgentTurn)
            .filter(AgentTurn.session_id == session_id, AgentTurn.status == "running")
            .order_by(AgentTurn.created_at.desc(), AgentTurn.id.desc())
            .first()
        )
        if not turn:
            return None

        with self._event_lock:
            worker = self._turn_workers.get(turn.id)
        if worker and worker.is_alive():
            return turn

        try:
            created_at = datetime.fromisoformat(turn.created_at)
        except (TypeError, ValueError):
            return None
        if (datetime.now() - created_at).total_seconds() <= 120:
            return turn
        return None

    def _complete_busy_turn(
        self,
        db,
        *,
        session_id: str,
        project_id: str,
        message: str,
        active_turn_id: str,
    ) -> dict:
        now = datetime.now().isoformat()
        assistant_message = (
            "上一轮 Agent 任务仍在运行或收尾中。请等当前分析完成后再发送新的分析请求；"
            f"当前占用的 turn_id 是 `{active_turn_id}`。"
        )
        turn = AgentTurn(
            id=f"turn_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            project_id=project_id,
            user_message=message,
            assistant_message=assistant_message,
            status="completed",
            created_at=now,
            completed_at=now,
        )
        db.add(turn)
        db.flush()
        with self._event_lock:
            self._turn_order.setdefault(session_id, []).append(turn.id)

        self._append_event(
            db,
            session_id,
            turn.id,
            project_id,
            self._thought_event(
                "A previous turn is still active, so this request was not sent to the model.",
                phase="runtime_busy",
                source="message_runtime",
            ),
        )
        self._append_event(
            db,
            session_id,
            turn.id,
            project_id,
            {"type": "final_answer", "turn_id": turn.id, "message": assistant_message},
        )
        db.commit()
        return {
            "turn_id": turn.id,
            "session_id": session_id,
            "status": "completed",
            "event_stream_url": f"/api/agent/sessions/{session_id}/events",
        }

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
            reason=event.get("reason") or f"Agent requested {action}.",
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
            self._append_event(
                db,
                session_id,
                turn_id,
                project_id,
                {
                    "type": "approval_requested",
                    "turn_id": turn_id,
                    "approval_id": approval.id,
                    "action": approval.action,
                    "reason": approval.reason or "",
                    "risk_level": approval.risk_level,
                    "payload": json.loads(approval.payload_json or "{}"),
                    "tool_call_id": tc.id,
                },
            )

        self._append_event(
            db,
            session_id,
            turn_id,
            project_id,
            {
                "type": "tool_call_finished" if result.ok else "tool_call_failed",
                "turn_id": turn_id,
                "tool": tool_name,
                "action": action,
                "ok": result.ok,
                "summary": result.summary,
                "tool_call_id": tc.id,
                "approval_required": bool(approval),
                "approval_id": approval.id if approval else None,
                "approval_reason": approval.reason if approval else None,
                "risk_level": approval.risk_level if approval else None,
                "approval_payload": json.loads(approval.payload_json or "{}") if approval else None,
            },
        )

        tc.result_json = json.dumps(result.model_dump(), ensure_ascii=False)
        tc.status = "waiting_approval" if approval else ("succeeded" if result.ok else "failed")
        tc.completed_at = datetime.now().isoformat()
        db.commit()

    def _append_event(self, db, session_id: str, turn_id: str, project_id: str, event: dict) -> None:
        event["turn_id"] = turn_id
        with self._event_lock:
            self._event_buffers.setdefault(session_id, []).append(event)
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

    def get_events(self, session_id: str, after_turn_id: str | None = None) -> list[dict]:
        """
        Get buffered events for a session.

        If after_turn_id is provided, return buffered events for that turn and any later
        turns according to runtime insertion order, then clear only returned buffered events.
        """
        if after_turn_id:
            with self._event_lock:
                events = self._event_buffers.get(session_id, [])
                turn_order = self._turn_order.get(session_id, [])
                try:
                    allowed_turns = set(turn_order[turn_order.index(after_turn_id):])
                except ValueError:
                    allowed_turns = set()

                if allowed_turns:
                    filtered_events = []
                    remaining_events = []
                    for event in events:
                        event_turn_id = event.get("turn_id", "")
                        if not event_turn_id or event_turn_id in allowed_turns:
                            filtered_events.append(event)
                        else:
                            remaining_events.append(event)
                    self._event_buffers[session_id] = remaining_events
                else:
                    filtered_events = []

            if not filtered_events:
                if self._is_turn_running(session_id, after_turn_id):
                    return []
                return self._replay_turn_events_from_db(session_id, after_turn_id)
            return filtered_events

        with self._event_lock:
            events = self._event_buffers.get(session_id, [])
            self._event_buffers[session_id] = []
        return events

    def _is_turn_running(self, session_id: str, turn_id: str) -> bool:
        db = get_session()
        try:
            turn = (
                db.query(AgentTurn)
                .filter(AgentTurn.session_id == session_id, AgentTurn.id == turn_id)
                .first()
            )
            return bool(turn and turn.status == "running")
        finally:
            db.close()

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

        with self._event_lock:
            self._event_buffers.setdefault(session_id, [])
            turn_order = self._turn_order.setdefault(session_id, [])
            if turn_id and turn_id not in turn_order:
                turn_order.append(turn_id)

        db = get_session()
        try:
            for event in events:
                event.setdefault("turn_id", turn_id)
                with self._event_lock:
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

    def wait_for_turn(self, turn_id: str, timeout: float = 5.0) -> bool:
        with self._event_lock:
            worker = self._turn_workers.get(turn_id)
        if not worker or worker is threading.current_thread():
            return True
        worker.join(timeout)
        if worker.is_alive():
            return False
        with self._event_lock:
            self._turn_workers.pop(turn_id, None)
        return True

    def wait_for_all_turns(self, timeout: float = 5.0) -> bool:
        deadline = datetime.now().timestamp() + timeout
        with self._event_lock:
            turn_ids = list(self._turn_workers)
        completed = True
        for turn_id in turn_ids:
            remaining = max(0.0, deadline - datetime.now().timestamp())
            if not self.wait_for_turn(turn_id, remaining):
                completed = False
        return completed

    def _get_or_create_runtime_session(self, project_id: str, session_id: Optional[str]):
        if session_id:
            session = self.session_store.get_session(session_id)
            if session and session.project_id == project_id:
                external_session_id = session.external_session_id
                if external_session_id:
                    self.adapter.resume_session(external_session_id, project_id)
                    if session.runtime_provider != self.runtime_provider:
                        self.session_store.update_session(session.id, runtime_provider=self.runtime_provider)
                        session.runtime_provider = self.runtime_provider
                else:
                    external_session_id = self.adapter.create_session(project_id)
                    self.session_store.update_session(
                        session.id,
                        external_session_id=external_session_id,
                        runtime_provider=self.runtime_provider,
                    )
                    session.external_session_id = external_session_id
                    session.runtime_provider = self.runtime_provider
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
