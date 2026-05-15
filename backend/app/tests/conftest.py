import os
from pathlib import Path

import pytest


os.environ.setdefault("APP_AGENT_RUNTIME_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def isolate_workspace_root(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.core.database import reset_engine

    previous_workspace_root = settings.workspace_root
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{(Path(tmp_path) / 'test.db').as_posix()}")
    settings.workspace_root = (Path(tmp_path) / "workspaces").resolve()
    reset_engine()
    try:
        yield
    finally:
        settings.workspace_root = previous_workspace_root
        reset_engine()
