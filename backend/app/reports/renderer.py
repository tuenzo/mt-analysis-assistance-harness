from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.tools.schemas import ToolResult


RESULT_SOURCES = {
    "diagnostics": ".analysis/diagnostics_result.json",
    "localgap": ".analysis/localgap_result.json",
    "psm_did": ".analysis/psm_did_result.json",
    "uplift": ".analysis/uplift_result.json",
}

CHART_SOURCES = {
    "gmv_trend": "artifacts/charts/gmv_trend.json",
    "localgap": "artifacts/charts/localgap.json",
    "category_concentration": "artifacts/charts/category_concentration.json",
    "activity_comparison": "artifacts/charts/activity_comparison.json",
}


@dataclass(frozen=True)
class ReportSectionPlan:
    section_id: str
    title: str
    purpose: str
    prompt: str
    tool_calls: list[dict[str, Any]]
    evidence_artifacts: list[str]
    assumptions: list[str]
    limitations: list[str]
    recommended_follow_up: list[str]
    findings: list[str]


@dataclass(frozen=True)
class ReportSection:
    plan: ReportSectionPlan
    body: str


@dataclass(frozen=True)
class ReportContext:
    project_id: str
    project_name: str
    workspace_path: Path
    generated_at: str
    latest_result: dict[str, Any]
    results: dict[str, dict[str, Any]]
    panel_summary: dict[str, Any]
    manifest: dict[str, Any]
    charts: dict[str, dict[str, Any]]
    evidence_index: dict[str, Any]


