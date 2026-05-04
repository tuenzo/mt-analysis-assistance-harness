import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.database import get_session
from app.projects.models import ToolCall, ApprovalRequest, Job
from app.tools.registry import get_registry
from app.tools.schemas import BusinessAnalysisAction, ToolResult, ToolError
from app.core.permissions import action_to_permission_level, HIGH_RISK_ACTIONS, RISK_LEVEL_MAP, PermissionLevel


class AnalysisToolGateway:
    def __init__(self):
        self.registry = get_registry()

    def execute(
        self,
        tool_call_id: str,
        project_id: str,
        action_str: str,
        payload: dict,
        reason: str,
        session_id: str = "",
        turn_id: str = "",
        user_permission_level: int = PermissionLevel.SAFE_COMPUTE,
    ) -> ToolResult:
        try:
            action = BusinessAnalysisAction(action_str)
        except ValueError:
            return ToolResult(
                ok=False,
                action=action_str,
                summary="",
                error={"code": "INVALID_ACTION", "message": f"Unknown action: {action_str}", "details": {}},
                assistant_hint="请使用有效的 action。"
            )

        tool_info = self.registry.get_tool(action)
        if tool_info is None:
            return ToolResult(
                ok=False,
                action=action_str,
                summary="",
                error={"code": "ACTION_NOT_FOUND", "message": f"Action not registered: {action_str}", "details": {}},
            )

        tool_func, required_level = tool_info

        if user_permission_level < required_level.value:
            return ToolResult(
                ok=False,
                action=action_str,
                summary="",
                error={"code": "PERMISSION_DENIED", "message": "权限不足", "details": {"required": required_level.value, "actual": user_permission_level}},
                assistant_hint="此操作需要更高权限。"
            )

        db = get_session()
        try:
            tc = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
            if tc:
                tc.status = "running"
                db.commit()

            if action in HIGH_RISK_ACTIONS:
                approval = ApprovalRequest(
                    id=uuid.uuid4().hex,
                    project_id=project_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    action=action_str,
                    reason=reason,
                    risk_level=RISK_LEVEL_MAP.get(action, "medium"),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    status="pending",
                    created_at=datetime.now().isoformat(),
                )
                db.add(approval)
                if tc:
                    tc.status = "waiting_approval"
                    tc.approval_request_id = approval.id
                db.commit()

                self._write_tool_call_log({
                    "tool_call_id": tool_call_id,
                    "action": action_str,
                    "status": "waiting_approval",
                    "timestamp": datetime.now().isoformat(),
                })

                return ToolResult(
                    ok=True,
                    action=action_str,
                    summary="需要用户审批",
                    state_patch={},
                    assistant_hint="此操作需要用户审批，请在 UI 中确认。"
                )

            result = tool_func(project_id, payload)

            if tc:
                tc.status = "succeeded"
                tc.result_json = json.dumps(result.model_dump(), ensure_ascii=False)
                tc.completed_at = datetime.now().isoformat()
            db.commit()

            self._write_tool_call_log({
                "tool_call_id": tool_call_id,
                "action": action_str,
                "status": "succeeded",
                "timestamp": datetime.now().isoformat(),
            })

            return result

        except Exception as e:
            if tc:
                tc.status = "failed"
                tc.error_message = str(e)
                tc.completed_at = datetime.now().isoformat()
                db.commit()

            self._write_tool_call_log({
                "tool_call_id": tool_call_id,
                "action": action_str,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })

            return ToolResult(
                ok=False,
                action=action_str,
                summary="",
                error={"code": "EXECUTION_ERROR", "message": str(e), "details": {}},
            )
        finally:
            db.close()

    def _write_tool_call_log(self, log_entry: dict):
        try:
            log_path = Path("./workspaces") / "tool_calls.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def resume_from_approval(self, approval_id: str, approved: bool) -> ToolResult:
        db = get_session()
        try:
            approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
            if not approval:
                return ToolResult(ok=False, action="", summary="", error={"code": "NOT_FOUND", "message": "Approval not found"})

            if not approved:
                approval.status = "rejected"
                approval.resolved_at = datetime.now().isoformat()
                tc = db.query(ToolCall).filter(ToolCall.id == approval.tool_call_id).first()
                if tc:
                    tc.status = "rejected"
                db.commit()
                return ToolResult(ok=False, action=approval.action, summary="用户拒绝审批", error={"code": "REJECTED", "message": "User rejected"})

            approval.status = "approved"
            approval.resolved_at = datetime.now().isoformat()
            db.commit()

            tc = db.query(ToolCall).filter(ToolCall.id == approval.tool_call_id).first()
            if tc:
                payload = json.loads(approval.payload_json)
                result = self.execute(
                    tool_call_id=tc.id,
                    project_id=approval.project_id,
                    action_str=approval.action,
                    payload=payload,
                    reason=approval.reason or "",
                    session_id=approval.session_id or "",
                    turn_id=approval.turn_id or "",
                    user_permission_level=PermissionLevel.EXTERNAL_SYNC,
                )
                return result

            return ToolResult(ok=True, action=approval.action, summary="审批通过，已执行")
        finally:
            db.close()


_gateway: Optional[AnalysisToolGateway] = None


def get_gateway() -> AnalysisToolGateway:
    global _gateway
    if _gateway is None:
        _gateway = AnalysisToolGateway()
    return _gateway
