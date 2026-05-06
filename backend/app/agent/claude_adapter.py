import re
import uuid
from abc import ABC, abstractmethod
from typing import Generator


class ClaudeRuntimeAdapter(ABC):
    @abstractmethod
    def create_session(self, project_id: str) -> str:
        """Create session, return external_session_id."""
        pass

    @abstractmethod
    def resume_session(self, session_id: str, project_id: str) -> None:
        """Resume existing session."""
        pass

    @abstractmethod
    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        """Send message, yield runtime events."""
        pass

    @abstractmethod
    def interrupt(self, session_id: str) -> None:
        """Interrupt running session."""
        pass


class MockClaudeRuntimeAdapter(ClaudeRuntimeAdapter):
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._interrupted: set[str] = set()

    def create_session(self, project_id: str) -> str:
        sid = f"mock_{uuid.uuid4().hex[:12]}"
        self._sessions[sid] = {"project_id": project_id, "interrupted": False}
        return sid

    def resume_session(self, session_id: str, project_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {"project_id": project_id, "interrupted": False}

    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        if session_id in self._interrupted:
            self._interrupted.discard(session_id)
            return

        intent_message = context.get("user_message") or self._extract_user_message(message)
        msg_lower = intent_message.lower()
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        source_path = self._extract_source_path(intent_message)

        is_data_load = any(
            kw in msg_lower
            for kw in [
                "dataload",
                "data load",
                "load data",
                "ingest",
                "csv",
                "\u52a0\u8f7d",
                "\u5bfc\u5165",
                "\u6570\u636e\u52a0\u8f7d",
            ]
        )
        is_full_pipeline = any(
            kw in msg_lower
            for kw in [
                "full pipeline",
                "full promotion analysis",
                "run the full",
                "end to end",
                "end-to-end",
                "\u5168\u6d41\u7a0b",
                "\u5b8c\u6574\u5206\u6790",
                "\u771f\u5b9e\u5206\u6790",
            ]
        )
        is_panel_build = any(
            kw in msg_lower
            for kw in [
                "build panel",
                "panel build",
                "category day panel",
                "category-day panel",
                "\u751f\u6210panel",
                "\u6784\u5efapanel",
            ]
        )
        is_report = any(
            kw in msg_lower
            for kw in [
                "report",
                "report draft",
                "generate report",
                "\u62a5\u544a",
                "\u62a5\u544a\u8349\u7a3f",
            ]
        )
        is_analysis = any(
            kw in msg_lower
            for kw in [
                "analysis",
                "analyze",
                "generate",
                "run",
                "pipeline",
                "diagnostic",
                "\u5206\u6790",
                "\u8fd0\u884c",
                "\u751f\u6210",
            ]
        )
        is_status = any(
            kw in msg_lower
            for kw in ["state", "status", "project", "current", "\u72b6\u6001", "\u9879\u76ee"]
        )

        yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "Received. "}

        if is_data_load:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "I will discover source CSV files, ingest them, infer schema, and validate data. ",
            }
            yield self._tool_started(turn_id, "project.get_state", {})
            yield self._tool_started(
                turn_id,
                "data.discover_source_files",
                {"source_path": source_path} if source_path else {},
            )
            ingest_payload = {"selected_files": self._build_mock_selected_files(source_path)}
            if source_path:
                ingest_payload["source_path"] = source_path
            yield self._tool_started(turn_id, "data.ingest", ingest_payload)
            yield self._tool_started(turn_id, "schema.infer", {})
            yield self._tool_started(turn_id, "data.validate", {})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    "Data loading has been attempted through project.get_state -> "
                    "data.discover_source_files -> data.ingest -> schema.infer -> data.validate. "
                    "If validation remains partial, inspect the failed tool result for missing roles, "
                    "skipped files, or schema issues."
                ),
            }
            return

        if is_full_pipeline:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "I will request the approved full analysis pipeline now. ",
            }
            yield self._tool_started(turn_id, "project.get_state", {})
            yield self._tool_started(turn_id, "analysis.run_full_pipeline", {"format": "md"})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    "Full analysis pipeline has been requested. If approval is required, approve it "
                    "in the UI to run validation, panel build, diagnostics, causal checks, charts, "
                    "and report generation."
                ),
            }
            return

        if is_panel_build:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "I will request category-day panel generation. ",
            }
            yield self._tool_started(turn_id, "project.get_state", {})
            yield self._tool_started(turn_id, "panel.build_category_day", {})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    "Panel build has been requested. If approval is required, approve it in the UI "
                    "to generate the category-day panel."
                ),
            }
            return

        if is_report:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "I will gather the latest result and request report generation. ",
            }
            yield self._tool_started(turn_id, "project.get_state", {})
            yield self._tool_started(turn_id, "result.get_latest", {})
            yield self._tool_started(turn_id, "report.generate", {"format": "md"})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": "Report generation has been requested from the latest available analysis artifacts.",
            }
            return

        if is_analysis:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "I will inspect project state and validate the currently available data. ",
            }
            yield self._tool_started(turn_id, "project.get_state", {})
            yield self._tool_started(turn_id, "data.validate", {})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    f"Project {context.get('project_name', 'unknown')} is currently at "
                    f"{context.get('current_stage', 'unknown')} with data quality "
                    f"{context.get('data_quality', 'unknown')}."
                ),
            }
            return

        if is_status:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "I will fetch project state. "}
            yield self._tool_started(turn_id, "project.get_state", {})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    f"Project {context.get('project_name', 'unknown')} is at "
                    f"{context.get('current_stage', 'unknown')}; file count: "
                    f"{len(context.get('files', []))}."
                ),
            }
            return

        yield {
            "type": "assistant_message_delta",
            "turn_id": turn_id,
            "delta": "Hello, I am the business analysis assistant. ",
        }
        yield {
            "type": "final_answer",
            "turn_id": turn_id,
            "message": (
                "I can help load files, diagnose data, run analysis models, and generate reports. "
                "What would you like to test first?"
            ),
        }

    def interrupt(self, session_id: str) -> None:
        self._interrupted.add(session_id)
        if session_id in self._sessions:
            self._sessions[session_id]["interrupted"] = True

    @staticmethod
    def _tool_started(turn_id: str, action: str, payload: dict) -> dict:
        return {
            "type": "tool_call_started",
            "turn_id": turn_id,
            "tool": "business_analysis",
            "action": action,
            "payload": payload,
            "reason": MockClaudeRuntimeAdapter._reason_for_action(action),
        }

    @staticmethod
    def _reason_for_action(action: str) -> str:
        reasons = {
            "project.get_state": "Read current project state before choosing the next analysis action.",
            "data.discover_source_files": "Discover available CSV files before ingesting local data.",
            "data.ingest": "Import selected CSV files into the project workspace for analysis.",
            "schema.infer": "Infer source column mappings before validation.",
            "data.validate": "Check whether uploaded data satisfies the analysis contract.",
            "panel.build_category_day": "Generate the category-day panel required by downstream diagnostics and causal analysis.",
            "analysis.run_full_pipeline": "Run the approved end-to-end promotion analysis pipeline and generate outputs.",
            "result.get_latest": "Read latest analysis outputs before report generation.",
            "report.generate": "Generate a report draft from the latest analysis artifacts.",
        }
        return reasons.get(action, f"Run {action}.")

    @staticmethod
    def _extract_source_path(message: str) -> str | None:
        quoted = re.search(r'["\']([A-Za-z]:[\\/][^"\']+)["\']', message)
        if quoted:
            return quoted.group(1).strip()
        match = re.search(r"([A-Za-z]:[\\/][^\s\r\n\"']+)", message)
        if not match:
            return None
        return match.group(1).strip().rstrip(" .;,")

    @staticmethod
    def _extract_user_message(message: str) -> str:
        marker = "User message:"
        if marker not in message:
            return message
        return message.rsplit(marker, 1)[-1].strip()

    @staticmethod
    def _build_mock_selected_files(source_path: str | None) -> list[dict]:
        roles = [
            ("order_info.csv", "order_info", "Mock selected conventional order file after discovery."),
            ("exposure_info.csv", "exposure_info", "Mock selected conventional exposure file after discovery."),
            ("activity_timeline.csv", "activity_timeline", "Mock selected conventional activity timeline after discovery."),
        ]
        selected = []
        for filename, role, reason in roles:
            selected.append(
                {
                    "source_path": f"{source_path}\\{filename}" if source_path else filename,
                    "role": role,
                    "reason": reason,
                }
            )
        return selected
