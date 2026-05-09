from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any


class BusinessAnalysisAction(str, Enum):
    PROJECT_GET_STATE = "project.get_state"
    DATA_DISCOVER_SOURCE_FILES = "data.discover_source_files"
    DATA_INGEST = "data.ingest"
    DATA_VALIDATE = "data.validate"
    SCHEMA_INFER = "schema.infer"
    SCHEMA_APPLY_MAPPING = "schema.apply_mapping"
    PANEL_BUILD_CATEGORY_DAY = "panel.build_category_day"
    ANALYSIS_RUN_DIAGNOSTICS = "analysis.run_diagnostics"
    ANALYSIS_RUN_PSM_DID = "analysis.run_psm_did"
    ANALYSIS_RUN_LOCALGAP = "analysis.run_localgap"
    ANALYSIS_RUN_MECHANISM_REGRESSION = "analysis.run_mechanism_regression"
    ANALYSIS_RUN_CONVERSION_DIAGNOSTICS = "analysis.run_conversion_diagnostics"
    ANALYSIS_RUN_GPS_UPLIFT = "analysis.run_gps_uplift"
    ANALYSIS_RUN_FULL_PIPELINE = "analysis.run_full_pipeline"
    RESULT_GET_LATEST = "result.get_latest"
    ARTIFACT_READ = "artifact.read"
    CHART_RENDER = "chart.render"
    CHART_RENDER_DASHBOARD = "chart.render_dashboard"
    REPORT_GENERATE = "report.generate"
    MEMORY_PROPOSE_UPDATE = "memory.propose_update"
    STRATEGY_DESIGN_BLUEPRINT = "strategy.design_blueprint"
    STRATEGY_DESIGN_FLOW = "strategy.design_flow"
    STRATEGY_PROPOSE_BACKEND_CHANGE = "strategy.propose_backend_change"


class ToolResult(BaseModel):
    ok: bool
    action: str
    summary: str
    artifacts: list[dict] = []
    state_patch: dict = {}
    assistant_hint: str = ""
    error: Optional[dict] = None


class ToolError(BaseModel):
    code: str
    message: str
    details: dict = {}
