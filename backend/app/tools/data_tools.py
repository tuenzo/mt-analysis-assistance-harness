from pathlib import Path

from app.analysis.pipelines.build_panel import validate_files
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
    return ToolResult(
        ok=True,
        action="data.discover_source_files",
        summary=f"Discovered {len(result['candidates'])} item(s), including {csv_count} CSV candidate(s).",
        artifacts=[{"type": "data_source_discovery", **result}],
        assistant_hint=(
            "Inspect headers and previews, then call data.ingest with selected_files: "
            "[{source_path, role, reason}]. Do not ingest files you cannot classify."
        ),
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
    return ToolResult(
        ok=True,
        action="data.ingest",
        summary=f"Imported {imported_count} CSV file(s), skipped {skipped_count} item(s).",
        artifacts=[{"type": "data_ingest_result", **result}],
        state_patch={"current_stage": "data_uploaded"} if imported_count else {},
        assistant_hint="Next run schema.infer and data.validate." if imported_count else "No CSV files were imported.",
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

    workspace_path = Path(project.workspace_path)
    val_result = validate_files(workspace_path)

    issues = val_result.issues.copy()
    warnings = val_result.warnings.copy()
    file_info = val_result.file_info

    ok = val_result.ok
    summary = "Data validation passed" if ok else f"Found {len(issues)} issue(s)"

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
        assistant_hint="Fix missing or invalid files before continuing." if not ok else "Data validation passed; continue analysis.",
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
    return ToolResult(ok=True, action="schema.apply_mapping", summary="Field mapping saved (stub).")
