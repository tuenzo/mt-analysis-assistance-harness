from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


RESOURCE_TERMS = ["discount_rate_pp", "log_view_uv", "resource_interaction", "dist2pay", "dist2pay_sq"]


def run_mechanism_regression(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel = _load_best_panel(workspace)
    if panel is None:
        return ToolResult(
            ok=False,
            action="analysis.run_mechanism_regression",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before mechanism regression."},
        )
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_mechanism_regression",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    prepared = _prepare_panel(panel)
    warnings = _panel_warnings(prepared)
    models = [
        _fit_model(prepared, "gmv", RESOURCE_TERMS, "gmv_level", "GMV level"),
        _fit_model(prepared, "log_order_count", RESOURCE_TERMS, "order_log", "Log order count"),
        _fit_model(prepared[prepared["aov"].notna()].copy(), "log_aov", RESOURCE_TERMS, "aov_log", "Log AOV"),
    ]
    if prepared["local_gap"].notna().any():
        models.append(_fit_model(prepared[prepared["local_gap"].notna()].copy(), "local_gap", RESOURCE_TERMS, "local_gap_level", "LocalGap level"))

    warnings = _dedupe([*warnings, *[warning for model in models for warning in model.get("warnings", [])]])
    implemented_models = [model for model in models if model["status"] == "ok"]
    result = {
        "method": "twfe_mechanism_regression",
        "method_status": "implemented" if len(implemented_models) >= 2 and not warnings else "limited",
        "status": "completed",
        "project_id": project_id,
        "sample": _sample_summary(prepared),
        "model_spec": {
            "fixed_effects": ["category", "date"],
            "terms": RESOURCE_TERMS,
            "standard_errors": "homoskedastic_normal_approximation",
            "implementation": "numpy_lstsq_after_two_way_demeaning",
        },
        "models": models,
        "resource_decomposition": _resource_decomposition(models),
        "warnings": warnings,
        "interpretation_rules": [
            "Mechanism regression is directional and observational; it should not replace LocalGap increment accounting.",
            "Discount and exposure coefficients are interpreted after category and date fixed-effect demeaning.",
            "Use the GMV, order, and AOV models together to explain whether uplift came from traffic, conversion volume, or basket value.",
        ],
        "evidence_artifacts": _source_artifacts(workspace),
    }

    analysis_dir = workspace / ".analysis"
    table_dir = workspace / "artifacts" / "tables"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    result_path = analysis_dir / "mechanism_regression_result.json"
    table_path = table_dir / "mechanism_regression_summary.csv"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_model_table(table_path, models)

    return ToolResult(
        ok=True,
        action="analysis.run_mechanism_regression",
        summary=f"Mechanism regression completed: {len(implemented_models)}/{len(models)} model(s) estimable, status={result['method_status']}.",
        artifacts=[
            {
                "type": "model_output",
                "title": "mechanism_regression_result.json",
                "path": str(result_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "model_count": len(models),
                "estimable_model_count": len(implemented_models),
                "warnings": warnings,
            },
            {
                "type": "table",
                "title": "mechanism_regression_summary.csv",
                "path": str(table_path.relative_to(workspace)),
                "rows": sum(len(model.get("coefficients", [])) for model in models),
            },
        ],
        assistant_hint="Use mechanism regression to explain the channel of effect. Keep LocalGap as the main increment estimate.",
    )


def run_conversion_diagnostics(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel = _load_best_panel(workspace)
    if panel is None:
        return ToolResult(
            ok=False,
            action="analysis.run_conversion_diagnostics",
            summary="",
            error={"code": "PANEL_NOT_FOUND", "message": "Run panel.build_category_day before conversion diagnostics."},
        )
    if panel.empty:
        return ToolResult(
            ok=False,
            action="analysis.run_conversion_diagnostics",
            summary="",
            error={"code": "EMPTY_PANEL", "message": "Category-day panel is empty."},
        )

    prepared = _prepare_panel(panel)
    warnings = _panel_warnings(prepared)
    conversion_sample = prepared[prepared["view_uv"] > 0].copy()
    if conversion_sample.empty:
        warnings.append("No positive exposure rows are available for conversion diagnostics.")

    tiered = _assign_exposure_tiers(conversion_sample)
    tier_results = []
    for tier in ["low_exposure", "mid_exposure", "high_exposure"]:
        subset = tiered[tiered["exposure_tier"] == tier].copy()
        tier_results.append(_conversion_tier_result(tier, subset))

    warnings = _dedupe([*warnings, *[warning for item in tier_results for warning in item.get("warnings", [])]])
    estimable_tiers = [item for item in tier_results if item["model"]["status"] == "ok"]
    result = {
        "method": "conversion_discount_by_exposure_tier",
        "method_status": "implemented" if len(estimable_tiers) >= 2 and not warnings else "limited",
        "status": "completed",
        "project_id": project_id,
        "sample": {
            **_sample_summary(prepared),
            "conversion_rows": int(len(conversion_sample)),
            "positive_buy_uv_rows": int((prepared["buy_uv"] > 0).sum()),
        },
        "tiering": {
            "basis": "category average view_uv",
            "tiers": ["low_exposure", "mid_exposure", "high_exposure"],
        },
        "exposure_tiers": tier_results,
        "warnings": warnings,
        "interpretation_rules": [
            "Conversion diagnostics explain whether discount response changes with exposure scale.",
            "A positive discount slope inside low-exposure tiers should not be scaled without exposure support.",
            "Compare conversion evidence with GPS/uplift before making allocation recommendations.",
        ],
        "evidence_artifacts": _source_artifacts(workspace),
    }

    analysis_dir = workspace / ".analysis"
    table_dir = workspace / "artifacts" / "tables"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    result_path = analysis_dir / "conversion_diagnostics_result.json"
    table_path = table_dir / "conversion_by_exposure_tier.csv"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_conversion_table(table_path, tier_results)

    return ToolResult(
        ok=True,
        action="analysis.run_conversion_diagnostics",
        summary=f"Conversion diagnostics completed: {len(estimable_tiers)}/{len(tier_results)} exposure tier(s) estimable, status={result['method_status']}.",
        artifacts=[
            {
                "type": "model_output",
                "title": "conversion_diagnostics_result.json",
                "path": str(result_path.relative_to(workspace)),
                "method_status": result["method_status"],
                "estimable_tier_count": len(estimable_tiers),
                "warnings": warnings,
            },
            {
                "type": "table",
                "title": "conversion_by_exposure_tier.csv",
                "path": str(table_path.relative_to(workspace)),
                "rows": len(tier_results),
            },
        ],
        assistant_hint="Use tiered conversion diagnostics before recommending discount scaling for high- or low-exposure categories.",
    )


def _load_best_panel(workspace: Path) -> pd.DataFrame | None:
    candidates = [
        workspace / "data" / "processed" / "localgap_enriched_panel.csv",
        workspace / "data" / "processed" / "category_day_panel.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return pd.read_csv(candidate)
    json_path = workspace / "data" / "processed" / "category_day_panel.json"
    if not json_path.exists():
        return None
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return pd.DataFrame(data if isinstance(data, list) else [])


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    prepared = panel.copy()
    if "category_key" not in prepared.columns:
        prepared["category_key"] = prepared.get("category", prepared.get("category_name", "unknown"))
    if "category_name" not in prepared.columns:
        prepared["category_name"] = prepared.get("category", prepared["category_key"])
    prepared["category_key"] = prepared["category_key"].astype(str)
    prepared["category_name"] = prepared["category_name"].astype(str)
    prepared["date"] = pd.to_datetime(prepared.get("date"), errors="coerce")
    prepared = prepared.dropna(subset=["date", "category_key"]).copy()

    for column in [
        "gmv",
        "order_count",
        "view_uv",
        "exposure",
        "buy_uv",
        "discount_amount",
        "discount_rate",
        "local_gap",
    ]:
        if column not in prepared.columns:
            prepared[column] = np.nan if column == "local_gap" else 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    prepared["gmv"] = prepared["gmv"].fillna(0.0)
    prepared["order_count"] = prepared["order_count"].fillna(0.0)
    prepared["view_uv"] = prepared["view_uv"].fillna(0.0)
    prepared["exposure"] = prepared["exposure"].fillna(0.0)
    prepared["view_uv"] = np.where(prepared["view_uv"] > 0, prepared["view_uv"], prepared["exposure"])
    prepared["buy_uv"] = prepared["buy_uv"].fillna(0.0)
    prepared["discount_amount"] = prepared["discount_amount"].fillna(0.0)
    if prepared["discount_rate"].isna().all() and prepared["discount_amount"].sum() > 0:
        prepared["discount_rate"] = np.where(prepared["gmv"] > 0, prepared["discount_amount"] / prepared["gmv"], 0.0)
    prepared["discount_rate"] = prepared["discount_rate"].fillna(0.0).clip(lower=0.0, upper=1.0)

    if "is_activity" not in prepared.columns:
        prepared["is_activity"] = False
    prepared["is_activity"] = prepared["is_activity"].astype(bool)
    if "is_payday" not in prepared.columns:
        prepared["is_payday"] = False
    prepared["is_payday"] = prepared["is_payday"].astype(bool)

    prepared["aov"] = np.where(prepared["order_count"] > 0, prepared["gmv"] / prepared["order_count"], np.nan)
    prepared["log_gmv"] = np.log1p(prepared["gmv"].clip(lower=0.0))
    prepared["log_order_count"] = np.log1p(prepared["order_count"].clip(lower=0.0))
    prepared["log_aov"] = np.where(prepared["aov"] > 0, np.log(prepared["aov"]), np.nan)
    prepared["log_view_uv"] = np.log1p(prepared["view_uv"].clip(lower=0.0))
    prepared["discount_rate_pp"] = prepared["discount_rate"] * 100.0
    prepared["resource_interaction"] = prepared["discount_rate_pp"] * prepared["log_view_uv"]
    prepared["dist2pay"] = pd.to_numeric(
        prepared.get("dist2pay", prepared.get("days_to_payday", prepared["date"].dt.day - 27)),
        errors="coerce",
    ).fillna(0.0)
    prepared["dist2pay_sq"] = prepared["dist2pay"] ** 2
    prepared["conversion_per_10k_uv"] = np.where(
        prepared["view_uv"] > 0,
        prepared["buy_uv"] / prepared["view_uv"] * 10000.0,
        np.nan,
    )
    return prepared.replace([np.inf, -np.inf], np.nan)


def _panel_warnings(panel: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if panel["category_key"].nunique() < 2:
        warnings.append("Fewer than two categories are available; category fixed effects have weak support.")
    if panel["date"].nunique() < 3:
        warnings.append("Fewer than three dates are available; date fixed effects have weak support.")
    if int((panel["view_uv"] > 0).sum()) == 0:
        warnings.append("No positive exposure rows are available.")
    if int((panel["buy_uv"] > 0).sum()) == 0:
        warnings.append("No positive buy_uv rows are available; conversion diagnostics will be limited.")
    if float(panel["discount_rate"].std(ddof=0) or 0.0) == 0.0:
        warnings.append("Discount rate has no variation; discount coefficients are not identifiable.")
    return warnings


def _fit_model(frame: pd.DataFrame, outcome: str, terms: list[str], model_id: str, label: str) -> dict[str, Any]:
    columns = ["category_key", "date", outcome, *terms, "is_activity"]
    sample = frame[columns].replace([np.inf, -np.inf], np.nan).dropna().copy()
    fixed_effects = []
    if sample["category_key"].nunique() >= 2:
        fixed_effects.append("category")
    if sample["date"].nunique() >= 2:
        fixed_effects.append("date")

    min_rows = max(len(terms) + 6, 12)
    warnings: list[str] = []
    if len(sample) < min_rows:
        warnings.append(f"{model_id}: insufficient rows after filtering ({len(sample)} < {min_rows}).")
        return _empty_model(model_id, label, outcome, sample, fixed_effects, warnings)

    residuals = _residualized_frame(sample, [outcome, *terms], fixed_effects)
    usable_terms = [
        term
        for term in terms
        if term in residuals.columns and float(residuals[term].std(ddof=0) or 0.0) > 1e-9
    ]
    if not usable_terms:
        warnings.append(f"{model_id}: no resource terms have residual variation after fixed effects.")
        return _empty_model(model_id, label, outcome, sample, fixed_effects, warnings)

    y = residuals[outcome].to_numpy(dtype=float)
    x = residuals[usable_terms].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residual = y - fitted
    tss = float(np.sum((y - y.mean()) ** 2))
    rss = float(np.sum(residual ** 2))
    r_squared = 1.0 - rss / tss if tss > 1e-12 else 0.0
    dof = max(len(y) - len(usable_terms), 1)
    sigma2 = rss / dof
    xtx_inv = np.linalg.pinv(x.T @ x)
    std_errors = np.sqrt(np.maximum(np.diag(xtx_inv) * sigma2, 0.0))
    outcome_std = float(sample[outcome].std(ddof=0) or 0.0)

    coefficients = []
    for index, term in enumerate(usable_terms):
        coefficient = float(beta[index])
        std_error = float(std_errors[index])
        t_value = coefficient / std_error if std_error > 1e-12 else None
        term_std = float(sample[term].std(ddof=0) or 0.0)
        coefficients.append(
            {
                "term": term,
                "coefficient": round(coefficient, 6),
                "std_error": round(std_error, 6),
                "t_value": round(float(t_value), 4) if t_value is not None else None,
                "normal_approx_pvalue": _normal_pvalue(t_value),
                "standardized_coefficient": round(coefficient * term_std / outcome_std, 6) if outcome_std > 1e-12 else None,
            }
        )

    return {
        "model_id": model_id,
        "label": label,
        "outcome": outcome,
        "status": "ok",
        "fixed_effects": fixed_effects,
        "row_count": int(len(sample)),
        "category_count": int(sample["category_key"].nunique()),
        "date_count": int(sample["date"].nunique()),
        "r_squared_within": round(float(r_squared), 4),
        "coefficients": coefficients,
        "activity_resource_contributions": _activity_resource_contributions(sample, coefficients, outcome),
        "warnings": warnings,
    }


def _empty_model(
    model_id: str,
    label: str,
    outcome: str,
    sample: pd.DataFrame,
    fixed_effects: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "label": label,
        "outcome": outcome,
        "status": "insufficient_support",
        "fixed_effects": fixed_effects,
        "row_count": int(len(sample)),
        "category_count": int(sample["category_key"].nunique()) if "category_key" in sample else 0,
        "date_count": int(sample["date"].nunique()) if "date" in sample else 0,
        "r_squared_within": None,
        "coefficients": [],
        "activity_resource_contributions": [],
        "warnings": warnings,
    }


def _residualized_frame(sample: pd.DataFrame, columns: list[str], fixed_effects: list[str]) -> pd.DataFrame:
    residuals = pd.DataFrame(index=sample.index)
    for column in columns:
        values = pd.to_numeric(sample[column], errors="coerce").astype(float)
        resid = values - values.mean()
        if "category" in fixed_effects:
            resid = resid - values.groupby(sample["category_key"]).transform("mean") + values.mean()
        if "date" in fixed_effects:
            resid = resid - values.groupby(sample["date"]).transform("mean") + values.mean()
        residuals[column] = resid
    return residuals.replace([np.inf, -np.inf], np.nan).dropna()


def _activity_resource_contributions(sample: pd.DataFrame, coefficients: list[dict[str, Any]], outcome: str) -> list[dict[str, Any]]:
    activity = sample[sample["is_activity"]]
    non_activity = sample[~sample["is_activity"]]
    if activity.empty or non_activity.empty:
        return []
    contributions = []
    coef_by_term = {item["term"]: float(item["coefficient"]) for item in coefficients if item.get("coefficient") is not None}
    for term, coefficient in coef_by_term.items():
        active_mean = float(activity[term].mean())
        baseline_mean = float(non_activity[term].mean())
        contribution = coefficient * (active_mean - baseline_mean)
        contributions.append(
            {
                "term": term,
                "outcome": outcome,
                "activity_mean": round(active_mean, 6),
                "non_activity_mean": round(baseline_mean, 6),
                "active_minus_non_activity": round(active_mean - baseline_mean, 6),
                "estimated_contribution": round(float(contribution), 6),
            }
        )
    return contributions


def _resource_decomposition(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for model in models:
        for item in model.get("activity_resource_contributions", []):
            rows.append({"model_id": model["model_id"], **item})
    return rows


def _assign_exposure_tiers(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if output.empty:
        output["exposure_tier"] = []
        return output
    exposure = output.groupby("category_key")["view_uv"].mean().sort_values()
    if len(exposure) == 1:
        tier_map = {str(exposure.index[0]): "mid_exposure"}
    else:
        ranks = exposure.rank(method="first", pct=True)
        tier_map = {
            str(category): (
                "low_exposure" if rank <= 1 / 3 else "mid_exposure" if rank <= 2 / 3 else "high_exposure"
            )
            for category, rank in ranks.items()
        }
    output["exposure_tier"] = output["category_key"].map(tier_map).fillna("mid_exposure")
    return output


def _conversion_tier_result(tier: str, subset: pd.DataFrame) -> dict[str, Any]:
    if subset.empty:
        model = _empty_model(
            f"{tier}_conversion",
            f"{tier} conversion",
            "conversion_per_10k_uv",
            subset,
            [],
            [f"{tier}: no rows in exposure tier."],
        )
        return _tier_payload(tier, subset, model)

    terms = ["discount_rate_pp", "log_view_uv", "resource_interaction", "dist2pay", "dist2pay_sq"]
    model = _fit_model(subset, "conversion_per_10k_uv", terms, f"{tier}_conversion", f"{tier} conversion")
    return _tier_payload(tier, subset, model)


def _tier_payload(tier: str, subset: pd.DataFrame, model: dict[str, Any]) -> dict[str, Any]:
    activity = subset[subset["is_activity"]]
    non_activity = subset[~subset["is_activity"]]
    discount_coefficient = next(
        (item.get("coefficient") for item in model.get("coefficients", []) if item.get("term") == "discount_rate_pp"),
        None,
    )
    return {
        "tier": tier,
        "category_count": int(subset["category_key"].nunique()) if "category_key" in subset else 0,
        "row_count": int(len(subset)),
        "avg_view_uv": round(float(subset["view_uv"].mean()), 4) if not subset.empty else None,
        "avg_conversion_per_10k_uv": round(float(subset["conversion_per_10k_uv"].mean()), 4) if not subset.empty else None,
        "activity_conversion_per_10k_uv": round(float(activity["conversion_per_10k_uv"].mean()), 4) if not activity.empty else None,
        "non_activity_conversion_per_10k_uv": round(float(non_activity["conversion_per_10k_uv"].mean()), 4) if not non_activity.empty else None,
        "discount_slope_per_pp": discount_coefficient,
        "model": model,
        "warnings": model.get("warnings", []),
    }


def _sample_summary(panel: pd.DataFrame) -> dict[str, Any]:
    return {
        "row_count": int(len(panel)),
        "category_count": int(panel["category_key"].nunique()),
        "date_count": int(panel["date"].nunique()),
        "activity_rows": int(panel["is_activity"].sum()),
        "non_activity_rows": int((~panel["is_activity"]).sum()),
        "positive_exposure_rows": int((panel["view_uv"] > 0).sum()),
        "positive_order_rows": int((panel["order_count"] > 0).sum()),
    }


def _source_artifacts(workspace: Path) -> list[str]:
    candidates = [
        "data/processed/localgap_enriched_panel.csv",
        "data/processed/category_day_panel.csv",
        "data/processed/category_day_panel.json",
        ".analysis/localgap_result.json",
    ]
    return [path for path in candidates if (workspace / path).exists()]


def _write_model_table(path: Path, models: list[dict[str, Any]]) -> None:
    fields = [
        "model_id",
        "outcome",
        "status",
        "term",
        "coefficient",
        "std_error",
        "t_value",
        "normal_approx_pvalue",
        "standardized_coefficient",
        "row_count",
        "r_squared_within",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for model in models:
            coefficients = model.get("coefficients", []) or [{"term": "", "coefficient": None}]
            for coefficient in coefficients:
                writer.writerow(
                    {
                        "model_id": model["model_id"],
                        "outcome": model["outcome"],
                        "status": model["status"],
                        "term": coefficient.get("term"),
                        "coefficient": coefficient.get("coefficient"),
                        "std_error": coefficient.get("std_error"),
                        "t_value": coefficient.get("t_value"),
                        "normal_approx_pvalue": coefficient.get("normal_approx_pvalue"),
                        "standardized_coefficient": coefficient.get("standardized_coefficient"),
                        "row_count": model.get("row_count"),
                        "r_squared_within": model.get("r_squared_within"),
                    }
                )


def _write_conversion_table(path: Path, tiers: list[dict[str, Any]]) -> None:
    fields = [
        "tier",
        "category_count",
        "row_count",
        "avg_view_uv",
        "avg_conversion_per_10k_uv",
        "activity_conversion_per_10k_uv",
        "non_activity_conversion_per_10k_uv",
        "discount_slope_per_pp",
        "model_status",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in tiers:
            writer.writerow(
                {
                    "tier": item["tier"],
                    "category_count": item["category_count"],
                    "row_count": item["row_count"],
                    "avg_view_uv": item["avg_view_uv"],
                    "avg_conversion_per_10k_uv": item["avg_conversion_per_10k_uv"],
                    "activity_conversion_per_10k_uv": item["activity_conversion_per_10k_uv"],
                    "non_activity_conversion_per_10k_uv": item["non_activity_conversion_per_10k_uv"],
                    "discount_slope_per_pp": item["discount_slope_per_pp"],
                    "model_status": item["model"]["status"],
                }
            )


def _normal_pvalue(t_value: float | None) -> float | None:
    if t_value is None:
        return None
    return round(float(math.erfc(abs(t_value) / math.sqrt(2.0))), 6)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
