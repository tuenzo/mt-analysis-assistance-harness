import uuid
import re
from abc import ABC, abstractmethod
from typing import Generator, Optional
from datetime import datetime


class ClaudeRuntimeAdapter(ABC):
    @abstractmethod
    def create_session(self, project_id: str) -> str:
        """Create session, return external_session_id"""
        pass

    @abstractmethod
    def resume_session(self, session_id: str, project_id: str) -> None:
        """Resume existing session"""
        pass

    @abstractmethod
    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        """Send message, yield events"""
        pass

    @abstractmethod
    def interrupt(self, session_id: str) -> None:
        """Interrupt running session"""
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

        is_analysis = any(kw in msg_lower for kw in ["分析", "帮我", "运行", "跑", "generate", "run", "analyze"])
        is_status = any(kw in msg_lower for kw in ["状态", "项目", "当前", "state", "status", "project"])

        yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "收到您的消息，"}

        if is_analysis:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "正在分析当前项目状态..."}
            yield {
                "type": "tool_call_started", "turn_id": turn_id,
                "tool": "business_analysis", "action": "project.get_state"
            }
            yield {
                "type": "tool_call_finished", "turn_id": turn_id,
                "tool": "business_analysis", "action": "project.get_state", "ok": True
            }
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "正在检查数据文件..."}
            yield {
                "type": "tool_call_started", "turn_id": turn_id,
                "tool": "business_analysis", "action": "data.validate"
            }
            yield {
                "type": "tool_call_finished", "turn_id": turn_id,
                "tool": "business_analysis", "action": "data.validate", "ok": True
            }
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "数据校验完成。"}
            yield {
                "type": "final_answer", "turn_id": turn_id,
                "message": f"项目「{context.get('project_name', 'unknown')}」当前处于「{context.get('current_stage', 'unknown')}」阶段。数据质量：{context.get('data_quality', 'unknown')}。如需运行完整分析，请说「帮我运行完整 pipeline」。"
            }

        elif is_status:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "正在获取项目状态..."}
            yield {
                "type": "tool_call_started", "turn_id": turn_id,
                "tool": "business_analysis", "action": "project.get_state"
            }
            yield {
                "type": "tool_call_finished", "turn_id": turn_id,
                "tool": "business_analysis", "action": "project.get_state", "ok": True
            }
            yield {
                "type": "final_answer", "turn_id": turn_id,
                "message": f"项目「{context.get('project_name', 'unknown')}」当前阶段：{context.get('current_stage', 'unknown')}。文件数量：{len(context.get('files', []))}。"
            }

        else:
            yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": "您好！我是商业分析助手。"}
            yield {
                "type": "final_answer", "turn_id": turn_id,
                "message": "我可以帮您分析商业数据、上传文件、运行模型和生成报告。请问有什么可以帮您？"
            }

    def interrupt(self, session_id: str) -> None:
        self._interrupted.add(session_id)
        if session_id in self._sessions:
            self._sessions[session_id]["interrupted"] = True
