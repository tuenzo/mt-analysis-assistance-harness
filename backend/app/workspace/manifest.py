import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class FileEntry:
    file_id: str
    role: str
    original_name: str
    current_path: str
    checksum: str
    schema_hash: Optional[str] = None
    status: str = "uploaded"
    last_verified_at: Optional[str] = None


@dataclass
class AssetEntry:
    asset_id: str
    role: str
    path: str
    source_file_ids: list[str] = field(default_factory=list)
    checksum: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ProjectManifest:
    project_id: str
    version: int = 1
    current_stage: str = "created"
    files: list = field(default_factory=list)
    derived_assets: list = field(default_factory=list)
    latest_result: Optional[dict] = None

    @staticmethod
    def manifest_path(workspace_path: Path) -> Path:
        return workspace_path / ".analysis" / "project_manifest.json"

    @staticmethod
    def init_new(project_id: str, workspace_path: Path) -> "ProjectManifest":
        manifest = ProjectManifest(project_id=project_id)
        manifest.save(workspace_path)
        return manifest

    @staticmethod
    def load(workspace_path: Path) -> "ProjectManifest":
        path = ProjectManifest.manifest_path(workspace_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found at {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectManifest(**data)

    def save(self, workspace_path: Path) -> None:
        path = ProjectManifest.manifest_path(workspace_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


def compute_file_checksum(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return f"sha256:{sha256_hash.hexdigest()}"


def compute_schema_hash(schema_json: str) -> str:
    return f"sha256:{hashlib.sha256(schema_json.encode()).hexdigest()}"
