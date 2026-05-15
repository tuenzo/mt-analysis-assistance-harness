from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import resolve_project_path
from app.core.database import get_session
from app.projects.models import AnalysisSession, Job, Project, ProjectFile
from app.tools.schemas import ToolResult
from app.workspace.manifest import ProjectManifest, compute_file_checksum


REQUIRED_RAW_ROLES = ("order_info", "exposure_info", "activity_timeline")
RESULT_PATHS = {
    "diagnostics": ".analysis/diagnostics_result.json",
    "psm_did": ".analysis/psm_did_result.json",
    "localgap": ".analysis/localgap_result.json",
    "mechanism": ".analysis/mechanism_regression_result.json",
    "conversion": ".analysis/conversion_diagnostics_result.json",
    "uplift": ".analysis/uplift_result.json",
    "latest": ".analysis/latest_result.json",
    "latest_index": ".analysis/latest_result_index.json",
}
BLOCKING_ACTIONS = {"data.validate", "panel.build_category_day", "quality.audit_lineage"}
DOWNSTREAM_EVIDENCE_ACTIONS = {
    "analysis.run_diagnostics",
    "analysis.run_psm_did",
    "analysis.run_localgap",
    "analysis.run_mechanism_regression",
    "analysis.run_conversion_diagnostics",
    "analysis.run_gps_uplift",
    "chart.render_dashboard",
    "result.get_latest",
    "report.generate",
}


def quality_audit_lineage(project_id: str, payload: dict) -> ToolResult:
    audit = build_lineage_audit(project_id)
    status = audit["overall_status"]
    return ToolResult(
        ok=True,
        action="quality.audit_lineage",
        summary=f"Lineage audit {status}: {len(audit['issues'])} issue(s), {len(audit['warnings'])} warning(s).",
        artifacts=[{"type": "lineage_audit", "title": "Project lineage audit", "data": audit}],
        assistant_hint=(
            "If any gate failed, explain the blocking issues before running or interpreting analysis results."
        ),
    )


def quality_score_reference_alignment(project_id: str, payload: dict) -> ToolResult:
    audit = build_lineage_audit(project_id)
    workspace = Path(audit.get("workspace_path") or "")
    if audit.get("project_found") and workspace.exists():
        score = build_reference_alignment_score(workspace, audit)
        analysis_dir = workspace / ".analysis"
        table_dir = workspace / "artifacts" / "tables"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        table_dir.mkdir(parents=True, exist_ok=True)
        score_path = analysis_dir / "reference_alignment_score.json"
        diff_path = table_dir / "reference_alignment_diffs.csv"
        score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_diff_rows(diff_path, score["diffs"])
        artifacts = [
            {
                "type": "quality_score",
                "title": "reference_alignment_score.json",
                "path": str(score_path.relative_to(workspace)),
                "score": score["final_score"],
                "raw_score": score["raw_score"],
                "applied_caps": score["applied_caps"],
            },
            {
                "type": "quality_diff_table",
                "title": "reference_alignment_diffs.csv",
                "path": str(diff_path.relative_to(workspace)),
                "rows": len(score["diffs"]),
            },
        ]
        summary = (
            f"Reference alignment score={score['final_score']}/100 "
            f"(raw={score['raw_score']}, caps={len(score['applied_caps'])})."
        )
        return ToolResult(
            ok=True,
            action="quality.score_reference_alignment",
            summary=summary,
            artifacts=artifacts,
            assistant_hint="Use the cap reasons and diff table to guide the next optimization round.",
        )

    return ToolResult(
        ok=False,
        action="quality.score_reference_alignment",
        summary="Reference alignment scoring failed.",
        error={
            "code": "PROJECT_LINEAGE_UNAVAILABLE",
            "message": "Project or workspace could not be resolved for scoring.",
            "details": {"issues": audit.get("issues", [])},
        },
        assistant_hint="Fix project binding and workspace lineage before scoring reference alignment.",
    )


