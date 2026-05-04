from pathlib import Path
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class CheckpointInfo:
    checkpoint_id: str
    label: str
    created_at: str
    manifest_snapshot: dict


class CheckpointManager:
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.checkpoints_dir = workspace_path / ".analysis" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(self, project_id: str, manifest_snapshot: dict, label: str = "") -> CheckpointInfo:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"cp_{timestamp}"
        checkpoint = CheckpointInfo(
            checkpoint_id=checkpoint_id,
            label=label or "manual",
            created_at=datetime.now().isoformat(),
            manifest_snapshot=manifest_snapshot
        )
        filepath = self.checkpoints_dir / f"{timestamp}_{label or 'manual'}.json"
        filepath.write_text(json.dumps({
            "checkpoint_id": checkpoint.checkpoint_id,
            "label": checkpoint.label,
            "created_at": checkpoint.created_at,
            "manifest_snapshot": checkpoint.manifest_snapshot
        }, indent=2, ensure_ascii=False))
        return checkpoint

    def list_checkpoints(self) -> list[CheckpointInfo]:
        checkpoints = []
        if not self.checkpoints_dir.exists():
            return checkpoints
        for filepath in sorted(self.checkpoints_dir.glob("*.json"), reverse=True):
            data = json.loads(filepath.read_text())
            checkpoints.append(CheckpointInfo(
                checkpoint_id=data["checkpoint_id"],
                label=data["label"],
                created_at=data["created_at"],
                manifest_snapshot=data.get("manifest_snapshot", {})
            ))
        return checkpoints

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[dict]:
        if not self.checkpoints_dir.exists():
            return None
        for filepath in self.checkpoints_dir.glob("*.json"):
            data = json.loads(filepath.read_text())
            if data["checkpoint_id"] == checkpoint_id:
                return data.get("manifest_snapshot")
        return None
