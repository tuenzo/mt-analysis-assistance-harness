import json
import uuid
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.artifacts.service import persist_tool_result_artifacts
from app.projects.models import Job, Project, ToolCall
from app.tools.analysis_tools import (
    analysis_run_diagnostics,
    analysis_run_conversion_diagnostics,
    analysis_run_gps_uplift,
    analysis_run_hmm_state_path,
    analysis_run_localgap,
    analysis_run_mechanism_regression,
    analysis_run_psm_did,
)
from app.tools.chart_tools import chart_render, chart_render_dashboard
from app.tools.data_tools import data_validate
from app.tools.panel_tools import panel_build_category_day, panel_build_user_week
from app.tools.quality_tools import quality_audit_lineage, quality_score_reference_alignment
from app.tools.report_tools import report_generate
from app.tools.result_tools import result_get_latest
from app.tools.schemas import ToolResult


StepFunc = Callable[[str, dict], ToolResult]

BLOCKING_PIPELINE_ACTIONS = {"quality.audit_lineage", "data.validate", "panel.build_category_day"}


def _pipeline_lineage_gate(project_id: str, payload: dict) -> ToolResult:
    result = quality_audit_lineage(project_id, payload)
    audit = {}
    for artifact in result.artifacts or []:
        if artifact.get("type") == "lineage_audit" and isinstance(artifact.get("data"), dict):
            audit = artifact["data"]
            break
    if audit.get("overall_status") == "pass":
        return result

    issues = audit.get("issues", [])
    return ToolResult(
        ok=False,
        action="quality.audit_lineage",
        summary=f"Lineage gate failed: {len(issues)} blocking issue(s).",
        artifacts=result.artifacts,
        error={
            "code": "LINEAGE_GATE_FAILED",
            "message": "Project lineage, source roles, or anti-demo gates failed before full pipeline execution.",
            "details": {"issues": issues, "cap_reasons": audit.get("cap_reasons", [])},
        },
        assistant_hint="Explain the failed lineage gate and ask for corrected real source files before continuing.",
    )


PIPELINE_STEPS: list[tuple[str, str, StepFunc, dict]] = [
    ("Lineage audit", "quality.audit_lineage", _pipeline_lineage_gate, {}),
    ("Data validation", "data.validate", data_validate, {}),
    ("Panel build", "panel.build_category_day", panel_build_category_day, {}),
    ("User-week panel", "panel.build_user_week", panel_build_user_week, {}),
    ("HMM state path", "analysis.run_hmm_state_path", analysis_run_hmm_state_path, {}),
    ("Diagnostics", "analysis.run_diagnostics", analysis_run_diagnostics, {}),
    ("PSM-DID", "analysis.run_psm_did", analysis_run_psm_did, {}),
    ("LocalGap", "analysis.run_localgap", analysis_run_localgap, {}),
    ("Mechanism regression", "analysis.run_mechanism_regression", analysis_run_mechanism_regression, {}),
    ("Conversion diagnostics", "analysis.run_conversion_diagnostics", analysis_run_conversion_diagnostics, {}),
    ("GPS uplift", "analysis.run_gps_uplift", analysis_run_gps_uplift, {}),
    ("GMV trend chart", "chart.render", chart_render, {"type": "gmv_trend"}),
    ("LocalGap chart", "chart.render", chart_render, {"type": "localgap"}),
    ("Dashboard PNG charts", "chart.render_dashboard", chart_render_dashboard, {"charts": "all"}),
    ("Latest result", "result.get_latest", result_get_latest, {}),
    ("Reference alignment score", "quality.score_reference_alignment", quality_score_reference_alignment, {}),
    ("Report generation", "report.generate", report_generate, {"format": "md"}),
]


