from typing import Any

from pydantic import BaseModel, Field, model_validator


class StrategyBlueprintPayload(BaseModel):
    strategy_id: str | None = None
    version: str = "v1"
    parent_version: str | None = None
    status: str = "draft"
    title: str = "Untitled strategy blueprint"
    objective: str
    decision_questions: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    constraints: list[str] = []
    candidate_methods: list[Any] = []
    notes: str = ""


class FlowStagePayload(BaseModel):
    name: str
    purpose: str = ""
    inputs: list[str] = []
    outputs: list[str] = []
    action: str | None = None
    proposed_backend_change: str | None = None
    acceptance_criteria: list[str] = []

    @model_validator(mode="after")
    def require_action_or_proposal(self):
        if not self.action and not self.proposed_backend_change:
            raise ValueError("Each flow stage must include action or proposed_backend_change.")
        return self


class AnalysisFlowPayload(BaseModel):
    flow_id: str | None = None
    strategy_id: str | None = None
    version: str = "v1"
    parent_version: str | None = None
    status: str = "draft"
    title: str = "Untitled analysis flow"
    objective: str = ""
    stages: list[FlowStagePayload] = Field(min_length=1)
    notes: str = ""


class BackendChangeProposalPayload(BaseModel):
    proposal_id: str | None = None
    strategy_id: str | None = None
    flow_id: str | None = None
    version: str = "v1"
    parent_version: str | None = None
    status: str = "draft"
    title: str
    objective: str
    affected_modules: list[str] = Field(min_length=1)
    desired_behavior: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    review_notes: str = ""
    source_write_instructions: list[str] = []
