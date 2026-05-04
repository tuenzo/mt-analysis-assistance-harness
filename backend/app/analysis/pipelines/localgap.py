import json
from pathlib import Path
from collections import defaultdict
from app.tools.schemas import ToolResult


def run_localgap(project_id: str, workspace_path: str) -> ToolResult:
    """
    LocalGap 增量分解

    分解公式:
        LocalGap = actual - LocalBaseline
        LocalBaseline = 非活动期的平均 GMV
        分解:
            - exposure_gap: exposure 差异贡献
            - discount_gap: discount_rate 差异贡献
            - payday_gap: 发薪日效应
            - interaction: 交互效应
            - residual: 残差

    输入: category_day_panel.json
    输出: localgap_result.json
    """
    workspace_path = Path(workspace_path)
    panel_path = workspace_path / "data" / "processed" / "category_day_panel.json"

    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "请先运行 panel.build_category_day"},
        )

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    if not panel_data:
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Panel 数据为空"},
        )

    category_data = defaultdict(list)
    for row in panel_data:
        category = row.get("category", "")
        if category:
            category_data[category].append(row)

    results = []
    total_actual = 0
    total_baseline = 0

    for category, rows in category_data.items():
        activity_rows = [r for r in rows if r.get("is_activity")]
        non_activity_rows = [r for r in rows if not r.get("is_activity")]

        if not non_activity_rows:
            continue

        baseline_gmv = sum(r.get("gmv", 0) or 0 for r in non_activity_rows) / len(non_activity_rows)
        baseline_exposure = sum(r.get("exposure", 0) or 0 for r in non_activity_rows) / len(non_activity_rows)
        baseline_discount_rate = sum(r.get("discount_rate", 0) or 0 for r in non_activity_rows) / len(non_activity_rows)

        actual_gmv = sum(r.get("gmv", 0) or 0 for r in activity_rows) if activity_rows else 0
        actual_exposure = sum(r.get("exposure", 0) or 0 for r in activity_rows) if activity_rows else 0
        actual_discount_rate = sum(r.get("discount_rate", 0) or 0 for r in activity_rows) / len(activity_rows) if activity_rows else 0

        local_gap = actual_gmv - baseline_gmv

        exposure_gap = (actual_exposure - baseline_exposure) * (baseline_gmv / baseline_exposure if baseline_exposure > 0 else 0)
        discount_gap = (actual_discount_rate - baseline_discount_rate) * baseline_gmv * 0.01

        payday_rows = [r for r in activity_rows if r.get("is_payday")]
        payday_gap = (sum(r.get("gmv", 0) or 0 for r in payday_rows) / len(payday_rows) - baseline_gmv) if payday_rows else 0

        interaction = local_gap - exposure_gap - discount_gap - payday_gap

        total_actual += actual_gmv
        total_baseline += baseline_gmv

        results.append({
            "category": category,
            "baseline_gmv": round(baseline_gmv, 2),
            "actual_gmv": round(actual_gmv, 2),
            "local_gap": round(local_gap, 2),
            "exposure_gap": round(exposure_gap, 2),
            "discount_gap": round(discount_gap, 2),
            "payday_gap": round(payday_gap, 2),
            "interaction": round(interaction, 2),
            "residual": round(local_gap - exposure_gap - discount_gap - payday_gap - interaction, 2),
        })

    results.sort(key=lambda x: x["local_gap"], reverse=True)

    summary_result = {
        "categories": results,
        "total_actual_gmv": round(total_actual, 2),
        "total_baseline_gmv": round(total_baseline, 2),
        "total_local_gap": round(total_actual - total_baseline, 2),
        "method": "localgap",
        "method_status": "implemented",
    }

    output_path = workspace_path / ".analysis" / "localgap_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_result, f, ensure_ascii=False, indent=2)

    total_gap = total_actual - total_baseline
    summary = f"LocalGap 分析完成: {len(results)} 品类, 总增量={round(total_gap, 2)}"
    return ToolResult(
        ok=True,
        action="analysis.run_localgap",
        summary=summary,
        artifacts=[{
            "type": "localgap_result",
            "title": "localgap_result.json",
            "path": str(output_path.relative_to(workspace_path)),
            "total_gap": round(total_gap, 2),
        }],
        assistant_hint="增量分解完成，可查看各品类的 exposure_gap、discount_gap、payday_gap 贡献。"
    )
