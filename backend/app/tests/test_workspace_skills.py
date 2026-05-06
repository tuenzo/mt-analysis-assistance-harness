import shutil
import tempfile

from app.workspace.manager import WorkspaceManager


def test_workspace_manager_creates_project_business_analysis_skill():
    tmpdir = tempfile.mkdtemp()
    try:
        workspace = WorkspaceManager(tmpdir).create_workspace("proj_skill")

        skill_path = workspace / ".claude" / "skills" / "business-analysis" / "SKILL.md"

        assert skill_path.exists()
        content = skill_path.read_text(encoding="utf-8")
        assert "name: business-analysis" in content
        assert "business_analysis(project_id, action, payload, reason)" in content
    finally:
        shutil.rmtree(tmpdir)
