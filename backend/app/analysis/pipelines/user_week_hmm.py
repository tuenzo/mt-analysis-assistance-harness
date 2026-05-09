from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analysis.pipelines.build_panel import infer_schema_from_columns, parse_date_series, standardize_orders
from app.tools.schemas import ToolResult


def build_user_week_panel(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    analysis_dir = workspace / ".analysis"
    processed_dir = workspace / "data" / "processed"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    order_path = _find_order_file(workspace)
    if order_path is None:
        result = _limited_user_week_result(project_id, ["No order_info CSV is available for user-week panel build."])
        return _write_user_week_result(workspace, result, panel=None)

    try:
        raw_orders = pd.read_csv(order_path, encoding="utf-8-sig")
        mappings = infer_schema_from_columns(raw_orders.columns.tolist(), "order_info")
        orders = standardize_orders(raw_orders, mappings)
    except Exception as exc:
        result = _limited_user_week_result(project_id, [f"Order CSV could not be parsed: {exc}"])
        return _write_user_week_result(workspace, result, panel=None)

    warnings = _user_week_validation_warnings(orders, mappings)
    if warnings:
        result = _limited_user_week_result(project_id, warnings, source_path=str(order_path.relative_to(workspace)))
        return _write_user_week_result(workspace, result, panel=None)

    panel = _build_user_week_frame(orders)
    result = {
        "method": "user_week_panel",
        "method_status": "implemented" if not panel.empty else "limited",
        "status": "completed" if not panel.empty else "limited",
        "project_id": project_id,
        "source_path": str(order_path.relative_to(workspace)),
        "grain": "user_id x week_start",
        "summary": {
            "row_count": int(len(panel)),
            "user_count": int(panel["user_id"].nunique()) if not panel.empty else 0,
            "week_count": int(panel["week_start"].nunique()) if not panel.empty else 0,
            "total_gmv": round(float(panel["gmv"].sum()), 2) if not panel.empty else 0.0,
        },
        "required_fields": ["user_id", "date", "gmv"],
        "optional_fields": ["category_name", "discount_amount", "order_count", "quantity"],
        "warnings": [],
        "interpretation_rules": [
            "User-week output is an interface artifact for retention/state-path analysis.",
            "Do not infer user-level causal effects from aggregate category-day modules.",
        ],
        "evidence_artifacts": [str(order_path.relative_to(workspace))],
    }
    return _write_user_week_result(workspace, result, panel=panel)


def run_hmm_state_path(project_id: str, workspace_path: str) -> ToolResult:
    workspace = Path(workspace_path)
    panel_path = workspace / "data" / "processed" / "user_week_panel.csv"
    analysis_dir = workspace / ".analysis"
    table_dir = workspace / "artifacts" / "tables"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    if not panel_path.exists():
        result = _limited_hmm_result(
            project_id,
            ["User-week panel is missing. Run `panel.build_user_week` before HMM state-path analysis."],
        )
        return _write_hmm_result(workspace, result, paths=[])

    try:
        panel = pd.read_csv(panel_path)
    except Exception as exc:
        result = _limited_hmm_result(project_id, [f"User-week panel could not be parsed: {exc}"])
        return _write_hmm_result(workspace, result, paths=[])

    prepared = _prepare_user_week_panel(panel)
    warnings = _hmm_validation_warnings(prepared)
    if warnings:
        result = _limited_hmm_result(project_id, warnings, row_count=int(len(prepared)))
        return _write_hmm_result(workspace, result, paths=[])

    paths = _build_state_paths(prepared)
    transitions = _transition_summary(paths)
    states = _state_summary(paths)
    result = {
        "method": "hmm_state_path_interface",
        "method_status": "limited",
        "status": "completed",
        "project_id": project_id,
        "state_model": "quantile_proxy_pending_hmm_dependency",
        "grain": "user_id x week_start",
        "state_count": 3,
        "states": states,
        "transitions": transitions,
        "sample": {
            "row_count": int(len(prepared)),
            "user_count": int(prepared["user_id"].nunique()),
            "week_count": int(prepared["week_start"].nunique()),
        },
        "warnings": [
            "HMM dependency is not enabled yet; state paths use deterministic quantile states as an interface contract."
        ],
        "interpretation_rules": [
            "Treat this output as a segmentation interface until a probabilistic HMM backend is enabled.",
            "Do not integrate HMM claims into the standard report unless the standard pipeline explicitly runs this module.",
        ],
        "evidence_artifacts": ["data/processed/user_week_panel.csv"],
    }
    return _write_hmm_result(workspace, result, paths=paths)


def _find_order_file(workspace: Path) -> Path | None:
    raw_dir = workspace / "data" / "raw"
    if not raw_dir.exists():
        return None
    candidates = sorted(raw_dir.glob("*.csv"), key=lambda path: path.name.lower())
    for candidate in candidates:
        lower = candidate.name.lower()
        if "order_info" in lower or "orders" in lower or "order" in lower:
            return candidate
    return None


def _user_week_validation_warnings(orders: pd.DataFrame, mappings: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    if "user_id" not in mappings:
        warnings.append("Missing `user_id`; user-week panel cannot be built from aggregate orders.")
    if "date" not in mappings:
        warnings.append("Missing `date`; user-week panel requires a weekly time index.")
    if "gmv" not in mappings:
        warnings.append("Missing `gmv`; user-week panel requires a value metric.")
    if "user_id" in orders.columns and orders["user_id"].isna().all():
        warnings.append("All `user_id` values are missing.")
    return warnings


def _build_user_week_frame(orders: pd.DataFrame) -> pd.DataFrame:
    prepared = orders.copy()
    prepared["date"] = parse_date_series(prepared["date"])
    prepared = prepared.dropna(subset=["date", "user_id"]).copy()
    prepared["user_id"] = prepared["user_id"].astype(str)
    prepared["week_start"] = prepared["date"] - pd.to_timedelta(prepared["date"].dt.weekday, unit="D")
    for column in ["gmv", "discount_amount", "order_count", "quantity"]:
        if column not in prepared.columns:
            prepared[column] = 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    if "category_name" not in prepared.columns:
        prepared["category_name"] = "unknown"
    grouped = (
        prepared.groupby(["user_id", "week_start"], as_index=False)
        .agg(
            gmv=("gmv", "sum"),
            discount_amount=("discount_amount", "sum"),
            order_count=("order_count", "sum"),
            quantity=("quantity", "sum"),
            active_days=("date", "nunique"),
            category_count=("category_name", "nunique"),
        )
        .sort_values(["user_id", "week_start"])
    )
    grouped["aov"] = np.where(grouped["order_count"] > 0, grouped["gmv"] / grouped["order_count"], np.nan)
    grouped["discount_rate"] = np.where(grouped["gmv"] > 0, grouped["discount_amount"] / grouped["gmv"], 0.0)
    grouped["week_start"] = grouped["week_start"].dt.strftime("%Y-%m-%d")
    return grouped


def _limited_user_week_result(project_id: str, warnings: list[str], source_path: str | None = None) -> dict[str, Any]:
    return {
        "method": "user_week_panel",
        "method_status": "limited",
        "status": "limited",
        "project_id": project_id,
        "source_path": source_path,
        "grain": "user_id x week_start",
        "summary": {"row_count": 0, "user_count": 0, "week_count": 0, "total_gmv": 0.0},
        "required_fields": ["user_id", "date", "gmv"],
        "optional_fields": ["category_name", "discount_amount", "order_count", "quantity"],
        "warnings": warnings,
        "interpretation_rules": [
            "This is a limited interface artifact; collect user_id-level orders to enable user-week state analysis."
        ],
        "evidence_artifacts": [source_path] if source_path else [],
    }


def _write_user_week_result(workspace: Path, result: dict[str, Any], panel: pd.DataFrame | None) -> ToolResult:
    analysis_dir = workspace / ".analysis"
    processed_dir = workspace / "data" / "processed"
    result_path = analysis_dir / "user_week_panel_result.json"
    csv_path = processed_dir / "user_week_panel.csv"
    json_path = processed_dir / "user_week_panel.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = [
        {
            "type": "panel_result",
            "title": "user_week_panel_result.json",
            "path": str(result_path.relative_to(workspace)),
            "method_status": result["method_status"],
            "warnings": result["warnings"],
        }
    ]
    if panel is not None and not panel.empty:
        panel.to_csv(csv_path, index=False, encoding="utf-8-sig")
        panel.to_json(json_path, orient="records", force_ascii=False, indent=2)
        artifacts.extend(
            [
                {"type": "panel_data", "title": "user_week_panel.csv", "path": str(csv_path.relative_to(workspace)), "rows": int(len(panel))},
                {"type": "panel_data", "title": "user_week_panel.json", "path": str(json_path.relative_to(workspace)), "rows": int(len(panel))},
            ]
        )
    return ToolResult(
        ok=True,
        action="panel.build_user_week",
        summary=f"User-week panel status={result['method_status']}, rows={result['summary']['row_count']}.",
        artifacts=artifacts,
        assistant_hint="User-week panel is an optional interface for HMM/state-path analysis; it is not part of the standard pipeline yet.",
    )


def _prepare_user_week_panel(panel: pd.DataFrame) -> pd.DataFrame:
    prepared = panel.copy()
    prepared["week_start"] = pd.to_datetime(prepared.get("week_start"), errors="coerce")
    prepared = prepared.dropna(subset=["week_start", "user_id"]).copy()
    prepared["user_id"] = prepared["user_id"].astype(str)
    for column in ["gmv", "order_count", "discount_rate", "active_days", "category_count"]:
        if column not in prepared.columns:
            prepared[column] = 0.0
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0.0)
    return prepared.sort_values(["user_id", "week_start"])


