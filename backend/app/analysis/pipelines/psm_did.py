from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


TREATMENT_QUANTILE = 0.75
CONTROL_CLEAN_QUANTILE = 0.25
EVENT_WINDOWS = {
    "pre": (-7, -2),
    "post_early": (0, 5),
    "post_late": (6, 10),
    "post_full": (0, 10),
}
PRETREND_WINDOWS = {
    "pre_far": (-14, -8),
    "pre_near": (-7, -2),
}
COVARIATE_COLUMNS = [
    "baseline_avg_gmv",
    "baseline_log_gmv",
    "baseline_gmv_volatility",
    "baseline_avg_view_uv",
    "baseline_log_view_uv",
    "baseline_discount_rate",
    "baseline_buy_uv",
    "baseline_conversion_rate",
    "zero_gmv_share",
]


@dataclass(frozen=True)
class MatchPair:
    treated: str
    control: str
    treated_score: float
    control_score: float
    distance: float


def run_psm_did(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel_path = workspace / "data" / "processed" / "category_day_panel.json"
    if not panel_path.exists():
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before PSM-DID."},
        )

    panel = _load_panel(panel_path)
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_psm_did",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    panel = _prepare_panel(panel)
    features = _category_features(panel)
    event_panel = _add_event_time(panel, shift_days=0)

    exposure_result = _run_resource_design(
        panel=event_panel,
        features=features,
        treatment_name="exposure",
        lift_column="view_lift",
    )
    discount_result = _run_resource_design(
        panel=event_panel,
        features=features,
        treatment_name="discount",
        lift_column="discount_lift",
    )
    primary_name, primary = _choose_primary_result(exposure_result, discount_result)
    estimates = _compat_estimates(primary)
    lift = _compat_lift(primary)
    warnings = _dedupe([*exposure_result["warnings"], *discount_result["warnings"]])
    method_status = _overall_status(exposure_result, discount_result, warnings)

    result = {
        "method": "psm_did",
        "method_status": method_status,
        "primary_treatment": primary_name,
        "treatment_hierarchy": ["exposure", "discount"],
        "treatments": {
            "exposure": exposure_result,
            "discount": discount_result,
        },
        # Backward-compatible fields consumed by result/report code.
        "treated_categories_count": primary["matched_counts"]["treated_categories"],
        "control_categories_count": primary["matched_counts"]["control_categories"],
        "psm_median_threshold": primary["treatment_definition"].get("threshold"),
        "estimates": estimates,
        "lift": lift,
        "interpretation": {
            "did_estimate_interpretation": (
                f"Primary {primary_name} matched DID estimate is {estimates['did_estimate']} GMV units. "
                "Treat this as directional resource-lift evidence, not the final increment amount."
            ),
            "treated_lift_interpretation": f"Matched treated lift is {lift['treated_lift_pct']}%.",
            "control_lift_interpretation": f"Matched control lift is {lift['control_lift_pct']}%.",
            "guardrail": "LocalGap remains the main increment accounting layer.",
        },
        "diagnostics": {
            "category_count": int(panel["category_key"].nunique()),
            "row_count": int(len(panel)),
            "activity_rows": int(panel["is_activity"].sum()),
            "event_windows": EVENT_WINDOWS,
            "pretrend_windows": PRETREND_WINDOWS,
        },
        "warnings": warnings,
        "method_assumptions": [
            "Treatment is resource-lift intensity, not simple activity participation.",
            "Matching uses non-activity/pre-activity covariates only.",
            "DID/event-window outputs are directional support and do not replace LocalGap increment accounting.",
        ],
    }

    output_path = workspace / ".analysis" / "psm_did_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = (
        f"PSM-DID completed: primary={primary_name}, "
        f"matched_pairs={primary['matched_counts']['matched_pairs']}, "
        f"DID={estimates['did_estimate']}, status={method_status}."
    )
    return ToolResult(
        ok=True,
        action="analysis.run_psm_did",
        summary=summary,
        artifacts=[
            {
                "type": "psm_did_result",
                "title": "psm_did_result.json",
                "path": str(output_path.relative_to(workspace)),
                "method_status": method_status,
                "primary_treatment": primary_name,
                "did_estimate": estimates["did_estimate"],
                "matched_pairs": primary["matched_counts"]["matched_pairs"],
                "warnings": warnings,
            }
        ],
        assistant_hint=(
            "Use PSM-DID as directional causal support. Cite matching balance, event windows, "
            "and placebo/pretrend diagnostics before making resource-lift claims."
        ),
    )


