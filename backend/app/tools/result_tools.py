from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.config import resolve_project_path
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

    workspace_path = resolve_project_path(project.workspace_path)
    latest_data: dict[str, Any] = {}

    for name, relative_path in RESULT_FILES.items():
        path = workspace_path / relative_path
        if not path.exists():
            continue
        try:
            payload_data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload_data, dict):
            latest_data[name] = payload_data

    available_results = list(latest_data.keys())
    if not available_results:
        return ToolResult(
            ok=True,
            action="result.get_latest",
            summary="No analysis results are available yet.",
            artifacts=[],
            assistant_hint="Run diagnostics, LocalGap, PSM-DID, or the full pipeline before generating an evidence-backed report.",
        )

    latest_path = workspace_path / ".analysis" / "latest_result.json"
    index_path = workspace_path / ".analysis" / "latest_result_index.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(latest_data.get("uplift", {}).get("recommended_actions"), list):
        latest_data["recommended_actions"] = latest_data["uplift"]["recommended_actions"]
    latest_path.write_text(json.dumps(latest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    result_index = _build_result_index(latest_data, available_results)
    index_path.write_text(json.dumps(result_index, ensure_ascii=False, indent=2), encoding="utf-8")

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
                "metadata": result_index,
                "method_status": result_index["method_status"],
                "confidence": result_index["confidence"],
                "evidence_artifacts": result_index["evidence_artifacts"],
                "limitations": result_index["limitations"],
                "recommended_follow_up": result_index["recommended_follow_up"],
            },
            {
                "type": "result_index",
                "title": "latest_result_index.json",
                "path": str(index_path.relative_to(workspace_path)),
                "metadata": result_index,
            },
        ],
        assistant_hint="Use latest_result.json for raw values and latest_result_index.json for provenance, confidence, limitations, and follow-up.",
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

    workspace_path = resolve_project_path(project.workspace_path)
    full_path = workspace_path / artifact_path
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


def _build_result_index(latest_data: dict[str, Any], available_results: list[str]) -> dict[str, Any]:
    missing_results = [name for name in RESULT_FILES if name not in available_results]
    evidence_artifacts = [RESULT_FILES[name] for name in available_results if name in RESULT_FILES]
    limitations = _result_limitations(latest_data, missing_results)
    recommended_follow_up = _result_follow_up(missing_results, latest_data)

    return {
        "method_status": "aggregated_latest_results",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "available_results": available_results,
        "missing_results": missing_results,
        "evidence_artifacts": evidence_artifacts,
        "confidence": _result_confidence(latest_data, available_results),
        "findings": _result_findings(latest_data),
        "results": [
            {
                "name": name,
                "path": RESULT_FILES.get(name),
                "method_status": _method_status(name, latest_data.get(name, {})),
                "key_metrics": _key_metrics(name, latest_data.get(name, {})),
            }
            for name in available_results
        ],
        "limitations": limitations,
        "recommended_follow_up": recommended_follow_up,
        "claim_rules": [
            "Cite artifact paths before interpreting metrics.",
            "Use descriptive language for diagnostics-only findings.",
            "Use directional language for LocalGap or PSM-DID unless event-study and robustness evidence exist.",
            "Never present stub outputs as production evidence.",
        ],
    }


def _method_status(name: str, payload: dict[str, Any]) -> str:
    return str(payload.get("method_status") or payload.get("status") or payload.get("method") or f"{name}_available")


