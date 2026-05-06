from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.tools.schemas import ToolResult


def render_chart(workspace_path: str, chart_type: str) -> ToolResult:
    """
    Render lightweight chart data for frontend consumption.

    The payload intentionally stays JSON-first in MVP0. Existing plotting fields
    are preserved while metadata is added for provenance and report planning.
    """
    workspace = Path(workspace_path)
    chart_dir = workspace / "artifacts" / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    if chart_type == "gmv_trend":
        return _render_gmv_trend(workspace, chart_dir)
    if chart_type == "localgap":
        return _render_localgap(workspace, chart_dir)
    if chart_type == "category_concentration":
        return _render_category_concentration(workspace, chart_dir)
    if chart_type == "activity_comparison":
        return _render_activity_comparison(workspace, chart_dir)
    return ToolResult(
        ok=False,
        action="chart.render",
        summary="",
        error={"code": "UNKNOWN_CHART_TYPE", "message": f"Unknown chart type: {chart_type}"},
    )


def _render_gmv_trend(workspace: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace / ".analysis" / "diagnostics_result.json"
    data = _load_required_json(diagnostics_path, "Run diagnostics before rendering GMV trend.")
    if isinstance(data, ToolResult):
        return data

    trend = data.get("gmv_trend", [])
    x_values = [item.get("date") for item in trend]
    y_values = [_as_number(item.get("gmv")) for item in trend]
    findings = _trend_findings(trend)

    chart_data = _with_metadata(
        {
            "type": "line",
            "title": "GMV trend",
            "x": x_values,
            "y": y_values,
            "x_label": "Date",
            "y_label": "GMV",
        },
        chart_type="gmv_trend",
        source_results=["diagnostics"],
        evidence_artifacts=[".analysis/diagnostics_result.json"],
        findings=findings,
        limitations=[
            "Descriptive trend only; it does not identify causal lift.",
            "Missing dates or zero-filled panel rows can flatten or distort the trend.",
        ],
        recommended_follow_up=[
            "Compare trend inflections against activity_timeline dates.",
            "Run PSM-DID or an event-study before claiming causal impact.",
        ],
        confidence=_confidence_label(bool(trend), requires_causal=False),
    )

    return _write_chart(workspace, chart_dir, "gmv_trend.json", chart_data, "Rendered GMV trend chart data.")


def _render_localgap(workspace: Path, chart_dir: Path) -> ToolResult:
    localgap_path = workspace / ".analysis" / "localgap_result.json"
    data = _load_required_json(localgap_path, "Run LocalGap before rendering increment decomposition.")
    if isinstance(data, ToolResult):
        return data

    categories = data.get("categories", [])[:10]
    chart_data = _with_metadata(
        {
            "type": "bar",
            "title": "LocalGap decomposition",
            "x": [item.get("category") for item in categories],
            "y": [_as_number(item.get("local_gap")) for item in categories],
            "x_label": "Category",
            "y_label": "LocalGap",
            "segments": [
                {"key": "exposure_gap", "color": "#2F855A"},
                {"key": "discount_gap", "color": "#2B6CB0"},
                {"key": "payday_gap", "color": "#C05621"},
                {"key": "interaction", "color": "#6B46C1"},
            ],
            "series": [
                {
                    "category": item.get("category"),
                    "local_gap": _as_number(item.get("local_gap")),
                    "exposure_gap": _as_number(item.get("exposure_gap")),
                    "discount_gap": _as_number(item.get("discount_gap")),
                    "payday_gap": _as_number(item.get("payday_gap")),
                    "interaction": _as_number(item.get("interaction")),
                }
                for item in categories
            ],
        },
        chart_type="localgap",
        source_results=["localgap"],
        evidence_artifacts=[".analysis/localgap_result.json"],
        findings=_localgap_findings(data),
        limitations=[
            "LocalGap is an accounting decomposition against a local baseline, not a causal estimator.",
            "Seasonality, inventory shocks, and competitor actions are not fully controlled.",
        ],
        recommended_follow_up=[
            "Check top categories against margins and inventory before budget changes.",
            "Use DID/event-study robustness before attributing increment to campaign mechanics.",
        ],
        confidence=_confidence_label(bool(categories), requires_causal=False),
    )

    return _write_chart(workspace, chart_dir, "localgap.json", chart_data, "Rendered LocalGap decomposition chart data.")


def _render_category_concentration(workspace: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace / ".analysis" / "diagnostics_result.json"
    data = _load_required_json(diagnostics_path, "Run diagnostics before rendering category concentration.")
    if isinstance(data, ToolResult):
        return data

    concentration = data.get("category_concentration", [])
    chart_data = _with_metadata(
        {
            "type": "pie",
            "title": "Category concentration",
            "labels": [item.get("category") for item in concentration],
            "values": [_as_number(item.get("share")) for item in concentration],
        },
        chart_type="category_concentration",
        source_results=["diagnostics"],
        evidence_artifacts=[".analysis/diagnostics_result.json"],
        findings=_concentration_findings(concentration),
        limitations=[
            "Concentration describes GMV mix only; it does not rank incremental opportunity by itself.",
        ],
        recommended_follow_up=[
            "Cross-check top GMV categories with LocalGap and margin before prioritization.",
        ],
        confidence=_confidence_label(bool(concentration), requires_causal=False),
    )

    return _write_chart(workspace, chart_dir, "category_concentration.json", chart_data, "Rendered category concentration chart data.")


def _render_activity_comparison(workspace: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace / ".analysis" / "diagnostics_result.json"
    data = _load_required_json(diagnostics_path, "Run diagnostics before rendering activity comparison.")
    if isinstance(data, ToolResult):
        return data

    activity_vs_non = data.get("activity_vs_non", {})
    chart_data = _with_metadata(
        {
            "type": "bar",
            "title": "Activity vs non-activity average GMV",
            "x": ["Activity", "Non-activity"],
            "y": [
                _as_number(activity_vs_non.get("activity_avg_gmv")),
                _as_number(activity_vs_non.get("non_activity_avg_gmv")),
            ],
            "x_label": "Period",
            "y_label": "Average GMV",
        },
        chart_type="activity_comparison",
        source_results=["diagnostics"],
        evidence_artifacts=[".analysis/diagnostics_result.json"],
        findings=[f"Observed activity lift is {_fmt_percent(activity_vs_non.get('lift'))}."],
        limitations=[
            "Activity comparison is descriptive and can be confounded by payday, seasonality, or category mix.",
        ],
        recommended_follow_up=[
            "Run PSM-DID/event-study robustness before presenting the lift as causal.",
        ],
        confidence=_confidence_label(bool(activity_vs_non), requires_causal=True),
    )

    return _write_chart(workspace, chart_dir, "activity_comparison.json", chart_data, "Rendered activity comparison chart data.")


def _load_required_json(path: Path, message: str) -> dict[str, Any] | ToolResult:
    if not path.exists():
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NO_DATA", "message": message},
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "INVALID_JSON", "message": f"Could not parse {path.name}: {exc}"},
        )
    return payload if isinstance(payload, dict) else {}


def _with_metadata(
    chart_data: dict[str, Any],
    *,
    chart_type: str,
    source_results: list[str],
    evidence_artifacts: list[str],
    findings: list[str],
    limitations: list[str],
    recommended_follow_up: list[str],
    confidence: dict[str, Any],
) -> dict[str, Any]:
    chart_data["metadata"] = {
        "method_status": "chart_data_rendered",
        "chart_type": chart_type,
        "confidence": confidence,
        "source_results": source_results,
        "evidence_artifacts": evidence_artifacts,
        "findings": findings,
        "limitations": limitations,
        "recommended_follow_up": recommended_follow_up,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return chart_data


def _write_chart(workspace: Path, chart_dir: Path, filename: str, chart_data: dict[str, Any], summary: str) -> ToolResult:
    output_path = chart_dir / filename
    output_path.write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = chart_data["metadata"]
    return ToolResult(
        ok=True,
        action="chart.render",
        summary=summary,
        artifacts=[
            {
                "type": "chart",
                "title": filename,
                "path": str(output_path.relative_to(workspace)),
                "metadata": metadata,
                "method_status": metadata["method_status"],
                "confidence": metadata["confidence"],
                "evidence_artifacts": metadata["evidence_artifacts"],
                "limitations": metadata["limitations"],
                "recommended_follow_up": metadata["recommended_follow_up"],
            }
        ],
        assistant_hint="Chart data includes provenance metadata. Treat descriptive charts as evidence, not causal proof.",
    )


def _trend_findings(trend: list[dict[str, Any]]) -> list[str]:
    if not trend:
        return ["No GMV trend points are available."]
    if len(trend) == 1:
        return [f"One GMV point is available for {trend[0].get('date')}."]
    first = trend[0]
    last = trend[-1]
    delta = _as_number(last.get("gmv")) - _as_number(first.get("gmv"))
    return [
        f"GMV changed by {_fmt_signed(delta)} from {first.get('date')} to {last.get('date')}.",
        f"The trend contains {len(trend)} plotted day(s).",
    ]


def _localgap_findings(data: dict[str, Any]) -> list[str]:
    categories = data.get("categories", [])
    if not categories:
        return ["No category-level LocalGap rows are available."]
    top = categories[0]
    return [
        f"Total LocalGap is {_fmt_signed(data.get('total_local_gap'))}.",
        f"Top category by LocalGap is {top.get('category')} at {_fmt_signed(top.get('local_gap'))}.",
    ]


def _concentration_findings(concentration: list[dict[str, Any]]) -> list[str]:
    if not concentration:
        return ["No category concentration rows are available."]
    top = concentration[0]
    return [f"Top GMV category is {top.get('category')} with {_fmt_percent(top.get('share'))} share."]


def _confidence_label(has_data: bool, *, requires_causal: bool) -> dict[str, Any]:
    if not has_data:
        return {"label": "low", "score": 0.1, "basis": ["No source rows available."]}
    if requires_causal:
        return {
            "label": "low-medium",
            "score": 0.45,
            "basis": ["Descriptive comparison only; causal robustness is required for stronger claims."],
        }
    return {"label": "medium", "score": 0.65, "basis": ["Source analysis result is available."]}


def _as_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt_signed(value: Any) -> str:
    return f"{_as_number(value):+,.2f}"


def _fmt_percent(value: Any) -> str:
    return f"{_as_number(value):.2f}%"
