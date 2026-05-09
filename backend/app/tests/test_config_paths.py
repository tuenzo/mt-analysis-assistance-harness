from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings, resolve_project_path


def test_workspace_root_default_points_to_project_root_workspaces():
    default_root = Settings.model_fields["workspace_root"].default
    assert resolve_project_path(default_root) == (PROJECT_ROOT / "workspaces").resolve()


def test_project_relative_paths_resolve_from_project_root():
    assert resolve_project_path("./workspaces") == (PROJECT_ROOT / "workspaces").resolve()


def test_absolute_paths_are_preserved(tmp_path):
    assert resolve_project_path(tmp_path) == Path(tmp_path).resolve()
