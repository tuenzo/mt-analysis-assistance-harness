import json
from pathlib import Path

from app.projects.service import ProjectService
from app.tools.schemas import ToolResult


RESULT_FILES = {
    "diagnostics": ".analysis/diagnostics_result.json",
    "localgap": ".analysis/localgap_result.json",
    "psm_did": ".analysis/psm_did_result.json",
    "uplift": ".analysis/uplift_result.json",
}


def result_get_latest(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="result.get_latest",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    workspace_path = Path(project.workspace_path)
    latest_data = {}

    for name, relative_path in RESULT_FILES.items():
        path = workspace_path / relative_path
        if not path.exists():
            continue
        try:
            latest_data[name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

    available_results = list(latest_data.keys())
    if not available_results:
        return ToolResult(ok=True, action="result.get_latest", summary="No analysis results are available yet.", artifacts=[])

    latest_path = workspace_path / ".analysis" / "latest_result.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(latest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="result.get_latest",
        summary=f"Loaded {len(available_results)} analysis result(s): {', '.join(available_results)}.",
        artifacts=[
            {
                "type": "result_summary",
                "title": "latest_result.json",
                "path": str(latest_path.relative_to(workspace_path)),
                "available": available_results,
                "data": latest_data,
            }
        ],
        assistant_hint=(
            "Use available result names as the source of truth. If uplift is present, "
            "analysis.run_gps_uplift has completed for the latest pipeline."
        ),
    )


def artifact_read(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="artifact.read",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found"},
        )

    artifact_path = payload.get("path")
    if not artifact_path:
        return ToolResult(
            ok=False,
            action="artifact.read",
            summary="",
            error={"code": "MISSING_PATH", "message": "A path parameter is required."},
        )

    full_path = Path(project.workspace_path) / artifact_path
    if not full_path.exists():
        return ToolResult(
            ok=False,
            action="artifact.read",
            summary="",
            error={"code": "NOT_FOUND", "message": f"File does not exist: {artifact_path}"},
        )

    if full_path.suffix == ".json":
        data = json.loads(full_path.read_text(encoding="utf-8"))
        return ToolResult(
            ok=True,
            action="artifact.read",
            summary=f"Read {artifact_path}.",
            artifacts=[{"type": "data_file", "path": artifact_path, "data": data}],
        )

    return ToolResult(
        ok=True,
        action="artifact.read",
        summary=f"Read {artifact_path}.",
        artifacts=[{"type": "file", "path": artifact_path}],
    )
