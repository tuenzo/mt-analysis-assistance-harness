from enum import IntEnum
from app.tools.schemas import BusinessAnalysisAction


class PermissionLevel(IntEnum):
    READ_STATE = 0
    SAFE_COMPUTE = 1
    WRITE_ARTIFACT = 2
    MODIFY_WORKSPACE = 3
    EXTERNAL_SYNC = 4


ACTION_PERMISSION_MAP: dict[BusinessAnalysisAction, PermissionLevel] = {
    BusinessAnalysisAction.PROJECT_GET_STATE: PermissionLevel.READ_STATE,
    BusinessAnalysisAction.DATA_DISCOVER_SOURCE_FILES: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.DATA_INGEST: PermissionLevel.MODIFY_WORKSPACE,
    BusinessAnalysisAction.DATA_VALIDATE: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.SCHEMA_INFER: PermissionLevel.READ_STATE,
    BusinessAnalysisAction.SCHEMA_APPLY_MAPPING: PermissionLevel.MODIFY_WORKSPACE,
    BusinessAnalysisAction.PANEL_BUILD_CATEGORY_DAY: PermissionLevel.MODIFY_WORKSPACE,
    BusinessAnalysisAction.ANALYSIS_RUN_DIAGNOSTICS: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.ANALYSIS_RUN_PSM_DID: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.ANALYSIS_RUN_LOCALGAP: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.ANALYSIS_RUN_GPS_UPLIFT: PermissionLevel.SAFE_COMPUTE,
    BusinessAnalysisAction.ANALYSIS_RUN_FULL_PIPELINE: PermissionLevel.MODIFY_WORKSPACE,
    BusinessAnalysisAction.RESULT_GET_LATEST: PermissionLevel.READ_STATE,
    BusinessAnalysisAction.ARTIFACT_READ: PermissionLevel.READ_STATE,
    BusinessAnalysisAction.CHART_RENDER: PermissionLevel.WRITE_ARTIFACT,
    BusinessAnalysisAction.REPORT_GENERATE: PermissionLevel.WRITE_ARTIFACT,
    BusinessAnalysisAction.MEMORY_PROPOSE_UPDATE: PermissionLevel.EXTERNAL_SYNC,
}


HIGH_RISK_ACTIONS = {BusinessAnalysisAction.DATA_INGEST, BusinessAnalysisAction.PANEL_BUILD_CATEGORY_DAY, BusinessAnalysisAction.ANALYSIS_RUN_FULL_PIPELINE, BusinessAnalysisAction.MEMORY_PROPOSE_UPDATE}

RISK_LEVEL_MAP: dict[BusinessAnalysisAction, str] = {
    BusinessAnalysisAction.MEMORY_PROPOSE_UPDATE: "high",
    BusinessAnalysisAction.ANALYSIS_RUN_FULL_PIPELINE: "high",
    BusinessAnalysisAction.PANEL_BUILD_CATEGORY_DAY: "medium",
    BusinessAnalysisAction.DATA_INGEST: "medium",
    BusinessAnalysisAction.DATA_DISCOVER_SOURCE_FILES: "low",
    BusinessAnalysisAction.SCHEMA_APPLY_MAPPING: "medium",
    BusinessAnalysisAction.DATA_VALIDATE: "low",
    BusinessAnalysisAction.SCHEMA_INFER: "low",
    BusinessAnalysisAction.PROJECT_GET_STATE: "low",
    BusinessAnalysisAction.RESULT_GET_LATEST: "low",
    BusinessAnalysisAction.ARTIFACT_READ: "low",
    BusinessAnalysisAction.CHART_RENDER: "low",
    BusinessAnalysisAction.REPORT_GENERATE: "low",
    BusinessAnalysisAction.ANALYSIS_RUN_DIAGNOSTICS: "low",
    BusinessAnalysisAction.ANALYSIS_RUN_PSM_DID: "low",
    BusinessAnalysisAction.ANALYSIS_RUN_LOCALGAP: "low",
    BusinessAnalysisAction.ANALYSIS_RUN_GPS_UPLIFT: "low",
}


def check_permission(user_level: int, required_level: PermissionLevel) -> bool:
    return user_level >= required_level.value


def action_to_permission_level(action: BusinessAnalysisAction) -> PermissionLevel:
    return ACTION_PERMISSION_MAP.get(action, PermissionLevel.READ_STATE)
