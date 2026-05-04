from pathlib import Path
from datetime import datetime
from .manifest import ProjectManifest, FileEntry, AssetEntry, compute_file_checksum
from .context_summary import ContextSummaryWriter
from .checkpoints import CheckpointManager, CheckpointInfo


WORKSPACE_TEMPLATE = {
    "data/raw": [],
    "data/processed": [],
    "scripts": [],
    "artifacts/charts": [],
    "artifacts/tables": [],
    "artifacts/model_outputs": [],
    "reports": [],
    "logs": [],
    ".analysis": [],
    ".claude": [],
}


class WorkspaceManager:
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)

    def get_workspace_path(self, project_id: str) -> Path:
        return self.workspace_root / "projects" / project_id

    def create_workspace(self, project_id: str) -> Path:
        workspace_path = self.get_workspace_path(project_id)

        for dir_path in WORKSPACE_TEMPLATE.keys():
            (workspace_path / dir_path).mkdir(parents=True, exist_ok=True)

        self._init_empty_files(workspace_path)

        ProjectManifest.init_new(project_id, workspace_path)

        ctx_writer = ContextSummaryWriter(workspace_path)
        ctx_writer.init_default(project_id)

        self._init_claude_context(project_id, workspace_path)

        return workspace_path

    def _init_empty_files(self, workspace_path: Path) -> None:
        for dir_path in WORKSPACE_TEMPLATE.keys():
            dir_full = workspace_path / dir_path
            for filename in ["agent_events.jsonl", "tool_calls.jsonl", "jobs.jsonl", "errors.jsonl"]:
                filepath = dir_full / filename
                filepath.touch(exist_ok=True)

    def _init_claude_context(self, project_id: str, workspace_path: Path) -> None:
        claude_md_path = workspace_path / ".claude" / "CLAUDE.md"
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        if not claude_md_path.exists():
            claude_md_path.write_text(
                "你正在 Business Analysis Companion Workspace 中工作。\n"
                "不要臆造数据结果。\n"
                "需要真实数据、图表、模型、报告时，调用 business_analysis 工具。\n"
                "当前项目状态以 .analysis/context_summary.md 和 project_manifest.json 为准。\n"
            )

    def update_project_manifest(self, project_id: str) -> ProjectManifest:
        workspace_path = self.get_workspace_path(project_id)
        manifest = ProjectManifest.load(workspace_path)
        manifest.save(workspace_path)
        return manifest

    def scan_workspace(self, project_id: str) -> list[FileEntry]:
        workspace_path = self.get_workspace_path(project_id)
        manifest = ProjectManifest.load(workspace_path)
        existing_paths = {f.current_path for f in manifest.files}

        scanned = []
        for dir_key in ["data/raw", "data/processed", "scripts", "artifacts/charts", "artifacts/tables", "artifacts/model_outputs", "reports"]:
            dir_path = workspace_path / dir_key
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob("*"):
                if file_path.is_file() and file_path.name not in ["agent_events.jsonl", "tool_calls.jsonl", "jobs.jsonl", "errors.jsonl"]:
                    rel_path = str(file_path.relative_to(workspace_path))
                    if rel_path not in existing_paths:
                        checksum = compute_file_checksum(file_path)
                        scanned.append(FileEntry(
                            file_id=f"file_{len(manifest.files) + len(scanned) + 1}",
                            role="unknown",
                            original_name=file_path.name,
                            current_path=rel_path,
                            checksum=checksum,
                            status="scanned"
                        ))
        return scanned

    def create_checkpoint(self, project_id: str, label: str = "") -> CheckpointInfo:
        workspace_path = self.get_workspace_path(project_id)
        manifest = ProjectManifest.load(workspace_path)
        snapshot = {
            "project_id": manifest.project_id,
            "version": manifest.version,
            "current_stage": manifest.current_stage,
            "files": [f.__dict__ for f in manifest.files],
            "derived_assets": [a.__dict__ for a in manifest.derived_assets],
            "latest_result": manifest.latest_result
        }
        cp_manager = CheckpointManager(workspace_path)
        return cp_manager.create_checkpoint(project_id, snapshot, label)

    def list_checkpoints(self, project_id: str) -> list[CheckpointInfo]:
        workspace_path = self.get_workspace_path(project_id)
        cp_manager = CheckpointManager(workspace_path)
        return cp_manager.list_checkpoints()

    def restore_checkpoint(self, project_id: str, checkpoint_id: str) -> bool:
        workspace_path = self.get_workspace_path(project_id)
        cp_manager = CheckpointManager(workspace_path)
        snapshot = cp_manager.restore_checkpoint(checkpoint_id)
        if snapshot is None:
            return False
        manifest = ProjectManifest(**snapshot)
        manifest.save(workspace_path)
        return True
