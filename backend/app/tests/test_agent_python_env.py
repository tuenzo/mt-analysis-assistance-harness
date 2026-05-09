import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent.python_env import apply_python_environment, discover_python_environment


def test_discovers_backend_venv_when_workspace_has_no_venv(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    env = discover_python_environment(tmp_path)

    assert env.available is True
    assert env.source == "backend:.venv"
    assert env.python_executable is not None
    assert env.python_executable.name in {"python.exe", "python"}


def test_apply_python_environment_sets_child_runtime_env(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    base_env = {"PATH": "C:\\existing"}

    updated = apply_python_environment(base_env, tmp_path)
    discovered = discover_python_environment(tmp_path)

    assert updated["VIRTUAL_ENV"] == str(discovered.venv_path)
    assert updated["PYTHONUTF8"] == "1"
    assert updated["PYTHONIOENCODING"] == "utf-8"
    assert updated["PATH"].split(os.pathsep)[0] == str(discovered.scripts_path)
    assert base_env["PATH"] == "C:\\existing"


def test_sdk_options_include_discovered_venv(monkeypatch, tmp_path):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    if not sdk_adapter.HAS_CLAUDE_AGENT_SDK:
        pytest.skip("claude_agent_sdk is not installed")

    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {
            "provider": "claude_agent_sdk",
            "workspace_root": str(tmp_path / "workspaces"),
            "skills": ["business-analysis"],
        }
    )
    session_id = adapter.create_session("proj_sdk")
    options = adapter._build_options(session_id, adapter._sessions[session_id])
    discovered = discover_python_environment(Path(adapter._sessions[session_id]["workspace_path"]))

    assert options.env["VIRTUAL_ENV"] == str(discovered.venv_path)
    assert options.env["PATH"].split(os.pathsep)[0] == str(discovered.scripts_path)
    assert adapter._sessions[session_id]["python_environment"]["available"] is True
    assert adapter._sessions[session_id]["python_environment"]["python_executable"] == str(discovered.python_executable)


def test_sdk_prompt_mentions_venv_python_rule(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())
    adapter = sdk_adapter.ClaudeAgentSDKAdapter({"provider": "claude_agent_sdk"})

    prompt = adapter._build_prompt(
        {
            "project_id": "proj_env",
            "project_name": "Runtime Env",
            "python_environment": {
                "available": True,
                "python_executable": "E:\\repo\\backend\\.venv\\Scripts\\python.exe",
            },
        },
        "Run analysis",
    )

    assert "python_environment" in prompt
    assert "prefer python_environment.python_executable over bare python" in prompt