def build_lineage_audit(project_id: str) -> dict[str, Any]:
    db = get_session()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return _audit_payload(
                project_id=project_id,
                workspace_path=None,
                project_found=False,
                gates={},
                issues=[_issue("project_not_found", "Project record was not found.", "database")],
                warnings=[],
                source_inventory=[],
                result_artifacts=[],
                pipeline_findings=[],
                demo_indicators=[],
            )

        workspace = resolve_project_path(project.workspace_path)
        project_files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        sessions = db.query(AnalysisSession).filter(AnalysisSession.project_id == project_id).all()
        jobs = (
            db.query(Job)
            .filter(Job.project_id == project_id, Job.action == "analysis.run_full_pipeline")
            .order_by(Job.created_at.desc(), Job.id.desc())
            .all()
        )

        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        gates: dict[str, dict[str, Any]] = {}

        if not workspace.exists():
            issues.append(_issue("workspace_missing", f"Workspace does not exist: {workspace}", "workspace"))

        manifest_data, manifest_errors = _load_manifest(workspace)
        issues.extend(manifest_errors)
        if manifest_data and manifest_data.get("project_id") != project_id:
            issues.append(
                _issue(
                    "manifest_project_mismatch",
                    f"Manifest project_id={manifest_data.get('project_id')} does not match database project_id={project_id}.",
                    ".analysis/project_manifest.json",
                )
            )
        issues.extend(_checksum_issues(workspace, manifest_data))

        source_inventory = _source_inventory(workspace, project_files)
        raw_roles = {
            role: [item for item in source_inventory if item["role"] == role and item["is_raw"]]
            for role in REQUIRED_RAW_ROLES
        }
        missing_roles = [role for role, items in raw_roles.items() if not items]
        valid_panel = _has_explicit_valid_panel(workspace, source_inventory)
        if missing_roles and not valid_panel:
            issues.append(
                _issue(
                    "source_roles_missing",
                    f"Missing required raw source role(s): {', '.join(missing_roles)}.",
                    "data/raw",
                    {"missing_roles": missing_roles},
                )
            )

        processed_as_raw = [
            item for item in source_inventory if item["role"] in REQUIRED_RAW_ROLES and item.get("looks_processed_panel")
        ]
        if processed_as_raw:
            issues.append(
                _issue(
                    "processed_panel_as_raw",
                    "Processed category-day panel candidate is registered as a raw source role.",
                    "project_files",
                    {"files": [item["path"] for item in processed_as_raw]},
                )
            )

        demo_indicators = _demo_indicators(project, workspace, manifest_data, sessions)
        if demo_indicators:
            issues.append(
                _issue(
                    "demo_contamination",
                    "Project contains demo, mock, fixture, or seeded result indicators.",
                    "project/latest_result",
                    {"indicators": demo_indicators},
                )
            )

        result_artifacts = _result_artifacts(workspace)
        pipeline_findings = _pipeline_findings(jobs, workspace, result_artifacts)
        if any(item["code"] == "fatal_pipeline_continued" for item in pipeline_findings):
            issues.append(
                _issue(
                    "fatal_pipeline_continued",
                    "A failed blocking pipeline step was followed by downstream evidence artifacts.",
                    "jobs.output_json",
                    {"findings": pipeline_findings},
                )
            )
        gates["project_binding"] = _gate("pass" if workspace.exists() and manifest_data else "fail")
        gates["manifest"] = _gate(
            "pass"
            if manifest_data
            and not any(issue["code"] in {"manifest_missing", "manifest_project_mismatch", "checksum_mismatch"} for issue in issues)
            else "fail"
        )
        gates["source_roles"] = _gate("pass" if not missing_roles or valid_panel else "fail", {"missing_roles": missing_roles, "valid_panel": valid_panel})
        gates["anti_demo"] = _gate("fail" if demo_indicators else "pass", {"indicators": demo_indicators})
        gates["pipeline_blocking"] = _gate(
            "fail" if any(item["code"] == "fatal_pipeline_continued" for item in pipeline_findings) else "pass",
            {"findings": pipeline_findings},
        )

        return _audit_payload(
            project_id=project_id,
            workspace_path=str(workspace),
            project_found=True,
            gates=gates,
            issues=issues,
            warnings=warnings,
            source_inventory=source_inventory,
            result_artifacts=result_artifacts,
            pipeline_findings=pipeline_findings,
            demo_indicators=demo_indicators,
            project={
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "current_stage": project.current_stage,
                "workspace_path": project.workspace_path,
            },
        )
    finally:
        db.close()


