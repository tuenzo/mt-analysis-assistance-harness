from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


def run_diagnostics(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel_path = workspace / "data" / "processed" / "category_day_panel.json"
    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before diagnostics."},
        )

    panel = _load_panel(panel_path)
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_diagnostics",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    panel = _prepare_panel(panel)
    warnings = _quality_warnings(panel)
    gmv_trend = _gmv_trend(panel)
    category_concentration = _category_concentration(panel)
    activity_vs_non = _activity_comparison(panel)
    payday_overlap = _binary_context(panel, "is_payday", "payday")
    weekday_context = _weekday_context(panel)

    result = {
        "method": "diagnostics",
        "method_status": "limited" if warnings else "implemented",
        "gmv_trend": gmv_trend,
        "activity_vs_non": activity_vs_non,
        "payday_overlap": payday_overlap,
        "weekday_context": weekday_context,
        "category_concentration": category_concentration,
        "quality": {
            "row_count": int(len(panel)),
            "category_count": int(panel["category"].nunique()),
            "date_count": int(panel["date"].nunique()),
            "activity_rows": int(panel["is_activity"].sum()),
            "non_activity_rows": int((~panel["is_activity"]).sum()),
            "zero_gmv_share": round(float((panel["gmv"] <= 0).mean()), 4),
            "missing_gmv_share": round(float(panel["gmv"].isna().mean()), 4),
        },
        "summary": {
            "total_gmv": round(float(panel["gmv"].sum()), 2),
            "total_days": int(panel["date"].nunique()),
            "total_categories": int(panel["category"].nunique()),
            "activity_days": int(panel.loc[panel["is_activity"], "date"].nunique()),
            "payday_days": int(panel.loc[panel["is_payday"], "date"].nunique()),
            "activity_lift_pct": activity_vs_non.get("lift_pct"),
        },
        "warnings": warnings,
        "interpretation_rules": [
            "Diagnostics are descriptive context, not causal evidence.",
            "Use LocalGap as the main increment accounting layer before making promotion increment claims.",
        ],
    }

    output_path = workspace / ".analysis" / "diagnostics_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = (
        f"Diagnostics completed with gmv_trend: {result['summary']['total_days']} day(s), "
        f"{result['summary']['total_categories']} category/categories, "
        f"activity lift={result['summary']['activity_lift_pct']}%."
    )
    return ToolResult(
        ok=True,
        action="analysis.run_diagnostics",
        summary=summary,
        artifacts=[
            {
                "type": "diagnostics_result",
                "title": "diagnostics_result.json",
                "path": str(output_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "gmv_trend_days": len(gmv_trend),
                "top_category": category_concentration[0]["category"] if category_concentration else None,
                "warnings": warnings,
            }
        ],
        assistant_hint="Diagnostics are descriptive. Continue with PSM-DID and LocalGap before causal interpretation.",
    )


def _load_panel(panel_path: Path) -> pd.DataFrame:
    data = json.loads(panel_path.read_text(encoding="utf-8"))
    return pd.DataFrame(data if isinstance(data, list) else [])


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    prepared = panel.copy()
    prepared["date"] = pd.to_datetime(prepared.get("date"), errors="coerce")
    prepared = prepared.dropna(subset=["date"]).copy()
    if "category" not in prepared.columns:
        prepared["category"] = prepared.get("category_name", prepared.get("category_key", "unknown"))
    prepared["category"] = prepared["category"].astype(str)
    for column in ["gmv", "discount_rate", "view_uv", "buy_uv", "exposure"]:
        if column not in prepared.columns:
            prepared[column] = 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    if "is_payday" not in prepared.columns:
        prepared["is_payday"] = False
    if "pre_activity_window" not in prepared.columns:
        prepared["pre_activity_window"] = 0
    if "post_activity_window" not in prepared.columns:
        prepared["post_activity_window"] = 0
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    prepared["is_payday"] = prepared["is_payday"].astype(bool)
    prepared["pre_activity_window"] = pd.to_numeric(prepared["pre_activity_window"], errors="coerce").fillna(0).astype(int)
    prepared["post_activity_window"] = pd.to_numeric(prepared["post_activity_window"], errors="coerce").fillna(0).astype(int)
    prepared["weekday"] = prepared["date"].dt.weekday
    prepared["weekday_name"] = prepared["date"].dt.day_name()
    prepared["conversion_rate"] = np.where(prepared["view_uv"] > 0, prepared["buy_uv"] / prepared["view_uv"], 0.0)
    return prepared


def _gmv_trend(panel: pd.DataFrame) -> list[dict[str, Any]]:
    trend = (
        panel.groupby("date", as_index=False)
        .agg(
            gmv=("gmv", "sum"),
            activity_rows=("is_activity", "sum"),
            pre_activity_rows=("pre_activity_window", "sum"),
            post_activity_rows=("post_activity_window", "sum"),
            category_count=("category", "nunique"),
        )
        .sort_values("date")
    )
    trend["rolling_7d_gmv"] = trend["gmv"].rolling(7, min_periods=1).mean()
    return [
        {
            "date": row.date.date().isoformat(),
            "gmv": round(float(row.gmv), 2),
            "rolling_7d_gmv": round(float(row.rolling_7d_gmv), 2),
            "activity_rows": int(row.activity_rows),
            "pre_activity_rows": int(row.pre_activity_rows),
            "post_activity_rows": int(row.post_activity_rows),
            "category_count": int(row.category_count),
        }
        for row in trend.itertuples(index=False)
    ]


def _activity_comparison(panel: pd.DataFrame) -> dict[str, Any]:
    return _binary_context(panel, "is_activity", "activity")


def _binary_context(panel: pd.DataFrame, flag_column: str, label: str) -> dict[str, Any]:
    positive = panel[panel[flag_column]]
    negative = panel[~panel[flag_column]]
    pos_mean = float(positive["gmv"].mean()) if not positive.empty else 0.0
    neg_mean = float(negative["gmv"].mean()) if not negative.empty else 0.0
    pvalue = _normal_approx_pvalue(positive["gmv"], negative["gmv"])
    return {
        f"{label}_rows": int(len(positive)),
        f"non_{label}_rows": int(len(negative)),
        f"{label}_total_gmv": round(float(positive["gmv"].sum()), 2),
        f"non_{label}_total_gmv": round(float(negative["gmv"].sum()), 2),
        f"{label}_avg_gmv": round(pos_mean, 2),
        f"non_{label}_avg_gmv": round(neg_mean, 2),
        "mean_diff": round(pos_mean - neg_mean, 2),
        "lift_pct": round((pos_mean - neg_mean) / neg_mean * 100, 2) if neg_mean > 0 else None,
        "normal_approx_pvalue": pvalue,
    }


def _category_concentration(panel: pd.DataFrame) -> list[dict[str, Any]]:
    total = float(panel["gmv"].sum())
    grouped = (
        panel.groupby("category", as_index=False)
        .agg(gmv=("gmv", "sum"), activity_gmv=("gmv", lambda values: float(values[panel.loc[values.index, "is_activity"]].sum())))
        .sort_values("gmv", ascending=False)
    )
    cumulative = 0.0
    rows: list[dict[str, Any]] = []
    for row in grouped.itertuples(index=False):
        share = float(row.gmv) / total if total > 0 else 0.0
        cumulative += share
        rows.append(
            {
                "category": str(row.category),
                "gmv": round(float(row.gmv), 2),
                "activity_gmv": round(float(row.activity_gmv), 2),
                "share": round(share * 100, 2),
                "cumulative_share": round(cumulative * 100, 2),
            }
        )
    return rows[:10]


def _weekday_context(panel: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        panel.groupby(["weekday", "weekday_name"], as_index=False)
        .agg(avg_gmv=("gmv", "mean"), total_gmv=("gmv", "sum"), activity_rows=("is_activity", "sum"), rows=("gmv", "size"))
        .sort_values("weekday")
    )
    return [
        {
            "weekday": int(row.weekday),
            "weekday_name": str(row.weekday_name),
            "avg_gmv": round(float(row.avg_gmv), 2),
            "total_gmv": round(float(row.total_gmv), 2),
            "activity_rows": int(row.activity_rows),
            "rows": int(row.rows),
        }
        for row in grouped.itertuples(index=False)
    ]


def _quality_warnings(panel: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if int(panel["is_activity"].sum()) == 0:
        warnings.append("No activity rows are available; activity comparison is not estimable.")
    if int((~panel["is_activity"]).sum()) == 0:
        warnings.append("No non-activity rows are available; baseline comparisons are not estimable.")
    if panel["date"].nunique() < 14:
        warnings.append("Date coverage is shorter than 14 days; cyclical diagnostics are weak.")
    if panel["category"].nunique() < 2:
        warnings.append("Only one category is available; category concentration is limited.")
    if (panel["gmv"] <= 0).mean() > 0.5:
        warnings.append("More than half of rows have zero or negative GMV.")
    return warnings


def _normal_approx_pvalue(left: pd.Series, right: pd.Series) -> float | None:
    left = pd.to_numeric(left, errors="coerce").dropna()
    right = pd.to_numeric(right, errors="coerce").dropna()
    if len(left) < 2 or len(right) < 2:
        return None
    se = math.sqrt(float(left.var(ddof=1)) / len(left) + float(right.var(ddof=1)) / len(right))
    if not np.isfinite(se) or se <= 0:
        return None
    z = abs((float(left.mean()) - float(right.mean())) / se)
    return round(float(math.erfc(z / math.sqrt(2))), 6)
