from app.analysis.pipelines.build_panel import validate_files
from app.core.config import resolve_project_path
from app.projects.service import ProjectService
from app.tools.schemas import ToolResult


def data_discover_source_files(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    try:
        result = service.discover_source_files(
            project_id=project_id,
            source_path=payload.get("source_path"),
        )
    except FileNotFoundError as e:
        return ToolResult(
            ok=False,
            action="data.discover_source_files",
            summary="Data source discovery failed",
            error={"code": "SOURCE_NOT_FOUND", "message": str(e), "details": {}},
            assistant_hint="Ask the user to confirm the local data source directory.",
        )
    except ValueError as e:
        code = "NOT_FOUND" if "not found" in str(e).lower() else "INVALID_SOURCE_PATH"
        return ToolResult(
            ok=False,
            action="data.discover_source_files",
            summary="Data source discovery failed",
            error={"code": code, "message": str(e), "details": {}},
            assistant_hint="Ask the user to set a valid absolute data source directory.",
        )

    csv_count = sum(1 for item in result["candidates"] if not item.get("skipped") and item.get("extension") == ".csv")
    if csv_count == 0:
        assistant_hint = (
            "No importable first-level CSV files were found. Tell the user which items were skipped "
            "and ask for a directory containing order_info, exposure_info, and activity_timeline CSV files."
        )
    else:
        assistant_hint = (
            "Inspect headers and previews, then call data.ingest with selected_files: "
            "[{source_path, role, reason}]. Do not ingest files you cannot classify."
        )
    return ToolResult(
        ok=True,
        action="data.discover_source_files",
        summary=f"Discovered {len(result['candidates'])} item(s), including {csv_count} CSV candidate(s).",
        artifacts=[{"type": "data_source_discovery", **result}],
        assistant_hint=assistant_hint,
    )


def data_ingest(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    try:
        result = service.ingest_data_source(
            project_id=project_id,
            source_path=payload.get("source_path"),
            roles=payload.get("roles"),
            selected_files=payload.get("selected_files"),
        )
    except FileNotFoundError as e:
        return ToolResult(
            ok=False,
            action="data.ingest",
            summary="Data ingest failed",
            error={"code": "SOURCE_NOT_FOUND", "message": str(e), "details": {}},
            assistant_hint="Ask the user to confirm the local data source directory.",
        )
    except ValueError as e:
        code = "NOT_FOUND" if "not found" in str(e).lower() else "INVALID_SOURCE_PATH"
        if "selected_files is required" in str(e):
            code = "SELECTED_FILES_REQUIRED"
        return ToolResult(
            ok=False,
            action="data.ingest",
            summary="Data ingest failed",
            error={"code": code, "message": str(e), "details": {}},
            assistant_hint="Ask the user to set a valid absolute data source directory.",
        )

    imported_count = result["imported_count"]
    skipped_count = result["skipped_count"]
    if imported_count:
        assistant_hint = "Next run schema.infer, then data.validate. Do not call data load complete until validation succeeds."
    else:
        skipped = ", ".join(f"{item.get('name') or '(missing name)'}:{item.get('reason')}" for item in result["skipped"])
        assistant_hint = (
            "No CSV files were imported. Explain the skipped selections and fix the selected_files payload "
            f"or ask the user for corrected files/source directory. Skipped: {skipped or 'none'}."
        )

    return ToolResult(
        ok=True,
        action="data.ingest",
        summary=f"Imported {imported_count} CSV file(s), skipped {skipped_count} item(s).",
        artifacts=[{"type": "data_ingest_result", **result}],
        state_patch={"current_stage": "data_uploaded"} if imported_count else {},
        assistant_hint=assistant_hint,
    )


def data_validate(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    project = service.get_project(project_id)
    if not project:
        return ToolResult(
            ok=False,
            action="data.validate",
            summary="",
            error={"code": "NOT_FOUND", "message": "Project not found", "details": {}},
        )

    workspace_path = resolve_project_path(project.workspace_path)
    val_result = validate_files(workspace_path)

    issues = val_result.issues.copy()
    warnings = val_result.warnings.copy()
    file_info = val_result.file_info

    ok = val_result.ok
    summary = "Data validation passed" if ok else f"Found {len(issues)} issue(s)"
    state_patch = service.mark_data_validation(
        project_id=project_id,
        validation_ok=ok,
        file_info=file_info,
        issues=issues,
        warnings=warnings,
    )

    artifacts = [{"type": "validation_report", "title": "Data quality report", "issues": issues, "warnings": warnings}]
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
        state_patch=state_patch,
        assistant_hint=(
            "Data load is complete. Continue with panel.build_category_day or analysis."
            if ok
            else "Data load remains partial. Explain these validation issues and ask for corrected files or mappings."
        ),
    )


def schema_infer(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    files = service.infer_schema(project_id)
    if not files:
        return ToolResult(
            ok=False,
            action="schema.infer",
            summary="No project files found for schema inference.",
            error={"code": "NO_FILES", "message": "Upload or ingest CSV files before schema inference.", "details": {}},
            assistant_hint="Ask the user to upload or ingest order, exposure, and activity CSV files.",
        )

    mapped_count = sum(1 for item in files if item.get("recommended_mappings"))
    return ToolResult(
        ok=True,
        action="schema.infer",
        summary=f"Schema inference completed for {len(files)} file(s); {mapped_count} file(s) have recommended mappings.",
        artifacts=[{"type": "schema_inference", "title": "Recommended schema mappings", "files": files}],
        assistant_hint="Review recommended mappings, then run data.validate or schema.apply_mapping if overrides are needed.",
    )


def schema_apply_mapping(project_id: str, payload: dict) -> ToolResult:
    service = ProjectService()
    result = service.apply_schema(project_id, payload.get("mappings") or {})
    if result.get("status") == "not_found":
        return ToolResult(
            ok=False,
            action="schema.apply_mapping",
            summary="Project not found.",
            error={"code": "NOT_FOUND", "message": "Project not found", "details": {}},
        )
    return ToolResult(
        ok=True,
        action="schema.apply_mapping",
        summary="Field mapping saved.",
        state_patch={"current_stage": "schema_mapping"},
        assistant_hint="Run data.validate after applying mappings.",
    )
