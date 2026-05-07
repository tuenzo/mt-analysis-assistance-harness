from typing import Callable
from app.tools.schemas import BusinessAnalysisAction


class ToolRegistry:
    def __init__(self):
        self._tools: dict[BusinessAnalysisAction, tuple[Callable, int]] = {}

    def register(self, action: BusinessAnalysisAction, func: Callable, permission_level: int):
        self._tools[action] = (func, permission_level)

    def get_tool(self, action: BusinessAnalysisAction):
        return self._tools.get(action)

    def list_actions(self):
        return list(self._tools.keys())


# Global registry
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_all_tools(_registry)
    return _registry


def _register_all_tools(registry: ToolRegistry):
    from app.tools.project_tools import project_get_state
    from app.tools.data_tools import data_discover_source_files, data_ingest, data_validate, schema_infer, schema_apply_mapping
    from app.tools.panel_tools import panel_build_category_day
    from app.tools.analysis_tools import (
        analysis_run_diagnostics, analysis_run_psm_did, analysis_run_localgap,
        analysis_run_gps_uplift, analysis_run_full_pipeline
    )
    from app.tools.result_tools import result_get_latest, artifact_read
    from app.tools.chart_tools import chart_render, chart_render_dashboard
    from app.tools.report_tools import report_generate
    from app.tools.memory_tools import memory_propose_update
    from app.tools.strategy_tools import (
        strategy_design_blueprint,
        strategy_design_flow,
        strategy_propose_backend_change,
    )
    from app.core.permissions import PermissionLevel

    registry.register(BusinessAnalysisAction.PROJECT_GET_STATE, project_get_state, PermissionLevel.READ_STATE)
    registry.register(BusinessAnalysisAction.DATA_DISCOVER_SOURCE_FILES, data_discover_source_files, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.DATA_INGEST, data_ingest, PermissionLevel.MODIFY_WORKSPACE)
    registry.register(BusinessAnalysisAction.DATA_VALIDATE, data_validate, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.SCHEMA_INFER, schema_infer, PermissionLevel.READ_STATE)
    registry.register(BusinessAnalysisAction.SCHEMA_APPLY_MAPPING, schema_apply_mapping, PermissionLevel.MODIFY_WORKSPACE)
    registry.register(BusinessAnalysisAction.PANEL_BUILD_CATEGORY_DAY, panel_build_category_day, PermissionLevel.MODIFY_WORKSPACE)
    registry.register(BusinessAnalysisAction.ANALYSIS_RUN_DIAGNOSTICS, analysis_run_diagnostics, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.ANALYSIS_RUN_PSM_DID, analysis_run_psm_did, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.ANALYSIS_RUN_LOCALGAP, analysis_run_localgap, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.ANALYSIS_RUN_GPS_UPLIFT, analysis_run_gps_uplift, PermissionLevel.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.ANALYSIS_RUN_FULL_PIPELINE, analysis_run_full_pipeline, PermissionLevel.MODIFY_WORKSPACE)
    registry.register(BusinessAnalysisAction.RESULT_GET_LATEST, result_get_latest, PermissionLevel.READ_STATE)
    registry.register(BusinessAnalysisAction.ARTIFACT_READ, artifact_read, PermissionLevel.READ_STATE)
    registry.register(BusinessAnalysisAction.CHART_RENDER, chart_render, PermissionLevel.WRITE_ARTIFACT)
    registry.register(BusinessAnalysisAction.CHART_RENDER_DASHBOARD, chart_render_dashboard, PermissionLevel.WRITE_ARTIFACT)
    registry.register(BusinessAnalysisAction.REPORT_GENERATE, report_generate, PermissionLevel.WRITE_ARTIFACT)
    registry.register(BusinessAnalysisAction.MEMORY_PROPOSE_UPDATE, memory_propose_update, PermissionLevel.EXTERNAL_SYNC)
    registry.register(BusinessAnalysisAction.STRATEGY_DESIGN_BLUEPRINT, strategy_design_blueprint, PermissionLevel.WRITE_ARTIFACT)
    registry.register(BusinessAnalysisAction.STRATEGY_DESIGN_FLOW, strategy_design_flow, PermissionLevel.WRITE_ARTIFACT)
    registry.register(BusinessAnalysisAction.STRATEGY_PROPOSE_BACKEND_CHANGE, strategy_propose_backend_change, PermissionLevel.WRITE_ARTIFACT)
