import uuid
from datetime import datetime
from app.tools.schemas import ToolResult
from app.core.database import get_session
from app.projects.models import MemoryCandidate


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
