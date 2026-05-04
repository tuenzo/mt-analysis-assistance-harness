from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any


class BusinessAnalysisAction(str, Enum):
    PROJECT_GET_STATE = "project.get_state"
    DATA_INGEST = "data.ingest"
    DATA_VALIDATE = "data.validate"
    SCHEMA_INFER = "schema.infer"
    SCHEMA_APPLY_MAPPING = "schema.apply_mapping"
    PANEL_BUILD_CATEGORY_DAY = "panel.build_category_day"
    ANALYSIS_RUN_DIAGNOSTICS = "analysis.run_diagnostics"
    ANALYSIS_RUN_PSM_DID = "analysis.run_psm_did"
    ANALYSIS_RUN_LOCALGAP = "analysis.run_localgap"
    ANALYSIS_RUN_GPS_UPLIFT = "analysis.run_gps_uplift"
    ANALYSIS_RUN_FULL_PIPELINE = "analysis.run_full_pipeline"
    RESULT_GET_LATEST = "result.get_latest"
    ARTIFACT_READ = "artifact.read"
    CHART_RENDER = "chart.render"
    REPORT_GENERATE = "report.generate"
    MEMORY_PROPOSE_UPDATE = "memory.propose_update"


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
