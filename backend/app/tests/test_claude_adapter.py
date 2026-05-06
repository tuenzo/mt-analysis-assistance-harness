import pytest
import tempfile
import shutil
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, reset_engine
from app.agent.claude_adapter import MockClaudeRuntimeAdapter, ClaudeRuntimeAdapter
from app.agent.claude_agent_sdk_adapter import get_claude_adapter, ClaudeAgentSDKAdapter


@pytest.fixture
def test_db():
    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    reset_engine()
    init_db()
    try:
        yield
    finally:
        reset_engine()
        os.chdir(old_cwd)
        shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_mock_adapter_implements_interface():
    """验证 MockClaudeRuntimeAdapter 实现了 ClaudeRuntimeAdapter 接口"""
    adapter = MockClaudeRuntimeAdapter()

    assert isinstance(adapter, ClaudeRuntimeAdapter)
    assert hasattr(adapter, "create_session")
    assert hasattr(adapter, "resume_session")
    assert hasattr(adapter, "send_message")
    assert hasattr(adapter, "interrupt")


def test_get_claude_adapter_requires_key_when_sdk_provider_requested(monkeypatch):
    """当没有 API key 时，返回 mock adapter"""
    import app.agent.claude_agent_sdk_adapter as sdk_adapter
    from app.core.config import settings as app_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(app_settings, "anthropic_api_key", "")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_claude_adapter({"provider": "claude_agent_sdk"})


def test_get_claude_adapter_returns_mock_when_provider_is_mock():
    """当 provider 是 mock 时，返回 mock adapter"""
    adapter = get_claude_adapter({"provider": "mock"})

    assert isinstance(adapter, MockClaudeRuntimeAdapter)


def test_mock_adapter_create_session():
    adapter = MockClaudeRuntimeAdapter()
    session_id = adapter.create_session("test_project")

    assert session_id is not None
    assert session_id.startswith("mock_")


def test_mock_adapter_resume_session():
    adapter = MockClaudeRuntimeAdapter()
    adapter.resume_session("test_session", "test_project")

    assert "test_session" in adapter._sessions


def test_mock_adapter_send_message_returns_generator():
    adapter = MockClaudeRuntimeAdapter()
    session_id = adapter.create_session("test_project")

    events = list(adapter.send_message(session_id, "你好", {}))

    assert len(events) > 0
    assert any(e["type"] == "assistant_message_delta" for e in events)


def test_mock_adapter_interrupt():
    adapter = MockClaudeRuntimeAdapter()
    session_id = adapter.create_session("test_project")

    adapter.interrupt(session_id)

    assert session_id in adapter._interrupted


def test_claude_adapter_class_exists():
    """验证 ClaudeAgentSDKAdapter 类存在（即使不能实例化）"""
    from app.agent.claude_agent_sdk_adapter import ClaudeAgentSDKAdapter
    assert ClaudeAgentSDKAdapter is not None


def test_get_claude_adapter_with_settings():
    """验证 get_claude_adapter 可以接受配置参数"""
    adapter = get_claude_adapter({
        "provider": "mock",
        "permission_mode": "dontAsk",
        "enable_user_setting_sources": True,
    })

    assert isinstance(adapter, MockClaudeRuntimeAdapter)
