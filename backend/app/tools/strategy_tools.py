from typing import Any, Callable

from app.strategy_lab.service import StrategyLabError, StrategyLabService
from app.tools.schemas import ToolResult


def strategy_design_blueprint(project_id: str, payload: dict) -> ToolResult:
    return _run_strategy_action(
        project_id=project_id,
        payload=payload,
        action="strategy.design_blueprint",
        artifact_type="strategy_blueprint",
        create_func=StrategyLabService().create_blueprint,
        summary_template="Created strategy blueprint {id} ({version}).",
        assistant_hint="Use strategy.design_flow next to turn this blueprint into an ordered analysis flow.",
    )


def strategy_design_flow(project_id: str, payload: dict) -> ToolResult:
    return _run_strategy_action(
        project_id=project_id,
        payload=payload,
        action="strategy.design_flow",
        artifact_type="analysis_flow",
        create_func=StrategyLabService().create_flow,
        summary_template="Created analysis flow {id} ({version}) with {stage_count} stage(s).",
        assistant_hint="Review the flow stages. For any proposed-only stage, use strategy.propose_backend_change.",
    )


def strategy_propose_backend_change(project_id: str, payload: dict) -> ToolResult:
    return _run_strategy_action(
        project_id=project_id,
        payload=payload,
        action="strategy.propose_backend_change",
        artifact_type="backend_change_proposal",
        create_func=StrategyLabService().create_backend_change,
        summary_template="Created backend change proposal {id} ({version}).",
        assistant_hint=(
            "This is a proposal artifact only. It does not modify backend source code until a human "
            "or Codex implements it on an isolated branch."
        ),
    )


def _run_strategy_action(
    *,
    project_id: str,
    payload: dict,
    action: str,
    artifact_type: str,
    create_func: Callable[[str, dict[str, Any]], dict[str, Any]],
    summary_template: str,
    assistant_hint: str,
) -> ToolResult:
    try:
        result = create_func(project_id, payload or {})
    except StrategyLabError as exc:
        return ToolResult(
            ok=False,
            action=action,
            summary="Strategy lab action failed.",
            error={"code": exc.code, "message": str(exc), "details": exc.details},
            assistant_hint="Revise the strategy payload and retry the same strategy action.",
        )

    artifact = {
        "type": artifact_type,
        "title": result["title"],
        "path": result["path"],
        "id": result["id"],
        "version": result["version"],
        "status": result["status"],
        "created_at": result["created_at"],
    }
    if "stage_count" in result:
        artifact["stage_count"] = result["stage_count"]

    return ToolResult(
        ok=True,
        action=action,
        summary=summary_template.format(**result),
        artifacts=[artifact],
        state_patch={"strategy_lab": {"latest": artifact}},
        assistant_hint=assistant_hint,
    )
