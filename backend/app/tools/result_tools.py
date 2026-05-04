import json
from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService


def result_get_latest(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="result.get_latest", summary="", error={"code": "NOT_FOUND", "message": "Project not found"})

    result_path = Path(project.workspace_path) / ".analysis" / "latest_result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        return ToolResult(ok=True, action="result.get_latest", summary="读取最新结果", artifacts=[{"type": "result_summary", "data": result}])
    return ToolResult(ok=True, action="result.get_latest", summary="暂无分析结果", artifacts=[])


def artifact_read(project_id: str, payload: dict) -> ToolResult:
    artifact_id = payload.get("artifact_id")
    return ToolResult(ok=True, action="artifact.read", summary=f"Artifact {artifact_id} 读取完成（stub）")
