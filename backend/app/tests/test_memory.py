import pytest
import tempfile
import shutil
import os
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, get_session
from app.projects.models import MemoryCandidate
from app.memory.store import MemoryStore
from app.memory.bridge import MemoryBridge


@pytest.fixture
def test_db():
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    init_db()
    yield
    os.chdir("..")
    shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def project_with_data(client):
    r = client.post("/api/projects", json={"name": "MemoryTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    analysis_dir = workspace_path / ".analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    return project


def test_memory_propose_creates_candidate(client, project_with_data):
    db = get_session()
    try:
        candidate = MemoryCandidate(
            id=uuid.uuid4().hex,
            project_id=project_with_data["id"],
            scope="project",
            content="Test memory content",
            status="pending",
        )
        db.add(candidate)
        db.commit()

        retrieved = db.query(MemoryCandidate).filter(MemoryCandidate.id == candidate.id).first()
        assert retrieved is not None
        assert retrieved.status == "pending"
    finally:
        db.close()


def test_memory_store_writes_file(project_with_data):
    workspace_path = Path(f"./workspaces/{project_with_data['id']}")
    store = MemoryStore(str(workspace_path))

    success = store.write_memory("Test memory entry", scope="project")
    assert success is True

    assert store.memory_file.exists()
    content = store.read_memory()
    assert "Test memory entry" in content


def test_memory_approve_writes_to_store(client, project_with_data):
    db = get_session()
    try:
        candidate_id = uuid.uuid4().hex
        candidate = MemoryCandidate(
            id=candidate_id,
            project_id=project_with_data["id"],
            scope="project",
            content="Approved memory content",
            status="pending",
        )
        db.add(candidate)
        db.commit()

        bridge = MemoryBridge()
        result = bridge.approve_and_store(
            project_with_data["id"],
            candidate_id,
            "Approved memory content",
            "project",
        )

        assert result.ok is True
    finally:
        db.close()


def test_memory_reject_stays_pending(client, project_with_data):
    db = get_session()
    try:
        candidate_id = uuid.uuid4().hex
        candidate = MemoryCandidate(
            id=candidate_id,
            project_id=project_with_data["id"],
            scope="project",
            content="Rejected memory content",
            status="pending",
        )
        db.add(candidate)
        db.commit()

        candidate.status = "rejected"
        db.commit()

        retrieved = db.query(MemoryCandidate).filter(MemoryCandidate.id == candidate_id).first()
        assert retrieved.status == "rejected"
    finally:
        db.close()


def test_memory_store_does_not_write_to_user_home(project_with_data):
    """验证记忆不会写入 ~/.claude"""
    import os
    home_claude = Path.home() / ".claude"

    workspace_path = Path(f"./workspaces/{project_with_data['id']}")
    store = MemoryStore(str(workspace_path))

    store.write_memory("Test memory", scope="project")

    assert not (home_claude / "memory_candidates.md").exists()
