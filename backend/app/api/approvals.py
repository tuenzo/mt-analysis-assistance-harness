from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.tools.gateway import get_gateway

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalRequest(BaseModel):
    scope: str = "project"


@router.post("/{approval_id}/approve")
def approve_tool_call(approval_id: str):
    gateway = get_gateway()
    result = gateway.resume_from_approval(approval_id, approved=True)
    if not result.ok and result.error:
        raise HTTPException(status_code=400, detail=result.error.get("message", "Approval failed"))
    return {"ok": True, "result": result.model_dump()}


@router.post("/{approval_id}/reject")
def reject_tool_call(approval_id: str):
    gateway = get_gateway()
    result = gateway.resume_from_approval(approval_id, approved=False)
    return {"ok": True, "result": result.model_dump()}
