from collections.abc import Iterable
from pathlib import Path


BUSINESS_ANALYSIS_SKILL_NAME = "business-analysis"
DEFAULT_PROJECT_SKILLS = [BUSINESS_ANALYSIS_SKILL_NAME]

BUSINESS_ANALYSIS_SKILL_BODY = """---
name: business-analysis
description: Use the controlled business_analysis gateway for project state, data intake, validation, panel building, diagnostics, causal analysis, reports, and memory candidates.
---

# Business Analysis Harness

You are running inside the Business Analysis Companion workspace.

Use natural language for discussion and clarification. When you need project state,
data files, analysis outputs, artifacts, reports, or memory candidates, call exactly
one custom gateway tool:

business_analysis(project_id, action, payload, reason)

Do not invent project identifiers. Use the exact project_id from the request context.
Do not read source data directly from disk for business facts. Use backend workspace
context and business_analysis tool results as the source of truth.

For data-load requests, run this loop:

project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate

Data loading is complete only after data.validate succeeds. If validation fails,
summarize the partial state, list the blocking files or schema issues, and ask for
the smallest concrete correction.

For analysis requests, prefer this progression:

panel.build_category_day -> analysis.run_diagnostics -> analysis.run_psm_did ->
analysis.run_localgap -> analysis.run_gps_uplift -> result.get_latest

For report requests, inspect latest results or artifacts before calling report.generate.
When reading a specific artifact, call artifact.read with payload {"path": ".analysis/<file>.json"}.
Default business-facing summaries and reports to Chinese unless the user asks for
another language.

For strategy-design requests, you may lead the analysis strategy instead of only
running the fixed pipeline. Use these actions through the same gateway:

- strategy.design_blueprint: create objective, decision questions, assumptions,
  constraints, candidate methods, and success criteria.
- strategy.design_flow: turn the blueprint into ordered stages. Each stage must
  include either an existing backend action or a proposed_backend_change.
- strategy.propose_backend_change: describe required backend framework changes
  as a proposal artifact only.

Do not claim you edited backend source code through strategy actions. Strategy
lab outputs are isolated review artifacts under .analysis/strategy_lab/.
"""


def ensure_project_skill_files(workspace_path: Path, skill_names: Iterable[str] | str | None) -> list[str]:
    """Create project-local Claude skill files required by the agent SDK request."""

    normalized = normalize_skill_names(skill_names)
    if normalized == "all":
        normalized = DEFAULT_PROJECT_SKILLS

    installed: list[str] = []
    for skill_name in normalized:
        if skill_name != BUSINESS_ANALYSIS_SKILL_NAME:
            continue
        skill_path = Path(workspace_path) / ".claude" / "skills" / skill_name / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        if not skill_path.exists() or skill_path.read_text(encoding="utf-8") != BUSINESS_ANALYSIS_SKILL_BODY:
            skill_path.write_text(BUSINESS_ANALYSIS_SKILL_BODY, encoding="utf-8")
        installed.append(skill_name)
    return installed


def normalize_skill_names(skill_names: Iterable[str] | str | None) -> list[str] | str:
    if skill_names is None:
        return DEFAULT_PROJECT_SKILLS.copy()
    if isinstance(skill_names, str):
        value = skill_names.strip()
        if not value:
            return []
        if value.lower() == "all":
            return "all"
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in skill_names if str(item).strip()]
