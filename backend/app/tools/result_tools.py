import json
from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService


def result_get_latest(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="result.get_latest", summary="", error={"code": "NOT_FOUND", "message": "Project not found"})

    workspace_path = Path(project.workspace_path)
    analysis_dir = workspace_path / ".analysis"

    available_results = []
    latest_data = {}

    result_files = {
        "diagnostics": analysis_dir / "diagnostics_result.json",
        "localgap": analysis_dir / "localgap_result.json",
        "psm_did": analysis_dir / "psm_did_result.json",
    }

    for name, path in result_files.items():
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                available_results.append(name)
                latest_data[name] = data
            except Exception:
                pass

    if available_results:
        latest_path = analysis_dir / "latest_result.json"
        latest_path.write_text(json.dumps(latest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return ToolResult(
            ok=True,
            action="result.get_latest",
            summary=f"读取到 {len(available_results)} 个分析结果",
            artifacts=[{"type": "result_summary", "available": available_results, "data": latest_data}],
        )
    return ToolResult(ok=True, action="result.get_latest", summary="暂无分析结果", artifacts=[])


def artifact_read(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="artifact.read", summary="", error={"code": "NOT_FOUND", "message": "Project not found"})

    artifact_path = payload.get("path")
    if not artifact_path:
        return ToolResult(ok=False, action="artifact.read", summary="", error={"code": "MISSING_PATH", "message": "需要提供 path 参数"})

    full_path = Path(project.workspace_path) / artifact_path
    if not full_path.exists():
        return ToolResult(ok=False, action="artifact.read", summary="", error={"code": "NOT_FOUND", "message": f"文件不存在: {artifact_path}"})

    if full_path.suffix == ".json":
        data = json.loads(full_path.read_text(encoding="utf-8"))
        return ToolResult(
            ok=True,
            action="artifact.read",
            summary=f"读取 {artifact_path}",
            artifacts=[{"type": "data_file", "path": artifact_path, "data": data}],
        )

    return ToolResult(ok=True, action="artifact.read", summary=f"读取 {artifact_path}", artifacts=[{"type": "file", "path": artifact_path}])
