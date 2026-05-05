import os
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from app.agent.claude_adapter import MockClaudeRuntimeAdapter
from app.agent.session_store import SessionStore
from app.core.database import get_session, init_db
from app.projects.models import AnalysisSession


@pytest.fixture
def isolated_db():
    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    init_db()
    try:
        yield tmp
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmp)


def test_adapter_factory_falls_back_to_mock_without_key(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)

    adapter = sdk_adapter.get_claude_adapter({"provider": "claude_agent_sdk"})

    assert isinstance(adapter, MockClaudeRuntimeAdapter)


def test_adapter_factory_falls_back_to_mock_when_provider_is_mock(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)

    adapter = sdk_adapter.get_claude_adapter({"provider": "mock"})

    assert isinstance(adapter, MockClaudeRuntimeAdapter)


def test_adapter_factory_creates_real_sdk_adapter_when_sdk_and_key_available(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.get_claude_adapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    external_session_id = adapter.create_session("proj_sdk")

    assert isinstance(adapter, sdk_adapter.ClaudeAgentSDKAdapter)
    assert external_session_id
    assert adapter._sessions[external_session_id]["project_id"] == "proj_sdk"


def test_sdk_event_mapping_includes_expected_stream_events(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeTextBlock:
        text = "Starting analysis."

    class FakeToolUseBlock:
        def __init__(self):
            self.id = "toolu_1"
            self.name = "business_analysis"
            self.input = {
                "project_id": "proj_sdk",
                "action": "project.get_state",
                "payload": {},
                "reason": "inspect state",
            }

    class FakeToolResultBlock:
        tool_use_id = "toolu_1"
        is_error = False
        content = [{"type": "text", "text": '{"ok": true, "summary": "state loaded"}'}]

    class FakeAssistantMessage:
        content = [FakeTextBlock(), FakeToolUseBlock()]

    class FakeUserMessage:
        content = [FakeToolResultBlock()]

    class FakeResultMessage:
        is_error = False
        result = "Done."
        session_id = "sdk_session_1"

    async def fake_query(**_):
        yield FakeAssistantMessage()
        yield FakeUserMessage()
        yield FakeResultMessage()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_adapter, "UserMessage", FakeUserMessage)
    monkeypatch.setattr(sdk_adapter, "ResultMessage", FakeResultMessage)
    monkeypatch.setattr(sdk_adapter, "ToolUseBlock", FakeToolUseBlock)
    monkeypatch.setattr(sdk_adapter, "ToolResultBlock", FakeToolResultBlock)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "query", fake_query)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    session_id = adapter.create_session("proj_sdk")

    events = list(adapter.send_message(session_id, "Check state", {"project_name": "Demo"}))
    event_types = [event["type"] for event in events]

    assert "assistant_message_delta" in event_types
    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types
    assert "final_answer" in event_types


def test_sdk_event_mapping_emits_tool_call_failed_when_tool_result_is_not_ok(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeToolUseBlock:
        id = "toolu_2"
        name = "business_analysis"
        input = {
            "project_id": "proj_sdk",
            "action": "data.validate",
            "payload": {},
            "reason": "validate data",
        }

    class FakeToolResultBlock:
        tool_use_id = "toolu_2"
        is_error = True
        content = [{"type": "text", "text": '{"ok": false, "summary": "validation failed"}'}]

    class FakeAssistantMessage:
        content = [FakeToolUseBlock()]

    class FakeUserMessage:
        content = [FakeToolResultBlock()]

    async def fake_query(**_):
        yield FakeAssistantMessage()
        yield FakeUserMessage()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_adapter, "UserMessage", FakeUserMessage)
    monkeypatch.setattr(sdk_adapter, "ToolUseBlock", FakeToolUseBlock)
    monkeypatch.setattr(sdk_adapter, "ToolResultBlock", FakeToolResultBlock)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "query", fake_query)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    session_id = adapter.create_session("proj_sdk")

    events = list(adapter.send_message(session_id, "Validate", {}))

    failed = [event for event in events if event["type"] == "tool_call_failed"]
    assert failed
    assert failed[0]["ok"] is False
    assert failed[0]["action"] == "data.validate"


