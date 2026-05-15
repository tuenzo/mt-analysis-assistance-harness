from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.tools.schemas import ToolResult


ROLE_ALIASES: dict[str, dict[str, list[str]]] = {
    "order_info": {
        "order_id": ["order_id", "main_order_id", "stat_pay_main_order_id"],
        "user_id": ["user_id", "stat_pay_user_id"],
        "sku_id": ["sku_id", "base_sku_id", "sku"],
        "category_id": ["category_id", "cate_id"],
        "category_name": ["category_name", "category_name_cn", "category", "cat_name"],
        "date": ["date", "dt", "pay_date", "pay_time", "order_date"],
        "gmv": ["gmv", "sale_amount", "sku_sale_amt", "pay_amount"],
        "discount_amount": ["discount_amount", "discount", "coupon_amount", "biz_total_discount_amt"],
        "quantity": ["quantity", "qty", "sku_sale_num"],
        "order_count": ["order_count"],
    },
    "exposure_info": {
        "sku_id": ["sku_id", "base_sku_id", "sku"],
        "category_id": ["category_id", "cate_id"],
        "category_name": ["category_name", "category_name_cn", "category", "cat_name"],
        "date": ["date", "dt", "exposure_date"],
        "view_uv": ["view_uv", "exposure", "exposure_count", "expo_uv"],
        "buy_uv": ["buy_uv"],
        "exposure_pv": ["exposure_pv", "view_pv"],
    },
    "activity_timeline": {
        "category_id": ["category_id", "cate_id"],
        "category_name": ["category_name", "category_name_cn", "category", "cat_name"],
        "date": ["date", "dt", "activity_date", "日期"],
        "start_date": ["start_date", "开始日期", "开始时间"],
        "end_date": ["end_date", "结束日期", "结束时间"],
        "activity_name": ["activity_name", "activity_id", "activity", "营销活动", "活动名称"],
        "payday": ["payday", "is_payday", "发薪日"],
    },
}

ROLE_PATTERNS = {
    "order_info": ["order_info", "orders", "order"],
    "exposure_info": ["exposure_info", "exposure", "expo"],
    "activity_timeline": ["activity_timeline", "activity", "timeline"],
}

REQUIRED_FIELDS = {
    "order_info": ["date", "category_name", "gmv"],
    "exposure_info": ["date", "view_uv"],
    "activity_timeline": [],
}


@dataclass
class ValidationResult:
    ok: bool
    issues: list[str]
    warnings: list[str]
    file_info: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class PanelConfig:
    project_id: str
    payday_day: int = 27
    pre_activity_days: int = 7
    post_activity_days: int = 7


@dataclass(frozen=True)
class PanelBuildResult:
    panel_df: pd.DataFrame
    summary: dict[str, Any]


def validate_files(workspace_path: Path) -> ValidationResult:
    workspace_path = Path(workspace_path)
    data_dir = workspace_path / "data" / "raw"
    files = _find_role_files(data_dir)
    issues: list[str] = []
    warnings: list[str] = []
    file_info: dict[str, dict[str, Any]] = {}

    for role in ROLE_ALIASES:
        csv_path = files.get(role)
        if csv_path is None:
            issues.append(f"Missing required CSV for role `{role}`.")
            continue

        try:
            frame = _read_csv(csv_path)
        except Exception as exc:
            issues.append(f"{role}: failed to read CSV: {exc}")
            continue

        mappings = infer_csv_schema(csv_path, role)
        role_issues, role_warnings = _validate_frame(frame, role, mappings)
        issues.extend(f"{role}: {issue}" for issue in role_issues)
        warnings.extend(f"{role}: {warning}" for warning in role_warnings)
        file_info[role] = {
            "path": str(csv_path),
            "rows": int(len(frame)),
            "columns": frame.columns.tolist(),
            "recommended_mappings": mappings,
        }
        if role == "order_info":
            file_info[role]["measure_units"] = infer_measure_units_from_mappings(mappings)

    return ValidationResult(ok=not issues, issues=issues, warnings=warnings, file_info=file_info)


