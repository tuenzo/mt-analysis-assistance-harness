import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.database import get_session
from app.projects.models import ApprovalRequest as ApprovalRequestModel, ToolCall
from app.agent.message_runtime import get_message_runtime
from app.jobs.pipeline_runner import run_approved_full_pipeline
from app.tools.gateway import get_gateway

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalRequest(BaseModel):
    scope: str = "project"


@router.get("")
def list_pending_approvals(project_id: str, session_id: str | None = None):
    db = get_session()
    try:
        query = db.query(ApprovalRequestModel).filter(
            ApprovalRequestModel.project_id == project_id,
            ApprovalRequestModel.status == "pending",
        )
        if session_id:
            query = query.filter(ApprovalRequestModel.session_id == session_id)
        approvals = query.order_by(ApprovalRequestModel.created_at.asc()).all()
        return {
            "ok": True,
            "data": [
                {
                    "id": approval.id,
                    "turn_id": approval.turn_id,
                    "action": approval.action,
                    "reason": approval.reason or "",
                    "risk_level": approval.risk_level,
                    "payload": json.loads(approval.payload_json or "{}"),
                    "created_at": approval.created_at,
                }
                for approval in approvals
            ],
        }
    finally:
        db.close()


@router.post("/{approval_id}/approve")
def approve_tool_call(approval_id: str):
    special_result = _run_full_pipeline_approval(approval_id)
    if special_result is not None:
        return special_result

    gateway = get_gateway()
    result = gateway.resume_from_approval(approval_id, approved=True)
    if not result.ok and result.error:
        raise HTTPException(status_code=400, detail=result.error.get("message", "Approval failed"))

    events = _events_for_simple_approval(approval_id, result.model_dump())
    if events:
        runtime = get_message_runtime()
        first = events[0]
        runtime.publish_events(
            first["session_id"],
            first["project_id"],
            first["turn_id"],
            [{k: v for k, v in event.items() if k not in {"session_id", "project_id"}} for event in events],
        )
    return {"ok": True, "data": {"result": result.model_dump(), "events": _public_events(events)}}


@router.post("/{approval_id}/reject")
def reject_tool_call(approval_id: str):
    gateway = get_gateway()
    result = gateway.resume_from_approval(approval_id, approved=False)
    events = _events_for_simple_approval(approval_id, result.model_dump(), rejected=True)
    if events:
        runtime = get_message_runtime()
        first = events[0]
        runtime.publish_events(
            first["session_id"],
            first["project_id"],
            first["turn_id"],
            [{k: v for k, v in event.items() if k not in {"session_id", "project_id"}} for event in events],
        )
    return {"ok": True, "data": {"result": result.model_dump(), "events": _public_events(events)}}


def _run_full_pipeline_approval(approval_id: str):
    db = get_session()
    try:
        approval = db.query(ApprovalRequestModel).filter(ApprovalRequestModel.id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.action != "analysis.run_full_pipeline":
            return None

        if approval.status != "pending":
            raise HTTPException(status_code=400, detail=f"Approval is already {approval.status}")

        approval.status = "approved"
        from datetime import datetime

        approval.resolved_at = datetime.now().isoformat()
        tool_call = db.query(ToolCall).filter(ToolCall.id == approval.tool_call_id).first()
        payload = json.loads(approval.payload_json or "{}")

        result, events = run_approved_full_pipeline(
            db,
            project_id=approval.project_id,
            session_id=approval.session_id or "",
            turn_id=approval.turn_id or "",
            tool_call=tool_call,
            payload=payload,
        )
        db.commit()

        if approval.session_id and approval.turn_id:
            get_message_runtime().publish_events(approval.session_id, approval.project_id, approval.turn_id, events)

        return {"ok": True, "data": {"result": result.model_dump(), "events": events}}
    finally:
        db.close()


def _events_for_simple_approval(approval_id: str, result: dict, rejected: bool = False) -> list[dict]:
    db = get_session()
    try:
        approval = db.query(ApprovalRequestModel).filter(ApprovalRequestModel.id == approval_id).first()
        if not approval or not approval.session_id or not approval.turn_id:
            return []
        return [
            {
                "type": "tool_call_finished" if result.get("ok") else "tool_call_failed",
                "session_id": approval.session_id,
                "project_id": approval.project_id,
                "turn_id": approval.turn_id,
                "tool": "business_analysis",
                "action": approval.action,
                "ok": bool(result.get("ok")) and not rejected,
                "summary": result.get("summary", ""),
                "sdk_executed": True,
            },
            {
                "type": "final_answer",
                "session_id": approval.session_id,
                "project_id": approval.project_id,
                "turn_id": approval.turn_id,
                "message": result.get("summary", "Approval handled."),
            },
        ]
    finally:
        db.close()


def _public_events(events: list[dict]) -> list[dict]:
    return [{k: v for k, v in event.items() if k not in {"session_id", "project_id"}} for event in events]