def _key_metrics(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name == "diagnostics":
        summary = payload.get("summary", {})
        return {
            "total_gmv": summary.get("total_gmv"),
            "total_days": summary.get("total_days"),
            "total_categories": summary.get("total_categories"),
            "activity_lift_pct": payload.get("activity_vs_non", {}).get("lift"),
        }
    if name == "localgap":
        categories = payload.get("categories", [])
        return {
            "total_local_gap": payload.get("total_local_gap"),
            "category_count": len(categories) if isinstance(categories, list) else 0,
            "top_category": categories[0].get("category") if isinstance(categories, list) and categories else None,
        }
    if name == "psm_did":
        return {
            "did_estimate": payload.get("estimates", {}).get("did_estimate"),
            "incremental_lift_pct": payload.get("lift", {}).get("incremental_lift_pct"),
        }
    if name == "uplift":
        segments = payload.get("segments", [])
        recommendations = payload.get("recommended_actions", [])
        return {
            "segment_count": len(segments) if isinstance(segments, list) else 0,
            "method_status": payload.get("method_status"),
            "recommendation_count": len(recommendations) if isinstance(recommendations, list) else 0,
        }
    return {}


def _result_findings(latest_data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    diagnostics = latest_data.get("diagnostics", {})
    if diagnostics:
        summary = diagnostics.get("summary", {})
        findings.append(
            f"Diagnostics cover {_fmt_int(summary.get('total_days'))} day(s), {_fmt_int(summary.get('total_categories'))} category/categories, and {_fmt_money(summary.get('total_gmv'))} GMV."
        )
    localgap = latest_data.get("localgap", {})
    if localgap:
        findings.append(f"LocalGap total is {_fmt_signed(localgap.get('total_local_gap'))}.")
    psm_did = latest_data.get("psm_did", {})
    if psm_did:
        findings.append(f"Directional DID estimate is {_fmt_signed(psm_did.get('estimates', {}).get('did_estimate'))}.")
    return findings or ["No interpreted findings are available from current results."]


def _result_confidence(latest_data: dict[str, Any], available_results: list[str]) -> dict[str, Any]:
    score = 0.2 + min(0.4, len(available_results) * 0.1)
    if "diagnostics" in latest_data:
        score += 0.1
    if "localgap" in latest_data:
        score += 0.1
    if "psm_did" in latest_data:
        score += 0.1
    if latest_data.get("uplift", {}).get("method_status") == "stub":
        score -= 0.05
    score = max(0.1, min(round(score, 2), 0.9))
    label = "medium-high" if score >= 0.75 else "medium" if score >= 0.5 else "low"
    return {
        "label": label,
        "score": score,
        "basis": [
            f"available_results={available_results}",
            "Causal confidence requires DID/event-study/robustness evidence beyond result aggregation.",
        ],
    }


def _result_limitations(latest_data: dict[str, Any], missing_results: list[str]) -> list[str]:
    limitations: list[str] = []
    if missing_results:
        limitations.append(f"Missing result families: {', '.join(missing_results)}.")
    if "psm_did" not in latest_data:
        limitations.append("No PSM-DID result is available; do not claim causal lift.")
    elif latest_data["psm_did"].get("method_status") in {None, "simplified", "stub"}:
        limitations.append("PSM-DID is simplified in this MVP and should be treated as directional.")
    if latest_data.get("uplift", {}).get("method_status") == "stub":
        limitations.append("GPS-Uplift is a stub; segment strategy remains illustrative.")
    if "localgap" in latest_data:
        limitations.append("LocalGap is increment accounting, not causal proof.")
    return limitations or ["No material result limitations detected from available metadata."]


def _result_follow_up(missing_results: list[str], latest_data: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for name in missing_results:
        if name == "uplift":
            actions.append("Run `analysis.run_gps_uplift` before segment-level strategy claims.")
        elif name == "psm_did":
            actions.append("Run `analysis.run_psm_did` before causal direction claims.")
        elif name == "localgap":
            actions.append("Run `analysis.run_localgap` before increment decomposition claims.")
        elif name == "diagnostics":
            actions.append("Run `analysis.run_diagnostics` before descriptive performance claims.")
    if "psm_did" in latest_data:
        actions.append("Add event-study or robustness checks before production causal decisions.")
    actions.append("Regenerate charts and report after any source data or panel changes.")
    return _dedupe(actions)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _fmt_int(value: Any) -> str:
    number = _as_float(value)
    return "N/A" if number is None else f"{int(round(number)):,}"


def _fmt_money(value: Any) -> str:
    number = _as_float(value)
    return "N/A" if number is None else f"{number:,.2f}"


def _fmt_signed(value: Any) -> str:
    number = _as_float(value)
    return "N/A" if number is None else f"{number:+,.2f}"


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