def run_approved_full_pipeline(
    db: Session,
    *,
    project_id: str,
    session_id: str,
    turn_id: str,
    tool_call: ToolCall | None,
    payload: dict,
) -> tuple[ToolResult, list[dict]]:
    now = datetime.now().isoformat()
    job = Job(
        id=f"job_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        session_id=session_id,
        turn_id=turn_id,
        tool_call_id=tool_call.id if tool_call else None,
        action="analysis.run_full_pipeline",
        status="running",
        progress=0,
        input_json=json.dumps(payload or {}, ensure_ascii=False),
        started_at=now,
        created_at=now,
    )
    db.add(job)
    if tool_call:
        tool_call.status = "running"
    db.commit()

    events: list[dict] = [
        {
            "type": "job_started",
            "turn_id": turn_id,
            "job_id": job.id,
            "action": job.action,
            "message": "Starting approved analysis pipeline.",
        }
    ]

    step_results: list[dict] = []
    all_artifacts: list[dict] = []
    all_ok = True

    for index, (label, action, func, step_payload) in enumerate(PIPELINE_STEPS, start=1):
        progress_before = round((index - 1) / len(PIPELINE_STEPS), 4)
        events.append(
            {
                "type": "job_progress",
                "turn_id": turn_id,
                "job_id": job.id,
                "progress": progress_before,
                "message": f"Running {label}",
            }
        )
        events.append(
            {
                "type": "tool_call_started",
                "turn_id": turn_id,
                "tool": "business_analysis",
                "action": action,
                "payload": step_payload,
                "sdk_executed": True,
            }
        )

        try:
            result = func(project_id, step_payload)
        except Exception as exc:
            result = ToolResult(
                ok=False,
                action=action,
                summary=f"{label} failed",
                error={"code": "PIPELINE_STEP_ERROR", "message": str(exc), "details": {}},
            )

        step_results.append({"action": action, "ok": result.ok, "summary": result.summary})
        all_artifacts.extend(result.artifacts or [])
        all_ok = all_ok and result.ok

        artifact_events = persist_tool_result_artifacts(
            db,
            project_id=project_id,
            job_id=job.id,
            tool_call_id=tool_call.id if tool_call else None,
            result=result,
        )
        events.extend(
            {
                "type": "artifact_created",
                "turn_id": turn_id,
                "artifact_id": artifact.id,
                "name": artifact.title,
                "path": artifact.path,
            }
            for artifact in artifact_events
        )

        events.append(
            {
                "type": "tool_call_finished" if result.ok else "tool_call_failed",
                "turn_id": turn_id,
                "tool": "business_analysis",
                "action": action,
                "ok": result.ok,
                "summary": result.summary,
                "sdk_executed": True,
            }
        )

        job.progress = round(index / len(PIPELINE_STEPS), 4)
        db.commit()
        events.append(
            {
                "type": "job_progress",
                "turn_id": turn_id,
                "job_id": job.id,
                "progress": job.progress,
                "message": f"Finished {label}",
            }
        )

        if not result.ok and action in BLOCKING_PIPELINE_ACTIONS:
            events.append(
                {
                    "type": "job_progress",
                    "turn_id": turn_id,
                    "job_id": job.id,
                    "progress": job.progress,
                    "message": f"Stopping pipeline after blocking failure in {label}.",
                }
            )
            break

    finished_at = datetime.now().isoformat()
    job.status = "succeeded" if all_ok else "failed"
    job.progress = 1
    job.finished_at = finished_at
    job.output_json = json.dumps({"steps": step_results}, ensure_ascii=False)
    if not all_ok:
        job.error_message = "One or more pipeline steps failed."

    project = db.query(Project).filter(Project.id == project_id).first()
    if project and all_ok:
        project.current_stage = "report_ready"
        project.status = "report_ready"
        project.updated_at = finished_at

    summary = (
        "全流程已完成：数据校验、面板构建、诊断分析、因果方向检查、图表和报告均已生成，可以查看结果看板与报告。"
        if all_ok
        else "全流程已结束，但存在失败步骤；已保存可用的阶段性产物，请查看失败步骤摘要后继续修正。"
    )
    final_result = ToolResult(
        ok=all_ok,
        action="analysis.run_full_pipeline",
        summary=summary,
        artifacts=all_artifacts,
        state_patch={"current_stage": "report_ready"} if all_ok else {},
        assistant_hint="请打开结果看板或报告页查看已生成的产物。",
    )
    if tool_call:
        tool_call.status = "succeeded" if all_ok else "failed"
        tool_call.result_json = json.dumps(final_result.model_dump(), ensure_ascii=False)
        tool_call.completed_at = finished_at
        tool_call.error_message = None if all_ok else job.error_message

    db.commit()

    events.append(
        {
            "type": "tool_call_finished" if all_ok else "tool_call_failed",
            "turn_id": turn_id,
            "tool": "business_analysis",
            "action": "analysis.run_full_pipeline",
            "ok": all_ok,
            "summary": summary,
            "tool_call_id": tool_call.id if tool_call else None,
            "sdk_executed": True,
        }
    )
    events.append(
        {
            "type": "job_finished",
            "turn_id": turn_id,
            "job_id": job.id,
            "ok": all_ok,
            "message": summary,
        }
    )
    events.append({"type": "final_answer", "turn_id": turn_id, "message": summary})
    return final_result, events
