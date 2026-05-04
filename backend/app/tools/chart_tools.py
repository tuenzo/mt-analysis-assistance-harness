from app.tools.schemas import ToolResult


def chart_render(project_id: str, payload: dict) -> ToolResult:
    chart_type = payload.get("type", "unknown")
    return ToolResult(
        ok=True,
        action="chart.render",
        summary=f"图表 {chart_type} 渲染完成（stub）",
        artifacts=[{"type": "chart", "title": f"{chart_type}.png", "path": f"artifacts/charts/{chart_type}.png"}],
    )
