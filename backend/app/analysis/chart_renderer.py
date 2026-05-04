import json
from pathlib import Path
from app.tools.schemas import ToolResult


def render_chart(workspace_path: str, chart_type: str) -> ToolResult:
    """
    图表渲染（生成 ASCII/JSON 图表数据用于前端渲染）

    输入: .analysis/ 下的各种 result JSON
    输出: artifacts/charts/ 下的图表数据
    """
    workspace_path = Path(workspace_path)
    chart_dir = workspace_path / "artifacts" / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    if chart_type == "gmv_trend":
        return _render_gmv_trend(workspace_path, chart_dir)
    elif chart_type == "localgap":
        return _render_localgap(workspace_path, chart_dir)
    elif chart_type == "category_concentration":
        return _render_category_concentration(workspace_path, chart_dir)
    elif chart_type == "activity_comparison":
        return _render_activity_comparison(workspace_path, chart_dir)
    else:
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "UNKNOWN_CHART_TYPE", "message": f"Unknown chart type: {chart_type}"},
        )


def _render_gmv_trend(workspace_path: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace_path / ".analysis" / "diagnostics_result.json"
    if not diagnostics_path.exists():
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NO_DATA", "message": "请先运行 diagnostics 分析"},
        )

    data = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    trend = data.get("gmv_trend", [])

    chart_data = {
        "type": "line",
        "title": "GMV 趋势",
        "x": [d["date"] for d in trend],
        "y": [d["gmv"] for d in trend],
        "x_label": "日期",
        "y_label": "GMV",
    }

    output_path = chart_dir / "gmv_trend.json"
    output_path.write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="chart.render",
        summary="GMV 趋势图渲染完成",
        artifacts=[{"type": "chart", "title": "gmv_trend.json", "path": str(output_path.relative_to(workspace_path))}],
    )


def _render_localgap(workspace_path: Path, chart_dir: Path) -> ToolResult:
    localgap_path = workspace_path / ".analysis" / "localgap_result.json"
    if not localgap_path.exists():
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NO_DATA", "message": "请先运行 LocalGap 分析"},
        )

    data = json.loads(localgap_path.read_text(encoding="utf-8"))
    categories = data.get("categories", [])[:10]

    chart_data = {
        "type": "bar",
        "title": "LocalGap 分解",
        "x": [c["category"] for c in categories],
        "y": [c["local_gap"] for c in categories],
        "x_label": "品类",
        "y_label": "LocalGap",
        "segments": [
            {"key": "exposure_gap", "color": "#4CAF50"},
            {"key": "discount_gap", "color": "#2196F3"},
            {"key": "payday_gap", "color": "#FF9800"},
            {"key": "interaction", "color": "#9C27B0"},
        ],
    }

    output_path = chart_dir / "localgap.json"
    output_path.write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="chart.render",
        summary="LocalGap 图表渲染完成",
        artifacts=[{"type": "chart", "title": "localgap.json", "path": str(output_path.relative_to(workspace_path))}],
    )


def _render_category_concentration(workspace_path: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace_path / ".analysis" / "diagnostics_result.json"
    if not diagnostics_path.exists():
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NO_DATA", "message": "请先运行 diagnostics 分析"},
        )

    data = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    concentration = data.get("category_concentration", [])

    chart_data = {
        "type": "pie",
        "title": "品类集中度",
        "labels": [c["category"] for c in concentration],
        "values": [c["share"] for c in concentration],
    }

    output_path = chart_dir / "category_concentration.json"
    output_path.write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="chart.render",
        summary="品类集中度图表渲染完成",
        artifacts=[{"type": "chart", "title": "category_concentration.json", "path": str(output_path.relative_to(workspace_path))}],
    )


def _render_activity_comparison(workspace_path: Path, chart_dir: Path) -> ToolResult:
    diagnostics_path = workspace_path / ".analysis" / "diagnostics_result.json"
    if not diagnostics_path.exists():
        return ToolResult(
            ok=False,
            action="chart.render",
            summary="",
            error={"code": "NO_DATA", "message": "请先运行 diagnostics 分析"},
        )

    data = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    activity_vs_non = data.get("activity_vs_non", {})

    chart_data = {
        "type": "bar",
        "title": "活动期 vs 非活动期",
        "x": ["活动期", "非活动期"],
        "y": [activity_vs_non.get("activity_avg_gmv", 0), activity_vs_non.get("non_activity_avg_gmv", 0)],
        "x_label": "期间",
        "y_label": "平均 GMV",
    }

    output_path = chart_dir / "activity_comparison.json"
    output_path.write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        ok=True,
        action="chart.render",
        summary="活动期对比图表渲染完成",
        artifacts=[{"type": "chart", "title": "activity_comparison.json", "path": str(output_path.relative_to(workspace_path))}],
    )
