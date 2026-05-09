from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.tools.schemas import ToolResult


RESULT_SOURCES = {
    "diagnostics": ".analysis/diagnostics_result.json",
    "user_week": ".analysis/user_week_panel_result.json",
    "hmm_state_path": ".analysis/hmm_state_path_result.json",
    "localgap": ".analysis/localgap_result.json",
    "psm_did": ".analysis/psm_did_result.json",
    "mechanism": ".analysis/mechanism_regression_result.json",
    "conversion": ".analysis/conversion_diagnostics_result.json",
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
            error={"code": "NO_RESULTS", "message": "请先运行分析，再生成报告。"},
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
        summary=f"已生成中文分析报告：包含 {len(sections)} 个规划章节和 {context.evidence_index['coverage']['available_artifact_count']} 个证据文件。",
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
            "默认使用中文解读 reports/report.md。使用 report_metadata.json 追踪每个章节对应的结果或图表证据；"
            "如果章节指出缺失证据，先运行 recommended_follow_up 中的工具调用，再给出最终建议。"
        ),
    )


def export_report(report_path: str, export_format: str) -> ToolResult:
    """Export report in a compatible MVP form. Markdown is the durable source."""
    if export_format != "md":
        return ToolResult(
            ok=True,
            action="report.export",
            summary=f"暂不支持导出为 {export_format}；Markdown 仍是当前源报告。",
            artifacts=[],
            assistant_hint="MVP 阶段请使用 Markdown 报告。PDF/LaTeX 后续可基于同一份 report_metadata 扩展。",
        )

    return ToolResult(
        ok=True,
        action="report.export",
        summary="报告已按 Markdown 输出。",
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
    sections = [
        _executive_snapshot_section(context),
        _evidence_coverage_section(context),
        _observed_performance_section(context),
        _increment_causal_section(context),
        _mechanism_conversion_section(context),
    ]
    if "user_week" in context.results or "hmm_state_path" in context.results:
        sections.append(_user_state_path_section(context))
    sections.extend([_action_plan_section(context), _assumptions_next_checks_section(context)])
    return sections


def _executive_snapshot_section(context: ReportContext) -> ReportSection:
    diagnostics = context.results.get("diagnostics", {})
    localgap = context.results.get("localgap", {})
    psm_did = context.results.get("psm_did", {})
    summary = diagnostics.get("summary", {})
    lift = diagnostics.get("activity_vs_non", {})
    estimates = psm_did.get("estimates", {})

    findings = [
        f"诊断口径覆盖 {_fmt_int(summary.get('total_days'))} 天、{_fmt_int(summary.get('total_categories'))} 个品类；总 GMV: {_fmt_money(summary.get('total_gmv'))}。",
        f"活动期平均 GMV 相对非活动样本的观察性提升为 {_fmt_percent(lift.get('lift'))}。",
        f"LocalGap 基于局部基线估算的总增量: {_fmt_money(localgap.get('total_local_gap'))}。",
    ]
    if estimates:
        findings.append(
            f"PSM-DID 方向性估计为 {_fmt_signed_money(estimates.get('did_estimate'))}；这只能作为方向性证据，不等同于生产级因果结论。"
        )
    else:
        findings.append("当前没有 PSM-DID 估计，因此本报告不做因果 lift 结论。")

    plan = _plan(
        "executive_snapshot",
        "执行摘要",
        "用最短篇幅给出可汇报的业务结论，同时保持每个判断都能追溯到证据文件。",
        "综合 diagnostics、LocalGap 与 PSM-DID，生成谨慎的决策摘要。",
        [
            _tool_call("result.get_latest", "加载最新分析结果包。"),
            _tool_call("artifact.read", "当指标被追问时，读取对应 report metadata 或 result JSON。"),
        ],
        _artifact_paths(context, ["diagnostics", "localgap", "psm_did", "gmv_trend", "localgap_chart"]),
        ["所有金额指标沿用输入 GMV 字段的单位。"],
        _limitations_for(context, ["diagnostics", "localgap", "psm_did"]),
        _recommended_next_actions(context)[:3],
        findings=findings,
    )
    return ReportSection(plan, _bullets(findings))


def _evidence_coverage_section(context: ReportContext) -> ReportSection:
    coverage = context.evidence_index["coverage"]
    rows = []
    for item in context.evidence_index["results"]:
        rows.append([item["name"], "是" if item["available"] else "否", item["path"], item.get("method_status") or "-"])
    result_table = _markdown_table(["结果", "可用", "路径", "状态"], rows)

    chart_rows = []
    for item in context.evidence_index["charts"]:
        chart_rows.append([item["name"], "是" if item["available"] else "否", item["path"], item.get("title") or "-"])
    chart_table = _markdown_table(["图表", "可用", "路径", "标题"], chart_rows)

    panel = context.panel_summary
    panel_lines = [
        f"Panel 行数：{_fmt_int(panel.get('row_count'))}",
        f"Panel 品类数：{_fmt_int(panel.get('category_count'))}",
        f"Panel 日期范围：{_date_range_label(panel.get('date_range'))}",
        f"可用证据文件：{coverage['available_artifact_count']} / {coverage['expected_artifact_count']}",
    ]

    plan = _plan(
        "evidence_coverage",
        "证据覆盖",
        "在给出建议前先展示证据来源和缺口。",
        "列出支撑报告的结果文件与图表文件，并标明缺失证据。",
        [_tool_call("result.get_latest", "生成报告前刷新 latest_result 与 latest_result_index。")],
        _all_available_artifact_paths(context),
        ["文件和 artifact 路径均相对于项目 workspace。"],
        context.evidence_index["missing_evidence"],
        _recommended_next_actions(context),
        findings=panel_lines,
    )
    body = "\n".join([_bullets(panel_lines), "\n**结果文件**\n", result_table, "\n**图表文件**\n", chart_table])
    return ReportSection(plan, body)


def _observed_performance_section(context: ReportContext) -> ReportSection:
    diagnostics = context.results.get("diagnostics", {})
    trend = diagnostics.get("gmv_trend", [])
    activity = diagnostics.get("activity_vs_non", {})
    payday = diagnostics.get("payday_overlap", {})
    concentration = diagnostics.get("category_concentration", [])

    trend_line = "GMV 趋势证据缺失。"
    if len(trend) >= 2:
        first = trend[0]
        last = trend[-1]
        delta = _as_float(last.get("gmv")) - _as_float(first.get("gmv"))
        trend_line = (
            f"GMV 从 {first.get('date')} 的 {_fmt_money(first.get('gmv'))} "
            f"变化到 {last.get('date')} 的 {_fmt_money(last.get('gmv'))}，变动 {_fmt_signed_money(delta)}。"
        )
    elif len(trend) == 1:
        trend_line = f"GMV 趋势只有一个观测日：{trend[0].get('date')}，GMV {_fmt_money(trend[0].get('gmv'))}。"

    rows = [
        ["活动期平均 GMV", _fmt_money(activity.get("activity_avg_gmv"))],
        ["非活动期平均 GMV", _fmt_money(activity.get("non_activity_avg_gmv"))],
        ["活动期观察性提升", _fmt_percent(activity.get("lift"))],
        ["发薪日平均 GMV", _fmt_money(payday.get("payday_avg_gmv"))],
        ["非发薪日平均 GMV", _fmt_money(payday.get("non_payday_avg_gmv"))],
        ["发薪日观察性提升", _fmt_percent(payday.get("lift"))],
    ]
    concentration_rows = [
        [item.get("category", ""), _fmt_money(item.get("gmv")), _fmt_percent(item.get("share"))]
        for item in concentration[:8]
    ]

    plan = _plan(
        "observed_performance",
        "观察性表现",
        "把描述性变化与因果归因分开呈现。",
        "使用 diagnostics 和图表文件描述趋势、品类集中度、活动期与发薪日模式。",
        [
            _tool_call("chart.render", "渲染 GMV 趋势图表数据。", {"type": "gmv_trend"}),
            _tool_call("chart.render", "渲染品类集中度图表数据。", {"type": "category_concentration"}),
        ],
        _artifact_paths(context, ["diagnostics", "gmv_trend", "category_concentration", "activity_comparison"]),
        ["描述性对比基于当前 panel builder 生成的 panel 行。"],
        _limitations_for(context, ["diagnostics", "gmv_trend"]),
        ["复核趋势变化是否与活动日期、库存可用性和季节性因素一致。"],
        findings=[trend_line],
    )
    body = "\n".join(
        [
            _bullets([trend_line]),
            "\n**活动期与发薪日对比**\n",
            _markdown_table(["指标", "数值"], rows),
            "\n**品类集中度**\n",
            _markdown_table(["品类", "GMV", "占比"], concentration_rows),
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
        ["DID 估计值", _fmt_signed_money(estimates.get("did_estimate"))],
        ["处理组活动前均值", _fmt_money(estimates.get("treated_pre_avg"))],
        ["处理组活动后均值", _fmt_money(estimates.get("treated_post_avg"))],
        ["对照组活动前均值", _fmt_money(estimates.get("control_pre_avg"))],
        ["对照组活动后均值", _fmt_money(estimates.get("control_post_avg"))],
        ["增量 lift", _fmt_percent(lift.get("incremental_lift_pct"))],
    ]

    plan = _plan(
        "increment_causal_direction",
        "增量与因果方向",
        "解释哪些变化看起来像增量，以及因果证据强度到什么程度。",
        "使用 LocalGap 做增量核算，使用 PSM-DID 做方向性因果检查。",
        [
            _tool_call("analysis.run_localgap", "如果源 panel 更新，刷新增量分解。"),
            _tool_call("analysis.run_psm_did", "如果源 panel 更新，刷新方向性因果估计。"),
            _tool_call("chart.render", "渲染 LocalGap 分解图表数据。", {"type": "localgap"}),
        ],
        _artifact_paths(context, ["localgap", "psm_did", "localgap_chart"]),
        ["LocalGap 是增量核算层，不是随机实验。"],
        _limitations_for(context, ["localgap", "psm_did"]),
        ["在基于因果 lift 分配预算前，应补充 holdout 或更强匹配控制。"],
        findings=[
            f"估算 LocalGap 为 {_fmt_signed_money(localgap.get('total_local_gap'))}。",
            (
                f"DID 方向性估计为 {_fmt_signed_money(estimates.get('did_estimate'))}。"
                if estimates
                else "DID 证据缺失，因此不做因果归因结论。"
            ),
        ],
    )
    body = "\n".join(
        [
            _bullets(
                [
                    f"活动期实际 GMV 合计为 {_fmt_money(localgap.get('total_actual_gmv'))}。",
                    f"局部基线 GMV 合计为 {_fmt_money(localgap.get('total_baseline_gmv'))}。",
                    f"估算 LocalGap 为 {_fmt_signed_money(localgap.get('total_local_gap'))}。",
                ]
            ),
            "\n**分品类 LocalGap**\n",
            _markdown_table(
                ["品类", "基线", "实际", "增量", "曝光", "折扣", "发薪日"],
                category_rows,
            ),
            "\n**PSM-DID 方向性检查**\n",
            _markdown_table(["指标", "数值"], did_rows),
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
        "行动计划",
        "把当前证据转化为下一轮谨慎可执行的运营计划。",
        "基于 LocalGap、diagnostics 与 uplift 输出排序品类行动。",
        [
            _tool_call("analysis.run_gps_uplift", "在放大动作前生成分群策略。"),
            _tool_call("artifact.read", "读取品类建议或 report metadata，支撑运营计划。"),
        ],
        _artifact_paths(context, ["localgap", "uplift"]),
        ["建议默认假设库存、毛利等业务约束会在 MVP 外另行复核。"],
        _limitations_for(context, ["uplift"]),
        ["执行前复核单品毛利、库存深度和渠道承载能力。"],
        findings=[
            f"{item.get('category', '-')}: {item.get('action', '-')}"
            for item in actions[:5]
        ],
    )
    body = _markdown_table(["品类", "动作", "证据", "护栏"], rows)
    return ReportSection(plan, body)


def _user_state_path_section(context: ReportContext) -> ReportSection:
    user_week = context.results.get("user_week", {})
    hmm = context.results.get("hmm_state_path", {})
    state_rows = [
        [item.get("state", "-"), _fmt_int(item.get("rows")), _fmt_money(item.get("avg_gmv"))]
        for item in hmm.get("states", [])
        if isinstance(item, dict)
    ]
    transition_rows = [
        [item.get("from_state", "-"), item.get("to_state", "-"), _fmt_int(item.get("count")), _fmt_percent(_as_float(item.get("share")) * 100)]
        for item in hmm.get("transitions", [])[:8]
        if isinstance(item, dict)
    ]
    findings = [
        f"User-week status={user_week.get('method_status', 'missing')}, rows={user_week.get('summary', {}).get('row_count', 0)}.",
        f"HMM state-path status={hmm.get('method_status', 'missing')}, states={len(state_rows)}, transitions={len(transition_rows)}.",
    ]
    plan = _plan(
        "user_state_path",
        "User State Path",
        "Add optional user-week and state-path context when user-level artifacts exist or explicitly downgraded artifacts were generated.",
        "Use user-week and HMM state-path outputs as optional segmentation context after aggregate mechanism diagnostics.",
        [
            _tool_call("panel.build_user_week", "Refresh user-week panel when user-level order data changes."),
            _tool_call("analysis.run_hmm_state_path", "Refresh state-path artifact with method-status downgrade when support is thin."),
        ],
        _artifact_paths(context, ["user_week", "hmm_state_path"]),
        ["User state paths require user_id-level orders and multiple weeks of history."],
        _limitations_for(context, ["user_week", "hmm_state_path"]),
        ["Treat limited HMM outputs as segmentation scaffolding until a probabilistic HMM backend is enabled."],
        findings=findings,
    )
    body = "\n".join(
        [
            _bullets(findings),
            "\n**States**\n",
            _markdown_table(["state", "rows", "avg GMV"], state_rows),
            "\n**Top Transitions**\n",
            _markdown_table(["from", "to", "count", "share"], transition_rows),
        ]
    )
    return ReportSection(plan, body)


def _mechanism_conversion_section(context: ReportContext) -> ReportSection:
    mechanism = context.results.get("mechanism", {})
    conversion = context.results.get("conversion", {})
    model_rows = []
    for model in mechanism.get("models", []):
        if not isinstance(model, dict):
            continue
        discount = next(
            (
                coefficient
                for coefficient in model.get("coefficients", [])
                if isinstance(coefficient, dict) and coefficient.get("term") == "discount_rate_pp"
            ),
            {},
        )
        exposure = next(
            (
                coefficient
                for coefficient in model.get("coefficients", [])
                if isinstance(coefficient, dict) and coefficient.get("term") == "log_view_uv"
            ),
            {},
        )
        model_rows.append(
            [
                model.get("model_id", "-"),
                model.get("outcome", "-"),
                model.get("status", "-"),
                _fmt_signed_money(discount.get("coefficient")),
                _fmt_signed_money(exposure.get("coefficient")),
                _fmt_percent(model.get("r_squared_within") * 100 if model.get("r_squared_within") is not None else None),
            ]
        )

    tier_rows = [
        [
            item.get("tier", "-"),
            _fmt_int(item.get("category_count")),
            _fmt_int(item.get("row_count")),
            _fmt_money(item.get("avg_conversion_per_10k_uv")),
            _fmt_signed_money(item.get("discount_slope_per_pp")),
            item.get("model", {}).get("status", "-") if isinstance(item.get("model"), dict) else "-",
        ]
        for item in conversion.get("exposure_tiers", [])
        if isinstance(item, dict)
    ]
    findings = [
        f"Mechanism models available: {len(model_rows)}; status={mechanism.get('method_status', 'missing')}.",
        f"Conversion exposure tiers available: {len(tier_rows)}; status={conversion.get('method_status', 'missing')}.",
    ]

    plan = _plan(
        "mechanism_conversion",
        "Mechanism And Conversion",
        "Explain whether resource effects came through traffic, order volume, AOV, or discount conversion by exposure tier.",
        "Use mechanism regression and conversion diagnostics after LocalGap and before resource allocation.",
        [
            _tool_call("analysis.run_mechanism_regression", "Refresh GMV/order/AOV resource mechanism models."),
            _tool_call("analysis.run_conversion_diagnostics", "Refresh discount conversion by exposure tier."),
        ],
        _artifact_paths(context, ["mechanism", "conversion"]),
        ["Mechanism and conversion models are observational diagnostics over the current category-day panel."],
        _limitations_for(context, ["mechanism", "conversion"]),
        ["Compare mechanism signals with GPS/uplift before scaling discount or exposure investment."],
        findings=findings,
    )
    body = "\n".join(
        [
            _bullets(findings),
            "\n**Mechanism Models**\n",
            _markdown_table(
                ["model", "outcome", "status", "discount coef", "exposure coef", "within R2"],
                model_rows,
            ),
            "\n**Conversion By Exposure Tier**\n",
            _markdown_table(
                ["tier", "categories", "rows", "conversion per 10k UV", "discount slope", "status"],
                tier_rows,
            ),
        ]
    )
    return ReportSection(plan, body)


def _assumptions_next_checks_section(context: ReportContext) -> ReportSection:
    limitations = _global_limitations(context)
    follow_up = _recommended_next_actions(context)
    assumptions = [
        "输入 CSV 已映射到标准的订单、曝光和活动时间线角色。",
        "报告以当前 workspace artifact 作为事实来源。",
        "除非补充更强实验设计，所有因果表述都保持方向性措辞。",
    ]

    plan = _plan(
        "assumptions_next_checks",
        "假设、限制与下一步",
        "清楚说明证据质量和缺失工作，避免报告过度自信。",
        "总结 demo 或决策评审时必须携带的约束条件。",
        [_tool_call("result.get_latest", "每次 pipeline 更新后确认结果包是否最新。")],
        _all_available_artifact_paths(context),
        assumptions,
        limitations,
        follow_up,
        findings=[*limitations, *follow_up],
    )
    body = "\n".join(
        [
            "**关键假设**\n",
            _bullets(assumptions),
            "\n**限制条件**\n",
            _bullets(limitations),
            "\n**建议下一步**\n",
            _bullets(follow_up),
        ]
    )
    return ReportSection(plan, body)


def _render_markdown(context: ReportContext, sections: list[ReportSection]) -> str:
    lines = [
        f"# {context.project_name} 分析报告",
        "",
        f"**项目 ID**: `{context.project_id}`",
        f"**生成时间**: {context.generated_at}",
        "",
        "> 本报告由 workspace artifact 自动生成。每个章节都说明用途、证据、假设或限制，以及建议下一步。",
        "",
        "## 报告结构",
        "",
        _markdown_table(
            ["章节", "目的", "证据数量"],
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
                f"**本节目的**: {section.plan.purpose}",
                "",
                "**证据文件**",
                "",
                _bullets(section.plan.evidence_artifacts or ["暂无专属证据文件。"]),
                "",
                section.body,
                "",
                "**假设与限制**",
                "",
                _bullets([*section.plan.assumptions, *section.plan.limitations] or ["暂无。"]),
                "",
                "**建议下一步**",
                "",
                _bullets(section.plan.recommended_follow_up or ["暂无立即动作。"]),
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
            missing.append(f"缺失结果文件：{entry['name']}（{entry['path']}）。")
    for entry in chart_entries:
        if not entry["available"] and _chart_source_is_ready(entry["name"], results):
            missing.append(f"缺失图表文件：{entry['name']}（{entry['path']}）。")

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
    if name == "user_week":
        summary = data.get("summary", {})
        return {
            "row_count": summary.get("row_count"),
            "user_count": summary.get("user_count"),
            "week_count": summary.get("week_count"),
            "method_status": data.get("method_status"),
        }
    if name == "hmm_state_path":
        sample = data.get("sample", {})
        return {
            "state_count": data.get("state_count"),
            "transition_count": len(data.get("transitions", [])) if isinstance(data.get("transitions"), list) else 0,
            "row_count": sample.get("row_count"),
            "method_status": data.get("method_status"),
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
    if name == "mechanism":
        models = data.get("models", [])
        ok_models = [item for item in models if isinstance(item, dict) and item.get("status") == "ok"]
        return {
            "model_count": len(models) if isinstance(models, list) else 0,
            "estimable_model_count": len(ok_models),
            "method_status": data.get("method_status"),
        }
    if name == "conversion":
        tiers = data.get("exposure_tiers", [])
        estimable = [
            item
            for item in tiers
            if isinstance(item, dict) and isinstance(item.get("model"), dict) and item["model"].get("status") == "ok"
        ]
        return {
            "tier_count": len(tiers) if isinstance(tiers, list) else 0,
            "estimable_tier_count": len(estimable),
            "method_status": data.get("method_status"),
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
                "evidence": str(item.get("reason") or item.get("evidence") or "由 latest_result 提供。"),
                "guardrail": str(item.get("guardrail") or "复核毛利、库存和运营承载能力。"),
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
            action = "放大高质量曝光"
            guardrail = "避免低转化坑位，持续监控曝光到订单的转化。"
            evidence = f"曝光贡献 {_fmt_signed_money(exposure_gap)} 是当前最大可见驱动。"
        elif discount_gap >= payday_gap:
            action = "校准折扣深度"
            guardrail = "复核毛利，避免补贴外溢。"
            evidence = f"折扣贡献 {_fmt_signed_money(discount_gap)} 是当前最大可见驱动。"
        else:
            action = "围绕发薪日调整节奏"
            guardrail = "复核发薪窗口期的库存和渠道承载能力。"
            evidence = f"发薪日贡献 {_fmt_signed_money(payday_gap)} 是当前最大可见驱动。"
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
                    "action": str(segment.get("recommendation", "复核分群策略。")),
                    "evidence": "Uplift 分群输出。",
                    "guardrail": "GPS-Uplift 仍为 stub 或未验证时，只能作为方向性参考。",
                }
            )

    return actions or [
        {
            "category": "全部",
            "action": "先运行完整 pipeline，再给出品类级动作。",
            "evidence": "当前没有可用的品类建议 artifact。",
            "guardrail": "不要展示缺乏证据支撑的品类战术。",
        }
    ]


def _global_limitations(context: ReportContext) -> list[str]:
    limitations = []
    if "psm_did" in context.results:
        status = context.results["psm_did"].get("method_status")
        if status in {None, "simplified", "stub"}:
            limitations.append("PSM-DID 在 MVP 中是简化的方向性检查，不能替代实验级因果识别。")
    else:
        limitations.append("PSM-DID 证据缺失，因此当前没有可用的因果方向判断。")

    if "localgap" in context.results:
        limitations.append("LocalGap 是相对局部基线的观察性增量分解，尚未完全控制季节性、库存和竞品冲击。")
    else:
        limitations.append("LocalGap 证据缺失，因此当前无法审计增量分解。")

    uplift = context.results.get("uplift")
    if not uplift:
        limitations.append("GPS-Uplift 证据缺失，因此分群建议只能来自 diagnostics 和 LocalGap 的现有信号。")
    elif uplift.get("method_status") == "stub":
        limitations.append("GPS-Uplift 当前仍是 stub 输出，分群行动只能视为占位建议。")

    if "mechanism" not in context.results:
        limitations.append("Mechanism regression evidence is missing; traffic/order/AOV channel claims remain limited.")
    if "conversion" not in context.results:
        limitations.append("Conversion-by-exposure-tier evidence is missing; discount scaling claims remain limited.")
    hmm = context.results.get("hmm_state_path")
    if hmm and hmm.get("method_status") != "implemented":
        limitations.append("HMM state-path output is limited; use it as segmentation context rather than causal evidence.")

    if not context.panel_summary:
        limitations.append("Panel summary 缺失，因此行数和日期覆盖可能不完整。")

    if context.evidence_index["missing_evidence"]:
        limitations.append("部分预期证据文件缺失；请查看“证据覆盖”章节。")

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
    if "mechanism" in evidence_names:
        score += 0.05
    if "conversion" in evidence_names:
        score += 0.05
    if "user_week" in evidence_names:
        score += 0.02
    if "hmm_state_path" in evidence_names:
        score += 0.02
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
            "缺少 holdout、event-study 和稳健性证据时，因果表述保持方向性。",
        ],
    }


def _recommended_next_actions(context: ReportContext) -> list[str]:
    actions: list[str] = []
    if "diagnostics" not in context.results:
        actions.append("Panel 构建后运行 `analysis.run_diagnostics`。")
    if "psm_did" not in context.results:
        actions.append("运行 `analysis.run_psm_did` 以补充方向性因果证据。")
    if "localgap" not in context.results:
        actions.append("运行 `analysis.run_localgap` 以补充增量分解。")
    if "mechanism" not in context.results:
        actions.append("Run `analysis.run_mechanism_regression` before explaining traffic/order/AOV mechanisms.")
    if "conversion" not in context.results:
        actions.append("Run `analysis.run_conversion_diagnostics` before scaling discount recommendations by exposure tier.")
    if "uplift" not in context.results:
        actions.append("在提出分群策略前运行 `analysis.run_gps_uplift`。")
    if "user_week" not in context.results:
        actions.append("Run `panel.build_user_week` when user_id-level order data is available.")
    if "hmm_state_path" not in context.results:
        actions.append("Run `analysis.run_hmm_state_path` after user-week panel generation for optional state-path context.")
    if "diagnostics" in context.results and "gmv_trend" not in context.charts:
        actions.append("使用 `{type: 'gmv_trend'}` 运行 `chart.render`。")
    if "localgap" in context.results and "localgap" not in context.charts:
        actions.append("使用 `{type: 'localgap'}` 运行 `chart.render`。")
    actions.append("执行建议前复核毛利、库存和渠道承载能力。")
    return _dedupe_strings(actions)


def _limitations_for(context: ReportContext, evidence_names: list[str]) -> list[str]:
    limitations = []
    for name in evidence_names:
        normalized = "localgap" if name == "localgap_chart" else name
        if normalized in RESULT_SOURCES and normalized not in context.results:
            limitations.append(f"{normalized} 结果缺失。")
        if normalized in CHART_SOURCES and normalized not in context.charts:
            limitations.append(f"{normalized} 图表缺失。")
    if not limitations:
        return ["证据基于当前 workspace artifact；源数据变更后应刷新。"]
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
        return f"{start} 至 {end}"
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
