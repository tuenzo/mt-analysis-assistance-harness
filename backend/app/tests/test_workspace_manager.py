import pytest
import tempfile
import shutil
from pathlib import Path
from app.workspace.manager import WorkspaceManager, WORKSPACE_TEMPLATE
from app.workspace.manifest import ProjectManifest
from app.workspace.context_summary import ContextSummaryWriter
from app.workspace.checkpoints import CheckpointManager


@pytest.fixture
def temp_workspace():
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def manager(temp_workspace):
    return WorkspaceManager(temp_workspace)


def test_workspace_template_exists():
    assert "data/raw" in WORKSPACE_TEMPLATE
    assert "data/processed" in WORKSPACE_TEMPLATE
    assert ".analysis" in WORKSPACE_TEMPLATE
    assert ".claude" in WORKSPACE_TEMPLATE


def test_create_workspace(manager, temp_workspace):
    path = manager.create_workspace("proj_001")
    assert path == temp_workspace / "projects" / "proj_001"
    assert path.exists()


def test_workspace_directory_structure(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    for dir_key in WORKSPACE_TEMPLATE.keys():
        assert (wp / dir_key).exists(), f"{dir_key} should exist"


def test_manifest_created(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    manifest_path = wp / ".analysis" / "project_manifest.json"
    assert manifest_path.exists()
    manifest = ProjectManifest.load(wp)
    assert manifest.project_id == "proj_001"
    assert manifest.version == 1
    assert manifest.current_stage == "created"


def test_context_summary_created(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    ctx_path = wp / ".analysis" / "context_summary.md"
    assert ctx_path.exists()
    content = ctx_path.read_text(encoding="utf-8")
    assert "项目:" in content
    assert "当前阶段:" in content


def test_claude_md_created(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    claude_md = wp / ".claude" / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert "Business Analysis Companion Workspace" in content


def test_get_workspace_path(manager, temp_workspace):
    path = manager.get_workspace_path("proj_001")
    assert path == temp_workspace / "projects" / "proj_001"


def test_checkpoint_create_and_list(manager, temp_workspace):
    manager.create_workspace("proj_001")
    cp = manager.create_checkpoint("proj_001", label="test")
    assert cp.checkpoint_id.startswith("cp_")
    assert cp.label == "test"
    cps = manager.list_checkpoints("proj_001")
    assert len(cps) >= 1
    assert cps[0].checkpoint_id == cp.checkpoint_id


def test_checkpoint_restore(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    manifest = ProjectManifest.load(wp)
    manifest.current_stage = "modified"
    manifest.save(wp)
    cp = manager.create_checkpoint("proj_001", label="before")
    manifest.current_stage = "panel_ready"
    manifest.save(wp)
    restored = manager.restore_checkpoint("proj_001", cp.checkpoint_id)
    assert restored is True
    restored_manifest = ProjectManifest.load(wp)
    assert restored_manifest.current_stage == "modified"


def test_scan_workspace(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    (wp / "data/raw/test.csv").write_text("a,b,c\n1,2,3")
    scanned = manager.scan_workspace("proj_001")
    assert len(scanned) >= 1
    assert any(s.original_name == "test.csv" for s in scanned)


def test_checksum_computed(manager, temp_workspace):
    manager.create_workspace("proj_001")
    wp = temp_workspace / "projects" / "proj_001"
    test_file = wp / "data/raw/test.csv"
    test_file.write_text("a,b,c\n1,2,3")
    from app.workspace.manifest import compute_file_checksum
    checksum = compute_file_checksum(test_file)
    assert checksum.startswith("sha256:")
    assert len(checksum) == 71
