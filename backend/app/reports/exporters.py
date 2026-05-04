from pathlib import Path
from app.tools.schemas import ToolResult


def export_to_markdown(report_path: str) -> ToolResult:
    """导出为 Markdown 格式"""
    return ToolResult(
        ok=True,
        action="report.export",
        summary="报告已导出为 Markdown",
        artifacts=[{"type": "exported_report", "format": "md", "path": report_path}],
    )


def export_to_pdf(report_path: str) -> ToolResult:
    """导出为 PDF 格式 (stub)"""
    return ToolResult(
        ok=True,
        action="report.export",
        summary="PDF 导出功能开发中",
        artifacts=[],
        assistant_hint="PDF 导出暂未支持，请使用 Markdown 格式。"
    )


def export_to_latex(report_path: str) -> ToolResult:
    """导出为 LaTeX 格式 (stub)"""
    return ToolResult(
        ok=True,
        action="report.export",
        summary="LaTeX 导出功能开发中",
        artifacts=[],
    )


def export_report(report_path: str, export_format: str) -> ToolResult:
    """统一的导出入口"""
    if export_format == "md":
        return export_to_markdown(report_path)
    elif export_format == "pdf":
        return export_to_pdf(report_path)
    elif export_format == "latex":
        return export_to_latex(report_path)
    else:
        return ToolResult(
            ok=False,
            action="report.export",
            summary="",
            error={"code": "UNSUPPORTED_FORMAT", "message": f"不支持的导出格式: {export_format}"},
        )
