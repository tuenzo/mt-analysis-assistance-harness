import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent.claude_adapter import MockClaudeRuntimeAdapter
from app.agent.session_store import SessionStore
from app.core.database import get_session, init_db, reset_engine
from app.projects.models import AnalysisSession


def collect_runtime_events(runtime, session_id, turn_id, predicate, timeout=3.0):
    deadline = time.time() + timeout
    collected = []
    while time.time() < deadline:
        events = runtime.get_events(session_id, turn_id)
        collected.extend(events)
        if predicate(collected):
            return collected
        time.sleep(0.05)
    return collected


@pytest.fixture
def isolated_db():
    import app.agent.message_runtime as message_runtime

    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    reset_engine()
    message_runtime._message_runtime = None
    init_db()
    try:
        yield tmp
    finally:
        if message_runtime._message_runtime is not None:
            message_runtime._message_runtime.wait_for_all_turns()
        message_runtime._message_runtime = None
        reset_engine()
        os.chdir(old_cwd)
        shutil.rmtree(tmp)


def test_adapter_factory_requires_key_when_sdk_provider_requested(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter
    from app.core.config import settings as app_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(app_settings, "anthropic_api_key", "")

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        sdk_adapter.get_claude_adapter({"provider": "claude_agent_sdk"})


def test_adapter_factory_falls_back_to_mock_when_provider_is_mock(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)

    adapter = sdk_adapter.get_claude_adapter({"provider": "mock"})

    assert isinstance(adapter, MockClaudeRuntimeAdapter)


def test_prompt_composer_guides_discover_first_data_load():
    from app.agent.prompt_composer import PromptComposer

    prompt = PromptComposer().compose(
        {
            "project_id": "proj_prompt",
            "project_name": "Prompt",
            "current_stage": "created",
            "runtime_provider": "claude_agent_sdk",
            "available_actions": ["data.discover_source_files", "data.ingest", "schema.infer", "data.validate"],
        },
        "加载 D:\\data\\hello 的数据",
    )

    assert "project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate" in prompt
    assert "selected_files" in prompt
    assert "Data load is complete only after data.validate succeeds" in prompt
    assert "- runtime_provider: claude_agent_sdk" in prompt
    assert "do not infer runtime from demo artifacts" in prompt


def test_sdk_prompt_includes_exact_project_id_instruction():
    from app.agent.claude_agent_sdk_adapter import ClaudeAgentSDKAdapter

    adapter = ClaudeAgentSDKAdapter({"provider": "claude_agent_sdk"})
    prompt = adapter._build_prompt(
        {
            "project_id": "proj_exact_123",
            "project_name": "Exact Project",
            "current_stage": "created",
            "data_quality": "unknown",
        },
        "Check state",
    )

    assert "- project_id: proj_exact_123" in prompt
    assert 'always pass exactly this project_id: "proj_exact_123"' in prompt
    assert "Do not use the route name" in prompt


def test_mock_adapter_emits_autonomous_dataload_tool_sequence():
    adapter = MockClaudeRuntimeAdapter()
    session_id = adapter.create_session("proj_mock")

    events = list(adapter.send_message(session_id, "请 dataload D:\\data\\hello", {"project_name": "Mock"}))
    started = [event for event in events if event["type"] == "tool_call_started"]

    assert [event["action"] for event in started] == [
        "project.get_state",
        "data.discover_source_files",
        "data.ingest",
        "schema.infer",
        "data.validate",
    ]
    ingest = next(event for event in started if event["action"] == "data.ingest")
    assert ingest["payload"]["source_path"].startswith("D:\\data\\hello")
    assert {item["role"] for item in ingest["payload"]["selected_files"]} == {
        "order_info",
        "exposure_info",
        "activity_timeline",
    }


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
    assert adapter._sessions[external_session_id]["workspace_path"].replace("\\", "/").endswith(
        "workspaces/projects/proj_sdk"
    )
    assert adapter._sessions[external_session_id]["skills"] == ["business-analysis"]


def test_sdk_adapter_emits_runtime_diagnostic_without_mock_fallback(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    async def fake_query(**_):
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

    events = list(adapter.send_message(session_id, "Check runtime", {"project_name": "Demo"}))

    diagnostic = next(event for event in events if event["type"] == "runtime_diagnostic")
    assert diagnostic["runtime"] == "claude_agent_sdk"
    assert diagnostic["adapter"] == "ClaudeAgentSDKAdapter"
    assert diagnostic["api_key_present"] is True
    assert diagnostic["auth_token_present"] is True
    assert diagnostic["mock_fallback"] is False
    assert diagnostic["claude_config_dir_isolated"] is True
    assert ".analysis" in diagnostic["claude_config_dir"]
    assert diagnostic["skills"] == ["business-analysis"]
    assert diagnostic["skill_allowed_tools"] == ["Skill(business-analysis)"]


def test_sdk_options_include_project_skill(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces", "skills": ["business-analysis"]}
    )
    session_id = adapter.create_session("proj_sdk")
    options = adapter._build_options(session_id, adapter._sessions[session_id])

    assert options.skills == ["business-analysis"]
    assert "mcp__business_analysis__business_analysis" in options.allowed_tools
    assert "Skill(business-analysis)" not in options.allowed_tools


def test_sdk_options_isolate_claude_config_from_user_account(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_BASE_URL", "http://127.0.0.1:9/anthropic")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    tmp = tempfile.mkdtemp()
    try:
        workspace_root = Path(tmp) / "workspaces"
        adapter = sdk_adapter.ClaudeAgentSDKAdapter(
            {
                "provider": "claude_agent_sdk",
                "workspace_root": str(workspace_root),
                "skills": ["business-analysis"],
            }
        )
        session_id = adapter.create_session("proj_sdk")
        options = adapter._build_options(session_id, adapter._sessions[session_id])

        config_dir = Path(options.env["CLAUDE_CONFIG_DIR"])
        expected_workspace = workspace_root / "projects" / "proj_sdk"

        assert config_dir.exists()
        assert config_dir == expected_workspace / ".analysis" / "claude-sdk-config" / session_id
        assert Path.home() / ".claude" not in config_dir.parents
        assert "ANTHROPIC_API_KEY" not in options.env
        assert options.env["ANTHROPIC_AUTH_TOKEN"] == "test-key"
        assert options.env["ANTHROPIC_API_BASE_URL"] == "http://127.0.0.1:9/anthropic"
        assert options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:9/anthropic"
        assert options.env["CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"] == "1"
    finally:
        shutil.rmtree(tmp)


def test_sdk_options_forward_api_key_for_official_anthropic_host(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_BASE_URL", "https://api.anthropic.com")
    monkeypatch.setattr(sdk_adapter, "HAS_CLAUDE_AGENT_SDK", True)
    monkeypatch.setattr(sdk_adapter, "ClaudeAgentOptions", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(sdk_adapter, "tool", lambda *_, **__: (lambda fn: fn))
    monkeypatch.setattr(sdk_adapter, "create_sdk_mcp_server", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    tmp = tempfile.mkdtemp()
    try:
        adapter = sdk_adapter.ClaudeAgentSDKAdapter(
            {
                "provider": "claude_agent_sdk",
                "workspace_root": str(Path(tmp) / "workspaces"),
                "skills": ["business-analysis"],
            }
        )
        session_id = adapter.create_session("proj_sdk")
        options = adapter._build_options(session_id, adapter._sessions[session_id])

        assert options.env["ANTHROPIC_API_KEY"] == "test-key"
        assert options.env["ANTHROPIC_AUTH_TOKEN"] == "test-key"
    finally:
        shutil.rmtree(tmp)


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


def test_sdk_event_mapping_emits_thinking_block_as_thought(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeThinkingBlock:
        thinking = "Reviewing project facts before choosing an action."

    class FakeAssistantMessage:
        content = [FakeThinkingBlock()]

    monkeypatch.setattr(sdk_adapter, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_adapter, "ThinkingBlock", FakeThinkingBlock)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )

    events = adapter._map_sdk_message(
        FakeAssistantMessage(),
        tool_uses={},
        project_id="proj_sdk",
        runtime_session_id="sess_sdk",
        runtime_turn_id="turn_sdk",
    )

    thought = next(event for event in events if event["type"] == "assistant_thought_delta")
    assert thought["delta"] == "Reviewing project facts before choosing an action."
    assert thought["phase"] == "provider_thinking"
    assert thought["visibility"] == "provider"


def test_sdk_event_mapping_ignores_unsupported_null_tool_use(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeToolUseBlock:
        def __init__(self):
            self.id = "toolu_null"
            self.name = "null"
            self.input = {}

    class FakeAssistantMessage:
        content = [FakeToolUseBlock()]

    monkeypatch.setattr(sdk_adapter, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_adapter, "ToolUseBlock", FakeToolUseBlock)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    tool_uses = {}

    events = adapter._map_sdk_message(
        FakeAssistantMessage(),
        tool_uses=tool_uses,
        project_id="proj_sdk",
        runtime_session_id="sess_sdk",
        runtime_turn_id="turn_sdk",
    )

    assert events == []
    assert tool_uses == {}


def test_sdk_event_mapping_emits_streamed_thinking_delta(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeStreamEvent:
        event = {
            "type": "content_block_delta",
            "delta": {
                "type": "thinking_delta",
                "thinking": "Comparing available actions.",
            },
        }

    monkeypatch.setattr(sdk_adapter, "StreamEvent", FakeStreamEvent)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )

    events = adapter._map_sdk_message(
        FakeStreamEvent(),
        tool_uses={},
        project_id="proj_sdk",
        runtime_session_id="sess_sdk",
        runtime_turn_id="turn_sdk",
    )

    assert events == [
        {
            "type": "assistant_thought_delta",
            "delta": "Comparing available actions.",
            "phase": "provider_thinking",
            "visibility": "provider",
            "source": "claude_agent_sdk",
        }
    ]


def test_sdk_event_mapping_overrides_hallucinated_project_id(monkeypatch, isolated_db):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeToolUseBlock:
        id = "toolu_wrong_project"
        name = "business_analysis"
        input = {
            "project_id": "agent-analysis-test",
            "action": "project.get_state",
            "payload": {},
            "reason": "inspect state",
        }

    class FakeAssistantMessage:
        content = [FakeToolUseBlock()]

    monkeypatch.setattr(sdk_adapter, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_adapter, "ToolUseBlock", FakeToolUseBlock)
    monkeypatch.setattr(sdk_adapter, "get_gateway", lambda: SimpleNamespace())

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    events = adapter._map_sdk_message(
        FakeAssistantMessage(),
        tool_uses={},
        project_id="proj_real_123",
        runtime_session_id="sess_real",
        runtime_turn_id="turn_real",
    )

    started = [event for event in events if event["type"] == "tool_call_started"]
    assert started
    assert started[0]["payload"]["project_id"] == "proj_real_123"


def test_sdk_execution_reuses_pending_tool_call(isolated_db):
    from app.agent.claude_agent_sdk_adapter import ClaudeAgentSDKAdapter
    from app.projects.models import ToolCall

    suffix = uuid.uuid4().hex[:8]
    tool_call_id = f"tc_pending_sdk_{suffix}"
    session_id = f"sess_claim_{suffix}"
    turn_id = f"turn_claim_{suffix}"
    project_id = f"proj_claim_{suffix}"

    db = get_session()
    try:
        db.add(
            ToolCall(
                id=tool_call_id,
                session_id=session_id,
                turn_id=turn_id,
                project_id=project_id,
                tool_name="business_analysis",
                action="project.get_state",
                payload_json="{}",
                payload_hash="sha256:test",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    adapter = ClaudeAgentSDKAdapter({"provider": "claude_agent_sdk"})

    claimed = adapter._claim_pending_sdk_tool_call(
        project_id=project_id,
        action="project.get_state",
        payload={},
        runtime_session_id=session_id,
        runtime_turn_id=turn_id,
    )

    assert claimed == tool_call_id


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


def test_sdk_event_mapping_emits_approval_requested_for_pending_approval(monkeypatch):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    class FakeToolResultBlock:
        tool_use_id = "toolu_approval"
        is_error = False
        content = [{"type": "text", "text": '{"ok": true, "summary": "需要用户审批"}'}]

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    monkeypatch.setattr(
        adapter,
        "_pending_approval",
        lambda *_, **__: {
            "id": "approval_123",
            "tool_call_id": "tc_approval",
            "reason": "高风险 panel build",
            "risk_level": "medium",
            "payload": {"foo": "bar"},
        },
    )

    events = []
    event = adapter._tool_result_event(
        FakeToolResultBlock(),
        {
            "toolu_approval": {
                "tool": "business_analysis",
                "action": "panel.build_category_day",
                "tool_call_id": "tc_approval",
                "persisted": True,
            }
        },
    )
    events.append(event)
    events.append(adapter._approval_requested_event(event))

    assert events[0]["approval_required"] is True
    assert events[0]["approval_id"] == "approval_123"
    assert events[1] == {
        "type": "approval_requested",
        "approval_id": "approval_123",
        "action": "panel.build_category_day",
        "reason": "高风险 panel build",
        "risk_level": "medium",
        "payload": {"foo": "bar"},
        "tool_call_id": "tc_approval",
        "sdk_executed": True,
    }


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


def test_longcat_text_tool_call_executes_gateway_once_and_strips_markup(isolated_db):
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    calls = []

    class FakeGateway:
        def execute(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                ok=True,
                action=kwargs["action_str"],
                summary="Project state loaded",
                artifacts=[],
                state_patch={},
                assistant_hint="",
                error=None,
            )

    adapter = sdk_adapter.ClaudeAgentSDKAdapter(
        {"provider": "claude_agent_sdk", "workspace_root": "./workspaces"}
    )
    adapter._gateway = FakeGateway()
    text = (
        "我先读取状态。"
        "<longcat_tool_call>business_analysis\n"
        "<longcat_arg_key>project_id</longcat_arg_key>\n"
        "<longcat_arg_value>wrong-project</longcat_arg_value>\n"
        "<longcat_arg_key>action</longcat_arg_key>\n"
        "<longcat_arg_value>project.get_state</longcat_arg_value>\n"
        "<longcat_arg_key>payload</longcat_arg_key>\n"
        "<longcat_arg_value>{}</longcat_arg_value>\n"
        "<longcat_arg_key>reason</longcat_arg_key>\n"
        "<longcat_arg_value>need state</longcat_arg_value>\n"
        "</longcat_tool_call>"
    )

    events = adapter._map_text_delta(
        text,
        project_id="proj_runtime",
        runtime_session_id="",
        runtime_turn_id="",
    )
    duplicate_events = adapter._map_text_delta(
        text,
        project_id="proj_runtime",
        runtime_session_id="",
        runtime_turn_id="",
    )

    assert len(calls) == 1
    assert calls[0]["project_id"] == "proj_runtime"
    assert calls[0]["action_str"] == "project.get_state"
    assert [event["type"] for event in events[:2]] == ["tool_call_started", "tool_call_finished"]
    assert events[0]["text_tool_compat"] is True
    assert events[-1] == {"type": "assistant_message_delta", "delta": "我先读取状态。"}
    assert all("<longcat_tool_call>" not in str(event) for event in events + duplicate_events)


def test_longcat_text_tool_max_turn_error_becomes_final_answer():
    import app.agent.claude_agent_sdk_adapter as sdk_adapter

    adapter = sdk_adapter.ClaudeAgentSDKAdapter({"provider": "claude_agent_sdk"})
    adapter._text_tool_results = [
        {
            "action": "project.get_state",
            "ok": True,
            "summary": "Project state loaded",
            "approval": None,
        }
    ]

    assert adapter._is_text_tool_max_turn_error("Reached maximum number of turns (8)")
    assert "project.get_state" in adapter._text_tool_compat_final_answer()
    assert "Project state loaded" in adapter._text_tool_compat_final_answer()


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

    runtime.wait_for_all_turns()
    assert fake_adapter.created_for == ["proj_runtime"]


def test_message_runtime_returns_before_slow_adapter_finishes(
    monkeypatch, isolated_db
):
    import app.agent.message_runtime as message_runtime

    class SlowAdapter:
        def create_session(self, project_id):
            return f"sdk_external_{project_id}"

        def resume_session(self, session_id, project_id):
            return None

        def send_message(self, session_id, message, context):
            time.sleep(0.25)
            yield {
                "type": "assistant_thought_delta",
                "delta": "Still evaluating the request.",
                "phase": "provider_thinking",
            }
            yield {"type": "final_answer", "message": "ok"}

        def interrupt(self, session_id):
            return None

    monkeypatch.setattr(
        message_runtime,
        "get_agent_runtime_config",
        lambda: {"provider": "claude_agent_sdk"},
    )
    monkeypatch.setattr(
        message_runtime,
        "get_claude_adapter",
        lambda config: SlowAdapter(),
    )

    runtime = message_runtime.MessageRuntime()
    start = time.perf_counter()
    response = runtime.handle_message("proj_slow", None, "hello", {})
    elapsed = time.perf_counter() - start

    assert elapsed < 0.2

    events = collect_runtime_events(
        runtime,
        response["session_id"],
        response["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
        timeout=3.0,
    )
    event_types = [event["type"] for event in events]
    assert "assistant_thought_delta" in event_types
    assert "final_answer" in event_types
    assert runtime.wait_for_turn(response["turn_id"])


def test_message_runtime_does_not_start_concurrent_turn_in_same_session(
    monkeypatch, isolated_db
):
    import app.agent.message_runtime as message_runtime

    class SlowAdapter:
        def __init__(self):
            self.send_count = 0

        def create_session(self, project_id):
            return f"sdk_external_{project_id}"

        def resume_session(self, session_id, project_id):
            return None

        def send_message(self, session_id, message, context):
            self.send_count += 1
            time.sleep(0.25)
            yield {"type": "final_answer", "message": "first done"}

        def interrupt(self, session_id):
            return None

    adapter = SlowAdapter()
    monkeypatch.setattr(
        message_runtime,
        "get_agent_runtime_config",
        lambda: {"provider": "claude_agent_sdk"},
    )
    monkeypatch.setattr(
        message_runtime,
        "get_claude_adapter",
        lambda config: adapter,
    )

    runtime = message_runtime.MessageRuntime()
    first = runtime.handle_message("proj_busy", None, "first", {})
    second = runtime.handle_message("proj_busy", first["session_id"], "second", {})

    assert second["status"] == "completed"
    events = collect_runtime_events(
        runtime,
        second["session_id"],
        second["turn_id"],
        lambda collected: any(event.get("type") == "final_answer" for event in collected),
        timeout=1.0,
    )

    final = next(event for event in events if event["type"] == "final_answer")
    assert "上一轮 Agent 任务仍在运行" in final["message"]
    assert adapter.send_count == 1
    assert runtime.wait_for_turn(first["turn_id"])


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
