from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


DEFAULT_RECENT_WINDOW_DAYS = 56
DEFAULT_FALLBACK_WINDOW_DAYS = 112
DEFAULT_MIN_BASELINE_OBS = 2
DEFAULT_RECOMMENDED_BASELINE_OBS = 4


def run_localgap(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel_path = workspace / "data" / "processed" / "category_day_panel.json"
    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before LocalGap."},
        )

    panel = _load_panel(panel_path)
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_localgap",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    panel = _prepare_panel(panel)
    panel_summary = _read_panel_summary(workspace)
    enriched = compute_localgap_enriched_panel(panel)
    result = summarize_localgap(enriched, panel_summary=panel_summary)

    output_dir = workspace / ".analysis"
    processed_dir = workspace / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    result_path = output_dir / "localgap_result.json"
    enriched_csv_path = processed_dir / "localgap_enriched_panel.csv"
    enriched_json_path = processed_dir / "localgap_enriched_panel.json"

    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    enriched.to_csv(enriched_csv_path, index=False, encoding="utf-8-sig")
    enriched.to_json(enriched_json_path, orient="records", force_ascii=False, indent=2, date_format="iso")

    summary = (
        f"LocalGap completed: {len(result['categories'])} category/categories, "
        f"coverage={round(result['diagnostics']['coverage_rate'] * 100, 1)}%, "
        f"total_gap={result['total_local_gap']}."
    )
    return ToolResult(
        ok=True,
        action="analysis.run_localgap",
        summary=summary,
        artifacts=[
            {
                "type": "localgap_result",
                "title": "localgap_result.json",
                "path": str(result_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "total_gap": result["total_local_gap"],
                "coverage_rate": result["diagnostics"]["coverage_rate"],
                "warnings": result["warnings"],
            },
            {
                "type": "panel_data",
                "title": "localgap_enriched_panel.csv",
                "path": str(enriched_csv_path.relative_to(workspace)),
                "rows": int(len(enriched)),
            },
            {
                "type": "panel_data",
                "title": "localgap_enriched_panel.json",
                "path": str(enriched_json_path.relative_to(workspace)),
                "rows": int(len(enriched)),
            },
        ],
        assistant_hint=(
            "Use LocalGap as the main increment accounting layer. GPS and uplift should consume "
            "localgap_enriched_panel when available."
        ),
    )


def compute_localgap_enriched_panel(panel: pd.DataFrame) -> pd.DataFrame:
    enriched = panel.sort_values(["category_key", "date"]).copy()
    enriched["aov"] = np.where(enriched["order_count"] > 0, enriched["gmv"] / enriched["order_count"], np.nan)
    enriched["local_baseline"] = np.nan
    enriched["cf_order_count"] = np.nan
    enriched["cf_aov"] = np.nan
    enriched["cf_component_gmv"] = np.nan
    enriched["baseline_obs"] = 0
    enriched["baseline_quality"] = "unavailable"

    for _, group in enriched.groupby("category_key", sort=False):
        ordered = group.sort_values("date")
        history_all = ordered[~ordered["is_activity"]].copy()
        for idx, row in ordered.iterrows():
            history = history_all[
                (history_all["date"] < row["date"])
                & (history_all["weekday"] == row["weekday"])
                & (history_all["date"] >= row["date"] - pd.Timedelta(days=DEFAULT_RECENT_WINDOW_DAYS))
            ]
            if len(history) < DEFAULT_MIN_BASELINE_OBS:
                history = history_all[
                    (history_all["date"] < row["date"])
                    & (history_all["weekday"] == row["weekday"])
                    & (history_all["date"] >= row["date"] - pd.Timedelta(days=DEFAULT_FALLBACK_WINDOW_DAYS))
                ]
            if len(history) < DEFAULT_MIN_BASELINE_OBS:
                history = history_all[
                    (history_all["date"] < row["date"])
                    & (history_all["date"] >= row["date"] - pd.Timedelta(days=DEFAULT_FALLBACK_WINDOW_DAYS))
                ]

            obs = int(len(history))
            if obs >= DEFAULT_MIN_BASELINE_OBS:
                enriched.loc[idx, "local_baseline"] = float(history["gmv"].mean())
                enriched.loc[idx, "cf_order_count"] = float(history["order_count"].mean())
                positive_aov = history["aov"].replace([np.inf, -np.inf], np.nan).dropna()
                if not positive_aov.empty:
                    enriched.loc[idx, "cf_aov"] = float(positive_aov.mean())
                    enriched.loc[idx, "cf_component_gmv"] = float(history["order_count"].mean()) * float(positive_aov.mean())
                enriched.loc[idx, "baseline_obs"] = obs
                enriched.loc[idx, "baseline_quality"] = (
                    "strong" if obs >= DEFAULT_RECOMMENDED_BASELINE_OBS else "weak"
                )

    enriched["local_gap"] = enriched["gmv"] - enriched["local_baseline"]
    enriched["component_gap"] = enriched["gmv"] - enriched["cf_component_gmv"]
    return _add_reference_terms(enriched)


def summarize_localgap(enriched: pd.DataFrame, panel_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    activity = enriched[enriched["is_activity"]].copy()
    estimable = activity[activity["local_baseline"].notna()].copy()
    model = _fit_decomposition_model(estimable)
    base_warnings = _localgap_warnings(enriched, activity, estimable)
    quality_gate = _localgap_quality_gate(enriched, activity, estimable, model, panel_summary)
    warnings = _dedupe([*base_warnings, *quality_gate["reasons"]])

    categories = _category_decomposition(estimable, model)
    monthly = _monthly_decomposition(estimable)
    lmdi = _lmdi_decomposition(estimable)
    total_actual = float(estimable["gmv"].sum()) if not estimable.empty else 0.0
    total_baseline = float(estimable["local_baseline"].sum()) if not estimable.empty else 0.0
    total_gap = float(estimable["local_gap"].sum()) if not estimable.empty else 0.0
    coverage_rate = float(len(estimable) / max(len(activity), 1))
    method_status = "implemented" if quality_gate["status"] == "ready" else "limited"

    return {
        "method": "localgap",
        "method_status": method_status,
        "quality_gate": quality_gate,
        "measure_units": (panel_summary or {}).get("measure_units", {}),
        "baseline_method": {
            "match": "historical_non_activity_same_weekday_then_fallback",
            "recent_window_days": DEFAULT_RECENT_WINDOW_DAYS,
            "fallback_window_days": DEFAULT_FALLBACK_WINDOW_DAYS,
            "min_local_baseline_obs": DEFAULT_MIN_BASELINE_OBS,
            "recommended_local_baseline_obs": DEFAULT_RECOMMENDED_BASELINE_OBS,
        },
        "categories": categories,
        "monthly_decomposition": monthly,
        "non_sparse_sample": _non_sparse_sample_summary(enriched, activity, estimable),
        "lmdi_decomposition": lmdi,
        "total_actual_gmv": round(total_actual, 2),
        "total_baseline_gmv": round(total_baseline, 2),
        "total_local_gap": round(total_gap, 2),
        "diagnostics": {
            "activity_rows": int(len(activity)),
            "estimable_rows": int(len(estimable)),
            "coverage_rate": round(coverage_rate, 4),
            "baseline_quality": {
                str(key): int(value) for key, value in activity["baseline_quality"].value_counts().items()
            },
            "model_terms": model["terms"],
            "r_squared": model["r_squared"],
            "component_baseline_coverage_rate": lmdi["diagnostics"]["coverage_rate"],
        },
        "warnings": warnings,
        "evidence_artifacts": [
            "data/processed/category_day_panel.json",
            "data/processed/localgap_enriched_panel.csv",
        ],
        "interpretation_rules": [
            "LocalGap is the main increment accounting layer.",
            "Channel attribution is conditional on the local baseline design and should be described directionally.",
            "Rows without LocalBaseline are excluded from increment totals rather than imputed.",
            "LMDI decomposes component counterfactual uplift where actual and counterfactual GMV/order/AOV are positive.",
        ],
    }


def _load_panel(panel_path: Path) -> pd.DataFrame:
    data = json.loads(panel_path.read_text(encoding="utf-8"))
    return pd.DataFrame(data if isinstance(data, list) else [])


def _read_panel_summary(workspace: Path) -> dict[str, Any]:
    path = workspace / ".analysis" / "panel_summary.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    prepared = panel.copy()
    if "category_key" not in prepared.columns:
        prepared["category_key"] = prepared.get("category", prepared.get("category_name", "unknown"))
    if "category_name" not in prepared.columns:
        prepared["category_name"] = prepared.get("category", prepared["category_key"])
    prepared["category_key"] = prepared["category_key"].astype(str)
    prepared["category_name"] = prepared["category_name"].astype(str)
    prepared["category"] = prepared.get("category", prepared["category_name"]).astype(str)
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared = prepared.dropna(subset=["date", "category_key"]).copy()
    for column in ["gmv", "view_uv", "exposure", "discount_rate", "discount_amount", "buy_uv", "order_count", "quantity"]:
        if column not in prepared.columns:
            prepared[column] = 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    prepared["view_uv"] = np.where(prepared["view_uv"] > 0, prepared["view_uv"], prepared["exposure"])
    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    if "is_payday" not in prepared.columns:
        prepared["is_payday"] = False
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    prepared["is_payday"] = prepared["is_payday"].astype(bool)
    prepared["weekday"] = prepared["date"].dt.weekday
    prepared["month"] = prepared["date"].dt.to_period("M").astype(str)
    prepared["days_to_payday"] = pd.to_numeric(
        prepared.get("days_to_payday", prepared["date"].dt.day - 27), errors="coerce"
    ).fillna(0.0)
    return prepared


def _add_reference_terms(panel: pd.DataFrame) -> pd.DataFrame:
    output = panel.copy()
    output["log_view_uv"] = np.log1p(output["view_uv"].clip(lower=0))
    non_activity = output[~output["is_activity"]].copy()
    refs = (
        non_activity.groupby("category_key", as_index=False)
        .agg(ref_log_view=("log_view_uv", "median"), ref_discount=("discount_rate", "median"))
    )
    output = output.merge(refs, on="category_key", how="left")
    output["ref_log_view"] = output["ref_log_view"].fillna(output["log_view_uv"].median())
    output["ref_discount"] = output["ref_discount"].fillna(output["discount_rate"].median())
    output["excess_view"] = output["log_view_uv"] - output["ref_log_view"]
    output["excess_discount"] = output["discount_rate"] - output["ref_discount"]
    output["excess_inter"] = output["excess_view"] * output["excess_discount"]
    output["dist2pay"] = output["days_to_payday"].astype(float)
    output["dist2pay_sq"] = output["dist2pay"] ** 2
    return output


def _fit_decomposition_model(estimable: pd.DataFrame) -> dict[str, Any]:
    candidate_terms = ["excess_discount", "excess_view", "excess_inter", "dist2pay", "dist2pay_sq"]
    terms = [
        term
        for term in candidate_terms
        if term in estimable.columns and estimable[term].notna().sum() >= 3 and estimable[term].nunique(dropna=True) > 1
    ]
    if estimable.empty or not terms or len(estimable) <= len(terms) + 1:
        return {"terms": [], "beta": {}, "r_squared": None}

    frame = estimable.dropna(subset=["local_gap", *terms]).copy()
    if len(frame) <= len(terms) + 1:
        return {"terms": [], "beta": {}, "r_squared": None}
    X = np.column_stack([np.ones(len(frame)), *[frame[term].astype(float).to_numpy() for term in terms]])
    y = frame["local_gap"].astype(float).to_numpy()
    beta = _safe_lstsq(X, y)
    pred = X @ beta
    sst = float(np.sum((y - np.mean(y)) ** 2))
    sse = float(np.sum((y - pred) ** 2))
    r_squared = 1 - sse / sst if sst > 0 else None
    return {
        "terms": terms,
        "beta": {"intercept": float(beta[0]), **{term: float(beta[index + 1]) for index, term in enumerate(terms)}},
        "r_squared": round(float(r_squared), 4) if r_squared is not None else None,
    }


def _category_decomposition(estimable: pd.DataFrame, model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    terms = model.get("terms") or []
    beta = model.get("beta") or {}
    for (category_key, category_name), group in estimable.groupby(["category_key", "category_name"], sort=False):
        local_gap = float(group["local_gap"].sum())
        exposure_gap = _term_contribution(group, beta, ["excess_view"])
        discount_gap = _term_contribution(group, beta, ["excess_discount"])
        interaction = _term_contribution(group, beta, ["excess_inter"])
        payday_gap = _term_contribution(group, beta, ["dist2pay", "dist2pay_sq"])
        explained = exposure_gap + discount_gap + interaction + payday_gap
        rows.append(
            {
                "category_key": str(category_key),
                "category": str(category_name),
                "activity_rows": int(len(group)),
                "baseline_quality": {str(k): int(v) for k, v in group["baseline_quality"].value_counts().items()},
                "baseline_gmv": round(float(group["local_baseline"].sum()), 2),
                "actual_gmv": round(float(group["gmv"].sum()), 2),
                "local_gap": round(local_gap, 2),
                "exposure_gap": round(exposure_gap, 2),
                "discount_gap": round(discount_gap, 2),
                "payday_gap": round(payday_gap, 2),
                "interaction": round(interaction, 2),
                "residual": round(local_gap - explained, 2),
                "decomposition_terms": terms,
            }
        )
    return sorted(rows, key=lambda item: item["local_gap"], reverse=True)


def _monthly_decomposition(estimable: pd.DataFrame) -> list[dict[str, Any]]:
    if estimable.empty:
        return []
    grouped = (
        estimable.groupby("month", as_index=False)
        .agg(actual_gmv=("gmv", "sum"), baseline_gmv=("local_baseline", "sum"), local_gap=("local_gap", "sum"), rows=("gmv", "size"))
        .sort_values("month")
    )
    return [
        {
            "month": str(row.month),
            "actual_gmv": round(float(row.actual_gmv), 2),
            "baseline_gmv": round(float(row.baseline_gmv), 2),
            "local_gap": round(float(row.local_gap), 2),
            "rows": int(row.rows),
        }
        for row in grouped.itertuples(index=False)
    ]


def _non_sparse_sample_summary(enriched: pd.DataFrame, activity: pd.DataFrame, estimable: pd.DataFrame) -> dict[str, Any]:
    component_estimable = _component_estimable(activity)
    total_activity_gmv = float(activity["gmv"].sum()) if not activity.empty else 0.0
    retained_gmv = float(component_estimable["gmv"].sum()) if not component_estimable.empty else 0.0
    all_categories = set(enriched["category_key"].astype(str).unique())
    retained_categories = set(estimable["category_key"].astype(str).unique())
    component_categories = set(component_estimable["category_key"].astype(str).unique())
    return {
        "definition": (
            "Activity rows with historical non-activity LocalBaseline support; component LMDI additionally "
            "requires positive actual/counterfactual GMV, order, and AOV."
        ),
        "total_category_count": int(len(all_categories)),
        "localgap_retained_category_count": int(len(retained_categories)),
        "component_retained_category_count": int(len(component_categories)),
        "dropped_category_count": int(max(len(all_categories - retained_categories), 0)),
        "activity_rows": int(len(activity)),
        "localgap_estimable_rows": int(len(estimable)),
        "component_estimable_rows": int(len(component_estimable)),
        "retained_activity_gmv_share": round(retained_gmv / total_activity_gmv, 4) if total_activity_gmv > 0 else 0.0,
    }


def _lmdi_decomposition(estimable: pd.DataFrame) -> dict[str, Any]:
    component = _component_estimable(estimable)
    total_activity_rows = int(len(estimable))
    if component.empty:
        return {
            "method": "additive_lmdi_order_aov",
            "status": "limited",
            "overall": _empty_lmdi_row("overall", "overall", "no_positive_component_cells"),
            "monthly": [],
            "category": [],
            "diagnostics": {
                "activity_rows": total_activity_rows,
                "estimable_rows": 0,
                "coverage_rate": 0.0,
                "zero_or_invalid_rows": total_activity_rows,
            },
            "warnings": ["No positive component counterfactual rows are available for LMDI."],
        }

    overall = _lmdi_group_row("overall", "overall", component)
    monthly = [
        _lmdi_group_row("month", str(month), group)
        for month, group in component.groupby("month", sort=True)
    ]
    category = [
        _lmdi_group_row("category", str(category), group)
        for category, group in component.groupby("category_name", sort=False)
    ]
    warnings = []
    coverage = len(component) / max(total_activity_rows, 1)
    if coverage < 0.5:
        warnings.append("Less than half of LocalGap-estimable activity rows are eligible for exact LMDI.")
    return {
        "method": "additive_lmdi_order_aov",
        "status": "implemented" if not warnings else "limited",
        "identity": "GMV = order_count * AOV",
        "overall": overall,
        "monthly": monthly,
        "category": sorted(category, key=lambda item: item["gmv_uplift"], reverse=True),
        "diagnostics": {
            "activity_rows": total_activity_rows,
            "estimable_rows": int(len(component)),
            "coverage_rate": round(float(coverage), 4),
            "zero_or_invalid_rows": int(total_activity_rows - len(component)),
        },
        "warnings": warnings,
    }


def _component_estimable(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["gmv", "cf_component_gmv", "order_count", "cf_order_count", "aov", "cf_aov"]
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=frame.columns)
    component = frame.dropna(subset=required).copy()
    for column in required:
        component = component[pd.to_numeric(component[column], errors="coerce") > 0]
    return component


def _lmdi_group_row(level: str, name: str, group: pd.DataFrame) -> dict[str, Any]:
    actual_gmv = float(group["gmv"].sum())
    counterfactual_gmv = float(group["cf_component_gmv"].sum())
    actual_order = float(group["order_count"].sum())
    counterfactual_order = float(group["cf_order_count"].sum())
    actual_aov = actual_gmv / actual_order if actual_order > 0 else np.nan
    counterfactual_aov = counterfactual_gmv / counterfactual_order if counterfactual_order > 0 else np.nan
    if min(actual_gmv, counterfactual_gmv, actual_order, counterfactual_order, actual_aov, counterfactual_aov) <= 0:
        return _empty_lmdi_row(level, name, "zero_baseline_or_zero_actual")

    log_mean = _log_mean(actual_gmv, counterfactual_gmv)
    order_contribution = log_mean * math.log(actual_order / counterfactual_order)
    aov_contribution = log_mean * math.log(actual_aov / counterfactual_aov)
    uplift = actual_gmv - counterfactual_gmv
    residual = uplift - order_contribution - aov_contribution
    return {
        "level": level,
        "name": name,
        "rows": int(len(group)),
        "actual_gmv": round(actual_gmv, 2),
        "counterfactual_gmv": round(counterfactual_gmv, 2),
        "gmv_uplift": round(uplift, 2),
        "actual_order": round(actual_order, 2),
        "counterfactual_order": round(counterfactual_order, 2),
        "actual_aov": round(actual_aov, 4),
        "counterfactual_aov": round(counterfactual_aov, 4),
        "order_contribution": round(float(order_contribution), 2),
        "aov_contribution": round(float(aov_contribution), 2),
        "order_contribution_share": _safe_share(order_contribution, uplift),
        "aov_contribution_share": _safe_share(aov_contribution, uplift),
        "lmdi_residual_check": round(float(residual), 6),
        "zero_handling_flag": "exact_positive",
    }


def _empty_lmdi_row(level: str, name: str, flag: str) -> dict[str, Any]:
    return {
        "level": level,
        "name": name,
        "rows": 0,
        "actual_gmv": 0.0,
        "counterfactual_gmv": 0.0,
        "gmv_uplift": 0.0,
        "actual_order": 0.0,
        "counterfactual_order": 0.0,
        "actual_aov": 0.0,
        "counterfactual_aov": 0.0,
        "order_contribution": 0.0,
        "aov_contribution": 0.0,
        "order_contribution_share": None,
        "aov_contribution_share": None,
        "lmdi_residual_check": None,
        "zero_handling_flag": flag,
    }


def _log_mean(current: float, baseline: float) -> float:
    if abs(current - baseline) <= 1e-12:
        return float(current)
    return float((current - baseline) / (math.log(current) - math.log(baseline)))


def _safe_share(value: float, total: float) -> float | None:
    if abs(total) <= 1e-9:
        return None
    return round(float(value / total), 6)


def _term_contribution(group: pd.DataFrame, beta: dict[str, float], terms: list[str]) -> float:
    value = 0.0
    for term in terms:
        if term in group.columns and term in beta:
            value += float((group[term].fillna(0.0) * beta[term]).sum())
    return value


def _localgap_warnings(enriched: pd.DataFrame, activity: pd.DataFrame, estimable: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if activity.empty:
        warnings.append("No activity rows are available for LocalGap.")
    coverage = len(estimable) / max(len(activity), 1)
    if coverage < 0.5:
        warnings.append("Less than half of activity rows have enough historical non-activity baseline support.")
    if (activity["baseline_quality"] == "weak").mean() > 0.5:
        warnings.append("Most estimable activity rows have weak baseline support.")
    if enriched["category_key"].nunique() < 2:
        warnings.append("Only one category is available; category-level decomposition is limited.")
    if estimable["excess_view"].nunique(dropna=True) < 2 and estimable["excess_discount"].nunique(dropna=True) < 2:
        warnings.append("Exposure and discount variation are too thin for channel attribution.")
    return warnings


def _localgap_quality_gate(
    enriched: pd.DataFrame,
    activity: pd.DataFrame,
    estimable: pd.DataFrame,
    model: dict[str, Any],
    panel_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    panel_summary = panel_summary or {}
    reasons: list[str] = []
    reason_codes: list[str] = []
    date_count = int(enriched["date"].nunique()) if "date" in enriched.columns else 0
    category_count = int(enriched["category_key"].nunique()) if "category_key" in enriched.columns else 0
    activity_rows = int(len(activity))
    estimable_rows = int(len(estimable))
    coverage_rate = round(float(estimable_rows / max(activity_rows, 1)), 4)
    weak_share = 0.0
    if activity_rows and "baseline_quality" in activity.columns:
        weak_share = round(float((activity["baseline_quality"] == "weak").mean()), 4)

    readiness = panel_summary.get("analysis_readiness")
    if isinstance(readiness, dict) and readiness.get("status") == "limited":
        for reason in readiness.get("reasons") or []:
            reason_text = str(reason)
            if reason_text:
                reasons.append(reason_text)
        for code in readiness.get("reason_codes") or []:
            code_text = str(code)
            if code_text:
                reason_codes.append(code_text)
    if date_count < 14:
        reason_codes.append("short_date_coverage")
        reasons.append(f"LocalGap panel covers {date_count} day(s), below the 14-day minimum for stable local baselines.")
    if activity_rows < max(6, category_count * 2):
        reason_codes.append("sparse_activity_rows")
        reasons.append(f"LocalGap has {activity_rows} activity row(s), too few for stable category-level action ranking.")
    if coverage_rate < 0.5:
        reason_codes.append("low_baseline_coverage")
        reasons.append("Less than half of activity rows have enough historical non-activity baseline support.")
    if weak_share > 0.5:
        reason_codes.append("weak_baseline_support")
        reasons.append("Most estimable activity rows have weak LocalBaseline support.")
    if not model.get("terms"):
        reason_codes.append("no_channel_attribution_terms")
        reasons.append("No channel attribution model terms were estimable; exposure, discount, and payday components should not be interpreted as drivers.")

    reason_codes = list(dict.fromkeys(reason_codes))
    reasons = _dedupe(reasons)
    status = "limited" if reasons else "ready"
    return {
        "status": status,
        "reason_codes": reason_codes,
        "reasons": reasons,
        "metrics": {
            "date_count": date_count,
            "category_count": category_count,
            "activity_rows": activity_rows,
            "estimable_rows": estimable_rows,
            "coverage_rate": coverage_rate,
            "weak_baseline_share": weak_share,
            "model_term_count": len(model.get("terms") or []),
        },
        "recommended_interpretation": "smoke_test_only" if status == "limited" else "directional_increment_accounting",
    }


def _dedupe(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(values) if value]


def _safe_lstsq(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        beta = np.zeros(X.shape[1])
    return np.nan_to_num(beta, nan=0.0, posinf=0.0, neginf=0.0)