def test_sdk_event_mapping_emits_error_on_sdk_exception(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    async def fake_query(**_):
        raise RuntimeError("sdk exploded")
        yield

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "query", fake_query)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    session_id = adapter.create_session("proj_sdk")

    events = list(adapter.send_message(session_id, "Hello", {}))

    errors = [event for event in events if event["type"] == "error"]
    assert errors
    assert "sdk exploded" in errors[0]["error"]


def test_business_analysis_tool_call_invokes_gateway_exactly_once(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    calls = []

    class FakeGateway:
        def execute(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                ok=True,
                summary="ok",
                action=kwargs["action_str"],
                artifacts=[],
                error=None,
            )

    server = sdk_adapter.BusinessAnalysisMCPServer(FakeGateway())

    result = server.handle_tool_call(
        "business_analysis",
        {
            "project_id": "proj_tool",
            "action": "project.get_state",
            "payload": {},
            "reason": "need state",
        },
    )

    assert result["ok"] is True
    assert len(calls) == 1
    assert calls[0]["project_id"] == "proj_tool"
    assert calls[0]["action_str"] == "project.get_state"
    assert calls[0]["reason"] == "need state"


def test_tool_handler_returns_is_error_true_instead_of_raising_on_failure():
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class ExplodingGateway:
        def execute(self, **_):
            raise RuntimeError("gateway failed")

    server = sdk_adapter.BusinessAnalysisMCPServer(ExplodingGateway())

    result = server.handle_tool_call(
        "business_analysis",
        {
            "project_id": "proj_tool",
            "action": "project.get_state",
            "payload": {},
            "reason": "need state",
        },
    )

    assert result["is_error"] is True
    assert result["ok"] is False
    assert "gateway failed" in result["error"]["message"]


def test_message_runtime_stores_runtime_provider_and_external_session_id(
    monkeypatch, isolated_db
):
    import app.agent.message_runtime as message_runtime

    class FakeAdapter:
        def __init__(self):
            self.created_for = []

        def create_session(self, project_id):
            self.created_for.append(project_id)
            return "sdk_external_123"

        def resume_session(self, session_id, project_id):
            return None

        def send_message(self, session_id, message, context):
            yield {"type": "final_answer", "message": "ok"}

        def interrupt(self, session_id):
            return None

    fake_adapter = FakeAdapter()

    monkeypatch.setattr(
        message_runtime,
        "get_agent_runtime_config",
        lambda: {"provider": "claude_agent_sdk"},
    )
    monkeypatch.setattr(
        message_runtime,
        "get_claude_adapter",
        lambda config: fake_adapter,
    )

    runtime = message_runtime.MessageRuntime()
    response = runtime.handle_message("proj_runtime", None, "hello", {})

    db = get_session()
    try:
        session = (
            db.query(AnalysisSession)
            .filter(AnalysisSession.id == response["session_id"])
            .one()
        )
        assert session.runtime_provider == "claude_agent_sdk"
        assert session.external_session_id == "sdk_external_123"
    finally:
        db.close()

    assert fake_adapter.created_for == ["proj_runtime"]


def test_session_store_persists_runtime_provider_and_external_session_id(isolated_db):
    store = SessionStore()

    session = store.create_session(
        "proj_store",
        provider="claude_agent_sdk",
        external_session_id="sdk_external_456",
    )

    db = get_session()
    try:
        persisted = db.query(AnalysisSession).filter(AnalysisSession.id == session.id).one()
        assert persisted.runtime_provider == "claude_agent_sdk"
        assert persisted.external_session_id == "sdk_external_456"
    finally:
        db.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not (
        os.environ.get("ANTHROPIC_API_KEY")
        and os.environ.get("RUN_AGENT_SDK_INTEGRATION") == "1"
    ),
    reason="requires ANTHROPIC_API_KEY and RUN_AGENT_SDK_INTEGRATION=1",
)
def test_claude_agent_sdk_integration_smoke():
    from app.agent.claude_agent_sdk_adapter import ClaudeAgentSDKAdapter

    adapter = ClaudeAgentSDKAdapter({"provider": "claude_agent_sdk"})
    session_id = adapter.create_session("proj_integration_smoke")

    events = list(
        adapter.send_message(
            session_id,
            "Reply with a short acknowledgement only.",
            {"project_name": "Integration Smoke"},
        )
    )

    assert any(event["type"] in {"assistant_message_delta", "final_answer"} for event in events)
    assert not any(event["type"] == "error" for event in events)
