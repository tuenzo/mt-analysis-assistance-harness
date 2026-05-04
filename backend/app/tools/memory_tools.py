import uuid
from datetime import datetime
from app.tools.schemas import ToolResult
from app.core.database import get_session
from app.projects.models import MemoryCandidate
from app.memory.bridge import MemoryBridge
from app.projects.service import ProjectService
from pathlib import Path


def memory_propose_update(project_id: str, payload: dict) -> ToolResult:
    content = payload.get("content", "")
    scope = payload.get("scope", "project")

    if not content:
        return ToolResult(ok=False, action="memory.propose_update", summary="", error={"code": "EMPTY_CONTENT", "message": "记忆内容不能为空"})

    db = get_session()
    try:
        candidate = MemoryCandidate(
            id=uuid.uuid4().hex,
            project_id=project_id,
            scope=scope,
            content=content,
            status="pending",
            created_at=datetime.now().isoformat(),
        )
        db.add(candidate)
        db.commit()

        return ToolResult(
            ok=True,
            action="memory.propose_update",
            summary=f"记忆候选已创建，等待审批",
            artifacts=[{"type": "memory_summary", "candidate_id": candidate.id, "scope": scope}],
            assistant_hint="记忆候选已生成，请在 Memory Review Panel 中审批。"
        )
    finally:
        db.close()


def memory_generate_summary(project_id: str, payload: dict) -> ToolResult:
    """从分析结果生成记忆摘要"""
    bridge = MemoryBridge()
    return bridge.generate_summary(project_id)


def memory_get(project_id: str, payload: dict) -> ToolResult:
    """获取项目记忆"""
    scope = payload.get("scope", "project")
    bridge = MemoryBridge()
    return bridge.get_memory(project_id, scope)


def memory_approve(project_id: str, candidate_id: str, content: str, scope: str) -> ToolResult:
    """审批通过，写入记忆存储"""
    bridge = MemoryBridge()
    return bridge.approve_and_store(project_id, candidate_id, content, scope)