def _hmm_validation_warnings(panel: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if panel.empty:
        warnings.append("User-week panel has no usable rows.")
    if panel["user_id"].nunique() < 2:
        warnings.append("HMM state paths require at least two users for a useful transition view.")
    if panel["week_start"].nunique() < 3:
        warnings.append("HMM state paths require at least three weeks of history.")
    return warnings


def _build_state_paths(panel: pd.DataFrame) -> list[dict[str, Any]]:
    scores = (
        np.log1p(panel["gmv"].clip(lower=0.0))
        + 0.35 * np.log1p(panel["order_count"].clip(lower=0.0))
        + 0.15 * panel["active_days"].clip(lower=0.0)
    )
    low, high = scores.quantile([1 / 3, 2 / 3]).tolist()
    labels = np.where(scores <= low, "dormant_or_light", np.where(scores <= high, "active", "core"))
    output = panel.copy()
    output["state"] = labels
    output["state_score"] = scores
    rows = []
    for row in output.itertuples(index=False):
        rows.append(
            {
                "user_id": str(row.user_id),
                "week_start": row.week_start.date().isoformat(),
                "state": str(row.state),
                "state_score": round(float(row.state_score), 6),
                "gmv": round(float(row.gmv), 2),
                "order_count": round(float(row.order_count), 2),
                "discount_rate": round(float(row.discount_rate), 6),
            }
        )
    return rows


def _state_summary(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(paths)
    if frame.empty:
        return []
    grouped = frame.groupby("state", as_index=False).agg(rows=("state", "size"), avg_gmv=("gmv", "mean"))
    return [
        {"state": str(row.state), "rows": int(row.rows), "avg_gmv": round(float(row.avg_gmv), 2)}
        for row in grouped.itertuples(index=False)
    ]


def _transition_summary(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame = pd.DataFrame(paths)
    if frame.empty:
        return []
    transitions: dict[tuple[str, str], int] = {}
    for _, group in frame.sort_values(["user_id", "week_start"]).groupby("user_id"):
        states = group["state"].tolist()
        for previous, current in zip(states, states[1:]):
            transitions[(str(previous), str(current))] = transitions.get((str(previous), str(current)), 0) + 1
    total = sum(transitions.values()) or 1
    return [
        {"from_state": src, "to_state": dst, "count": count, "share": round(count / total, 4)}
        for (src, dst), count in sorted(transitions.items(), key=lambda item: (-item[1], item[0]))
    ]


def _limited_hmm_result(project_id: str, warnings: list[str], row_count: int = 0) -> dict[str, Any]:
    return {
        "method": "hmm_state_path_interface",
        "method_status": "limited",
        "status": "limited",
        "project_id": project_id,
        "state_model": "unavailable",
        "grain": "user_id x week_start",
        "state_count": 0,
        "states": [],
        "transitions": [],
        "sample": {"row_count": row_count, "user_count": 0, "week_count": 0},
        "warnings": warnings,
        "interpretation_rules": [
            "This output reserves the HMM artifact contract but does not provide state-path evidence yet."
        ],
        "evidence_artifacts": [],
    }


def _write_hmm_result(workspace: Path, result: dict[str, Any], paths: list[dict[str, Any]]) -> ToolResult:
    result_path = workspace / ".analysis" / "hmm_state_path_result.json"
    path_table = workspace / "artifacts" / "tables" / "hmm_state_paths.csv"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = [
        {
            "type": "model_output",
            "title": "hmm_state_path_result.json",
            "path": str(result_path.relative_to(workspace)),
            "method_status": result["method_status"],
            "status": result["status"],
            "warnings": result["warnings"],
        }
    ]
    if paths:
        with path_table.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["user_id", "week_start", "state", "state_score", "gmv", "order_count", "discount_rate"])
            writer.writeheader()
            writer.writerows(paths)
        artifacts.append({"type": "table", "title": "hmm_state_paths.csv", "path": str(path_table.relative_to(workspace)), "rows": len(paths)})
    return ToolResult(
        ok=True,
        action="analysis.run_hmm_state_path",
        summary=f"HMM state-path interface status={result['method_status']}, rows={result['sample']['row_count']}.",
        artifacts=artifacts,
        assistant_hint="HMM state paths are optional reference-skill outputs and are not part of the standard pipeline yet.",
    )