def build_reference_alignment_score(workspace: Path, audit: dict[str, Any]) -> dict[str, Any]:
    results = {name: _read_json(workspace / rel_path) for name, rel_path in RESULT_PATHS.items()}
    diffs: list[dict[str, Any]] = []
    subscores = {
        "lineage": _score_lineage(audit, diffs),
        "core_trend": _score_core_trend(results, diffs),
        "resource_mechanism": _score_resource_mechanism(results, diffs),
        "gps_uplift": _score_gps_uplift(results, diffs),
        "claim_calibration": _score_claim_calibration(workspace, results, audit, diffs),
    }
    raw_score = round(sum(item["score"] for item in subscores.values()), 2)
    applied_caps = _score_caps(audit)
    final_score = raw_score
    if applied_caps:
        final_score = min(final_score, min(item["max_score"] for item in applied_caps))
    final_score = round(max(0.0, min(100.0, final_score)), 2)

    return {
        "method": "reference_alignment_quality_score",
        "method_status": "implemented",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "reference_anchors": {
            "source": "参考报告pdf/【终版】Keemart_业务选题-v2 (2)/business_analysis_report.tex and 参考报告pdf/参考skills.md",
            "target": "trend-level agreement, not exact numeric reproduction",
            "expected_profile": {
                "category_count": 336,
                "date_range": "2025-09-01 to 2025-11-30",
                "activity_days": 33,
                "main_increment_layer": "LocalGap/LMDI",
                "resource_logic": "exposure broad coverage; discount targeted and payday-aware",
            },
        },
        "raw_score": raw_score,
        "final_score": final_score,
        "applied_caps": applied_caps,
        "subscores": subscores,
        "diffs": diffs,
        "lineage_audit": audit,
        "interpretation": _score_interpretation(final_score, applied_caps),
    }


def _audit_payload(**kwargs) -> dict[str, Any]:
    issues = kwargs["issues"]
    gates = kwargs["gates"]
    overall_status = "pass" if not issues and all(gate.get("status") == "pass" for gate in gates.values()) else "fail"
    return {
        **kwargs,
        "overall_status": overall_status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cap_reasons": [issue["code"] for issue in issues if issue["code"] in _CAP_BY_ISSUE],
    }


def _issue(code: str, message: str, evidence: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "evidence": evidence, "details": details or {}}