def _load_panel(panel_path: Path) -> pd.DataFrame:
    data = json.loads(panel_path.read_text(encoding="utf-8"))
    return pd.DataFrame(data if isinstance(data, list) else [])


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    prepared = panel.copy()
    prepared["date"] = pd.to_datetime(prepared.get("date"), errors="coerce")
    prepared = prepared.dropna(subset=["date"]).copy()
    if "category_key" not in prepared.columns:
        prepared["category_key"] = prepared.get("category", prepared.get("category_name", "unknown"))
    if "category_name" not in prepared.columns:
        prepared["category_name"] = prepared.get("category", prepared["category_key"])
    if "category" not in prepared.columns:
        prepared["category"] = prepared["category_name"]
    prepared["category_key"] = prepared["category_key"].astype(str)
    prepared["category_name"] = prepared["category_name"].astype(str)
    prepared["category"] = prepared["category"].astype(str)

    for column in ["gmv", "view_uv", "exposure", "buy_uv", "discount_rate", "discount_amount", "order_count", "quantity"]:
        if column not in prepared.columns:
            prepared[column] = 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    prepared["view_uv"] = np.where(prepared["view_uv"] > 0, prepared["view_uv"], prepared["exposure"])
    prepared["discount_rate"] = prepared["discount_rate"].clip(lower=0.0)
    prepared["log_gmv"] = np.log1p(prepared["gmv"].clip(lower=0.0))
    prepared["log_view_uv"] = np.log1p(prepared["view_uv"].clip(lower=0.0))
    prepared["conversion_rate"] = np.where(prepared["view_uv"] > 0, prepared["buy_uv"] / prepared["view_uv"], 0.0)
    prepared["weekday"] = prepared["date"].dt.weekday
    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    return prepared


