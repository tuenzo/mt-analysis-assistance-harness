from app.tools.schemas import ToolResult


def report_generate(project_id: str, payload: dict) -> ToolResult:
    fmt = payload.get("format", ["md"])
    return ToolResult(
        ok=True,
        action="report.generate",
        summary="报告生成完成（stub）",
        artifacts=[{"type": "report_source", "title": "report.md", "path": "reports/report.md"}],
        assistant_hint="报告已生成，可以查看或导出。"
    )
