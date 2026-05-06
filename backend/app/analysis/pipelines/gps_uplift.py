from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


def run_gps_uplift(project_id: str, workspace_path: str, payload: dict | None = None) -> ToolResult:
    workspace = Path(workspace_path)
    panel_path = workspace / "data" / "processed" / "category_day_panel.json"
    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before GPS/uplift analysis."},
        )

    panel = _load_panel(panel_path)
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_gps_uplift",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    config = payload or {}
    panel = _prepare_panel(panel, config)
    localgap_by_category = _load_localgap_by_category(workspace)
    warnings = _support_warnings(panel)

    dose_response = {
        "exposure": _estimate_dose_response(panel, "exposure_intensity"),
        "discount": _estimate_dose_response(panel, "discount_intensity"),
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
    ranking = _build_uplift_ranking(panel, dose_response, localgap_by_category)
    recommendations = _build_recommendations(ranking, dose_response)

    method_status = "limited" if warnings or any(item.get("status") == "limited" for item in dose_response.values()) else "implemented"
    result = {
        "method": "gps_uplift",
        "method_status": method_status,
        "status": "completed",
        "outcome": "local_gap",
        "dose_response": dose_response,
        "uplift_ranking": ranking,
        "segments": [
            {
                "segment": item["bucket"],
                "category": item["category"],
                "recommendation": item["action"],
                "uplift_score": item["uplift_score"],
                "evidence": item["evidence"],
            }
            for item in recommendations
        ],
        "recommended_actions": recommendations,
        "diagnostics": {
            "row_count": int(len(panel)),
            "category_count": int(panel["category_key"].nunique()),
            "activity_rows": int(panel["is_activity"].sum()),
            "treatments": ["exposure", "discount"],
            "baseline_quality": {str(key): int(value) for key, value in panel["baseline_quality"].value_counts().items()},
        },
        "method_assumptions": [
            "Dose-response uses a deterministic generalized-propensity approximation on category-day panel data.",
            "Uplift ranking uses LocalGap as the primary increment accounting layer and treats GPS curves as directional support.",
            "Recommendations require business guardrails such as margin, stock, and channel capacity before rollout.",
        ],
        "warnings": warnings,
        "evidence_artifacts": [
            "data/processed/category_day_panel.json",
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
    gps_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    uplift_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_recommendations_csv(rec_path, recommendations)

    summary = (
        f"GPS/uplift analysis completed: {len(ranking)} categories, "
        f"{len(recommendations)} recommendations, status={method_status}."
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
                "method_status": method_status,
                "status": "completed",
            },
            {
                "type": "model_output",
                "title": "uplift_result.json",
                "path": str(uplift_path.relative_to(workspace)),
                "method_status": method_status,
                "status": "completed",
                "segment_count": len(result["segments"]),
            },
            {
                "type": "table",
                "title": "category_action_recommendations.csv",
                "path": str(rec_path.relative_to(workspace)),
                "rows": len(recommendations),
            },
        ],
        assistant_hint=(
            "GPS/uplift is implemented as directional ranking evidence. Use recommended_actions for report planning, "
            "but keep LocalGap as the main increment accounting layer."
        ),
    )


def _load_panel(panel_path: Path) -> pd.DataFrame:
    data = json.loads(panel_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return pd.DataFrame()
    return pd.DataFrame(data)


def _prepare_panel(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    prepared = panel.copy()
    if "category_key" not in prepared.columns:
        prepared["category_key"] = prepared.get("category", prepared.get("category_name", "unknown")).astype(str)
    if "category_name" not in prepared.columns:
        prepared["category_name"] = prepared.get("category", prepared["category_key"]).astype(str)
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared = prepared.dropna(subset=["date", "category_key"]).copy()

    for column in ["gmv", "view_uv", "exposure", "discount_rate", "discount_amount", "is_payday"]:
        if column not in prepared.columns:
            prepared[column] = 0
    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    prepared["is_payday"] = prepared["is_payday"].astype(bool)
    for column in ["gmv", "view_uv", "exposure", "discount_rate", "discount_amount"]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    prepared["view_uv"] = np.where(prepared["view_uv"] > 0, prepared["view_uv"], prepared["exposure"])
    prepared["weekday"] = prepared["date"].dt.weekday
    prepared["exposure_intensity"] = np.log1p(prepared["view_uv"].clip(lower=0))
    prepared["discount_intensity"] = prepared["discount_rate"].clip(lower=0)
    return _add_local_baseline(prepared, int(config.get("baseline_window_days", 56)))


def _add_local_baseline(panel: pd.DataFrame, baseline_window_days: int) -> pd.DataFrame:
    output = panel.sort_values(["category_key", "date"]).copy()
    output["local_baseline"] = 0.0
    output["baseline_obs"] = 0
    output["baseline_quality"] = "unavailable"

    for _, group in output.groupby("category_key"):
        ordered = group.sort_values("date")
        category_non_activity = ordered.loc[~ordered["is_activity"], "gmv"]
        category_fallback = float(category_non_activity.mean()) if not category_non_activity.empty else 0.0
        for idx, row in ordered.iterrows():
            history = ordered[
                (ordered["date"] < row["date"])
                & (~ordered["is_activity"])
                & (ordered["weekday"] == row["weekday"])
                & (ordered["date"] >= row["date"] - pd.Timedelta(days=baseline_window_days))
            ]
            if len(history) < 2:
                history = ordered[(ordered["date"] < row["date"]) & (~ordered["is_activity"])]
            baseline = float(history["gmv"].mean()) if len(history) >= 2 else category_fallback
            obs = int(len(history))
            quality = "strong" if obs >= 4 else "weak" if obs >= 2 else "fallback" if category_fallback else "unavailable"
            output.loc[idx, "local_baseline"] = baseline
            output.loc[idx, "baseline_obs"] = obs
            output.loc[idx, "baseline_quality"] = quality

    output["local_gap"] = output["gmv"] - output["local_baseline"]
    return output


def _estimate_dose_response(panel: pd.DataFrame, treatment_col: str) -> dict[str, Any]:
    frame = panel.copy()
    support = int(frame[treatment_col].nunique())
    if len(frame) < 4 or support < 2:
        return {
            "status": "limited",
            "treatment": treatment_col,
            "curve": [],
            "diagnostics": {"support": support, "row_count": int(len(frame))},
            "warnings": [f"{treatment_col} has insufficient support for a dose-response curve."],
        }

    treatment = frame[treatment_col].astype(float).to_numpy()
    outcome = frame["local_gap"].astype(float).to_numpy()
    gps = _estimate_gps(frame, treatment_col)
    X = np.column_stack([np.ones(len(frame)), treatment, treatment**2, gps, treatment * gps, frame["is_activity"].astype(float)])
    beta = _safe_lstsq(X, outcome)

    quantiles = np.linspace(0.05, 0.95, min(7, max(3, support)))
    doses = np.unique(np.quantile(treatment, quantiles))
    curve: list[dict[str, Any]] = []
    for dose in doses:
        gps_at_dose = float(np.median(gps))
        predicted = float(np.array([1.0, dose, dose**2, gps_at_dose, dose * gps_at_dose, 1.0]) @ beta)
        nearest = frame.iloc[np.argsort(np.abs(treatment - dose))[: max(1, min(5, len(frame)))]]
        curve.append(
            {
                "dose": round(float(dose), 4),
                "predicted_local_gap": round(predicted, 4),
                "observed_mean_local_gap": round(float(nearest["local_gap"].mean()), 4),
                "row_count": int(len(nearest)),
            }
        )

    shape = _curve_shape([row["predicted_local_gap"] for row in curve])
    warnings = []
    if support < 4:
        warnings.append(f"{treatment_col} support is thin; interpret the curve directionally.")
    if shape == "unstable":
        warnings.append(f"{treatment_col} response curve is unstable across supported doses.")

    return {
        "status": "limited" if warnings else "implemented",
        "treatment": treatment_col,
        "curve": curve,
        "diagnostics": {
            "support": support,
            "row_count": int(len(frame)),
            "gps_mean": round(float(np.mean(gps)), 6),
            "response_shape": shape,
        },
        "warnings": warnings,
    }


def _estimate_gps(frame: pd.DataFrame, treatment_col: str) -> np.ndarray:
    y = frame[treatment_col].astype(float).to_numpy()
    covariates = pd.DataFrame(
        {
            "intercept": 1.0,
            "weekday": frame["weekday"].astype(float),
            "is_payday": frame["is_payday"].astype(float),
            "baseline": frame["local_baseline"].astype(float),
            "category_avg_gmv": frame.groupby("category_key")["gmv"].transform("mean").astype(float),
        }
    ).to_numpy()
    beta = _safe_lstsq(covariates, y)
    predicted = covariates @ beta
    residual = y - predicted
    sigma = max(float(np.std(residual)), 1e-6)
    density = np.exp(-0.5 * ((residual / sigma) ** 2)) / (sigma * math.sqrt(2 * math.pi))
    return np.clip(density, 1e-9, None)


def _build_uplift_ranking(
    panel: pd.DataFrame,
    dose_response: dict[str, dict[str, Any]],
    localgap_by_category: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (category_key, category_name), group in panel.groupby(["category_key", "category_name"]):
        exposure_uplift = _dose_uplift(group, "exposure_intensity")
        discount_uplift = _dose_uplift(group, "discount_intensity")
        local_gap_total = float(localgap_by_category.get(str(category_key), group.loc[group["is_activity"], "local_gap"].sum()))
        baseline_gmv = float(group["local_baseline"].mean())
        uplift_score = exposure_uplift + 0.6 * discount_uplift + 0.2 * local_gap_total
        bucket = _classify_bucket(uplift_score, local_gap_total, baseline_gmv)
        rows.append(
            {
                "category_key": str(category_key),
                "category": str(category_name),
                "bucket": bucket,
                "uplift_score": round(float(uplift_score), 4),
                "exposure_uplift": round(float(exposure_uplift), 4),
                "discount_uplift": round(float(discount_uplift), 4),
                "local_gap": round(float(local_gap_total), 4),
                "baseline_gmv": round(float(baseline_gmv), 4),
                "evidence": _ranking_evidence(dose_response),
            }
        )
    return sorted(rows, key=lambda item: item["uplift_score"], reverse=True)


def _dose_uplift(group: pd.DataFrame, treatment_col: str) -> float:
    if group[treatment_col].nunique() < 2:
        return 0.0
    low_cut = float(group[treatment_col].quantile(0.35))
    high_cut = float(group[treatment_col].quantile(0.65))
    low = group.loc[group[treatment_col] <= low_cut, "local_gap"]
    high = group.loc[group[treatment_col] >= high_cut, "local_gap"]
    if low.empty or high.empty:
        return 0.0
    return float(high.mean() - low.mean())


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
                    f"LocalGap={item['local_gap']}; exposure_uplift={item['exposure_uplift']}; "
                    f"discount_uplift={item['discount_uplift']}"
                ),
                "guardrail": _guardrail_for_bucket(item["bucket"]),
                "evidence": item["evidence"],
                "bucket": item["bucket"],
                "uplift_score": item["uplift_score"],
                "local_gap": item["local_gap"],
                "exposure_uplift": item["exposure_uplift"],
                "discount_uplift": item["discount_uplift"],
            }
        )
    return recommendations


def _action_for_bucket(item: dict[str, Any], exposure_shape: str, discount_shape: str) -> str:
    if item["bucket"] == "Prioritize" and exposure_shape in {"increasing", "flattening"}:
        return "scale_exposure_selectively"
    if item["bucket"] == "Prioritize":
        return "protect_high_response_category"
    if item["bucket"] == "Selective" and item["discount_uplift"] > item["exposure_uplift"] and discount_shape != "unstable":
        return "target_discount_test"
    if item["bucket"] == "Selective":
        return "controlled_exposure_test"
    if item["bucket"] == "Do Not Disturb":
        return "avoid_extra_subsidy"
    return "observe_and_refresh"


def _guardrail_for_bucket(bucket: str) -> str:
    if bucket == "Prioritize":
        return "Check margin, stock, and channel capacity before scaling."
    if bucket == "Selective":
        return "Run a narrow holdout or event-study before broad rollout."
    if bucket == "Do Not Disturb":
        return "Avoid incremental discount pressure unless new evidence appears."
    return "Keep monitoring; do not present as causal proof."


def _classify_bucket(uplift_score: float, local_gap: float, baseline_gmv: float) -> str:
    if uplift_score > 0 and local_gap > 0:
        return "Prioritize"
    if uplift_score > 0:
        return "Selective"
    if uplift_score < 0 and baseline_gmv > 0:
        return "Do Not Disturb"
    return "Observe"


def _ranking_evidence(dose_response: dict[str, dict[str, Any]]) -> str:
    exposure_shape = dose_response.get("exposure", {}).get("diagnostics", {}).get("response_shape", "unknown")
    discount_shape = dose_response.get("discount", {}).get("diagnostics", {}).get("response_shape", "unknown")
    return f"GPS exposure curve={exposure_shape}; discount curve={discount_shape}; ranked by category local_gap response."


def _load_localgap_by_category(workspace: Path) -> dict[str, float]:
    path = workspace / ".analysis" / "localgap_result.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    values: dict[str, float] = {}
    for item in payload.get("categories", []):
        category = item.get("category")
        if category is not None:
            values[str(category)] = float(item.get("local_gap") or 0)
    return values


def _support_warnings(panel: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if panel["category_key"].nunique() < 2:
        warnings.append("Only one category is available; uplift ranking cannot compare categories.")
    if int(panel["is_activity"].sum()) < 2:
        warnings.append("Fewer than two activity rows are available; recommendations are directional.")
    if panel["exposure_intensity"].nunique() < 3 and panel["discount_intensity"].nunique() < 3:
        warnings.append("Treatment dose support is thin for both exposure and discount.")
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


def _safe_lstsq(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        beta = np.zeros(X.shape[1])
    return np.nan_to_num(beta, nan=0.0, posinf=0.0, neginf=0.0)


def _write_recommendations_csv(path: Path, recommendations: list[dict[str, Any]]) -> None:
    fieldnames = ["category", "action", "reason", "guardrail", "evidence", "bucket"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in recommendations:
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
