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

        msg_lower = message.lower()
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        source_path = self._extract_source_path(message)

        is_data_load = any(
            kw in msg_lower
            for kw in ["dataload", "data load", "load data", "ingest", "csv", "加载", "导入", "数据加载"]
        )
        is_analysis = any(
            kw in msg_lower
            for kw in ["analysis", "analyze", "generate", "run", "pipeline", "diagnostic", "分析", "运行", "生成"]
        )
        is_status = any(kw in msg_lower for kw in ["state", "status", "project", "current", "状态", "项目"])

        yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "收到。"}

        if is_data_load:
            yield {
                "type": "assistant_message_delta",
                "turn_id": turn_id,
                "delta": "我会先发现源文件，再导入、推断 schema 并校验数据。",
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
                    "我已按 project.get_state -> data.discover_source_files -> data.ingest -> "
                    "schema.infer -> data.validate 的顺序尝试完成数据加载。若校验仍为 partial，"
                    "请查看工具结果中的缺失角色、跳过文件或字段问题，我会基于这些问题继续给出修正方案。"
                ),
            }
            return

        if is_analysis:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "我先检查当前项目状态。"}
            yield self._tool_started(turn_id, "project.get_state", {})
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "接着检查数据文件。"}
            yield self._tool_started(turn_id, "data.validate", {})
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "数据校验已执行。"}
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    f"项目 {context.get('project_name', 'unknown')} 当前处于 "
                    f"{context.get('current_stage', 'unknown')} 阶段；"
                    f"数据质量为 {context.get('data_quality', 'unknown')}。"
                ),
            }
            return

        if is_status:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "正在获取项目状态。"}
            yield self._tool_started(turn_id, "project.get_state", {})
            yield {
                "type": "final_answer",
                "turn_id": turn_id,
                "message": (
                    f"项目 {context.get('project_name', 'unknown')} 当前阶段："
                    f"{context.get('current_stage', 'unknown')}；"
                    f"文件数量：{len(context.get('files', []))}。"
                ),
            }
            return

        yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "你好，我是商业分析助手。"}
        yield {
            "type": "final_answer",
            "turn_id": turn_id,
            "message": "我可以帮你加载文件、诊断数据、运行分析模型并生成报告。你想先做哪一步？",
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
        }

    @staticmethod
    def _extract_source_path(message: str) -> str | None:
        quoted = re.search(r'["\']([A-Za-z]:[\\/][^"\']+)["\']', message)
        if quoted:
            return quoted.group(1).strip()
        match = re.search(r"([A-Za-z]:[\\/][^\s\r\n\"']+)", message)
        if not match:
            return None
        return match.group(1).strip().rstrip(" .。；;,，")

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
