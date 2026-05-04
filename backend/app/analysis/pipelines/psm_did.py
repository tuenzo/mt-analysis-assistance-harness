import json
from pathlib import Path
from collections import defaultdict
import math
from app.tools.schemas import ToolResult


def run_psm_did(project_id: str, workspace_path: str) -> ToolResult:
    """
    简化版 PSM-DID 因果推断

    方法:
        1. 计算每个品类的 exposure probability (活动期占比)
        2. 基于 exposure probability 做简单的倾向性得分匹配
        3. 计算 DID: (Treated_post - Treated_pre) - (Control_post - Control_pre)

    输入: category_day_panel.json
    输出: psm_did_result.json
    """
    workspace_path = Path(workspace_path)
    panel_path = workspace_path / "data" / "processed" / "category_day_panel.json"

    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "请先运行 panel.build_category_day"},
        )

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    if not panel_data:
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Panel 数据为空"},
        )

    category_data = defaultdict(list)
    for row in panel_data:
        category = row.get("category", "")
        if category:
            category_data[category].append(row)

    propensity_scores = {}
    for category, rows in category_data.items():
        activity_days = sum(1 for r in rows if r.get("is_activity"))
        total_days = len(rows)
        propensity_scores[category] = activity_days / total_days if total_days > 0 else 0

    sorted_categories = sorted(propensity_scores.items(), key=lambda x: x[1])
    median_score = sorted_categories[len(sorted_categories) // 2][1]

    treated_categories = [c for c, score in propensity_scores.items() if score > median_score]
    control_categories = [c for c, score in propensity_scores.items() if score <= median_score]

    def calc_avg_gmv(categories):
        total_gmv = 0
        total_rows = 0
        for cat in categories:
            for row in category_data[cat]:
                total_gmv += row.get("gmv", 0) or 0
                total_rows += 1
        return total_gmv / total_rows if total_rows > 0 else 0

    treated_pre = 0
    treated_post = 0
    control_pre = 0
    control_post = 0

    treated_pre_count = 0
    treated_post_count = 0
    control_pre_count = 0
    control_post_count = 0

    for cat, rows in category_data.items():
        for row in rows:
            is_treated = cat in treated_categories
            is_activity = row.get("is_activity", False)

            gmv = row.get("gmv", 0) or 0

            if is_treated:
                if is_activity:
                    treated_post += gmv
                    treated_post_count += 1
                else:
                    treated_pre += gmv
                    treated_pre_count += 1
            else:
                if is_activity:
                    control_post += gmv
                    control_post_count += 1
                else:
                    control_pre += gmv
                    control_pre_count += 1

    treated_pre_avg = treated_pre / treated_pre_count if treated_pre_count > 0 else 0
    treated_post_avg = treated_post / treated_post_count if treated_post_count > 0 else 0
    control_pre_avg = control_pre / control_pre_count if control_pre_count > 0 else 0
    control_post_avg = control_post / control_post_count if control_post_count > 0 else 0

    did_estimate = (treated_post_avg - treated_pre_avg) - (control_post_avg - control_pre_avg)

    treated_lift = ((treated_post_avg - treated_pre_avg) / treated_pre_avg * 100) if treated_pre_avg > 0 else 0
    control_lift = ((control_post_avg - control_pre_avg) / control_pre_avg * 100) if control_pre_avg > 0 else 0

    result = {
        "method": "psm_did",
        "method_status": "simplified",
        "treated_categories_count": len(treated_categories),
        "control_categories_count": len(control_categories),
        "psm_median_threshold": round(median_score, 4),
        "estimates": {
            "did_estimate": round(did_estimate, 2),
            "treated_pre_avg": round(treated_pre_avg, 2),
            "treated_post_avg": round(treated_post_avg, 2),
            "control_pre_avg": round(control_pre_avg, 2),
            "control_post_avg": round(control_post_avg, 2),
        },
        "lift": {
            "treated_lift_pct": round(treated_lift, 2),
            "control_lift_pct": round(control_lift, 2),
            "incremental_lift_pct": round(treated_lift - control_lift, 2),
        },
        "interpretation": {
            "did_estimate_interpretation": f"活动对GMV的净效应为 {round(did_estimate, 2)}",
            "treated_lift_interpretation": f"处理组活动期相比非活动期提升 {round(treated_lift, 2)}%",
            "control_lift_interpretation": f"对照组活动期相比非活动期提升 {round(control_lift, 2)}%",
        }
    }

    output_path = workspace_path / ".analysis" / "psm_did_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary = f"PSM-DID 完成: 处理组 {len(treated_categories)} 品类, DID估计={round(did_estimate, 2)}"
    return ToolResult(
        ok=True,
        action="analysis.run_psm_did",
        summary=summary,
        artifacts=[{
            "type": "psm_did_result",
            "title": "psm_did_result.json",
            "path": str(output_path.relative_to(workspace_path)),
            "did_estimate": round(did_estimate, 2),
        }],
        assistant_hint="PSM-DID 分析完成，可查看因果效应估计和处理组/对照组对比。"
    )
