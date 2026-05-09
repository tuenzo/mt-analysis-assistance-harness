import os
from pathlib import Path

import pytest


os.environ.setdefault("APP_AGENT_RUNTIME_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def isolate_workspace_root(tmp_path):
    from app.core.config import settings

    previous_workspace_root = settings.workspace_root
    settings.workspace_root = (Path(tmp_path) / "workspaces").resolve()
    try:
        yield
    finally:
        settings.workspace_root = previous_workspace_root