def _gate(status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": status, "details": details or {}}


def _load_manifest(workspace: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = workspace / ".analysis" / "project_manifest.json"
    if not path.exists():
        return None, [_issue("manifest_missing", "Workspace manifest is missing.", ".analysis/project_manifest.json")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("manifest_invalid_json", f"Workspace manifest is invalid JSON: {exc}", str(path))]
    return data if isinstance(data, dict) else None, []


def _checksum_issues(workspace: Path, manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not manifest:
        return []
    issues: list[dict[str, Any]] = []
    for entry in manifest.get("files") or []:
        rel_path = entry.get("current_path")
        expected = entry.get("checksum")
        if not rel_path or not expected:
            continue
        path = workspace / rel_path
        if not path.exists():
            issues.append(_issue("manifest_file_missing", f"Manifest file is missing: {rel_path}", rel_path))
            continue
        actual = compute_file_checksum(path)
        if actual != expected:
            issues.append(
                _issue(
                    "checksum_mismatch",
                    f"Checksum mismatch for {rel_path}.",
                    rel_path,
                    {"expected": expected, "actual": actual},
                )
            )
    return issues


def _source_inventory(workspace: Path, project_files: list[ProjectFile]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for file_record in project_files:
        path = str(file_record.current_path)
        abs_path = workspace / path
        headers = _read_headers(abs_path) if abs_path.exists() and abs_path.suffix.lower() == ".csv" else []
        looks_processed = _looks_like_processed_panel(abs_path.name, headers)
        inventory.append(
            {
                "source": "database",
                "file_id": file_record.id,
                "role": file_record.role,
                "original_name": file_record.original_name,
                "path": path,
                "status": file_record.status,
                "checksum": file_record.checksum,
                "exists": abs_path.exists(),
                "is_raw": _is_raw_path(path),
                "headers": headers,
                "role_guess": _guess_source_role(abs_path.name, headers),
                "looks_processed_panel": looks_processed,
            }
        )
        seen_paths.add(Path(path).as_posix())

    raw_dir = workspace / "data" / "raw"
    if raw_dir.exists():
        for path in sorted(raw_dir.glob("*.csv"), key=lambda item: item.name.lower()):
            rel_path = path.relative_to(workspace).as_posix()
            if rel_path in seen_paths or rel_path.replace("/", "\\") in seen_paths:
                continue
            headers = _read_headers(path)
            inventory.append(
                {
                    "source": "workspace_scan",
                    "file_id": None,
                    "role": _guess_source_role(path.name, headers),
                    "original_name": path.name,
                    "path": rel_path,
                    "status": "scanned",
                    "checksum": compute_file_checksum(path),
                    "exists": True,
                    "is_raw": True,
                    "headers": headers,
                    "role_guess": _guess_source_role(path.name, headers),
                    "looks_processed_panel": _looks_like_processed_panel(path.name, headers),
                }
            )
    return inventory


def _is_raw_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return normalized.startswith("data/raw/")


def _has_explicit_valid_panel(workspace: Path, inventory: list[dict[str, Any]]) -> bool:
    has_registered_panel = any(
        item["role"] == "category_day_panel" and item["status"] in {"generated", "validated", "scanned"}
        for item in inventory
    )
    has_panel_artifact = (workspace / "data" / "processed" / "category_day_panel.json").exists()
    has_summary = (workspace / ".analysis" / "panel_summary.json").exists()
    return bool(has_registered_panel and has_panel_artifact and has_summary)


def _demo_indicators(
    project: Project,
    workspace: Path,
    manifest: dict[str, Any] | None,
    sessions: list[AnalysisSession],
) -> list[dict[str, str]]:
    indicators: list[dict[str, str]] = []
    haystack = " ".join([project.id or "", project.name or "", str(workspace)]).lower()
    if "demo" in haystack:
        indicators.append({"source": "project_metadata", "reason": "project id/name/path contains demo"})
    if any(session.runtime_provider == "demo" for session in sessions):
        indicators.append({"source": "analysis_sessions", "reason": "runtime_provider=demo"})

    latest = _read_json(workspace / ".analysis" / "latest_result.json")
    if latest and _contains_truthy_demo(latest):
        indicators.append({"source": ".analysis/latest_result.json", "reason": "demo marker present"})
    if manifest and _contains_truthy_demo(manifest.get("latest_result")):
        indicators.append({"source": ".analysis/project_manifest.json", "reason": "manifest latest_result demo marker present"})
    return indicators


def _contains_truthy_demo(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("demo") is True or value.get("showcase") is True:
            return True
        return any(_contains_truthy_demo(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_truthy_demo(item) for item in value)
    if isinstance(value, str):
        text = value.lower()
        return "demo" in text or "fixture" in text or "mock" in text
    return False


def _pipeline_findings(jobs: list[Job], workspace: Path, result_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for job in jobs[:1]:
        try:
            output = json.loads(job.output_json or "{}")
        except json.JSONDecodeError:
            continue
        steps = output.get("steps") or []
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            action = step.get("action")
            if action not in BLOCKING_ACTIONS or step.get("ok") is not False:
                continue
            downstream = [
                later
                for later in steps[index + 1 :]
                if isinstance(later, dict)
                and later.get("ok") is True
                and later.get("action") in DOWNSTREAM_EVIDENCE_ACTIONS
                and _downstream_evidence_still_exists(workspace, result_artifacts, later.get("action"))
            ]
            if downstream:
                findings.append(
                    {
                        "code": "fatal_pipeline_continued",
                        "job_id": job.id,
                        "failed_action": action,
                        "downstream_actions": [item.get("action") for item in downstream],
                    }
                )
    return findings


def _downstream_evidence_still_exists(workspace: Path, result_artifacts: list[dict[str, Any]], action: str | None) -> bool:
    if action in {
        "analysis.run_diagnostics",
        "analysis.run_psm_did",
        "analysis.run_localgap",
        "analysis.run_mechanism_regression",
        "analysis.run_conversion_diagnostics",
        "analysis.run_gps_uplift",
        "result.get_latest",
    }:
        return any(item.get("exists") for item in result_artifacts)
    if action == "chart.render_dashboard":
        return any((workspace / "artifacts" / "charts" / "dashboard").glob("*.png"))
    if action == "report.generate":
        return (workspace / "reports" / "report.md").exists() or any((workspace / "reports").glob("*.pdf"))
    return False


def _result_artifacts(workspace: Path) -> list[dict[str, Any]]:
    artifacts = []
    for name, rel_path in RESULT_PATHS.items():
        path = workspace / rel_path
        artifacts.append({"name": name, "path": rel_path, "exists": path.exists()})
    return artifacts


def _score_lineage(audit: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    score = 20.0
    for issue in audit.get("issues", []):
        code = issue["code"]
        penalty = 0.0
        if code in {"project_not_found", "workspace_missing", "manifest_missing", "manifest_project_mismatch"}:
            penalty = 8.0
        elif code in {"source_roles_missing", "processed_panel_as_raw"}:
            penalty = 7.0
        elif code == "demo_contamination":
            penalty = 7.0
        elif code == "fatal_pipeline_continued":
            penalty = 4.0
        elif code in {"manifest_file_missing", "checksum_mismatch"}:
            penalty = 3.0
        score -= penalty
        _diff(diffs, "lineage", code, "no blocking issue", issue["message"], "fail", -penalty, issue.get("evidence", ""))
    if not audit.get("issues"):
        _diff(diffs, "lineage", "lineage_gates", "all gates pass", "all gates pass", "pass", 20.0, "")
    return {"max_score": 20, "score": round(max(0.0, score), 2), "status": "pass" if score >= 16 else "limited"}


def _score_core_trend(results: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    score = 0.0
    diagnostics = results.get("diagnostics") or {}
    localgap = results.get("localgap") or {}
    psm = results.get("psm_did") or {}

    score += _pass_if(diffs, "core_trend", "activity_lift", "activity-period GMV is higher descriptively", _activity_lift_positive(diagnostics), 6)
    score += _pass_if(diffs, "core_trend", "psm_did_direction", "resource-lift DID is positive or directionally supportive", _psm_positive(psm), 7)
    score += _pass_if(diffs, "core_trend", "localgap_increment", "LocalGap total increment is positive", _as_float(localgap.get("total_local_gap")) and _as_float(localgap.get("total_local_gap")) > 0, 9)
    score += _pass_if(diffs, "core_trend", "lmdi_order_dominance", "order contribution exceeds AOV contribution", _lmdi_order_dominates(localgap), 8)
    score += _pass_if(diffs, "core_trend", "payday_context", "payday context is represented", bool(diagnostics.get("payday_overlap") or _json_contains(localgap, "payday")), 5)
    return {"max_score": 35, "score": round(score, 2), "status": "pass" if score >= 25 else "limited"}


def _score_resource_mechanism(results: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    mechanism = results.get("mechanism") or {}
    conversion = results.get("conversion") or {}
    localgap = results.get("localgap") or {}
    score = 0.0
    score += _pass_if(diffs, "resource_mechanism", "mechanism_available", "mechanism regression exists with non-stub status", _usable_result(mechanism), 7)
    score += _pass_if(diffs, "resource_mechanism", "conversion_tiers", "conversion diagnostics cover low/mid/high exposure tiers", len(conversion.get("exposure_tiers") or []) >= 3, 5)
    score += _pass_if(diffs, "resource_mechanism", "exposure_over_discount_signal", "exposure signal is at least as strong as discount signal", _exposure_stronger_than_discount(localgap), 5)
    score += _pass_if(diffs, "resource_mechanism", "discount_caution", "discount claims are caveated or tiered", _json_contains(conversion, "discount") or _json_contains(mechanism, "discount"), 3)
    return {"max_score": 20, "score": round(score, 2), "status": "pass" if score >= 14 else "limited"}


def _score_gps_uplift(results: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    uplift = results.get("uplift") or {}
    dose = uplift.get("dose_response") or {}
    score = 0.0
    score += _pass_if(diffs, "gps_uplift", "uplift_available", "GPS/uplift result exists and is not stub", _usable_result(uplift), 4)
    score += _pass_if(diffs, "gps_uplift", "dose_response", "exposure and discount dose-response outputs exist", bool(dose.get("exposure") and dose.get("discount")), 4)
    score += _pass_if(diffs, "gps_uplift", "rank_curves", "rank curves compare prioritization with random baseline", bool((uplift.get("rank_curves") or {}).get("exposure") or (uplift.get("rank_curves") or {}).get("combined")), 3)
    score += _pass_if(diffs, "gps_uplift", "quadrants", "marketing quadrants are available", bool(uplift.get("marketing_quadrants") or uplift.get("resource_uplift_scores")), 4)
    return {"max_score": 15, "score": round(score, 2), "status": "pass" if score >= 11 else "limited"}


def _score_claim_calibration(workspace: Path, results: dict[str, Any], audit: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    latest_index = results.get("latest_index") or {}
    report_text = _read_text(workspace / "reports" / "report.md")
    limited_results = [
        name
        for name, payload in results.items()
        if isinstance(payload, dict) and (payload.get("method_status") == "limited" or payload.get("warnings"))
    ]
    score = 0.0
    score += _pass_if(diffs, "claim_calibration", "limitations_index", "latest result index exposes limitations", bool(latest_index.get("limitations")), 3)
    score += _pass_if(diffs, "claim_calibration", "method_status", "method status/warnings are machine-readable", bool(limited_results or latest_index.get("quality_gates")), 3)
    score += _pass_if(diffs, "claim_calibration", "report_caveats", "report references caveats or evidence", _report_has_caveats(report_text), 2)
    score += _pass_if(diffs, "claim_calibration", "anti_demo_claim", "demo outputs are not treated as production evidence", not audit.get("demo_indicators"), 2)
    return {"max_score": 10, "score": round(score, 2), "status": "pass" if score >= 7 else "limited"}


_CAP_BY_ISSUE = {
    "project_not_found": ("lineage_failure", 20),
    "workspace_missing": ("lineage_failure", 20),
    "manifest_missing": ("lineage_failure", 20),
    "manifest_project_mismatch": ("lineage_failure", 20),
    "checksum_mismatch": ("lineage_failure", 20),
    "demo_contamination": ("demo_contamination", 20),
    "source_roles_missing": ("source_incomplete", 40),
    "processed_panel_as_raw": ("source_incomplete", 40),
    "fatal_pipeline_continued": ("fatal_pipeline_continued", 50),
}


def _score_caps(audit: dict[str, Any]) -> list[dict[str, Any]]:
    caps = []
    seen: set[str] = set()
    for issue in audit.get("issues", []):
        cap = _CAP_BY_ISSUE.get(issue["code"])
        if not cap:
            continue
        reason, max_score = cap
        key = f"{reason}:{max_score}"
        if key in seen:
            continue
        seen.add(key)
        caps.append({"reason": reason, "max_score": max_score, "source_issue": issue["code"], "message": issue["message"]})
    return caps


def _score_interpretation(score: float, caps: list[dict[str, Any]]) -> str:
    if caps:
        return "Hard gate failed; fix cap reasons before interpreting reference trend consistency."
    if score >= 75:
        return "Reference trend agreement is usable for business review with normal caveats."
    if score >= 50:
        return "Partial agreement; use for diagnosis, not final business claims."
    return "Low agreement; treat current analysis as a failed or smoke-test run."


def _write_diff_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["section", "item", "expected", "observed", "status", "score_delta", "detail"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _diff(
    diffs: list[dict[str, Any]],
    section: str,
    item: str,
    expected: str,
    observed: str,
    status: str,
    score_delta: float,
    detail: str,
) -> None:
    diffs.append(
        {
            "section": section,
            "item": item,
            "expected": expected,
            "observed": observed,
            "status": status,
            "score_delta": score_delta,
            "detail": detail,
        }
    )


def _pass_if(
    diffs: list[dict[str, Any]],
    section: str,
    item: str,
    expected: str,
    condition: Any,
    points: float,
) -> float:
    passed = bool(condition)
    _diff(diffs, section, item, expected, "matched" if passed else "missing_or_conflicting", "pass" if passed else "fail", points if passed else 0.0, "")
    return points if passed else 0.0


def _activity_lift_positive(diagnostics: dict[str, Any]) -> bool:
    lift = diagnostics.get("summary", {}).get("activity_lift_pct")
    if lift is None:
        lift = diagnostics.get("activity_vs_non", {}).get("lift_pct")
    value = _as_float(lift)
    return bool(value is not None and value > 0)


def _psm_positive(psm: dict[str, Any]) -> bool:
    estimates = psm.get("estimates") or {}
    lift = psm.get("lift") or {}
    did = _as_float(estimates.get("did_estimate"))
    incremental = _as_float(lift.get("incremental_lift_pct"))
    if did is not None and did > 0:
        return True
    if incremental is not None and incremental > 0:
        return True
    exposure = ((psm.get("treatments") or {}).get("exposure") or {}).get("event_study", {}).get("matched", {})
    primary = _as_float(exposure.get("primary_did"))
    return bool(primary is not None and primary > 0)


def _lmdi_order_dominates(localgap: dict[str, Any]) -> bool:
    overall = ((localgap.get("lmdi_decomposition") or {}).get("overall") or {})
    order = _as_float(overall.get("order_contribution"))
    aov = _as_float(overall.get("aov_contribution"))
    if order is None or aov is None:
        return False
    return order > aov


def _exposure_stronger_than_discount(localgap: dict[str, Any]) -> bool:
    categories = localgap.get("categories") or []
    if not isinstance(categories, list) or not categories:
        return False
    exposure = sum(abs(_as_float(item.get("exposure_gap")) or 0.0) for item in categories if isinstance(item, dict))
    discount = sum(abs(_as_float(item.get("discount_gap")) or 0.0) for item in categories if isinstance(item, dict))
    return exposure >= discount and exposure > 0


def _usable_result(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    status = str(payload.get("method_status") or payload.get("status") or "").lower()
    return status not in {"", "stub", "failed", "error"}


def _report_has_caveats(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ["artifact", "method_status", "limitations", "caveat", "局限", "证据", "口径", "谨慎"])


def _json_contains(payload: Any, text: str) -> bool:
    return text.lower() in json.dumps(payload or {}, ensure_ascii=False).lower()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_headers(path: Path) -> list[str]:
    try:
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
            return next(csv.reader(handle), [])
    except (OSError, StopIteration):
        return []


def _guess_source_role(filename: str, headers: list[str]) -> str:
    lower_name = filename.lower()
    if _looks_like_processed_panel(filename, headers):
        return "category_day_panel"
    if "exposure_info" in lower_name or "exposure" in lower_name or "expo" in lower_name:
        return "exposure_info"
    if "activity_timeline" in lower_name or "activity" in lower_name or "timeline" in lower_name:
        return "activity_timeline"
    if "order_info" in lower_name or "order" in lower_name:
        return "order_info"
    lowered = {header.strip().lower() for header in headers}
    if {"base_sku_id", "view_uv"}.issubset(lowered) or "buy_uv" in lowered and "sku_sale_amt" not in lowered:
        return "exposure_info"
    if {"start_date", "end_date"}.issubset(lowered) or "activity_name" in lowered or "营销活动" in lowered or "日期" in lowered:
        return "activity_timeline"
    if "order_id" in lowered or "stat_pay_main_order_id" in lowered or "sku_sale_amt" in lowered:
        return "order_info"
    return "unknown"


def _looks_like_processed_panel(filename: str, headers: list[str]) -> bool:
    lower_name = filename.lower()
    if "category_date_panel" in lower_name or "category_day_panel" in lower_name or "category_daily_panel" in lower_name:
        return True
    lowered = {header.strip().lower() for header in headers}
    has_category_date = "date" in lowered and bool({"category", "category_name", "category_name_cn", "category_key"} & lowered)
    has_panel_metrics = bool({"gmv", "sku_sale_amt"} & lowered) and bool({"is_activity", "activity_name"} & lowered)
    has_exposure_metrics = bool({"view_uv", "exposure", "buy_uv"} & lowered)
    return has_category_date and has_panel_metrics and has_exposure_metrics


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
