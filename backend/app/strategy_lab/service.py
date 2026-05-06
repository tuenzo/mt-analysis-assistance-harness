from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.projects.service import ProjectService
from app.strategy_lab.schemas import (
    AnalysisFlowPayload,
    BackendChangeProposalPayload,
    StrategyBlueprintPayload,
)


class StrategyLabError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class StrategyLabService:
    def __init__(self, project_service: ProjectService | None = None):
        self.project_service = project_service or ProjectService()

    def create_blueprint(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        blueprint = self._validate(StrategyBlueprintPayload, payload)
        tool_context = _tool_context(payload)
        artifact_id = _safe_identifier(blueprint.strategy_id, "strategy")
        document = self._document(
            project_id=project_id,
            artifact_type="strategy_blueprint",
            artifact_id=artifact_id,
            version=blueprint.version,
            parent_version=blueprint.parent_version,
            status=blueprint.status,
            source=tool_context,
            content=blueprint.model_dump(mode="json"),
        )
        return self._write_document(project_id, "blueprints", artifact_id, blueprint.version, document)

    def create_flow(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        flow = self._validate(AnalysisFlowPayload, payload)
        tool_context = _tool_context(payload)
        artifact_id = _safe_identifier(flow.flow_id, "flow")
        document = self._document(
            project_id=project_id,
            artifact_type="analysis_flow",
            artifact_id=artifact_id,
            version=flow.version,
            parent_version=flow.parent_version,
            status=flow.status,
            source=tool_context,
            content=flow.model_dump(mode="json"),
        )
        result = self._write_document(project_id, "flows", artifact_id, flow.version, document)
        result["stage_count"] = len(flow.stages)
        return result

    def create_backend_change(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        proposal = self._validate(BackendChangeProposalPayload, payload)
        tool_context = _tool_context(payload)
        artifact_id = _safe_identifier(proposal.proposal_id, "backend_change")
        document = self._document(
            project_id=project_id,
            artifact_type="backend_change_proposal",
            artifact_id=artifact_id,
            version=proposal.version,
            parent_version=proposal.parent_version,
            status=proposal.status,
            source=tool_context,
            content=proposal.model_dump(mode="json"),
        )
        return self._write_document(project_id, "backend_changes", artifact_id, proposal.version, document)

    def _workspace_path(self, project_id: str) -> Path:
        project = self.project_service.get_project(project_id)
        if not project:
            raise StrategyLabError("NOT_FOUND", "Project not found.", {"project_id": project_id})
        workspace_path = Path(project.workspace_path).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        return workspace_path

    def _write_document(
        self,
        project_id: str,
        category: str,
        artifact_id: str,
        version: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        workspace_path = self._workspace_path(project_id)
        lab_root = (workspace_path / ".analysis" / "strategy_lab").resolve()
        target_dir = (lab_root / category).resolve()
        self._assert_inside_workspace(workspace_path, target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{artifact_id}_{_safe_identifier(version, 'v1')}.json"
        target_path = (target_dir / filename).resolve()
        self._assert_inside_workspace(workspace_path, target_path)
        if target_path.exists():
            raise StrategyLabError(
                "ARTIFACT_EXISTS",
                f"Strategy lab artifact already exists: {target_path.relative_to(workspace_path)}",
                {"path": str(target_path.relative_to(workspace_path))},
            )

        target_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        relative_path = str(target_path.relative_to(workspace_path)).replace("\\", "/")
        return {
            "id": artifact_id,
            "version": version,
            "status": document["status"],
            "path": relative_path,
            "artifact_type": document["artifact_type"],
            "created_at": document["created_at"],
            "title": document["content"].get("title", artifact_id),
        }

    @staticmethod
    def _validate(schema, payload: dict[str, Any]):
        try:
            return schema.model_validate(payload or {})
        except ValidationError as exc:
            raise StrategyLabError(
                "VALIDATION_FAILED",
                "Strategy lab payload validation failed.",
                {"errors": exc.errors()},
            ) from exc

    @staticmethod
    def _document(
        *,
        project_id: str,
        artifact_type: str,
        artifact_id: str,
        version: str,
        parent_version: str | None,
        status: str,
        source: dict[str, Any],
        content: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "strategy_lab.v1",
            "artifact_type": artifact_type,
            "id": artifact_id,
            "version": version,
            "parent_version": parent_version,
            "status": status or "draft",
            "project_id": project_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "content": content,
        }

    @staticmethod
    def _assert_inside_workspace(workspace_path: Path, path: Path) -> None:
        try:
            path.relative_to(workspace_path)
        except ValueError as exc:
            raise StrategyLabError(
                "INVALID_PATH",
                "Strategy lab artifacts must stay inside the current project workspace.",
                {"workspace_path": str(workspace_path), "path": str(path)},
            ) from exc


def _safe_identifier(value: str | None, prefix: str) -> str:
    text = (value or "").strip()
    if not text:
        text = f"{prefix}_{uuid.uuid4().hex[:12]}"
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    if not text:
        text = f"{prefix}_{uuid.uuid4().hex[:12]}"
    return text[:80]


def _tool_context(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("_tool_context") if isinstance(payload, dict) else None
    if not isinstance(value, dict):
        return {}
    return {
        "tool_call_id": value.get("tool_call_id") or "",
        "session_id": value.get("session_id") or "",
        "turn_id": value.get("turn_id") or "",
        "reason": value.get("reason") or "",
    }