def infer_csv_schema(csv_path: Path, role: str) -> dict[str, str]:
    headers = _read_headers(csv_path)
    return infer_schema_from_columns(headers, role)


def infer_schema_from_columns(columns: list[str], role: str) -> dict[str, str]:
    aliases = ROLE_ALIASES.get(role, {})
    lower_to_original = {str(column).strip().lower(): str(column) for column in columns}
    mappings: dict[str, str] = {}

    for standard_field, candidates in aliases.items():
        for candidate in candidates:
            match = lower_to_original.get(candidate.lower())
            if match is not None:
                mappings[standard_field] = match
                break

    return mappings


def infer_measure_units_from_mappings(order_mappings: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {
        "gmv": _infer_amount_unit("gmv", order_mappings.get("gmv")),
        "discount_amount": _infer_amount_unit("discount_amount", order_mappings.get("discount_amount")),
    }


def build_category_day_panel(
    project_id: str,
    workspace_path: str,
    schema_mappings: dict[str, dict[str, str]] | None = None,
) -> ToolResult:
    workspace = Path(workspace_path)
    output_dir = workspace / "data" / "processed"
    analysis_dir = workspace / ".analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    files = _find_role_files(workspace / "data" / "raw")
    validation = validate_files(workspace)
    if not validation.ok:
        return ToolResult(
            ok=False,
            action="panel.build_category_day",
            summary="Data validation failed before panel build.",
            error={"code": "VALIDATION_FAILED", "message": "; ".join(validation.issues), "details": {"warnings": validation.warnings}},
        )

    try:
        orders_raw = _read_csv(files["order_info"])
        exposure_raw = _read_csv(files["exposure_info"])
        activity_raw = _read_csv(files["activity_timeline"])

        mappings = schema_mappings or {}
        order_mappings = mappings.get("order_info") or infer_schema_from_columns(orders_raw.columns.tolist(), "order_info")
        exposure_mappings = mappings.get("exposure_info") or infer_schema_from_columns(exposure_raw.columns.tolist(), "exposure_info")
        activity_mappings = mappings.get("activity_timeline") or infer_schema_from_columns(activity_raw.columns.tolist(), "activity_timeline")
        measure_units = infer_measure_units_from_mappings(order_mappings)
        orders = standardize_orders(orders_raw, order_mappings)
        exposure = standardize_exposure(exposure_raw, exposure_mappings)
        activity = standardize_activity(activity_raw, activity_mappings)
        result = build_panel_from_frames(
            orders,
            exposure,
            activity,
            PanelConfig(project_id=project_id),
            measure_units=measure_units,
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            action="panel.build_category_day",
            summary="Panel build failed.",
            error={"code": "PANEL_BUILD_FAILED", "message": str(exc), "details": {}},
        )

    json_path = output_dir / "category_day_panel.json"
    csv_path = output_dir / "category_day_panel.csv"
    summary_path = analysis_dir / "panel_summary.json"

    records = result.panel_df.to_dict(orient="records")
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    result.panel_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary_path.write_text(json.dumps(result.summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="panel.build_category_day",
        summary=(
            f"Panel build completed: {result.summary['row_count']} rows, "
            f"{result.summary['category_count']} categories, "
            f"{result.summary['date_range']['start']} to {result.summary['date_range']['end']}."
        ),
        artifacts=[
            {"type": "panel_data", "title": "category_day_panel.json", "path": str(json_path.relative_to(workspace)), "rows": result.summary["row_count"]},
            {"type": "panel_data", "title": "category_day_panel.csv", "path": str(csv_path.relative_to(workspace)), "rows": result.summary["row_count"]},
            {"type": "panel_summary", "title": "panel_summary.json", "path": str(summary_path.relative_to(workspace)), **result.summary},
        ],
        state_patch={"current_stage": "panel_ready"},
        assistant_hint="Panel is ready. Continue with diagnostics or full pipeline analysis.",
    )


def build_panel_from_frames(
    orders_df: pd.DataFrame,
    exposure_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    config: PanelConfig,
    measure_units: dict[str, Any] | None = None,
) -> PanelBuildResult:
    clean_orders = _prepare_orders(orders_df)
    clean_exposure = _prepare_exposure(exposure_df, clean_orders)
    clean_activity = _prepare_activity(activity_df, config)

    categories = pd.concat(
        [
            clean_orders[["category_key", "category_name"]].drop_duplicates(),
            clean_exposure[["category_key", "category_name"]].drop_duplicates(),
        ],
        ignore_index=True,
    ).dropna(subset=["category_key"]).drop_duplicates(subset=["category_key"])

    if categories.empty:
        raise ValueError("No categories could be inferred from order or exposure data.")

    min_date, max_date = _primary_date_bounds(clean_orders, clean_exposure)
    all_dates = pd.date_range(min_date, max_date, freq="D")
    full_index = pd.MultiIndex.from_product([categories["category_key"], all_dates], names=["category_key", "date"])
    panel = full_index.to_frame(index=False).merge(categories, on="category_key", how="left")

    order_agg = _aggregate_orders(clean_orders)
    exposure_agg = _aggregate_exposure(clean_exposure)
    panel = panel.merge(order_agg, on=["category_key", "date"], how="left", suffixes=("", "_order"))
    panel = panel.merge(exposure_agg, on=["category_key", "date"], how="left", suffixes=("", "_exposure"))
    panel = _merge_activity(panel, clean_activity)

    for column in ["gmv", "order_count", "quantity", "discount_amount", "user_count", "view_uv", "buy_uv", "exposure_pv"]:
        panel[column] = pd.to_numeric(panel[column], errors="coerce").fillna(0.0)

    panel["project_id"] = config.project_id
    panel["category"] = panel["category_name"]
    panel["discount"] = panel["discount_amount"]
    panel["exposure"] = panel["view_uv"]
    panel["discount_rate"] = np.where(panel["gmv"] > 0, panel["discount_amount"] / panel["gmv"], 0.0)
    panel["conversion_rate"] = np.where(panel["view_uv"] > 0, panel["buy_uv"] / panel["view_uv"], 0.0)
    panel["exposure_rate"] = panel["conversion_rate"] * 100
    panel["weekday"] = panel["date"].dt.weekday
    panel["month"] = panel["date"].dt.month
    panel["is_weekend"] = (panel["weekday"] >= 5).astype(int)
    panel["days_to_payday"] = panel["date"].dt.day - int(config.payday_day)
    panel["payday_phase"] = panel["days_to_payday"].apply(_build_payday_phase)
    panel["is_payday"] = panel["is_payday"] | (panel["days_to_payday"] == 0)
    panel["is_payday_activity"] = panel["is_activity"] & panel["is_payday"]
    panel["pre_activity_window"] = panel["date"].isin(_build_window_dates(clean_activity["date"], before=config.pre_activity_days, after=0)).astype(int)
    panel["post_activity_window"] = panel["date"].isin(_build_window_dates(clean_activity["date"], before=0, after=config.post_activity_days)).astype(int)

    output = panel[
        [
            "project_id",
            "category_key",
            "category_name",
            "category",
            "date",
            "gmv",
            "order_count",
            "quantity",
            "discount_amount",
            "discount",
            "discount_rate",
            "view_uv",
            "buy_uv",
            "exposure",
            "exposure_pv",
            "conversion_rate",
            "exposure_rate",
            "user_count",
            "is_activity",
            "activity_name",
            "is_payday",
            "is_payday_activity",
            "days_to_payday",
            "payday_phase",
            "weekday",
            "month",
            "is_weekend",
            "pre_activity_window",
            "post_activity_window",
        ]
    ].sort_values(["category_key", "date"]).reset_index(drop=True)

    readiness = _build_analysis_readiness(output)
    summary = {
        "date_range": {"start": str(output["date"].min().date()), "end": str(output["date"].max().date())},
        "category_count": int(output["category_key"].nunique()),
        "row_count": int(len(output)),
        "total_gmv": float(output["gmv"].sum()),
        "total_discount": float(output["discount_amount"].sum()),
        "total_view_uv": float(output["view_uv"].sum()),
        "activity_day_count": int(output.loc[output["is_activity"], "date"].nunique()),
        "measure_units": measure_units or _default_measure_units(),
        "analysis_readiness": readiness,
        "missing_summary": {
            "zero_gmv_rows": int((output["gmv"] == 0).sum()),
            "zero_view_uv_rows": int((output["view_uv"] == 0).sum()),
            "non_activity_rows": int((~output["is_activity"]).sum()),
        },
    }
    output["date"] = output["date"].dt.strftime("%Y-%m-%d")
    output["is_activity"] = output["is_activity"].astype(bool)
    output["is_payday"] = output["is_payday"].astype(bool)
    output["is_payday_activity"] = output["is_payday_activity"].astype(bool)
    return PanelBuildResult(panel_df=output, summary=summary)


def standardize_orders(frame: pd.DataFrame, mappings: dict[str, str]) -> pd.DataFrame:
    data = _apply_mappings(frame, mappings)
    if "category_name" not in data.columns and "category" in data.columns:
        data["category_name"] = data["category"]
    if "category_id" not in data.columns:
        data["category_id"] = None
    if "quantity" not in data.columns:
        data["quantity"] = 0
    if "order_count" not in data.columns:
        data["order_count"] = 1
    if "discount_amount" not in data.columns:
        data["discount_amount"] = 0
    if "user_id" not in data.columns:
        data["user_id"] = None
    return data


def standardize_exposure(frame: pd.DataFrame, mappings: dict[str, str]) -> pd.DataFrame:
    data = _apply_mappings(frame, mappings)
    if "category_name" not in data.columns and "category" in data.columns:
        data["category_name"] = data["category"]
    if "category_id" not in data.columns:
        data["category_id"] = None
    if "buy_uv" not in data.columns:
        data["buy_uv"] = 0
    if "exposure_pv" not in data.columns:
        data["exposure_pv"] = 0
    return data


def standardize_activity(frame: pd.DataFrame, mappings: dict[str, str]) -> pd.DataFrame:
    data = _apply_mappings(frame, mappings)
    if "category_name" not in data.columns and "category" in data.columns:
        data["category_name"] = data["category"]
    if "activity_name" not in data.columns:
        data["activity_name"] = "activity"
    if "payday" not in data.columns:
        data["payday"] = False
    return data


def parse_date_series(values: Any) -> pd.Series:
    series = pd.Series(values, copy=False)
    text = series.astype("string").str.strip()
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    compact_mask = text.str.fullmatch(r"\d{8}").fillna(False)
    if compact_mask.any():
        parsed.loc[compact_mask] = pd.to_datetime(text.loc[compact_mask], format="%Y%m%d", errors="coerce")

    remaining_mask = parsed.isna() & text.notna() & (text != "")
    if remaining_mask.any():
        parsed.loc[remaining_mask] = pd.to_datetime(text.loc[remaining_mask], errors="coerce")

    return parsed.dt.normalize()


def _default_measure_units() -> dict[str, dict[str, Any]]:
    return infer_measure_units_from_mappings({})


def _infer_amount_unit(measure: str, source_column: str | None) -> dict[str, Any]:
    display_name = "GMV" if measure == "gmv" else "折扣"
    source = str(source_column or "").strip()
    normalized = source.lower().replace("-", "_").replace(" ", "_")
    explicit_unit = _explicit_unit_from_column(normalized, source)
    declared = explicit_unit is not None
    unit_label = explicit_unit or "元"
    if source:
        provenance = (
            f"order_info.{source} includes an explicit unit marker."
            if declared
            else f"order_info.{source} has no explicit unit marker; values are treated as yuan by the Keemart source-data contract."
        )
    else:
        provenance = f"No mapped {display_name} source column was available; values default to yuan by the Keemart source-data contract."
    return {
        "measure": measure,
        "source_role": "order_info",
        "source_column": source or None,
        "unit": unit_label,
        "unit_label": unit_label,
        "declared": declared,
        "scale": 1.0,
        "provenance": provenance,
    }


def _explicit_unit_from_column(normalized: str, original: str) -> str | None:
    original_text = original.strip()
    markers = [
        ("万元", "万元"),
        ("万", "万元"),
        ("wan_yuan", "万元"),
        ("wanyuan", "万元"),
        ("ten_thousand_yuan", "万元"),
        ("yuan", "元"),
        ("rmb", "元"),
        ("cny", "元"),
        ("元", "元"),
        ("fen", "分"),
        ("cent", "分"),
        ("分", "分"),
        ("usd", "USD"),
        ("dollar", "USD"),
        ("sar", "SAR"),
        ("riyal", "SAR"),
    ]
    haystack = f"{normalized} {original_text}"
    for marker, label in markers:
        if marker in haystack:
            return label
    return None


def _build_analysis_readiness(panel: pd.DataFrame) -> dict[str, Any]:
    date_count = int(panel["date"].nunique())
    category_count = int(panel["category_key"].nunique())
    activity_rows = int(panel["is_activity"].sum())
    non_activity_rows = int((~panel["is_activity"]).sum())
    zero_gmv_share = round(float((panel["gmv"] <= 0).mean()), 4) if len(panel) else 0.0
    zero_view_uv_share = round(float((panel["view_uv"] <= 0).mean()), 4) if len(panel) else 0.0
    min_activity_rows = max(6, category_count * 2)
    min_non_activity_rows = max(6, category_count * 2)
    reasons: list[str] = []
    reason_codes: list[str] = []

    if date_count < 14:
        reason_codes.append("short_date_coverage")
        reasons.append(f"Panel covers {date_count} day(s), below the 14-day minimum for stable cyclical diagnostics.")
    if activity_rows < min_activity_rows:
        reason_codes.append("sparse_activity_rows")
        reasons.append(f"Panel has {activity_rows} activity row(s), below the recommended {min_activity_rows}.")
    if non_activity_rows < min_non_activity_rows:
        reason_codes.append("sparse_baseline_rows")
        reasons.append(f"Panel has {non_activity_rows} non-activity row(s), below the recommended {min_non_activity_rows}.")
    if zero_gmv_share > 0.5:
        reason_codes.append("high_zero_gmv_share")
        reasons.append(f"{round(zero_gmv_share * 100, 1)}% of panel rows have zero or negative GMV.")

    status = "limited" if reasons else "ready"
    return {
        "status": status,
        "reason_codes": reason_codes,
        "reasons": reasons,
        "metrics": {
            "date_count": date_count,
            "category_count": category_count,
            "activity_rows": activity_rows,
            "non_activity_rows": non_activity_rows,
            "zero_gmv_share": zero_gmv_share,
            "zero_view_uv_share": zero_view_uv_share,
        },
        "recommended_interpretation": "smoke_test_only" if status == "limited" else "standard_analysis",
    }


def _find_role_files(data_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not data_dir.exists():
        return files
    candidates = sorted(data_dir.glob("*.csv"), key=lambda path: path.name.lower())
    for role in ROLE_PATTERNS:
        ranked = [
            (_role_file_score(candidate, role), candidate)
            for candidate in candidates
        ]
        ranked = [(score, candidate) for score, candidate in ranked if score > 0]
        if ranked:
            files[role] = sorted(ranked, key=lambda item: (-item[0], item[1].name.lower()))[0][1]
    return files


def _role_file_score(candidate: Path, role: str) -> int:
    lower = candidate.name.lower()
    if _looks_like_processed_panel_file(candidate):
        return 0
    exact_markers = {
        "order_info": ["order_info"],
        "exposure_info": ["exposure_info"],
        "activity_timeline": ["activity_timeline"],
    }
    for marker in exact_markers.get(role, []):
        if marker in lower:
            return 100
    header_mappings = infer_csv_schema(candidate, role)
    required_hits = sum(1 for field in REQUIRED_FIELDS[role] if field in header_mappings)
    if role == "activity_timeline" and ("date" in header_mappings or ("start_date" in header_mappings and "end_date" in header_mappings)):
        required_hits += 1
    if required_hits:
        return 50 + required_hits
    for marker in ROLE_PATTERNS.get(role, []):
        if marker in lower:
            return 10
    return 0


def _looks_like_processed_panel_file(candidate: Path) -> bool:
    lower = candidate.name.lower()
    if "category_date_panel" in lower or "category_day_panel" in lower or "category_daily_panel" in lower:
        return True
    try:
        lowered = {header.strip().lower() for header in _read_headers(candidate)}
    except Exception:
        return False
    has_category_date = "date" in lowered or "dt" in lowered
    has_category = bool({"category", "category_name", "category_name_cn", "category_key"} & lowered)
    has_panel_metrics = bool({"gmv", "sku_sale_amt"} & lowered) and bool({"is_activity", "is_activity_day", "activity_name"} & lowered)
    has_exposure_metrics = bool({"view_uv", "exposure", "exposure_view_uv", "buy_uv", "exposure_buy_uv"} & lowered)
    return has_category_date and has_category and has_panel_metrics and has_exposure_metrics


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def _read_headers(path: Path) -> list[str]:
    return pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns.tolist()


def _validate_frame(frame: pd.DataFrame, role: str, mappings: dict[str, str]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    if frame.empty:
        warnings.append("CSV has no data rows.")

    for required in REQUIRED_FIELDS[role]:
        if required not in mappings:
            issues.append(f"Missing required field `{required}`.")

    if role == "activity_timeline" and not ("date" in mappings or ("start_date" in mappings and "end_date" in mappings)):
        issues.append("Missing activity date field; expected `date` or `start_date` plus `end_date`.")

    if role in {"order_info", "exposure_info"} and "category_name" not in mappings and "sku_id" not in mappings:
        issues.append("Missing category field; expected `category`, `category_name`, or `sku_id` for backfill.")

    for standard_field in ("date", "start_date", "end_date"):
        source = mappings.get(standard_field)
        if source and source in frame.columns:
            invalid = int(parse_date_series(frame[source]).isna().sum())
            if invalid:
                issues.append(f"`{standard_field}` has {invalid} unparsable row(s).")

    for standard_field in ("gmv", "discount_amount", "quantity", "order_count", "view_uv", "buy_uv", "exposure_pv"):
        source = mappings.get(standard_field)
        if source and source in frame.columns:
            numeric = pd.to_numeric(frame[source], errors="coerce")
            invalid = int(numeric.isna().sum())
            if invalid:
                issues.append(f"`{standard_field}` has {invalid} non-numeric row(s).")
            negative = int((numeric.fillna(0) < 0).sum())
            if negative:
                warnings.append(f"`{standard_field}` has {negative} negative value(s).")

    return issues, warnings


def _apply_mappings(frame: pd.DataFrame, mappings: dict[str, str]) -> pd.DataFrame:
    data = pd.DataFrame(index=frame.index)
    for standard_field, source_field in mappings.items():
        if source_field in frame.columns:
            data[standard_field] = frame[source_field]
    return data


def _prepare_orders(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.copy()
    clean["date"] = parse_date_series(clean["date"])
    clean["category_name"] = clean["category_name"].astype("string").str.strip()
    clean["category_key"] = clean["category_id"].where(clean["category_id"].notna(), clean["category_name"]).astype("string")
    clean["gmv"] = pd.to_numeric(clean["gmv"], errors="coerce").fillna(0.0)
    clean["discount_amount"] = pd.to_numeric(clean["discount_amount"], errors="coerce").fillna(0.0)
    clean["quantity"] = pd.to_numeric(clean["quantity"], errors="coerce").fillna(0.0)
    clean["order_count"] = pd.to_numeric(clean["order_count"], errors="coerce").fillna(1.0)
    return clean.dropna(subset=["date", "category_key"])


def _prepare_exposure(frame: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    clean = frame.copy()
    clean["date"] = parse_date_series(clean["date"])
    if "category_name" not in clean.columns:
        clean["category_name"] = pd.NA
    if "category_id" not in clean.columns:
        clean["category_id"] = pd.NA
    clean = _backfill_exposure_categories(clean, orders)
    clean["category_name"] = clean["category_name"].astype("string").str.strip()
    clean["category_key"] = clean["category_id"].where(clean["category_id"].notna(), clean["category_name"]).astype("string")
    clean["view_uv"] = pd.to_numeric(clean["view_uv"], errors="coerce").fillna(0.0)
    clean["buy_uv"] = pd.to_numeric(clean["buy_uv"], errors="coerce").fillna(0.0)
    clean["exposure_pv"] = pd.to_numeric(clean["exposure_pv"], errors="coerce").fillna(0.0)
    return clean.dropna(subset=["date", "category_key"])


def _prepare_activity(frame: pd.DataFrame, config: PanelConfig) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            {
                "date": pd.Series(dtype="datetime64[ns]"),
                "category_key": pd.Series(dtype="string"),
                "activity_name": pd.Series(dtype="object"),
                "is_activity": pd.Series(dtype="bool"),
                "is_payday": pd.Series(dtype="bool"),
            }
        )

    records: list[dict[str, Any]] = []
    has_range = "start_date" in frame.columns and "end_date" in frame.columns
    for _, row in frame.iterrows():
        raw_activity = row.get("activity_name")
        activity_name = str(raw_activity).strip() if pd.notna(raw_activity) else ""
        payday = _to_bool(row.get("payday"))
        is_activity = bool(activity_name and activity_name.lower() not in {"0", "none", "nan", "false", "no"}) or payday
        category_name = row.get("category_name") if "category_name" in frame.columns else pd.NA
        category_id = row.get("category_id") if "category_id" in frame.columns else pd.NA
        category_key = category_id if pd.notna(category_id) else category_name
        category_key = str(category_key).strip() if pd.notna(category_key) and str(category_key).strip() else pd.NA

        dates: list[pd.Timestamp] = []
        if "date" in frame.columns:
            parsed = parse_date_series([row.get("date")]).iloc[0]
            if pd.notna(parsed):
                dates.append(parsed)
        elif has_range:
            start_date = parse_date_series([row.get("start_date")]).iloc[0]
            end_date = parse_date_series([row.get("end_date")]).iloc[0]
            if pd.notna(start_date) and pd.notna(end_date):
                dates.extend(pd.date_range(start_date, end_date, freq="D").tolist())

        for date in dates:
            records.append(
                {
                    "date": date,
                    "category_key": category_key,
                    "activity_name": activity_name or "activity",
                    "is_activity": is_activity,
                    "is_payday": payday or date.day == config.payday_day,
                }
            )

    if not records:
        return pd.DataFrame(columns=["date", "category_key", "activity_name", "is_activity", "is_payday"])
    activity = pd.DataFrame(records)
    return (
        activity.groupby(["category_key", "date"], dropna=False, as_index=False)
        .agg(
            activity_name=("activity_name", lambda values: next((value for value in values if value), "activity")),
            is_activity=("is_activity", "max"),
            is_payday=("is_payday", "max"),
        )
    )


def _aggregate_orders(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby(["category_key", "date"], as_index=False)
        .agg(
            gmv=("gmv", "sum"),
            order_count=("order_count", "sum"),
            quantity=("quantity", "sum"),
            discount_amount=("discount_amount", "sum"),
            user_count=("user_id", lambda values: int(pd.Series(values).dropna().nunique())),
        )
    )
    return grouped


def _aggregate_exposure(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby(["category_key", "date"], as_index=False)
        .agg(view_uv=("view_uv", "sum"), buy_uv=("buy_uv", "sum"), exposure_pv=("exposure_pv", "sum"))
    )


def _merge_activity(panel: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    if activity.empty:
        panel["activity_name"] = "non_activity"
        panel["is_activity"] = False
        panel["is_payday"] = False
        return panel

    categorized = activity[activity["category_key"].notna()].copy()
    global_activity = activity[activity["category_key"].isna()].copy()

    if not categorized.empty:
        panel = panel.merge(categorized, on=["category_key", "date"], how="left")
    else:
        panel["activity_name"] = pd.NA
        panel["is_activity"] = pd.NA
        panel["is_payday"] = pd.NA

    if not global_activity.empty:
        global_activity = (
            global_activity.groupby("date", as_index=False)
            .agg(
                global_activity_name=("activity_name", lambda values: next((value for value in values if value), "activity")),
                global_is_activity=("is_activity", "max"),
                global_is_payday=("is_payday", "max"),
            )
        )
        panel = panel.merge(global_activity, on="date", how="left")
        panel["activity_name"] = panel["activity_name"].fillna(panel["global_activity_name"])
        panel["is_activity"] = panel["is_activity"].eq(True) | panel["global_is_activity"].eq(True)
        panel["is_payday"] = panel["is_payday"].eq(True) | panel["global_is_payday"].eq(True)
        panel = panel.drop(columns=["global_activity_name", "global_is_activity", "global_is_payday"])

    panel["activity_name"] = panel["activity_name"].fillna("non_activity")
    panel["is_activity"] = panel["is_activity"].eq(True)
    panel["is_payday"] = panel["is_payday"].eq(True)
    return panel


def _primary_date_bounds(*frames: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    dates = [frame["date"].dropna() for frame in frames if "date" in frame.columns and not frame["date"].dropna().empty]
    if not dates:
        raise ValueError("No valid dates found in order or exposure source data.")
    combined = pd.concat(dates)
    return combined.min(), combined.max()


def _build_payday_phase(days_to_payday: int) -> str:
    if days_to_payday == 0:
        return "payday"
    if -3 <= days_to_payday < 0:
        return "pre_payday"
    if 0 < days_to_payday <= 3:
        return "post_payday"
    return "normal"


def _build_window_dates(activity_dates: pd.Series, before: int, after: int) -> set[pd.Timestamp]:
    dates = parse_date_series(activity_dates.dropna().unique())
    window_dates: set[pd.Timestamp] = set()
    for current in dates:
        for offset in range(-before, after + 1):
            shifted = current + pd.Timedelta(days=offset)
            if shifted != current:
                window_dates.add(shifted)
    return window_dates


def _backfill_exposure_categories(exposure_df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    if "sku_id" not in exposure_df.columns or "sku_id" not in orders_df.columns:
        return exposure_df
    sku_map = (
        orders_df[["sku_id", "category_key", "category_name"]]
        .dropna(subset=["sku_id", "category_name"])
        .drop_duplicates(subset=["sku_id"])
        .rename(columns={"category_key": "orders_category_key", "category_name": "orders_category_name"})
    )
    if sku_map.empty:
        return exposure_df
    enriched = exposure_df.merge(sku_map, on="sku_id", how="left")
    enriched["category_name"] = enriched["category_name"].fillna(enriched["orders_category_name"])
    enriched["category_id"] = enriched["category_id"].fillna(enriched["orders_category_key"])
    return enriched.drop(columns=["orders_category_key", "orders_category_name"], errors="ignore")


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "payday"}
