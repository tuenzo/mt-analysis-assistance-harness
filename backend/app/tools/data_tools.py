from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService
from app.analysis.pipelines.build_panel import validate_files


def data_ingest(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="data.ingest", summary="数据接入完成（stub）")


def data_validate(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="data.validate", summary="", error={"code": "NOT_FOUND", "message": "Project not found"})

    workspace_path = Path(project.workspace_path)
    val_result = validate_files(workspace_path)

    issues = val_result.issues.copy()
    warnings = val_result.warnings.copy()
    file_info = val_result.file_info

    ok = val_result.ok
    summary = "数据校验通过" if ok else f"发现 {len(issues)} 个问题"

    artifacts = [{"type": "validation_report", "title": "数据质量报告", "issues": issues, "warnings": warnings}]
    for role, info in file_info.items():
        artifacts.append({
            "type": "file_info",
            "role": role,
            "rows": info.get("rows", 0),
            "columns": info.get("columns", []),
        })

    return ToolResult(
        ok=ok,
        action="data.validate",
        summary=summary,
        artifacts=artifacts,
        assistant_hint="如果有问题，请上传缺失文件或修正数据。" if not ok else "数据校验通过，可以继续分析。"
    )


def schema_infer(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="schema.infer", summary="Schema 推断完成（stub）")


def schema_apply_mapping(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="schema.apply_mapping", summary="字段映射已保存（stub）")
