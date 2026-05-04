import json
from pathlib import Path
from typing import Optional
from collections import defaultdict
from app.tools.schemas import ToolResult


def run_diagnostics(project_id: str, workspace_path: str) -> ToolResult:
    """
    描述性诊断分析

    输入: category_day_panel.json
    输出:
        - gmv_trend: 按日期的 GMV 趋势
        - activity_vs_non: 活动期 vs 非活动期对比
        - payday_overlap: 发薪日重叠分析
        - category_concentration: 品类集中度 top10
    """
    workspace_path = Path(workspace_path)
    panel_path = workspace_path / "data" / "processed" / "category_day_panel.json"

    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "请先运行 panel.build_category_day"},
        )

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    if not panel_data:
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Panel 数据为空"},
        )

    gmv_by_date = defaultdict(float)
    activity_gmv = []
    non_activity_gmv = []
    payday_gmv = []
    non_payday_gmv = []
    category_gmv = defaultdict(float)
    category_dates = defaultdict(list)

    for row in panel_data:
        date = row.get("date", "")
        category = row.get("category", "")
        gmv = row.get("gmv", 0) or 0
        is_activity = row.get("is_activity", False)
        is_payday = row.get("is_payday", False)

        gmv_by_date[date] += gmv
        category_gmv[category] += gmv
        category_dates[category].append(date)

        if is_activity:
            activity_gmv.append(gmv)
        else:
            non_activity_gmv.append(gmv)

        if is_payday:
            payday_gmv.append(gmv)
        else:
            non_payday_gmv.append(gmv)

    activity_avg = sum(activity_gmv) / len(activity_gmv) if activity_gmv else 0
    non_activity_avg = sum(non_activity_gmv) / len(non_activity_gmv) if non_activity_gmv else 0
    payday_avg = sum(payday_gmv) / len(payday_gmv) if payday_gmv else 0
    non_payday_avg = sum(non_payday_gmv) / len(non_payday_gmv) if non_payday_gmv else 0

    sorted_categories = sorted(category_gmv.items(), key=lambda x: x[1], reverse=True)
    top_categories = [{"category": c, "gmv": round(g, 2)} for c, g in sorted_categories[:10]]
    total_gmv = sum(category_gmv.values())
    concentration = [{"category": c, "gmv": round(g, 2), "share": round(g / total_gmv * 100, 2) if total_gmv > 0 else 0} for c, g in sorted_categories[:10]]

    trend_dates = sorted(gmv_by_date.keys())
    gmv_trend = [{"date": d, "gmv": round(gmv_by_date[d], 2)} for d in trend_dates]

    result = {
        "gmv_trend": gmv_trend,
        "activity_vs_non": {
            "activity_avg_gmv": round(activity_avg, 2),
            "non_activity_avg_gmv": round(non_activity_avg, 2),
            "lift": round((activity_avg - non_activity_avg) / non_activity_avg * 100, 2) if non_activity_avg > 0 else 0,
        },
        "payday_overlap": {
            "payday_avg_gmv": round(payday_avg, 2),
            "non_payday_avg_gmv": round(non_payday_avg, 2),
            "lift": round((payday_avg - non_payday_avg) / non_payday_avg * 100, 2) if non_payday_avg > 0 else 0,
        },
        "category_concentration": concentration,
        "summary": {
            "total_gmv": round(total_gmv, 2),
            "total_days": len(trend_dates),
            "total_categories": len(category_gmv),
            "activity_days": len(activity_gmv),
            "payday_days": len(payday_gmv),
        }
    }

    output_path = workspace_path / ".analysis" / "diagnostics_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary = f"诊断完成: {len(trend_dates)} 天, {len(category_gmv)} 品类, 活动期 lift={result['activity_vs_non']['lift']}%"
    return ToolResult(
        ok=True,
        action="analysis.run_diagnostics",
        summary=summary,
        artifacts=[{
            "type": "diagnostics_result",
            "title": "diagnostics_result.json",
            "path": str(output_path.relative_to(workspace_path)),
            "gmv_trend_days": len(gmv_trend),
            "top_category": top_categories[0]["category"] if top_categories else None,
        }],
        assistant_hint="诊断结果已生成，可查看 GMV 趋势、活动效果和品类集中度。"
    )