def _category_features(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for category_key, group in panel.groupby("category_key", sort=False):
        activity = group[group["is_activity"]]
        baseline = group[~group["is_activity"]]
        all_rows = group
        activity_view = float(activity["view_uv"].mean()) if not activity.empty else 0.0
        baseline_view = float(baseline["view_uv"].mean()) if not baseline.empty else 0.0
        activity_discount = float(activity["discount_rate"].mean()) if not activity.empty else 0.0
        baseline_discount = float(baseline["discount_rate"].mean()) if not baseline.empty else 0.0
        rows.append(
            {
                "category_key": str(category_key),
                "category": str(group["category_name"].iloc[0]),
                "activity_rows": int(len(activity)),
                "baseline_rows": int(len(baseline)),
                "view_lift": _safe_relative_lift(activity_view, baseline_view),
                "discount_lift": activity_discount - baseline_discount,
                "baseline_avg_gmv": float(baseline["gmv"].mean()) if not baseline.empty else float(all_rows["gmv"].mean()),
                "baseline_log_gmv": float(baseline["log_gmv"].mean()) if not baseline.empty else float(all_rows["log_gmv"].mean()),
                "baseline_gmv_volatility": float(baseline["gmv"].std(ddof=0)) if len(baseline) > 1 else 0.0,
                "baseline_avg_view_uv": baseline_view,
                "baseline_log_view_uv": float(baseline["log_view_uv"].mean()) if not baseline.empty else float(all_rows["log_view_uv"].mean()),
                "baseline_discount_rate": baseline_discount,
                "baseline_buy_uv": float(baseline["buy_uv"].mean()) if not baseline.empty else 0.0,
                "baseline_conversion_rate": float(baseline["conversion_rate"].mean()) if not baseline.empty else 0.0,
                "zero_gmv_share": float((baseline["gmv"] <= 0).mean()) if not baseline.empty else float((all_rows["gmv"] <= 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _safe_relative_lift(activity_value: float, baseline_value: float) -> float:
    if baseline_value > 0:
        return activity_value / baseline_value - 1.0
    return math.log1p(max(activity_value, 0.0)) - math.log1p(max(baseline_value, 0.0))


def _run_resource_design(
    *,
    panel: pd.DataFrame,
    features: pd.DataFrame,
    treatment_name: str,
    lift_column: str,
) -> dict[str, Any]:
    eligible = features[(features["activity_rows"] > 0) & (features["baseline_rows"] > 0)].copy()
    warnings: list[str] = []
    if len(eligible) < 3:
        return _limited_resource_result(treatment_name, lift_column, "Fewer than three eligible categories.")
    if eligible[lift_column].nunique(dropna=True) < 2:
        return _limited_resource_result(treatment_name, lift_column, f"{lift_column} has no treatment variation.")

    threshold = float(eligible[lift_column].quantile(TREATMENT_QUANTILE))
    clean_control_threshold = float(eligible[lift_column].quantile(CONTROL_CLEAN_QUANTILE))
    eligible["treated"] = eligible[lift_column] >= threshold
    if eligible["treated"].sum() == 0 or (~eligible["treated"]).sum() == 0:
        treated_count = max(1, int(math.ceil(len(eligible) * 0.25)))
        ranked = eligible.sort_values(lift_column, ascending=False).copy()
        eligible["treated"] = eligible["category_key"].isin(ranked.head(treated_count)["category_key"])
        threshold = float(ranked.iloc[treated_count - 1][lift_column])

    propensity = _estimate_propensity_scores(eligible, "treated", COVARIATE_COLUMNS)
    eligible["propensity_score"] = propensity
    treated_keys = eligible.loc[eligible["treated"], "category_key"].tolist()
    control_keys = eligible.loc[~eligible["treated"], "category_key"].tolist()
    clean_control_keys = eligible.loc[eligible[lift_column] <= clean_control_threshold, "category_key"].tolist()
    if not clean_control_keys:
        clean_control_keys = control_keys

    pairs = _nearest_neighbor_pairs(eligible, treated_keys, control_keys)
    matched_treated = [pair.treated for pair in pairs]
    matched_control = [pair.control for pair in pairs]
    before_balance = _balance_table(eligible, treated_keys, control_keys, COVARIATE_COLUMNS)
    after_balance = _balance_table(eligible, matched_treated, matched_control, COVARIATE_COLUMNS)
    raw_event = _event_window_summary(panel, treated_keys, clean_control_keys)
    matched_event = _event_window_summary(panel, matched_treated, matched_control)
    pretrend = _pretrend_diagnostic(panel, matched_treated, matched_control)
    placebo = _placebo_diagnostic(panel, matched_treated, matched_control)

    if len(pairs) < 2:
        warnings.append("Fewer than two matched pairs; DID evidence is limited.")
    if after_balance["max_abs_smd"] is not None and after_balance["max_abs_smd"] > 0.5:
        warnings.append("Post-matching balance remains weak; interpret DID directionally.")
    if not matched_event["windows"]:
        warnings.append("No supported matched event windows were available.")
    if placebo.get("abs_placebo_did") is not None and matched_event.get("primary_did") is not None:
        if abs(float(placebo["abs_placebo_did"])) > max(abs(float(matched_event["primary_did"])) * 0.75, 1.0):
            warnings.append("Placebo DID is large relative to the primary DID; causal language should be cautious.")

    status = "implemented" if len(pairs) >= 2 and not warnings else "limited"
    return {
        "status": status,
        "treatment": treatment_name,
        "treatment_definition": {
            "lift_column": lift_column,
            "quantile": TREATMENT_QUANTILE,
            "threshold": round(threshold, 6),
            "clean_control_quantile": CONTROL_CLEAN_QUANTILE,
            "clean_control_threshold": round(clean_control_threshold, 6),
            "description": f"Top {int((1 - TREATMENT_QUANTILE) * 100)}% by {lift_column} vs matched lower-lift controls.",
        },
        "matched_counts": {
            "eligible_categories": int(len(eligible)),
            "treated_categories": int(len(set(matched_treated))),
            "control_categories": int(len(set(matched_control))),
            "raw_treated_categories": int(len(treated_keys)),
            "raw_control_categories": int(len(control_keys)),
            "matched_pairs": int(len(pairs)),
        },
        "propensity_score_summary": _propensity_summary(eligible),
        "matched_pairs": [
            {
                "treated": pair.treated,
                "control": pair.control,
                "treated_score": round(pair.treated_score, 6),
                "control_score": round(pair.control_score, 6),
                "distance": round(pair.distance, 6),
            }
            for pair in pairs
        ],
        "balance": {
            "before_matching": before_balance,
            "after_matching": after_balance,
        },
        "event_study": {
            "raw": raw_event,
            "matched": matched_event,
        },
        "pretrend": pretrend,
        "placebo": placebo,
        "warnings": warnings,
    }


def _limited_resource_result(treatment_name: str, lift_column: str, warning: str) -> dict[str, Any]:
    return {
        "status": "limited",
        "treatment": treatment_name,
        "treatment_definition": {
            "lift_column": lift_column,
            "quantile": TREATMENT_QUANTILE,
            "threshold": None,
            "clean_control_quantile": CONTROL_CLEAN_QUANTILE,
            "clean_control_threshold": None,
        },
        "matched_counts": {
            "eligible_categories": 0,
            "treated_categories": 0,
            "control_categories": 0,
            "raw_treated_categories": 0,
            "raw_control_categories": 0,
            "matched_pairs": 0,
        },
        "propensity_score_summary": {},
        "matched_pairs": [],
        "balance": {"before_matching": _empty_balance(), "after_matching": _empty_balance()},
        "event_study": {"raw": _empty_event_summary(), "matched": _empty_event_summary()},
        "pretrend": {"status": "limited", "warnings": [warning]},
        "placebo": {"status": "limited", "warnings": [warning]},
        "warnings": [warning],
    }


def _estimate_propensity_scores(frame: pd.DataFrame, treatment_col: str, covariates: list[str]) -> np.ndarray:
    X = _standardized_matrix(frame, covariates)
    treated = frame[treatment_col].astype(bool).to_numpy()
    if treated.sum() == 0 or (~treated).sum() == 0 or X.size == 0:
        return np.full(len(frame), 0.5)
    diff = np.nan_to_num(X[treated].mean(axis=0) - X[~treated].mean(axis=0), nan=0.0)
    raw = X @ diff
    raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    return 1.0 / (1.0 + np.exp(-np.clip(raw, -30, 30)))


def _standardized_matrix(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    data = frame[columns].copy()
    for column in columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        median = data[column].median()
        data[column] = data[column].fillna(0.0 if pd.isna(median) else median)
        std = float(data[column].std(ddof=0))
        if not np.isfinite(std) or std <= 1e-9:
            data[column] = 0.0
        else:
            data[column] = (data[column] - float(data[column].mean())) / std
    return data.to_numpy(dtype=float)


def _nearest_neighbor_pairs(frame: pd.DataFrame, treated_keys: list[str], control_keys: list[str]) -> list[MatchPair]:
    if not treated_keys or not control_keys:
        return []
    scores = {str(row.category_key): float(row.propensity_score) for row in frame.itertuples(index=False)}
    available_controls = set(control_keys)
    pairs: list[MatchPair] = []
    for treated in sorted(treated_keys, key=lambda key: scores.get(key, 0.5)):
        if not available_controls:
            break
        control = min(available_controls, key=lambda key: abs(scores.get(treated, 0.5) - scores.get(key, 0.5)))
        available_controls.remove(control)
        distance = abs(scores.get(treated, 0.5) - scores.get(control, 0.5))
        pairs.append(
            MatchPair(
                treated=str(treated),
                control=str(control),
                treated_score=scores.get(treated, 0.5),
                control_score=scores.get(control, 0.5),
                distance=distance,
            )
        )
    return pairs


def _balance_table(frame: pd.DataFrame, treated_keys: list[str], control_keys: list[str], covariates: list[str]) -> dict[str, Any]:
    if not treated_keys or not control_keys:
        return _empty_balance()
    treated = frame[frame["category_key"].isin(treated_keys)]
    control = frame[frame["category_key"].isin(control_keys)]
    rows = []
    for column in covariates:
        smd = _smd(treated[column], control[column])
        rows.append(
            {
                "covariate": column,
                "treated_mean": round(float(pd.to_numeric(treated[column], errors="coerce").mean()), 6),
                "control_mean": round(float(pd.to_numeric(control[column], errors="coerce").mean()), 6),
                "smd": None if smd is None else round(float(smd), 6),
                "abs_smd": None if smd is None else round(abs(float(smd)), 6),
            }
        )
    abs_values = [row["abs_smd"] for row in rows if row["abs_smd"] is not None]
    return {
        "covariates": rows,
        "mean_abs_smd": round(float(np.mean(abs_values)), 6) if abs_values else None,
        "max_abs_smd": round(float(np.max(abs_values)), 6) if abs_values else None,
        "count_abs_smd_lt_0_1": int(sum(value < 0.1 for value in abs_values)),
        "count_abs_smd_lt_0_2": int(sum(value < 0.2 for value in abs_values)),
    }


def _smd(left: pd.Series, right: pd.Series) -> float | None:
    left_values = pd.to_numeric(left, errors="coerce").dropna()
    right_values = pd.to_numeric(right, errors="coerce").dropna()
    if left_values.empty or right_values.empty:
        return None
    pooled = math.sqrt((float(left_values.var(ddof=0)) + float(right_values.var(ddof=0))) / 2.0)
    diff = float(left_values.mean()) - float(right_values.mean())
    if pooled <= 1e-9:
        return 0.0 if abs(diff) <= 1e-9 else math.copysign(999.0, diff)
    return diff / pooled


def _add_event_time(panel: pd.DataFrame, shift_days: int) -> pd.DataFrame:
    output = panel.copy()
    windows = _activity_windows(output["date"][output["is_activity"]])
    shifted = [(start + pd.Timedelta(days=shift_days), end + pd.Timedelta(days=shift_days)) for start, end in windows]
    output["event_time"] = output["date"].apply(lambda date: _relative_event_day(date, shifted))
    return output


def _activity_windows(activity_dates: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    dates = sorted(pd.to_datetime(activity_dates.dropna().unique()))
    if not dates:
        return []
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = dates[0]
    previous = dates[0]
    for current in dates[1:]:
        if (current - previous).days > 1:
            windows.append((start, previous))
            start = current
        previous = current
    windows.append((start, previous))
    return windows


def _relative_event_day(date: pd.Timestamp, windows: list[tuple[pd.Timestamp, pd.Timestamp]]) -> float:
    candidates: list[tuple[int, int]] = []
    for start, end in windows:
        if start - pd.Timedelta(days=21) <= date <= end + pd.Timedelta(days=21):
            event_day = int((date - start).days)
            candidates.append((abs(event_day), event_day))
    if not candidates:
        return np.nan
    return float(min(candidates, key=lambda item: item[0])[1])


def _event_window_summary(panel: pd.DataFrame, treated_keys: list[str], control_keys: list[str]) -> dict[str, Any]:
    if not treated_keys or not control_keys or "event_time" not in panel.columns:
        return _empty_event_summary()
    comparisons = []
    pre = _window_means(panel, treated_keys, control_keys, *EVENT_WINDOWS["pre"])
    for name, (start, end) in EVENT_WINDOWS.items():
        current = _window_means(panel, treated_keys, control_keys, start, end)
        if current["treated_rows"] == 0 or current["control_rows"] == 0:
            continue
        did = None
        if name != "pre" and pre["treated_rows"] > 0 and pre["control_rows"] > 0:
            did = (current["treated_avg_gmv"] - pre["treated_avg_gmv"]) - (
                current["control_avg_gmv"] - pre["control_avg_gmv"]
            )
        comparisons.append(
            {
                "window": name,
                "event_day_start": start,
                "event_day_end": end,
                **current,
                "did_vs_pre": None if did is None else round(float(did), 6),
                "relative_diff_pct": _relative_diff_pct(current["treated_avg_gmv"], current["control_avg_gmv"]),
            }
        )
    primary = next((row["did_vs_pre"] for row in comparisons if row["window"] == "post_early"), None)
    if primary is None:
        primary = next((row["did_vs_pre"] for row in comparisons if row["window"] == "post_full"), None)
    return {
        "status": "ok" if comparisons else "limited",
        "windows": comparisons,
        "primary_did": primary,
        "baseline_window": "pre",
    }


def _window_means(panel: pd.DataFrame, treated_keys: list[str], control_keys: list[str], start: int, end: int) -> dict[str, Any]:
    window = panel[(panel["event_time"] >= start) & (panel["event_time"] <= end)]
    treated = window[window["category_key"].isin(treated_keys)]
    control = window[window["category_key"].isin(control_keys)]
    return {
        "treated_rows": int(len(treated)),
        "control_rows": int(len(control)),
        "treated_avg_gmv": round(float(treated["gmv"].mean()), 6) if not treated.empty else 0.0,
        "control_avg_gmv": round(float(control["gmv"].mean()), 6) if not control.empty else 0.0,
        "treated_avg_log_gmv": round(float(treated["log_gmv"].mean()), 6) if not treated.empty else 0.0,
        "control_avg_log_gmv": round(float(control["log_gmv"].mean()), 6) if not control.empty else 0.0,
    }


def _pretrend_diagnostic(panel: pd.DataFrame, treated_keys: list[str], control_keys: list[str]) -> dict[str, Any]:
    if not treated_keys or not control_keys:
        return {"status": "limited", "warnings": ["No matched categories for pretrend diagnostics."]}
    far = _window_means(panel, treated_keys, control_keys, *PRETREND_WINDOWS["pre_far"])
    near = _window_means(panel, treated_keys, control_keys, *PRETREND_WINDOWS["pre_near"])
    if min(far["treated_rows"], far["control_rows"], near["treated_rows"], near["control_rows"]) == 0:
        return {
            "status": "limited",
            "warnings": ["Insufficient pre-period rows for pretrend comparison."],
            "pre_far": far,
            "pre_near": near,
        }
    pretrend_did = (near["treated_avg_gmv"] - far["treated_avg_gmv"]) - (
        near["control_avg_gmv"] - far["control_avg_gmv"]
    )
    scale = max(abs(far["treated_avg_gmv"]), abs(far["control_avg_gmv"]), 1.0)
    return {
        "status": "ok",
        "pretrend_did": round(float(pretrend_did), 6),
        "relative_to_baseline": round(float(pretrend_did / scale), 6),
        "passes_rule_of_thumb": bool(abs(pretrend_did / scale) < 0.25),
        "pre_far": far,
        "pre_near": near,
        "warnings": [] if abs(pretrend_did / scale) < 0.25 else ["Pre-period movement differs materially across groups."],
    }


def _placebo_diagnostic(panel: pd.DataFrame, treated_keys: list[str], control_keys: list[str]) -> dict[str, Any]:
    placebo_panel = _add_event_time(panel.drop(columns=["event_time"], errors="ignore"), shift_days=-7)
    summary = _event_window_summary(placebo_panel, treated_keys, control_keys)
    did = summary.get("primary_did")
    return {
        "status": summary["status"],
        "shift_days": -7,
        "placebo_did": did,
        "abs_placebo_did": None if did is None else abs(float(did)),
        "windows": summary["windows"],
        "warnings": [] if did is not None else ["Insufficient support for placebo timing check."],
    }


def _relative_diff_pct(treated: float, control: float) -> float | None:
    if control == 0:
        return None
    return round(float((treated - control) / control * 100.0), 6)


def _propensity_summary(frame: pd.DataFrame) -> dict[str, Any]:
    scores = pd.to_numeric(frame["propensity_score"], errors="coerce").dropna()
    if scores.empty:
        return {}
    return {
        "min": round(float(scores.min()), 6),
        "p25": round(float(scores.quantile(0.25)), 6),
        "median": round(float(scores.median()), 6),
        "p75": round(float(scores.quantile(0.75)), 6),
        "max": round(float(scores.max()), 6),
    }


def _choose_primary_result(exposure: dict[str, Any], discount: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    exposure_pairs = int(exposure.get("matched_counts", {}).get("matched_pairs") or 0)
    discount_pairs = int(discount.get("matched_counts", {}).get("matched_pairs") or 0)
    if exposure_pairs >= discount_pairs:
        return "exposure", exposure
    return "discount", discount


def _compat_estimates(resource_result: dict[str, Any]) -> dict[str, float]:
    matched = resource_result.get("event_study", {}).get("matched", {})
    windows = {row["window"]: row for row in matched.get("windows", [])}
    pre = windows.get("pre", {})
    post = windows.get("post_early") or windows.get("post_full") or {}
    did = matched.get("primary_did")
    return {
        "did_estimate": round(float(did), 2) if did is not None else 0.0,
        "treated_pre_avg": round(float(pre.get("treated_avg_gmv", 0.0)), 2),
        "treated_post_avg": round(float(post.get("treated_avg_gmv", 0.0)), 2),
        "control_pre_avg": round(float(pre.get("control_avg_gmv", 0.0)), 2),
        "control_post_avg": round(float(post.get("control_avg_gmv", 0.0)), 2),
    }


def _compat_lift(resource_result: dict[str, Any]) -> dict[str, float]:
    estimates = _compat_estimates(resource_result)
    treated_lift = _pct_change(estimates["treated_post_avg"], estimates["treated_pre_avg"])
    control_lift = _pct_change(estimates["control_post_avg"], estimates["control_pre_avg"])
    return {
        "treated_lift_pct": round(treated_lift, 2),
        "control_lift_pct": round(control_lift, 2),
        "incremental_lift_pct": round(treated_lift - control_lift, 2),
    }


def _pct_change(after: float, before: float) -> float:
    if before == 0:
        return 0.0
    return (after - before) / before * 100.0


def _overall_status(exposure: dict[str, Any], discount: dict[str, Any], warnings: list[str]) -> str:
    if exposure.get("status") == "implemented" or discount.get("status") == "implemented":
        return "limited" if warnings else "implemented"
    return "limited"


def _empty_balance() -> dict[str, Any]:
    return {
        "covariates": [],
        "mean_abs_smd": None,
        "max_abs_smd": None,
        "count_abs_smd_lt_0_1": 0,
        "count_abs_smd_lt_0_2": 0,
    }


def _empty_event_summary() -> dict[str, Any]:
    return {"status": "limited", "windows": [], "primary_did": None, "baseline_window": "pre"}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
