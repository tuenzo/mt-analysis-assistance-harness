from app.tools.schemas import ToolResult


def analysis_run_diagnostics(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="analysis.run_diagnostics",
        summary="诊断分析完成（stub）",
        artifacts=[{"type": "result_summary", "title": "diagnostics_result.json"}],
        assistant_hint="诊断完成，可以查看趋势图和活动效果对比。"
    )


def analysis_run_psm_did(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="analysis.run_psm_did",
        summary="PSM-DID 分析完成（stub）",
        artifacts=[{"type": "model_output", "title": "psm_did_result.json"}],
    )


def analysis_run_localgap(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="analysis.run_localgap",
        summary="LocalGap 增量分解完成（stub）",
        artifacts=[
            {"type": "chart", "title": "localgap_total.png", "path": "artifacts/charts/localgap_total.png"},
            {"type": "model_output", "title": "localgap_result.json"},
        ],
        assistant_hint="LocalGap 分析完成，可以查看各增量来源的贡献。"
    )


def analysis_run_gps_uplift(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="analysis.run_gps_uplift",
        summary="GPS-Uplift 分析完成（stub）",
        artifacts=[
            {"type": "chart", "title": "gps_dose_response.png"},
            {"type": "model_output", "title": "uplift_result.json", "method_status": "stub"},
        ],
    )


def analysis_run_full_pipeline(project_id: str, payload: dict) -> ToolResult:
    return ToolResult(
        ok=True,
        action="analysis.run_full_pipeline",
        summary="完整分析 pipeline 执行完成（stub）",
        artifacts=[
            {"type": "panel", "title": "category_day_panel.parquet"},
            {"type": "result_summary", "title": "diagnostics_result.json"},
            {"type": "model_output", "title": "localgap_result.json"},
            {"type": "model_output", "title": "uplift_result.json", "method_status": "stub"},
        ],
        assistant_hint="完整 pipeline 已执行完成，可以查看分析结果和生成报告。"
    )
