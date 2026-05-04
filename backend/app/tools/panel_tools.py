from app.tools.schemas import ToolResult


def panel_build_category_day(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="panel.build_category_day",
        summary="品类×日期面板构建完成（stub）",
        artifacts=[{"type": "panel", "title": "category_day_panel.parquet", "path": "data/processed/category_day_panel.parquet"}],
        assistant_hint="面板已生成，可以开始诊断分析。"
    )
