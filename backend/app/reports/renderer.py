import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.tools.schemas import ToolResult


def render_report(project_id: str, workspace_path: str, format: str = "md") -> ToolResult:
    """
    生成分析报告

    基于 .analysis/ 下的分析结果生成 Markdown 报告
    """
    workspace_path = Path(workspace_path)
    analysis_dir = workspace_path / ".analysis"

    latest_result_path = analysis_dir / "latest_result.json"
    if not latest_result_path.exists():
        return ToolResult(
            ok=False,
            action="report.generate",
            summary="",
            error={"code": "NO_RESULTS", "message": "请先运行完整分析 pipeline"},
        )

    results = json.loads(latest_result_path.read_text(encoding="utf-8"))

    diagnostics = results.get("diagnostics", {})
    localgap = results.get("localgap", {})
    psm_did = results.get("psm_did", {})

    report_sections = []

    report_sections.append("# 商业分析报告\n")
    report_sections.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_sections.append(f"**项目ID**: {project_id}\n")
    report_sections.append("---\n")

    report_sections.append("## 摘要\n")
    summary = diagnostics.get("summary", {})
    report_sections.append(f"- 总 GMV: {summary.get('total_gmv', 'N/A')}")
    report_sections.append(f"- 分析天数: {summary.get('total_days', 'N/A')}")
    report_sections.append(f"- 品类数量: {summary.get('total_categories', 'N/A')}")
    report_sections.append(f"- 活动天数: {summary.get('activity_days', 'N/A')}")
    report_sections.append("")

    if psm_did:
        report_sections.append("## 因果推断结果 (PSM-DID)\n")
        estimates = psm_did.get("estimates", {})
        report_sections.append(f"- DID 估计值: {estimates.get('did_estimate', 'N/A')}")
        report_sections.append(f"- 处理组活动期前平均: {estimates.get('treated_pre_avg', 'N/A')}")
        report_sections.append(f"- 处理组活动期后平均: {estimates.get('treated_post_avg', 'N/A')}")
        report_sections.append(f"- 对照组活动期前平均: {estimates.get('control_pre_avg', 'N/A')}")
        report_sections.append(f"- 对照组活动期后平均: {estimates.get('control_post_avg', 'N/A')}")
        lift = psm_did.get("lift", {})
        report_sections.append(f"- 处理组 lift: {lift.get('treated_lift_pct', 'N/A')}%")
        report_sections.append(f"- 对照组 lift: {lift.get('control_lift_pct', 'N/A')}%")
        report_sections.append("")

    if localgap:
        report_sections.append("## 增量分解 (LocalGap)\n")
        report_sections.append(f"- 总实际 GMV: {localgap.get('total_actual_gmv', 'N/A')}")
        report_sections.append(f"- 总基线 GMV: {localgap.get('total_baseline_gmv', 'N/A')}")
        report_sections.append(f"- 总增量: {localgap.get('total_local_gap', 'N/A')}")
        report_sections.append("")
        report_sections.append("### 品类分解\n")
        report_sections.append("| 品类 | 基线GMV | 实际GMV | 增量 | exposure_gap | discount_gap | payday_gap |")
        report_sections.append("|------|---------|---------|------|--------------|--------------|------------|")
        for cat in localgap.get("categories", [])[:10]:
            report_sections.append(
                f"| {cat.get('category', '')} | {cat.get('baseline_gmv', '')} | {cat.get('actual_gmv', '')} | {cat.get('local_gap', '')} | "
                f"{cat.get('exposure_gap', '')} | {cat.get('discount_gap', '')} | {cat.get('payday_gap', '')} |"
            )
        report_sections.append("")

    if diagnostics:
        report_sections.append("## 品类集中度\n")
        concentration = diagnostics.get("category_concentration", [])
        report_sections.append("| 品类 | GMV | 占比 |")
        report_sections.append("|------|-----|------|")
        for cat in concentration[:10]:
            report_sections.append(f"| {cat.get('category', '')} | {cat.get('gmv', '')} | {cat.get('share', '')}% |")
        report_sections.append("")

    report_sections.append("## 分析方法说明\n")
    report_sections.append("1. **数据校验**: 检查 order_info, exposure_info, activity_timeline 三个数据文件")
    report_sections.append("2. **Panel 构建**: 按品类×日期聚合数据，构建分析面板")
    report_sections.append("3. **描述性诊断**: GMV 趋势、活动期对比、品类集中度分析")
    report_sections.append("4. **因果推断**: PSM-DID 方法估计活动的净效应")
    report_sections.append("5. **增量分解**: LocalGap 方法分解增量的来源")
    report_sections.append("")

    report_sections.append("## 策略建议\n")
    if localgap and localgap.get("categories"):
        top_cat = localgap["categories"][0]
        report_sections.append(f"- **重点关注品类**: {top_cat.get('category')}，增量贡献最大")
        if top_cat.get("exposure_gap", 0) > top_cat.get("discount_gap", 0):
            report_sections.append(f"- **{top_cat.get('category')}** 的增量主要来自曝光贡献，建议加大活动曝光投入")
        else:
            report_sections.append(f"- **{top_cat.get('category')}** 的增量主要来自折扣贡献，建议优化折扣策略")
    report_sections.append("- 结合 PSM-DID 结果，评估活动的整体 ROI")
    report_sections.append("- 关注发薪日效应，提前配置资源")
    report_sections.append("")

    report_sections.append("## 局限性\n")
    report_sections.append("- PSM-DID 为简化版本，未包含复杂协变量调整")
    report_sections.append("- GPS-Uplift 模型为 stub 状态，完整版需要更多数据支持")
    report_sections.append("- 结果受数据质量和时间窗口影响")
    report_sections.append("")

    report_content = "\n".join(report_sections)

    report_dir = workspace_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"
    report_path.write_text(report_content, encoding="utf-8")

    return ToolResult(
        ok=True,
        action="report.generate",
        summary=f"报告已生成: {report_path.name}",
        artifacts=[{
            "type": "report",
            "title": "report.md",
            "path": str(report_path.relative_to(workspace_path)),
        }],
        assistant_hint="报告已生成，可以查看或导出。"
    )


def export_report(report_path: str, export_format: str) -> ToolResult:
    """导出报告到指定格式（当前仅支持 md）"""
    if export_format != "md":
        return ToolResult(
            ok=True,
            action="report.export",
            summary=f"导出格式 {export_format}暂不支持，仅支持 md",
            artifacts=[],
        )

    return ToolResult(
        ok=True,
        action="report.export",
        summary=f"报告已导出为 {export_format} 格式",
        artifacts=[],
    )