def render_report(project_id: str, workspace_path: str, format: str = "md", project_name: str | None = None) -> ToolResult:
    """
    Generate an evidence-backed Markdown report from workspace analysis outputs.

    The public behavior stays compatible with the MVP endpoint: a Markdown report
    is written to `reports/report.md` and returned as a ToolResult artifact.
    """
    workspace = Path(workspace_path)
    context = _build_report_context(project_id, workspace, project_name)

    if not context.results:
        return ToolResult(
            ok=False,
            action="report.generate",
            summary="",
            error={"code": "NO_RESULTS", "message": "Run analysis before generating a report."},
        )

    sections = _build_sections(context)
    report_content = _render_markdown(context, sections)

    report_dir = workspace / "reports"
    analysis_dir = workspace / ".analysis"
    report_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"
    metadata_path = report_dir / "report_metadata.json"
    plan_path = report_dir / "report_plan.json"
    analysis_metadata_path = analysis_dir / "report_metadata.json"
    analysis_plan_path = analysis_dir / "report_plan.json"

    report_path.write_text(report_content, encoding="utf-8")

    section_plans = [asdict(section.plan) for section in sections]
    metadata = {
        "project_id": project_id,
        "project_name": context.project_name,
        "generated_at": context.generated_at,
        "format": format,
        "method_status": "deterministic_report_plan",
        "confidence": _report_confidence(context),
        "report_path": str(report_path.relative_to(workspace)),
        "evidence_artifacts": _all_available_artifact_paths(context),
        "evidence_index": context.evidence_index,
        "findings": _dedupe_strings(
            finding
            for section in section_plans
            for finding in section.get("findings", [])
        ),
        "section_count": len(sections),
        "section_ids": [section.plan.section_id for section in sections],
        "limitations": _global_limitations(context),
        "recommended_follow_up": _recommended_next_actions(context),
        "tool_call_plan": _dedupe_tool_calls(section_plans),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    plan_payload = {"sections": section_plans, "metadata": metadata}
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis_metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis_plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_artifact = {
        "type": "report",
        "title": "report.md",
        "path": str(report_path.relative_to(workspace)),
        "metadata": {
            "method_status": "deterministic_report_plan",
            "confidence": _report_confidence(context),
            "section_count": len(sections),
            "evidence_artifact_count": context.evidence_index["coverage"]["available_artifact_count"],
            "evidence_artifacts": _all_available_artifact_paths(context),
            "findings": _dedupe_strings(
                finding
                for section in section_plans
                for finding in section.get("findings", [])
            ),
            "limitations": _global_limitations(context),
            "recommended_follow_up": _recommended_next_actions(context),
            "generated_at": context.generated_at,
            "format": format,
        },
        "sections": section_plans,
    }

    return ToolResult(
        ok=True,
        action="report.generate",
        summary=f"Report generated with {len(sections)} planned sections and {context.evidence_index['coverage']['available_artifact_count']} evidence artifact(s).",
        artifacts=[
            report_artifact,
            {
                "type": "report_metadata",
                "title": "report_metadata.json",
                "path": str(metadata_path.relative_to(workspace)),
                "metadata": metadata,
            },
            {
                "type": "report_plan",
                "title": "report_plan.json",
                "path": str(analysis_plan_path.relative_to(workspace)),
                "sections": section_plans,
            },
        ],
        state_patch={"current_stage": "report_ready", "latest_report": str(report_path.relative_to(workspace))},
        assistant_hint=(
            "Use report_metadata.json to trace every section to source result/chart artifacts. "
            "If a section names missing evidence, run the recommended follow-up tool calls before presenting final decisions."
        ),
    )


def export_report(report_path: str, export_format: str) -> ToolResult:
    """Export report in a compatible MVP form. Markdown is the durable source."""
    if export_format != "md":
        return ToolResult(
            ok=True,
            action="report.export",
            summary=f"Export format {export_format} is not available yet; Markdown remains the source artifact.",
            artifacts=[],
            assistant_hint="Use Markdown for this MVP build. PDF/LaTeX export can be layered on the same report metadata later.",
        )

    return ToolResult(
        ok=True,
        action="report.export",
        summary="Report exported as Markdown.",
        artifacts=[{"type": "exported_report", "format": "md", "path": report_path}],
    )


def _build_report_context(project_id: str, workspace: Path, project_name: str | None) -> ReportContext:
    generated_at = datetime.now().isoformat(timespec="seconds")
    latest_path = workspace / ".analysis" / "latest_result.json"
    latest_result = _read_json(latest_path)
    results = _collect_results(workspace, latest_result)
    panel_summary = _read_json(workspace / ".analysis" / "panel_summary.json")
    manifest = _read_json(workspace / ".analysis" / "project_manifest.json")
    charts = _collect_charts(workspace)
    evidence_index = _build_evidence_index(workspace, latest_result, results, panel_summary, manifest, charts, generated_at)

    context = ReportContext(
        project_id=project_id,
        project_name=project_name or _project_label(manifest, project_id),
        workspace_path=workspace,
        generated_at=generated_at,
        latest_result=latest_result,
        results=results,
        panel_summary=panel_summary,
        manifest=manifest,
        charts=charts,
        evidence_index=evidence_index,
    )
    context.evidence_index["recommended_next_actions"] = _recommended_next_actions(context)
    return context


def _collect_results(workspace: Path, latest_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name, relative_path in RESULT_SOURCES.items():
        latest_payload = latest_result.get(name)
        if isinstance(latest_payload, dict):
            results[name] = latest_payload
            continue

        file_payload = _read_json(workspace / relative_path)
        if file_payload:
            results[name] = file_payload
    return results


def _collect_charts(workspace: Path) -> dict[str, dict[str, Any]]:
    charts: dict[str, dict[str, Any]] = {}
    for name, relative_path in CHART_SOURCES.items():
        payload = _read_json(workspace / relative_path)
        if payload:
            charts[name] = payload

    chart_dir = workspace / "artifacts" / "charts"
    if chart_dir.exists():
        for path in sorted(chart_dir.glob("*.json")):
            charts.setdefault(path.stem, _read_json(path))
    return {name: payload for name, payload in charts.items() if payload}


def _build_sections(context: ReportContext) -> list[ReportSection]:
    return [
        _executive_snapshot_section(context),
        _evidence_coverage_section(context),
        _observed_performance_section(context),
        _increment_causal_section(context),
        _action_plan_section(context),
        _assumptions_next_checks_section(context),
    ]


def _executive_snapshot_section(context: ReportContext) -> ReportSection:
    diagnostics = context.results.get("diagnostics", {})
    localgap = context.results.get("localgap", {})
    psm_did = context.results.get("psm_did", {})
    summary = diagnostics.get("summary", {})
    lift = diagnostics.get("activity_vs_non", {})
    estimates = psm_did.get("estimates", {})

    findings = [
        f"Workspace covers {_fmt_int(summary.get('total_days'))} day(s), {_fmt_int(summary.get('total_categories'))} category/categories, and {_fmt_money(summary.get('total_gmv'))} GMV in diagnostics.",
        f"Activity-period average GMV lift is {_fmt_percent(lift.get('lift'))} versus non-activity rows when diagnostics are available.",
        f"LocalGap estimates {_fmt_money(localgap.get('total_local_gap'))} incremental GMV against a local baseline.",
    ]
    if estimates:
        findings.append(
            f"Directional PSM-DID estimate is {_fmt_signed_money(estimates.get('did_estimate'))}; interpret this as directional evidence, not a production-grade causal claim."
        )
    else:
        findings.append("No PSM-DID estimate is available, so this report does not make a causal lift claim.")

    plan = _plan(
        "executive_snapshot",
        "Executive Snapshot",
        "Give the demo audience the smallest decision-ready summary that is still tied to source evidence.",
        "Synthesize diagnostics, LocalGap, and PSM-DID into a concise decision snapshot.",
        [
            _tool_call("result.get_latest", "Load the freshest analysis result bundle."),
            _tool_call("artifact.read", "Inspect the report metadata or result JSON behind any challenged number."),
        ],
        _artifact_paths(context, ["diagnostics", "localgap", "psm_did", "gmv_trend", "localgap_chart"]),
        ["All monetary metrics use the same unit as the input GMV column."],
        _limitations_for(context, ["diagnostics", "localgap", "psm_did"]),
        _recommended_next_actions(context)[:3],
        findings=findings,
    )
    return ReportSection(plan, _bullets(findings))


def _evidence_coverage_section(context: ReportContext) -> ReportSection:
    coverage = context.evidence_index["coverage"]
    rows = []
    for item in context.evidence_index["results"]:
        rows.append([item["name"], "yes" if item["available"] else "no", item["path"], item.get("method_status") or "-"])
    result_table = _markdown_table(["Result", "Available", "Path", "Status"], rows)

    chart_rows = []
    for item in context.evidence_index["charts"]:
        chart_rows.append([item["name"], "yes" if item["available"] else "no", item["path"], item.get("title") or "-"])
    chart_table = _markdown_table(["Chart", "Available", "Path", "Title"], chart_rows)

    panel = context.panel_summary
    panel_lines = [
        f"Panel rows: {_fmt_int(panel.get('row_count'))}",
        f"Panel categories: {_fmt_int(panel.get('category_count'))}",
        f"Panel date range: {_date_range_label(panel.get('date_range'))}",
        f"Available evidence artifacts: {coverage['available_artifact_count']} of {coverage['expected_artifact_count']}",
    ]

    plan = _plan(
        "evidence_coverage",
        "Evidence Coverage",
        "Make provenance visible before presenting recommendations.",
        "List the result and chart artifacts that support the report, and call out gaps.",
        [_tool_call("result.get_latest", "Refresh latest_result and latest_result_index before report generation.")],
        _all_available_artifact_paths(context),
        ["File and artifact paths are relative to the project workspace."],
        context.evidence_index["missing_evidence"],
        _recommended_next_actions(context),
        findings=panel_lines,
    )
    body = "\n".join([_bullets(panel_lines), "\n**Result files**\n", result_table, "\n**Chart files**\n", chart_table])
    return ReportSection(plan, body)


def _observed_performance_section(context: ReportContext) -> ReportSection:
    diagnostics = context.results.get("diagnostics", {})
    trend = diagnostics.get("gmv_trend", [])
    activity = diagnostics.get("activity_vs_non", {})
    payday = diagnostics.get("payday_overlap", {})
    concentration = diagnostics.get("category_concentration", [])

    trend_line = "GMV trend evidence is missing."
    if len(trend) >= 2:
        first = trend[0]
        last = trend[-1]
        delta = _as_float(last.get("gmv")) - _as_float(first.get("gmv"))
        trend_line = (
            f"GMV moves from {_fmt_money(first.get('gmv'))} on {first.get('date')} "
            f"to {_fmt_money(last.get('gmv'))} on {last.get('date')} ({_fmt_signed_money(delta)} change)."
        )
    elif len(trend) == 1:
        trend_line = f"GMV trend has one observed day: {trend[0].get('date')} at {_fmt_money(trend[0].get('gmv'))}."

    rows = [
        ["Activity avg GMV", _fmt_money(activity.get("activity_avg_gmv"))],
        ["Non-activity avg GMV", _fmt_money(activity.get("non_activity_avg_gmv"))],
        ["Activity lift", _fmt_percent(activity.get("lift"))],
        ["Payday avg GMV", _fmt_money(payday.get("payday_avg_gmv"))],
        ["Non-payday avg GMV", _fmt_money(payday.get("non_payday_avg_gmv"))],
        ["Payday lift", _fmt_percent(payday.get("lift"))],
    ]
    concentration_rows = [
        [item.get("category", ""), _fmt_money(item.get("gmv")), _fmt_percent(item.get("share"))]
        for item in concentration[:8]
    ]

    plan = _plan(
        "observed_performance",
        "Observed Performance",
        "Separate descriptive movement from causal attribution.",
        "Use diagnostics and chart artifacts to describe trends, concentration, activity, and payday patterns.",
        [
            _tool_call("chart.render", "Render GMV trend chart data.", {"type": "gmv_trend"}),
            _tool_call("chart.render", "Render category concentration chart data.", {"type": "category_concentration"}),
        ],
        _artifact_paths(context, ["diagnostics", "gmv_trend", "category_concentration", "activity_comparison"]),
        ["Descriptive comparisons use the panel rows produced by the current panel builder."],
        _limitations_for(context, ["diagnostics", "gmv_trend"]),
        ["Validate whether visible trend shifts align with campaign dates, stock availability, and seasonality."],
        findings=[trend_line],
    )
    body = "\n".join(
        [
            _bullets([trend_line]),
            "\n**Activity and payday comparison**\n",
            _markdown_table(["Metric", "Value"], rows),
            "\n**Category concentration**\n",
            _markdown_table(["Category", "GMV", "Share"], concentration_rows),
        ]
    )
    return ReportSection(plan, body)


def _increment_causal_section(context: ReportContext) -> ReportSection:
    localgap = context.results.get("localgap", {})
    psm_did = context.results.get("psm_did", {})
    estimates = psm_did.get("estimates", {})
    lift = psm_did.get("lift", {})

    category_rows = [
        [
            item.get("category", ""),
            _fmt_money(item.get("baseline_gmv")),
            _fmt_money(item.get("actual_gmv")),
            _fmt_signed_money(item.get("local_gap")),
            _fmt_signed_money(item.get("exposure_gap")),
            _fmt_signed_money(item.get("discount_gap")),
            _fmt_signed_money(item.get("payday_gap")),
        ]
        for item in localgap.get("categories", [])[:10]
    ]
    did_rows = [
        ["DID estimate", _fmt_signed_money(estimates.get("did_estimate"))],
        ["Treated pre avg", _fmt_money(estimates.get("treated_pre_avg"))],
        ["Treated post avg", _fmt_money(estimates.get("treated_post_avg"))],
        ["Control pre avg", _fmt_money(estimates.get("control_pre_avg"))],
        ["Control post avg", _fmt_money(estimates.get("control_post_avg"))],
        ["Incremental lift", _fmt_percent(lift.get("incremental_lift_pct"))],
    ]

    plan = _plan(
        "increment_causal_direction",
        "Increment and Causal Direction",
        "Explain what appears incremental and how strong the causal evidence is.",
        "Use LocalGap for accounting and PSM-DID for directional causal checks.",
        [
            _tool_call("analysis.run_localgap", "Refresh increment decomposition if source panel changed."),
            _tool_call("analysis.run_psm_did", "Refresh directional causal estimate if source panel changed."),
            _tool_call("chart.render", "Render LocalGap decomposition chart data.", {"type": "localgap"}),
        ],
        _artifact_paths(context, ["localgap", "psm_did", "localgap_chart"]),
        ["LocalGap is an accounting layer, not a randomized experiment."],
        _limitations_for(context, ["localgap", "psm_did"]),
        ["Use a holdout or stronger matching controls before committing budget based on causal lift."],
        findings=[
            f"Estimated LocalGap is {_fmt_signed_money(localgap.get('total_local_gap'))}.",
            (
                f"Directional DID estimate is {_fmt_signed_money(estimates.get('did_estimate'))}."
                if estimates
                else "DID evidence is missing, so causal attribution remains unclaimed."
            ),
        ],
    )
    body = "\n".join(
        [
            _bullets(
                [
                    f"Actual activity GMV totals {_fmt_money(localgap.get('total_actual_gmv'))}.",
                    f"Local baseline totals {_fmt_money(localgap.get('total_baseline_gmv'))}.",
                    f"Estimated LocalGap is {_fmt_signed_money(localgap.get('total_local_gap'))}.",
                ]
            ),
            "\n**LocalGap by category**\n",
            _markdown_table(
                ["Category", "Baseline", "Actual", "Gap", "Exposure", "Discount", "Payday"],
                category_rows,
            ),
            "\n**Directional PSM-DID check**\n",
            _markdown_table(["Metric", "Value"], did_rows),
        ]
    )
    return ReportSection(plan, body)


def _action_plan_section(context: ReportContext) -> ReportSection:
    actions = _recommended_actions(context)
    rows = [
        [
            item.get("category", "-"),
            item.get("action", "-"),
            item.get("evidence", "-"),
            item.get("guardrail", "-"),
        ]
        for item in actions
    ]

    plan = _plan(
        "action_plan",
        "Action Plan",
        "Convert evidence into a cautious next-cycle operating plan.",
        "Rank categories and actions using available LocalGap, diagnostics, and uplift outputs.",
        [
            _tool_call("analysis.run_gps_uplift", "Generate segment strategy before scaling actions."),
            _tool_call("artifact.read", "Read category recommendations or report metadata for the operating plan."),
        ],
        _artifact_paths(context, ["localgap", "uplift"]),
        ["Recommendations assume business constraints such as inventory and margin are checked outside this MVP."],
        _limitations_for(context, ["uplift"]),
        ["Review unit margin, stock depth, and channel capacity before execution."],
        findings=[
            f"{item.get('category', '-')}: {item.get('action', '-')}"
            for item in actions[:5]
        ],
    )
    body = _markdown_table(["Category", "Action", "Evidence", "Guardrail"], rows)
    return ReportSection(plan, body)


def _assumptions_next_checks_section(context: ReportContext) -> ReportSection:
    limitations = _global_limitations(context)
    follow_up = _recommended_next_actions(context)
    assumptions = [
        "Input CSVs have already been mapped into the standard order, exposure, and activity roles.",
        "The report uses current workspace artifacts as the source of truth.",
        "All causal language is intentionally directional unless stronger experiment design is added.",
    ]

    plan = _plan(
        "assumptions_next_checks",
        "Assumptions, Limitations, and Next Checks",
        "Keep the report honest about evidence quality and missing work.",
        "Summarize the constraints that should accompany any demo or decision review.",
        [_tool_call("result.get_latest", "Confirm the result bundle is current after any new pipeline run.")],
        _all_available_artifact_paths(context),
        assumptions,
        limitations,
        follow_up,
        findings=[*limitations, *follow_up],
    )
    body = "\n".join(
        [
            "**Assumptions**\n",
            _bullets(assumptions),
            "\n**Limitations**\n",
            _bullets(limitations),
            "\n**Recommended follow-up**\n",
            _bullets(follow_up),
        ]
    )
    return ReportSection(plan, body)


def _render_markdown(context: ReportContext, sections: list[ReportSection]) -> str:
    lines = [
        f"# {context.project_name} Analysis Report",
        "",
        f"**Project ID**: `{context.project_id}`",
        f"**Generated at**: {context.generated_at}",
        "",
        "> This report is generated from workspace artifacts. Each section names its purpose, evidence, assumptions or limitations, and follow-up.",
        "",
        "## Report Plan",
        "",
        _markdown_table(
            ["Section", "Purpose", "Evidence Count"],
            [
                [section.plan.title, section.plan.purpose, str(len(section.plan.evidence_artifacts))]
                for section in sections
            ],
        ),
        "",
    ]

    for section in sections:
        lines.extend(
            [
                f"## {section.plan.title}",
                "",
                f"**Purpose**: {section.plan.purpose}",
                "",
                "**Evidence artifacts**",
                "",
                _bullets(section.plan.evidence_artifacts or ["No dedicated artifact available."]),
                "",
                section.body,
                "",
                "**Assumptions / limitations**",
                "",
                _bullets([*section.plan.assumptions, *section.plan.limitations] or ["None noted."]),
                "",
                "**Recommended follow-up**",
                "",
                _bullets(section.plan.recommended_follow_up or ["No immediate follow-up required."]),
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _build_evidence_index(
    workspace: Path,
    latest_result: dict[str, Any],
    results: dict[str, dict[str, Any]],
    panel_summary: dict[str, Any],
    manifest: dict[str, Any],
    charts: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    result_entries = []
    for name, relative_path in RESULT_SOURCES.items():
        data = results.get(name, {})
        result_entries.append(
            {
                "name": name,
                "path": relative_path,
                "available": bool(data),
                "method": data.get("method"),
                "method_status": data.get("method_status") or data.get("status"),
                "key_metrics": _result_key_metrics(name, data),
            }
        )

    chart_entries = []
    for name, relative_path in CHART_SOURCES.items():
        data = charts.get(name, {})
        chart_entries.append(
            {
                "name": name,
                "path": relative_path,
                "available": bool(data),
                "title": data.get("title"),
                "source_results": data.get("metadata", {}).get("source_results", []),
            }
        )

    available_artifacts = [
        entry["path"] for entry in [*result_entries, *chart_entries] if entry["available"]
    ]
    if panel_summary:
        available_artifacts.append(".analysis/panel_summary.json")
    if latest_result:
        available_artifacts.append(".analysis/latest_result.json")
    if manifest:
        available_artifacts.append(".analysis/project_manifest.json")

    missing = []
    for entry in result_entries:
        if not entry["available"]:
            missing.append(f"Missing result: {entry['name']} ({entry['path']}).")
    for entry in chart_entries:
        if not entry["available"] and _chart_source_is_ready(entry["name"], results):
            missing.append(f"Missing chart: {entry['name']} ({entry['path']}).")

    return {
        "generated_at": generated_at,
        "results": result_entries,
        "charts": chart_entries,
        "panel_summary": {
            "path": ".analysis/panel_summary.json",
            "available": bool(panel_summary),
            "date_range": panel_summary.get("date_range"),
            "row_count": panel_summary.get("row_count"),
            "category_count": panel_summary.get("category_count"),
        },
        "manifest": {
            "path": ".analysis/project_manifest.json",
            "available": bool(manifest),
            "version": manifest.get("version"),
            "current_stage": manifest.get("current_stage"),
            "file_count": len(manifest.get("files", [])) if isinstance(manifest.get("files"), list) else 0,
        },
        "coverage": {
            "available_artifact_count": len(available_artifacts),
            "expected_artifact_count": len(RESULT_SOURCES) + len(CHART_SOURCES) + 2,
            "available_artifacts": available_artifacts,
        },
        "missing_evidence": missing,
        "recommended_next_actions": [],
    }


def _result_key_metrics(name: str, data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    if name == "diagnostics":
        summary = data.get("summary", {})
        return {
            "total_gmv": summary.get("total_gmv"),
            "total_days": summary.get("total_days"),
            "total_categories": summary.get("total_categories"),
            "activity_lift_pct": data.get("activity_vs_non", {}).get("lift"),
        }
    if name == "localgap":
        categories = data.get("categories", [])
        return {
            "total_local_gap": data.get("total_local_gap"),
            "category_count": len(categories),
            "top_category": categories[0].get("category") if categories else None,
        }
    if name == "psm_did":
        return {
            "did_estimate": data.get("estimates", {}).get("did_estimate"),
            "incremental_lift_pct": data.get("lift", {}).get("incremental_lift_pct"),
        }
    if name == "uplift":
        return {
            "segment_count": len(data.get("segments", [])) if isinstance(data.get("segments"), list) else 0,
            "method_status": data.get("method_status"),
        }
    return {}


def _recommended_actions(context: ReportContext) -> list[dict[str, str]]:
    explicit = context.latest_result.get("recommended_actions")
    if isinstance(explicit, list) and explicit:
        return [
            {
                "category": str(item.get("category", "-")),
                "action": str(item.get("action", "-")),
                "evidence": str(item.get("reason") or item.get("evidence") or "Provided by latest_result."),
                "guardrail": str(item.get("guardrail") or "Check margin, stock, and operational capacity."),
            }
            for item in explicit[:8]
            if isinstance(item, dict)
        ]

    localgap = context.results.get("localgap", {})
    actions: list[dict[str, str]] = []
    for item in localgap.get("categories", [])[:8]:
        category = str(item.get("category") or "-")
        exposure_gap = _as_float(item.get("exposure_gap"))
        discount_gap = _as_float(item.get("discount_gap"))
        payday_gap = _as_float(item.get("payday_gap"))
        if exposure_gap >= discount_gap and exposure_gap >= payday_gap:
            action = "Scale qualified exposure"
            guardrail = "Avoid low-conversion placements; monitor exposure-to-order conversion."
            evidence = f"Exposure contribution {_fmt_signed_money(exposure_gap)} is the largest available driver."
        elif discount_gap >= payday_gap:
            action = "Tune discount depth"
            guardrail = "Check gross margin and avoid subsidy leakage."
            evidence = f"Discount contribution {_fmt_signed_money(discount_gap)} is the largest available driver."
        else:
            action = "Move timing around payday"
            guardrail = "Validate stock and channel capacity around payday windows."
            evidence = f"Payday contribution {_fmt_signed_money(payday_gap)} is the largest available driver."
        actions.append({"category": category, "action": action, "evidence": evidence, "guardrail": guardrail})

    uplift = context.results.get("uplift", {})
    segments = uplift.get("segments", [])
    if not actions and isinstance(segments, list):
        for segment in segments[:4]:
            if not isinstance(segment, dict):
                continue
            actions.append(
                {
                    "category": str(segment.get("segment", "Segment")),
                    "action": str(segment.get("recommendation", "Review segment strategy.")),
                    "evidence": "Uplift segment output.",
                    "guardrail": "Treat as directional while GPS-Uplift remains stub or unvalidated.",
                }
            )

    return actions or [
        {
            "category": "All",
            "action": "Run full pipeline before category-level action.",
            "evidence": "No category recommendation artifact is available.",
            "guardrail": "Do not present unsupported category tactics.",
        }
    ]


def _global_limitations(context: ReportContext) -> list[str]:
    limitations = []
    if "psm_did" in context.results:
        status = context.results["psm_did"].get("method_status")
        if status in {None, "simplified", "stub"}:
            limitations.append("PSM-DID is a simplified directional check in the MVP and does not replace experiment-grade causal identification.")
    else:
        limitations.append("PSM-DID evidence is missing, so causal direction is not available.")

    if "localgap" in context.results:
        limitations.append("LocalGap decomposes observed increment against a local baseline; seasonality, inventory, and competitor shocks are not fully controlled.")
    else:
        limitations.append("LocalGap evidence is missing, so increment decomposition is unavailable.")

    uplift = context.results.get("uplift")
    if not uplift:
        limitations.append("GPS-Uplift is missing, so segment recommendations are derived from available diagnostics and LocalGap only.")
    elif uplift.get("method_status") == "stub":
        limitations.append("GPS-Uplift output is currently a stub; treat segment actions as placeholders.")

    if not context.panel_summary:
        limitations.append("Panel summary is missing, so row counts and date coverage may be incomplete.")

    if context.evidence_index["missing_evidence"]:
        limitations.append("Some expected evidence artifacts are missing; see the Evidence Coverage section.")

    return limitations


def _report_confidence(context: ReportContext) -> dict[str, Any]:
    evidence_names = set(context.results.keys())
    score = 0.25
    if "diagnostics" in evidence_names:
        score += 0.2
    if "localgap" in evidence_names:
        score += 0.2
    if "psm_did" in evidence_names:
        score += 0.15
    if "uplift" in evidence_names and context.results["uplift"].get("method_status") != "stub":
        score += 0.1
    if context.panel_summary:
        score += 0.05
    if context.charts:
        score += min(0.05, len(context.charts) * 0.02)

    score = min(round(score, 2), 0.95)
    if score >= 0.75 and "psm_did" in evidence_names:
        label = "medium-high"
    elif score >= 0.55:
        label = "medium"
    else:
        label = "low"

    return {
        "label": label,
        "score": score,
        "basis": [
            f"results={sorted(evidence_names)}",
            f"charts={sorted(context.charts.keys())}",
            "causal claims remain directional without holdout, event-study, and robustness evidence.",
        ],
    }


def _recommended_next_actions(context: ReportContext) -> list[str]:
    actions: list[str] = []
    if "diagnostics" not in context.results:
        actions.append("Run `analysis.run_diagnostics` after panel build.")
    if "psm_did" not in context.results:
        actions.append("Run `analysis.run_psm_did` for directional causal evidence.")
    if "localgap" not in context.results:
        actions.append("Run `analysis.run_localgap` for increment decomposition.")
    if "uplift" not in context.results:
        actions.append("Run `analysis.run_gps_uplift` before segment-level strategy claims.")
    if "diagnostics" in context.results and "gmv_trend" not in context.charts:
        actions.append("Run `chart.render` with `{type: 'gmv_trend'}`.")
    if "localgap" in context.results and "localgap" not in context.charts:
        actions.append("Run `chart.render` with `{type: 'localgap'}`.")
    actions.append("Review margin, inventory, and channel capacity before moving recommendations into execution.")
    return _dedupe_strings(actions)


def _limitations_for(context: ReportContext, evidence_names: list[str]) -> list[str]:
    limitations = []
    for name in evidence_names:
        normalized = "localgap" if name == "localgap_chart" else name
        if normalized in RESULT_SOURCES and normalized not in context.results:
            limitations.append(f"{normalized} result is missing.")
        if normalized in CHART_SOURCES and normalized not in context.charts:
            limitations.append(f"{normalized} chart is missing.")
    if not limitations:
        return ["Evidence is based on current workspace artifacts and should be refreshed after source data changes."]
    return limitations


def _plan(
    section_id: str,
    title: str,
    purpose: str,
    prompt: str,
    tool_calls: list[dict[str, Any]],
    evidence_artifacts: list[str],
    assumptions: list[str],
    limitations: list[str],
    recommended_follow_up: list[str],
    findings: list[str] | None = None,
) -> ReportSectionPlan:
    return ReportSectionPlan(
        section_id=section_id,
        title=title,
        purpose=purpose,
        prompt=prompt,
        tool_calls=tool_calls,
        evidence_artifacts=evidence_artifacts,
        assumptions=assumptions,
        limitations=limitations,
        recommended_follow_up=recommended_follow_up,
        findings=findings or [],
    )


def _tool_call(action: str, reason: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "tool": "business_analysis",
        "action": action,
        "payload": payload or {},
        "reason": reason,
    }


def _artifact_paths(context: ReportContext, names: list[str]) -> list[str]:
    paths = []
    aliases = {"localgap_chart": "localgap"}
    for name in names:
        result_name = name
        chart_name = aliases.get(name, name)
        if result_name in context.results and result_name in RESULT_SOURCES:
            paths.append(RESULT_SOURCES[result_name])
        if chart_name in context.charts and chart_name in CHART_SOURCES:
            paths.append(CHART_SOURCES[chart_name])
    return _dedupe_strings(paths)


def _all_available_artifact_paths(context: ReportContext) -> list[str]:
    return list(context.evidence_index["coverage"]["available_artifacts"])


def _chart_source_is_ready(chart_name: str, results: dict[str, dict[str, Any]]) -> bool:
    if chart_name in {"gmv_trend", "category_concentration", "activity_comparison"}:
        return "diagnostics" in results
    if chart_name == "localgap":
        return "localgap" in results
    return False


def _dedupe_tool_calls(section_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    calls = []
    for plan in section_plans:
        for call in plan.get("tool_calls", []):
            key = json.dumps({"action": call.get("action"), "payload": call.get("payload", {})}, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            calls.append(call)
    return calls


def _dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _project_label(manifest: dict[str, Any], project_id: str) -> str:
    candidate = manifest.get("project_name") or manifest.get("name")
    if candidate:
        return str(candidate)
    return project_id


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        rows = [["-" for _ in headers]]
    header_line = "| " + " | ".join(_cell(header) for header in headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return "\n".join([header_line, sep_line, *row_lines])


def _bullets(items: list[Any]) -> str:
    return "\n".join(f"- {_cell(item)}" for item in items)


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _date_range_label(value: Any) -> str:
    if isinstance(value, dict):
        start = value.get("start") or "?"
        end = value.get("end") or "?"
        return f"{start} to {end}"
    return "-"


def _fmt_int(value: Any) -> str:
    number = _as_float_or_none(value)
    if number is None:
        return "N/A"
    return f"{int(round(number)):,}"


def _fmt_money(value: Any) -> str:
    number = _as_float_or_none(value)
    if number is None:
        return "N/A"
    return f"{number:,.2f}"


def _fmt_signed_money(value: Any) -> str:
    number = _as_float_or_none(value)
    if number is None:
        return "N/A"
    return f"{number:+,.2f}"


def _fmt_percent(value: Any) -> str:
    number = _as_float_or_none(value)
    if number is None:
        return "N/A"
    return f"{number:.2f}%"


def _as_float(value: Any) -> float:
    number = _as_float_or_none(value)
    return number if number is not None else 0.0


def _as_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
