import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from app.tools.schemas import ToolResult


@dataclass
class ValidationResult:
    ok: bool
    issues: list[str]
    warnings: list[str]
    file_info: dict


def validate_files(workspace_path: Path) -> ValidationResult:
    """检查 order_info, exposure_info, activity_timeline 三个 CSV 文件"""
    issues = []
    warnings = []

    required_roles = {
        "order_info": ["category", "gmv", "date"],
        "exposure_info": ["category", "exposure", "date"],
        "activity_timeline": ["category", "date", "payday"],
    }

    workspace_path = Path(workspace_path)
    data_dir = workspace_path / "data" / "raw"

    file_info = {}
    for role, required_fields in required_roles.items():
        matching_files = list(data_dir.glob(f"*{role}*.csv")) + list(data_dir.glob(f"*{role.replace('_', '')}*.csv"))

        if not matching_files:
            issues.append(f"缺少文件类型: {role}")
            continue

        csv_file = matching_files[0]
        file_info[role] = {"path": str(csv_file), "rows": 0, "columns": []}

        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = [h.lower().strip() for h in reader.fieldnames or []]
                file_info[role]["columns"] = headers

                missing_fields = []
                for field in required_fields:
                    if not any(field in h for h in headers):
                        missing_fields.append(field)

                if missing_fields:
                    issues.append(f"{role}: 缺少必需字段 {missing_fields}")

                row_count = 0
                for row in reader:
                    row_count += 1
                file_info[role]["rows"] = row_count

                if row_count == 0:
                    warnings.append(f"{role}: 文件为空")
                elif row_count < 100:
                    warnings.append(f"{role}: 数据量较少 ({row_count} 行)")

        except Exception as e:
            issues.append(f"{role}: 读取失败 - {str(e)}")

    ok = len(issues) == 0
    return ValidationResult(ok=ok, issues=issues, warnings=warnings, file_info=file_info)


def build_category_day_panel(project_id: str, workspace_path: str) -> ToolResult:
    """
    构建 category × day panel

    输入:
        - order_info.csv: category, date, gmv, discount, order_id, user_id
        - exposure_info.csv: category, date, exposure
        - activity_timeline.csv: category, date, payday, activity_id

    输出:
        - data/processed/category_day_panel.parquet (JSON for MVP)
        - 字段: date, category, gmv, discount, discount_rate,
                exposure, exposure_rate, order_count, user_count,
                is_payday, is_activity, is_payday_activity
    """
    workspace_path = Path(workspace_path)
    data_dir = workspace_path / "data" / "raw"
    output_dir = workspace_path / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    val_result = validate_files(workspace_path)
    if not val_result.ok:
        return ToolResult(
            ok=False,
            action="panel.build_category_day",
            summary="数据校验失败",
            error={"code": "VALIDATION_FAILED", "message": "; ".join(val_result.issues)},
        )

    order_file = None
    exposure_file = None
    activity_file = None

    for f in data_dir.glob("*.csv"):
        fname_lower = f.name.lower()
        if "order" in fname_lower:
            order_file = f
        elif "exposure" in fname_lower:
            exposure_file = f
        elif "activity" in fname_lower or "timeline" in fname_lower:
            activity_file = f

    order_data = _read_csv_by_category_date(order_file) if order_file else {}
    exposure_data = _read_csv_by_category_date(exposure_file) if exposure_file else {}
    activity_data = _read_activity(activity_file) if activity_file else {}

    all_keys = set(order_data.keys()) | set(exposure_data.keys())
    panel_rows = []

    for cat_date in all_keys:
        category, date = cat_date.split("||")
        order_row = order_data.get(cat_date, {})
        exposure_row = exposure_data.get(cat_date, {})
        activity_row = activity_data.get(cat_date, {})

        gmv = order_row.get("gmv", 0) or 0
        discount = order_row.get("discount", 0) or 0
        order_count = order_row.get("order_count", 0) or 0
        user_count = order_row.get("user_count", 0) or 0
        exposure = exposure_row.get("exposure", 0) or 0

        discount_rate = (discount / gmv * 100) if gmv > 0 else 0
        exposure_rate = (exposure / order_count * 100) if order_count > 0 else 0

        panel_rows.append({
            "date": date,
            "category": category,
            "gmv": float(gmv),
            "discount": float(discount),
            "discount_rate": round(discount_rate, 2),
            "exposure": float(exposure),
            "exposure_rate": round(exposure_rate, 2),
            "order_count": int(order_count),
            "user_count": int(user_count),
            "is_payday": activity_row.get("is_payday", False),
            "is_activity": activity_row.get("is_activity", False),
            "is_payday_activity": activity_row.get("is_payday_activity", False),
        })

    panel_rows.sort(key=lambda x: (x["date"], x["category"]))

    output_path = output_dir / "category_day_panel.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(panel_rows, f, ensure_ascii=False, indent=2)

    summary = f"Panel 构建完成: {len(panel_rows)} 行, {len(set(r['category'] for r in panel_rows))} 个品类"
    return ToolResult(
        ok=True,
        action="panel.build_category_day",
        summary=summary,
        artifacts=[{
            "type": "panel_data",
            "title": "category_day_panel.json",
            "path": str(output_path.relative_to(workspace_path)),
            "rows": len(panel_rows),
        }],
        assistant_hint="Panel 已生成，可以进行诊断分析和因果推断。"
    )


def _read_csv_by_category_date(csv_path: Path) -> dict[str, dict]:
    """按 category||date 聚合 CSV 数据"""
    result = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("category", "").strip()
            date = row.get("date", "").strip()

            if not category or not date:
                continue

            key = f"{category}||{date}"

            if key not in result:
                result[key] = {
                    "gmv": 0.0,
                    "discount": 0.0,
                    "order_count": 0,
                    "user_count": 0,
                }

            try:
                result[key]["gmv"] += float(row.get("gmv") or 0)
            except (ValueError, TypeError):
                pass

            try:
                result[key]["discount"] += float(row.get("discount") or 0)
            except (ValueError, TypeError):
                pass

            result[key]["order_count"] += 1

            user_id = row.get("user_id", "").strip()
            if user_id:
                result[key]["user_count"] += 1

    return result


def _read_activity(csv_path: Path) -> dict[str, dict]:
    """读取活动 timeline，返回 {category||date: activity_info}"""
    result = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("category", "").strip()
            date = row.get("date", "").strip()

            if not category or not date:
                continue

            key = f"{category}||{date}"

            payday_val = row.get("payday", "").strip().lower()
            activity_val = row.get("activity_id", "").strip()

            is_payday = payday_val in ("1", "true", "yes", "是")
            is_activity = activity_val not in ("", "0", "none", "无")

            result[key] = {
                "is_payday": is_payday,
                "is_activity": is_activity,
                "is_payday_activity": is_payday and is_activity,
            }

    return result
