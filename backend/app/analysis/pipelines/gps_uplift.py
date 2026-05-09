from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


DEFAULT_FEATURES = ["local_baseline", "gmv", "view_uv", "discount_rate", "buy_uv", "dist2pay"]


def run_gps_uplift(project_id: str, workspace_path: str, payload: dict | None = None) -> ToolResult:
    workspace = Path(workspace_path)
    panel = _load_best_panel(workspace)
    if panel is None:
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before GPS/uplift analysis."},
        )
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    config = payload or {}
    panel = _prepare_panel(panel, config)
    warnings = _support_warnings(panel)
    working = _analysis_sample(panel)

    dose_response = {
        "exposure": _estimate_dose_response(working, "exposure_intensity"),
        "discount": _estimate_dose_response(working, "discount_intensity"),
    }
    warnings = _dedupe(
        [
            *warnings,
            *[
                warning
                for item in dose_response.values()
                for warning in item.get("warnings", [])
            ],
        ]
    )

    uplift = _run_time_safe_uplift(working, treatment_col="combined_intensity", outcome_col="local_gap")
    warnings = _dedupe([*warnings, *uplift.get("warnings", [])])
    resource_scores = _resource_uplift_scores(panel, working)
    heterogeneity = _build_heterogeneity(working)
    warnings = _dedupe([*warnings, *heterogeneity.get("warnings", [])])
    ranking = _build_ranking(panel, working, dose_response, uplift)
    rank_curves = _build_rank_curves(ranking, resource_scores)
    marketing_quadrants = _build_marketing_quadrants(resource_scores)
    recommendations = _build_recommendations(ranking, dose_response)

    limited = bool(warnings) or any(item.get("status") == "limited" for item in dose_response.values())
    if uplift.get("status") != "ok":
        limited = True
    result = {
        "method": "gps_uplift",
        "method_status": "limited" if limited else "implemented",
        "status": "completed",
        "outcome": "local_gap",
        "sample": {
            "row_count": int(len(panel)),
            "analysis_rows": int(len(working)),
            "category_count": int(panel["category_key"].nunique()),
            "activity_rows": int(panel["is_activity"].sum()),
        },
        "dose_response": dose_response,
        "heterogeneity": heterogeneity,
        "uplift_model": uplift,
        "uplift_ranking": ranking,
        "resource_uplift_scores": resource_scores,
        "rank_curves": rank_curves,
        "marketing_quadrants": marketing_quadrants,
        "segments": [
            {
                "segment": item["bucket"],
                "category": item["category"],
                "recommendation": item["action"],
                "uplift_score": item["uplift_score"],
                "stability": item.get("stability"),
                "evidence": item["evidence"],
            }
            for item in recommendations
        ],
        "recommended_actions": recommendations,
        "diagnostics": {
            "row_count": int(len(panel)),
            "category_count": int(panel["category_key"].nunique()),
            "activity_rows": int(panel["is_activity"].sum()),
            "treatments": ["exposure", "discount", "combined_intensity"],
            "baseline_quality": {
                str(key): int(value) for key, value in panel["baseline_quality"].value_counts().items()
            },
            "fold_count": int(uplift.get("fold_count") or 0),
        },
        "method_assumptions": [
            "GPS estimates directional dose-response over supported treatment ranges.",
            "Uplift uses time-safe folds when enough temporal support exists.",
            "LocalGap remains the main increment accounting layer; uplift is prioritization logic.",
        ],
        "warnings": warnings,
        "evidence_artifacts": [
            "data/processed/localgap_enriched_panel.csv",
            ".analysis/localgap_result.json",
        ],
    }

    analysis_dir = workspace / ".analysis"
    table_dir = workspace / "artifacts" / "tables"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    gps_path = analysis_dir / "gps_uplift_result.json"
    uplift_path = analysis_dir / "uplift_result.json"
    rec_path = table_dir / "category_action_recommendations.csv"
    quadrant_path = table_dir / "resource_marketing_quadrants.csv"
    gps_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    uplift_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_recommendations_csv(rec_path, recommendations)
    _write_resource_scores_csv(quadrant_path, resource_scores)

    summary = (
        f"GPS/uplift completed: {len(ranking)} category/categories, "
        f"{len(recommendations)} recommendation(s), status={result['method_status']}."
    )
    return ToolResult(
        ok=True,
        action="analysis.run_gps_uplift",
        summary=summary,
        artifacts=[
            {
                "type": "model_output",
                "title": "gps_uplift_result.json",
                "path": str(gps_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "status": "completed",
                "warnings": warnings,
            },
            {
                "type": "model_output",
                "title": "uplift_result.json",
                "path": str(uplift_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "status": "completed",
                "segment_count": len(result["segments"]),
                "fold_count": result["diagnostics"]["fold_count"],
            },
            {
                "type": "table",
                "title": "category_action_recommendations.csv",
                "path": str(rec_path.relative_to(workspace)),
                "rows": len(recommendations),
            },
            {
                "type": "table",
                "title": "resource_marketing_quadrants.csv",
                "path": str(quadrant_path.relative_to(workspace)),
                "rows": len(resource_scores),
            },
        ],
        assistant_hint=(
            "Treat GPS and uplift as dose-response and prioritization evidence. Keep LocalGap as the main increment layer."
        ),
    )


def _load_best_panel(workspace: Path) -> pd.DataFrame | None:
    enriched_csv = workspace / "data" / "processed" / "localgap_enriched_panel.csv"
    if enriched_csv.exists():
        return pd.read_csv(enriched_csv)
    panel_json = workspace / "data" / "processed" / "category_day_panel.json"
    if not panel_json.exists():
        return None
    data = json.loads(panel_json.read_text(encoding="utf-8"))
    return pd.DataFrame(data if isinstance(data, list) else [])


def _prepare_panel(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    prepared = panel.copy()
    if "category_key" not in prepared.columns:
        prepared["category_key"] = prepared.get("category", prepared.get("category_name", "unknown"))
    if "category_name" not in prepared.columns:
        prepared["category_name"] = prepared.get("category", prepared["category_key"])
    prepared["category_key"] = prepared["category_key"].astype(str)
    prepared["category_name"] = prepared["category_name"].astype(str)
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared = prepared.dropna(subset=["date", "category_key"]).copy()

    for column in ["gmv", "view_uv", "exposure", "discount_rate", "discount_amount", "buy_uv", "local_baseline", "local_gap"]:
        if column not in prepared.columns:
            prepared[column] = np.nan if column in {"local_baseline", "local_gap"} else 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared["view_uv"] = prepared["view_uv"].fillna(0.0)
    prepared["exposure"] = prepared["exposure"].fillna(0.0)
    prepared["view_uv"] = np.where(prepared["view_uv"] > 0, prepared["view_uv"], prepared["exposure"])
    prepared["discount_rate"] = prepared["discount_rate"].fillna(0.0).clip(lower=0.0)
    prepared["gmv"] = prepared["gmv"].fillna(0.0)
    prepared["buy_uv"] = prepared["buy_uv"].fillna(0.0)

    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    if "is_payday" not in prepared.columns:
        prepared["is_payday"] = False
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    prepared["is_payday"] = prepared["is_payday"].astype(bool)
    prepared["weekday"] = prepared["date"].dt.weekday
    prepared["month"] = prepared["date"].dt.to_period("M").astype(str)
    prepared["dist2pay"] = pd.to_numeric(
        prepared.get("dist2pay", prepared.get("days_to_payday", prepared["date"].dt.day - 27)), errors="coerce"
    ).fillna(0.0)

    if prepared["local_baseline"].isna().all():
        prepared = _add_fallback_local_gap(prepared, int(config.get("baseline_window_days", 56)))
    prepared["local_gap"] = prepared["local_gap"].fillna(prepared["gmv"] - prepared["local_baseline"])
    prepared["baseline_quality"] = prepared.get("baseline_quality", "unavailable").fillna("unavailable").astype(str)
    prepared["exposure_intensity"] = np.log1p(prepared["view_uv"].clip(lower=0))
    prepared["discount_intensity"] = prepared["discount_rate"].clip(lower=0)
    prepared["combined_intensity"] = _standardize(prepared["exposure_intensity"]) + _standardize(prepared["discount_intensity"])
    return prepared


def _add_fallback_local_gap(panel: pd.DataFrame, baseline_window_days: int) -> pd.DataFrame:
    output = panel.sort_values(["category_key", "date"]).copy()
    output["local_baseline"] = np.nan
    output["baseline_obs"] = 0
    output["baseline_quality"] = "unavailable"
    for _, group in output.groupby("category_key", sort=False):
        ordered = group.sort_values("date")
        history_all = ordered[~ordered["is_activity"]]
        for idx, row in ordered.iterrows():
            history = history_all[
                (history_all["date"] < row["date"])
                & (history_all["weekday"] == row["weekday"])
                & (history_all["date"] >= row["date"] - pd.Timedelta(days=baseline_window_days))
            ]
            if len(history) < 2:
                history = history_all[(history_all["date"] < row["date"])]
            if len(history) >= 2:
                output.loc[idx, "local_baseline"] = float(history["gmv"].mean())
                output.loc[idx, "baseline_obs"] = int(len(history))
                output.loc[idx, "baseline_quality"] = "strong" if len(history) >= 4 else "weak"
    output["local_gap"] = output["gmv"] - output["local_baseline"]
    return output


def _analysis_sample(panel: pd.DataFrame) -> pd.DataFrame:
    sample = panel[panel["is_activity"] & panel["local_gap"].notna()].copy()
    if len(sample) < 6:
        sample = panel[panel["local_gap"].notna()].copy()
    return sample.dropna(subset=["local_gap", "combined_intensity"]).copy()


def _estimate_dose_response(panel: pd.DataFrame, treatment_col: str) -> dict[str, Any]:
    support = int(panel[treatment_col].nunique(dropna=True)) if treatment_col in panel.columns else 0
    if panel.empty or len(panel) < 6 or support < 3:
        return {
            "status": "limited",
            "treatment": treatment_col,
            "curve": [],
            "diagnostics": {"support": support, "row_count": int(len(panel)), "overlap_quality": "insufficient"},
            "warnings": [f"{treatment_col} has insufficient sample support for GPS dose-response."],
        }

    frame = panel.dropna(subset=[treatment_col, "local_gap"]).copy()
    treatment = frame[treatment_col].astype(float).to_numpy()
    outcome = frame["local_gap"].astype(float).to_numpy()
    gps_current, predicted_treatment, sigma = _estimate_gps(frame, treatment_col)
    X = np.column_stack(
        [
            np.ones(len(frame)),
            treatment,
            treatment**2,
            gps_current,
            gps_current**2,
            treatment * gps_current,
        ]
    )
    beta = _safe_lstsq(X, outcome)

    lower = float(np.quantile(treatment, 0.05))
    upper = float(np.quantile(treatment, 0.95))
    if lower == upper:
        lower = float(np.min(treatment))
        upper = float(np.max(treatment))
    grid = np.linspace(lower, upper, min(9, max(5, support)))

    curve: list[dict[str, Any]] = []
    for dose in grid:
        gps_for_dose = _normal_density(np.full(len(frame), dose), predicted_treatment, sigma)
        design = np.column_stack(
            [
                np.ones(len(frame)),
                np.full(len(frame), dose),
                np.full(len(frame), dose**2),
                gps_for_dose,
                gps_for_dose**2,
                np.full(len(frame), dose) * gps_for_dose,
            ]
        )
        predicted = design @ beta
        nearest = frame.iloc[np.argsort(np.abs(treatment - dose))[: max(1, min(8, len(frame)))]]
        curve.append(
            {
                "dose": round(float(dose), 4),
                "predicted_local_gap": round(float(np.mean(predicted)), 4),
                "observed_mean_local_gap": round(float(nearest["local_gap"].mean()), 4),
                "nearest_row_count": int(len(nearest)),
            }
        )

    shape = _curve_shape([row["predicted_local_gap"] for row in curve])
    gps_q = np.quantile(gps_current, [0.05, 0.5, 0.95])
    overlap_quality = "strong" if gps_q[0] > 1e-4 and support >= 5 else "thin"
    warnings = []
    if overlap_quality == "thin":
        warnings.append(f"{treatment_col} overlap is thin; interpret GPS curve directionally.")
    if shape == "unstable":
        warnings.append(f"{treatment_col} response curve is unstable across supported doses.")

    return {
        "status": "limited" if warnings else "implemented",
        "treatment": treatment_col,
        "supported_range": {"lower": round(lower, 4), "upper": round(upper, 4)},
        "curve": curve,
        "diagnostics": {
            "support": support,
            "row_count": int(len(frame)),
            "sigma": round(float(sigma), 6),
            "gps_quantiles": [round(float(value), 6) for value in gps_q],
            "overlap_quality": overlap_quality,
            "response_shape": shape,
        },
        "warnings": warnings,
    }


def _estimate_gps(frame: pd.DataFrame, treatment_col: str) -> tuple[np.ndarray, np.ndarray, float]:
    y = frame[treatment_col].astype(float).to_numpy()
    covariates = pd.DataFrame(
        {
            "intercept": 1.0,
            "weekday": frame["weekday"].astype(float),
            "is_payday": frame["is_payday"].astype(float),
            "local_baseline": frame["local_baseline"].fillna(frame["gmv"].mean()).astype(float),
            "category_avg_gmv": frame.groupby("category_key")["gmv"].transform("mean").astype(float),
            "dist2pay": frame["dist2pay"].astype(float),
        }
    ).to_numpy()
    beta = _safe_lstsq(covariates, y)
    predicted = covariates @ beta
    residual = y - predicted
    sigma = max(float(np.std(residual, ddof=1)), 1e-6)
    return _normal_density(y, predicted, sigma), predicted, sigma


def _run_time_safe_uplift(panel: pd.DataFrame, treatment_col: str, outcome_col: str) -> dict[str, Any]:
    if panel.empty or len(panel) < 8 or panel[treatment_col].nunique(dropna=True) < 3:
        return {
            "status": "insufficient_support",
            "warnings": ["Insufficient rows or treatment variation for time-safe uplift folds."],
            "scores": [],
            "fold_count": 0,
        }
    frame = panel.dropna(subset=[treatment_col, outcome_col, "date"]).sort_values("date").copy()
    threshold = float(frame[treatment_col].quantile(0.75))
    frame["treated"] = (frame[treatment_col] >= threshold).astype(int)
    if frame["treated"].nunique() < 2:
        return {
            "status": "insufficient_treatment_split",
            "warnings": ["High-treatment split has no variation."],
            "scores": [],
            "fold_count": 0,
        }

    features = [column for column in DEFAULT_FEATURES if column in frame.columns and column not in {treatment_col, outcome_col}]
    folds = _build_time_folds(frame)
    fold_rows: list[pd.DataFrame] = []
    for fold_id, (train_index, test_index) in enumerate(folds, start=1):
        train = frame.loc[train_index].copy()
        test = frame.loc[test_index].copy()
        if train.empty or test.empty or train["treated"].nunique() < 2:
            continue
        beta = _fit_linear_uplift(train, features, outcome_col)
        test["predicted_uplift"] = _predict_uplift(test, beta, features)
        test["fold_id"] = fold_id
        fold_rows.append(test[["category_key", "category_name", "predicted_uplift", "fold_id"]])

    if not fold_rows:
        return {
            "status": "insufficient_estimable_folds",
            "warnings": ["Time-safe folds could not estimate uplift with both treatment levels."],
            "scores": [],
            "fold_count": 0,
            "threshold": threshold,
            "features": features,
        }

    scores = pd.concat(fold_rows, ignore_index=True)
    category_scores = (
        scores.groupby(["category_key", "category_name"], as_index=False)
        .agg(
            mean_uplift=("predicted_uplift", "mean"),
            fold_count=("fold_id", "nunique"),
            positive_fold_share=("predicted_uplift", lambda values: float((values > 0).mean())),
        )
    )
    category_scores["stability"] = category_scores["positive_fold_share"].apply(lambda value: max(value, 1 - value))
    category_scores["bucket"] = category_scores.apply(
        lambda row: _assign_bucket(float(row["mean_uplift"]), float(row["stability"])),
        axis=1,
    )
    rows = [
        {
            "category_key": str(row.category_key),
            "category": str(row.category_name),
            "mean_uplift": round(float(row.mean_uplift), 4),
            "fold_count": int(row.fold_count),
            "positive_fold_share": round(float(row.positive_fold_share), 4),
            "stability": round(float(row.stability), 4),
            "bucket": str(row.bucket),
        }
        for row in category_scores.itertuples(index=False)
    ]
    return {
        "status": "ok",
        "threshold": round(threshold, 4),
        "features": features,
        "fold_count": int(scores["fold_id"].nunique()),
        "scores": rows,
        "warnings": [],
    }


def _resource_uplift_scores(panel: pd.DataFrame, working: pd.DataFrame) -> list[dict[str, Any]]:
    size_segments = _category_size_segments(panel)
    rows: list[dict[str, Any]] = []
    for (category_key, category_name), group in panel.groupby(["category_key", "category_name"], sort=False):
        work_group = working[working["category_key"] == category_key]
        exposure_uplift = _dose_uplift(work_group, "exposure_intensity") if not work_group.empty else 0.0
        discount_uplift = _dose_uplift(work_group, "discount_intensity") if not work_group.empty else 0.0
        combined = exposure_uplift + discount_uplift
        activity = group[group["is_activity"]]
        rows.append(
            {
                "category_key": str(category_key),
                "category": str(category_name),
                "category_size_segment": size_segments.get(str(category_key), "Mid"),
                "exposure_uplift": round(float(exposure_uplift), 4),
                "discount_uplift": round(float(discount_uplift), 4),
                "combined_resource_uplift": round(float(combined), 4),
                "local_gap": round(float(work_group["local_gap"].sum()) if not work_group.empty else 0.0, 4),
                "activity_gmv": round(float(activity["gmv"].sum()) if not activity.empty else 0.0, 4),
                "activity_rows": int(len(activity)),
            }
        )
    return _assign_resource_quadrants(rows)


def _category_size_segments(panel: pd.DataFrame) -> dict[str, str]:
    totals = (
        panel.groupby("category_key", as_index=False)
        .agg(total_gmv=("gmv", "sum"))
        .sort_values("total_gmv", ascending=False)
        .reset_index(drop=True)
    )
    count = len(totals)
    if count == 0:
        return {}
    segments: dict[str, str] = {}
    for index, row in totals.iterrows():
        if count < 3:
            segment = "Mid"
        elif index < math.ceil(count / 3):
            segment = "Top"
        elif index < math.ceil(count * 2 / 3):
            segment = "Mid"
        else:
            segment = "LongTail"
        segments[str(row["category_key"])] = segment
    return segments


def _assign_resource_quadrants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    exposure_cut = float(np.median([row["exposure_uplift"] for row in rows]))
    discount_cut = float(np.median([row["discount_uplift"] for row in rows]))
    combined_cut = float(np.median([row["combined_resource_uplift"] for row in rows]))
    baseline_cut = float(np.median([row["activity_gmv"] for row in rows]))
    output = []
    for row in rows:
        high_exposure = row["exposure_uplift"] >= exposure_cut
        high_discount = row["discount_uplift"] >= discount_cut
        high_combined = row["combined_resource_uplift"] >= combined_cut
        high_baseline = row["activity_gmv"] >= baseline_cut
        if high_exposure and high_discount:
            resource_quadrant = "High View / High Discount"
        elif high_exposure:
            resource_quadrant = "High View / Low Discount"
        elif high_discount:
            resource_quadrant = "Low View / High Discount"
        else:
            resource_quadrant = "Low View / Low Discount"

        if high_combined and not high_baseline:
            classic_quadrant = "Persuadables"
        elif high_combined and high_baseline:
            classic_quadrant = "Sure Things"
        elif not high_combined and high_baseline:
            classic_quadrant = "Lost Causes"
        else:
            classic_quadrant = "Do Not Disturb"
        output.append(
            {
                **row,
                "resource_quadrant": resource_quadrant,
                "classic_quadrant": classic_quadrant,
                "quadrant_cutoffs": {
                    "exposure_median": round(exposure_cut, 4),
                    "discount_median": round(discount_cut, 4),
                    "combined_median": round(combined_cut, 4),
                    "activity_gmv_median": round(baseline_cut, 4),
                },
            }
        )
    return sorted(output, key=lambda item: item["combined_resource_uplift"], reverse=True)


def _build_heterogeneity(working: pd.DataFrame) -> dict[str, Any]:
    if working.empty:
        return {
            "exposure_by_category_size": [],
            "discount_by_payday": [],
            "warnings": ["No analysis rows are available for heterogeneity diagnostics."],
        }
    enriched = working.copy()
    size_segments = _category_size_segments(enriched)
    enriched["category_size_segment"] = enriched["category_key"].map(size_segments).fillna("Mid")
    exposure_by_size = []
    for segment, group in enriched.groupby("category_size_segment", sort=False):
        response = _estimate_dose_response(group, "exposure_intensity")
        exposure_by_size.append({"segment": str(segment), **response})

    discount_by_payday = []
    for label, flag in [("Payday", True), ("NonPayday", False)]:
        group = enriched[enriched["is_payday"] == flag]
        response = _estimate_dose_response(group, "discount_intensity")
        discount_by_payday.append({"segment": label, **response})

    warnings = [
        warning
        for item in [*exposure_by_size, *discount_by_payday]
        for warning in item.get("warnings", [])
    ]
    return {
        "exposure_by_category_size": exposure_by_size,
        "discount_by_payday": discount_by_payday,
        "warnings": _dedupe(warnings),
    }


def _build_rank_curves(ranking: list[dict[str, Any]], resource_scores: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "combined": _rank_curve(ranking, "uplift_score", "local_gap"),
        "exposure": _rank_curve(resource_scores, "exposure_uplift", "local_gap"),
        "discount": _rank_curve(resource_scores, "discount_uplift", "local_gap"),
    }


def _rank_curve(rows: list[dict[str, Any]], score_col: str, value_col: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda item: float(item.get(score_col) or 0.0), reverse=True)
    total = sum(float(item.get(value_col) or 0.0) for item in ordered)
    cumulative = 0.0
    curve = []
    for index, item in enumerate(ordered, start=1):
        cumulative += float(item.get(value_col) or 0.0)
        random_baseline = total * index / len(ordered)
        curve.append(
            {
                "selected_count": index,
                "coverage": round(index / len(ordered), 4),
                "cumulative_value": round(cumulative, 4),
                "random_baseline": round(random_baseline, 4),
                "gain_over_random": round(cumulative - random_baseline, 4),
            }
        )
    return curve


def _build_marketing_quadrants(resource_scores: list[dict[str, Any]]) -> dict[str, Any]:
    resource_counts: dict[str, int] = {}
    classic_counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for row in resource_scores:
        resource = row["resource_quadrant"]
        classic = row["classic_quadrant"]
        resource_counts[resource] = resource_counts.get(resource, 0) + 1
        classic_counts[classic] = classic_counts.get(classic, 0) + 1
        examples.setdefault(resource, [])
        if len(examples[resource]) < 4:
            examples[resource].append(row["category"])
    return {
        "resource_quadrants": resource_counts,
        "classic_quadrants": classic_counts,
        "examples": examples,
        "cutoff_rule": "Median split on category-level exposure and discount uplift scores.",
    }


def _build_ranking(
    panel: pd.DataFrame,
    working: pd.DataFrame,
    dose_response: dict[str, dict[str, Any]],
    uplift: dict[str, Any],
) -> list[dict[str, Any]]:
    uplift_by_category = {item["category_key"]: item for item in uplift.get("scores", [])}
    rows: list[dict[str, Any]] = []
    for (category_key, category_name), group in panel.groupby(["category_key", "category_name"], sort=False):
        work_group = working[working["category_key"] == category_key]
        local_gap = float(work_group["local_gap"].sum()) if not work_group.empty else 0.0
        dose_signal = _dose_uplift(work_group, "combined_intensity") if not work_group.empty else 0.0
        uplift_score_record = uplift_by_category.get(str(category_key), {})
        model_uplift = float(uplift_score_record.get("mean_uplift", dose_signal) or 0.0)
        stability = uplift_score_record.get("stability")
        uplift_score = model_uplift + 0.2 * local_gap
        bucket = uplift_score_record.get("bucket") or _assign_bucket(uplift_score, stability)
        rows.append(
            {
                "category_key": str(category_key),
                "category": str(category_name),
                "bucket": bucket,
                "uplift_score": round(float(uplift_score), 4),
                "model_uplift": round(float(model_uplift), 4),
                "dose_uplift": round(float(dose_signal), 4),
                "local_gap": round(float(local_gap), 4),
                "fold_count": int(uplift_score_record.get("fold_count", 0) or 0),
                "positive_fold_share": uplift_score_record.get("positive_fold_share"),
                "stability": stability,
                "evidence": _ranking_evidence(dose_response, uplift.get("status")),
            }
        )
    return sorted(rows, key=lambda item: item["uplift_score"], reverse=True)


def _build_recommendations(ranking: list[dict[str, Any]], dose_response: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    exposure_shape = dose_response.get("exposure", {}).get("diagnostics", {}).get("response_shape", "unknown")
    discount_shape = dose_response.get("discount", {}).get("diagnostics", {}).get("response_shape", "unknown")
    for item in ranking:
        action = _action_for_bucket(item, exposure_shape, discount_shape)
        recommendations.append(
            {
                "category": item["category"],
                "action": action,
                "reason": (
                    f"bucket={item['bucket']}; uplift_score={item['uplift_score']}; "
                    f"model_uplift={item['model_uplift']}; LocalGap={item['local_gap']}; "
                    f"fold_count={item['fold_count']}; stability={item.get('stability')}"
                ),
                "guardrail": _guardrail_for_bucket(item["bucket"]),
                "evidence": item["evidence"],
                "bucket": item["bucket"],
                "uplift_score": item["uplift_score"],
                "local_gap": item["local_gap"],
                "model_uplift": item["model_uplift"],
                "dose_uplift": item["dose_uplift"],
                "fold_count": item["fold_count"],
                "stability": item.get("stability"),
            }
        )
    return recommendations


def _fit_linear_uplift(train: pd.DataFrame, features: list[str], outcome_col: str) -> np.ndarray:
    frame = train.copy()
    for column in features:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(frame[column].median())
    x_base = frame[features].to_numpy(dtype=float) if features else np.empty((len(frame), 0))
    treated = frame["treated"].to_numpy(dtype=float).reshape(-1, 1)
    interaction = x_base * treated if features else np.empty((len(frame), 0))
    design = np.column_stack([np.ones(len(frame)), treated, x_base, interaction])
    target = frame[outcome_col].to_numpy(dtype=float)
    return _safe_lstsq(design, target)


def _predict_uplift(df: pd.DataFrame, beta: np.ndarray, features: list[str]) -> np.ndarray:
    frame = df.copy()
    for column in features:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(frame[column].median())
    x_base = frame[features].to_numpy(dtype=float) if features else np.empty((len(frame), 0))
    ones = np.ones((len(frame), 1))
    treated_one = np.ones((len(frame), 1))
    treated_zero = np.zeros((len(frame), 1))
    design_one = np.column_stack([ones, treated_one, x_base, x_base * treated_one if features else np.empty((len(frame), 0))])
    design_zero = np.column_stack([ones, treated_zero, x_base, x_base * treated_zero if features else np.empty((len(frame), 0))])
    return design_one @ beta - design_zero @ beta


def _build_time_folds(frame: pd.DataFrame) -> list[tuple[pd.Index, pd.Index]]:
    periods = [value for value in sorted(frame["month"].dropna().unique())]
    if len(periods) >= 3:
        folds = []
        for index in range(1, len(periods)):
            train_periods = periods[:index]
            test_period = periods[index]
            train_index = frame.index[frame["month"].isin(train_periods)]
            test_index = frame.index[frame["month"] == test_period]
            if len(train_index) and len(test_index):
                folds.append((train_index, test_index))
        return folds
    ordered = frame.sort_values("date")
    cutoff = max(int(len(ordered) * 0.7), 1)
    if cutoff >= len(ordered):
        return []
    return [(ordered.index[:cutoff], ordered.index[cutoff:])]


def _dose_uplift(group: pd.DataFrame, treatment_col: str) -> float:
    if group.empty or group[treatment_col].nunique(dropna=True) < 2:
        return 0.0
    low_cut = float(group[treatment_col].quantile(0.35))
    high_cut = float(group[treatment_col].quantile(0.65))
    low = group.loc[group[treatment_col] <= low_cut, "local_gap"]
    high = group.loc[group[treatment_col] >= high_cut, "local_gap"]
    if low.empty or high.empty:
        return 0.0
    return float(high.mean() - low.mean())


def _action_for_bucket(item: dict[str, Any], exposure_shape: str, discount_shape: str) -> str:
    if item["bucket"] == "Prioritize" and exposure_shape in {"increasing", "flattening"}:
        return "scale_exposure_selectively"
    if item["bucket"] == "Prioritize":
        return "protect_high_response_category"
    if item["bucket"] == "Selective" and discount_shape != "unstable":
        return "controlled_discount_or_exposure_test"
    if item["bucket"] == "Do Not Disturb":
        return "avoid_extra_subsidy"
    return "observe_and_refresh"


def _guardrail_for_bucket(bucket: str) -> str:
    if bucket == "Prioritize":
        return "Check margin, stock, and channel capacity before scaling."
    if bucket == "Selective":
        return "Use a narrow holdout or event-study before broad rollout."
    if bucket == "Do Not Disturb":
        return "Avoid incremental discount pressure unless new evidence appears."
    return "Keep monitoring; do not present as causal proof."


def _assign_bucket(mean_uplift: float, stability: float | None) -> str:
    if stability is None:
        if mean_uplift > 0:
            return "Selective"
        if mean_uplift < 0:
            return "Do Not Disturb"
        return "Observe"
    if mean_uplift > 0 and stability >= 0.67:
        return "Prioritize"
    if mean_uplift > 0:
        return "Selective"
    if mean_uplift < 0 and stability >= 0.67:
        return "Do Not Disturb"
    return "Observe"


def _ranking_evidence(dose_response: dict[str, dict[str, Any]], uplift_status: str | None) -> str:
    exposure_shape = dose_response.get("exposure", {}).get("diagnostics", {}).get("response_shape", "unknown")
    discount_shape = dose_response.get("discount", {}).get("diagnostics", {}).get("response_shape", "unknown")
    return (
        f"GPS exposure curve={exposure_shape}; discount curve={discount_shape}; "
        f"time_safe_uplift_status={uplift_status or 'unknown'}."
    )


def _support_warnings(panel: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if panel["category_key"].nunique() < 2:
        warnings.append("Only one category is available; uplift ranking cannot compare categories.")
    if int(panel["is_activity"].sum()) < 2:
        warnings.append("Fewer than two activity rows are available; recommendations are directional.")
    if panel["combined_intensity"].nunique(dropna=True) < 3:
        warnings.append("Treatment intensity support is thin.")
    if (panel["baseline_quality"] == "unavailable").mean() > 0.5:
        warnings.append("More than half of rows lack a reliable local baseline.")
    return warnings


def _curve_shape(values: list[float]) -> str:
    if len(values) < 3:
        return "limited"
    diffs = np.diff(values)
    if np.all(diffs >= -1e-6):
        if len(diffs) >= 2 and diffs[-1] < diffs[0]:
            return "flattening"
        return "increasing"
    if np.all(diffs <= 1e-6):
        return "decreasing"
    return "unstable"


def _standardize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    std = float(values.std(ddof=0))
    if not np.isfinite(std) or std <= 1e-9:
        return values * 0.0
    return (values - float(values.mean())) / std


def _normal_density(values: np.ndarray, means: np.ndarray, sigma: float) -> np.ndarray:
    sigma = max(float(sigma), 1e-6)
    z = (values - means) / sigma
    return np.clip((1.0 / (sigma * math.sqrt(2 * math.pi))) * np.exp(-0.5 * np.square(z)), 1e-12, None)


def _safe_lstsq(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        beta = np.zeros(X.shape[1])
    return np.nan_to_num(beta, nan=0.0, posinf=0.0, neginf=0.0)


def _write_recommendations_csv(path: Path, recommendations: list[dict[str, Any]]) -> None:
    fieldnames = [
        "category",
        "action",
        "reason",
        "guardrail",
        "evidence",
        "bucket",
        "uplift_score",
        "local_gap",
        "model_uplift",
        "dose_uplift",
        "fold_count",
        "stability",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in recommendations:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_resource_scores_csv(path: Path, resource_scores: list[dict[str, Any]]) -> None:
    fieldnames = [
        "category",
        "category_size_segment",
        "exposure_uplift",
        "discount_uplift",
        "combined_resource_uplift",
        "local_gap",
        "activity_gmv",
        "resource_quadrant",
        "classic_quadrant",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in resource_scores:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
