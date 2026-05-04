from pathlib import Path
from app.tools.schemas import ToolResult
from app.projects.service import ProjectService


def data_ingest(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="data.ingest", summary="数据接入完成（stub）")


def data_validate(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(ok=False, action="data.validate", summary="", error={"code": "NOT_FOUND", "message": "Project not found"})

    files = service.list_files(project_id)
    missing = []
    issues = []

    required_roles = ["order_info", "exposure_info", "activity_timeline"]
    current_roles = {f.role for f in files}

    for role in required_roles:
        if role not in current_roles:
            missing.append(role)

    if missing:
        issues.append(f"缺少文件类型: {', '.join(missing)}")

    workspace_path = Path(project.workspace_path)
    for f in files:
        fpath = workspace_path / f.current_path
        if not fpath.exists():
            issues.append(f"文件不存在: {f.original_name}")

    ok = len(missing) == 0 and len(issues) == 0
    return ToolResult(
        ok=ok,
        action="data.validate",
        summary="数据校验完成" if ok else f"发现 {len(issues)} 个问题",
        artifacts=[{"type": "validation_report", "title": "数据质量报告", "issues": issues, "missing": missing}],
        assistant_hint="如果有问题，请上传缺失文件。" if not ok else "数据校验通过。"
    )


def schema_infer(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="schema.infer", summary="Schema 推断完成（stub）")


def schema_apply_mapping(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(ok=True, action="schema.apply_mapping", summary="字段映射已保存（stub）")
