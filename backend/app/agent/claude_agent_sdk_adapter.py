import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        StreamEvent,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        create_sdk_mcp_server,
        query,
        tool,
    )

    HAS_CLAUDE_AGENT_SDK = True
except ImportError:
    AssistantMessage = None
    ClaudeAgentOptions = None
    ResultMessage = None
    StreamEvent = None
    ToolResultBlock = None
    ToolUseBlock = None
    UserMessage = None
    create_sdk_mcp_server = None
    query = None
    tool = None
    HAS_CLAUDE_AGENT_SDK = False

from app.agent.claude_adapter import ClaudeRuntimeAdapter
from app.core.database import get_session
from app.core.permissions import PermissionLevel, action_to_permission_level
from app.projects.models import ApprovalRequest, ToolCall
from app.tools.gateway import get_gateway
from app.tools.schemas import BusinessAnalysisAction, ToolResult


SDK_MCP_SERVER_NAME = "business_analysis"
SDK_TOOL_NAME = "business_analysis"
SDK_ALLOWED_TOOL = "mcp__business_analysis__business_analysis"
READ_ONLY_BUILTINS = ["Read", "Glob", "Grep", "LS"]


class BusinessAnalysisMCPServer:
    """Small testable wrapper around the single business_analysis gateway tool."""

    def __init__(self, gateway):
        self.gateway = gateway

    def handle_tool_call(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        *,
        tool_call_id: str | None = None,
        session_id: str = "",
        turn_id: str = "",
    ) -> dict[str, Any]:
        if tool_name != SDK_TOOL_NAME:
            return {
                "ok": False,
                "is_error": True,
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Unknown tool: {tool_name}",
                    "details": {},
                },
            }

        try:
            result = self.gateway.execute(
                tool_call_id=tool_call_id or f"tc_{uuid.uuid4().hex[:12]}",
                project_id=parameters["project_id"],
                action_str=parameters["action"],
                payload=parameters.get("payload") or {},
                reason=parameters.get("reason", ""),
                session_id=session_id,
                turn_id=turn_id,
                user_permission_level=PermissionLevel.EXTERNAL_SYNC,
            )
            body = _tool_result_body(result)
            return {**body, "is_error": not body.get("ok", False)}
        except Exception as exc:
            return {
                "ok": False,
                "is_error": True,
                "action": parameters.get("action", ""),
                "summary": "",
                "artifacts": [],
                "state_patch": {},
                "assistant_hint": "",
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(exc),
                    "details": {},
                },
            }

    @staticmethod
    def to_sdk_content(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "is_error": bool(result.get("is_error")),
        }


def _tool_result_body(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {
        "ok": bool(getattr(result, "ok", False)),
        "action": getattr(result, "action", ""),
        "summary": getattr(result, "summary", ""),
        "artifacts": getattr(result, "artifacts", []),
        "state_patch": getattr(result, "state_patch", {}),
        "assistant_hint": getattr(result, "assistant_hint", ""),
        "error": getattr(result, "error", None),
    }


class ClaudeAgentSDKAdapter(ClaudeRuntimeAdapter):
    """Claude Agent SDK adapter with a single in-process business_analysis MCP tool."""

    def __init__(self, settings: dict | None = None):
        from app.core.config import settings as app_settings

        self._settings = settings or {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._interrupted: set[str] = set()
        self._gateway = get_gateway()

        self._api_key = os.environ.get("ANTHROPIC_API_KEY") or app_settings.anthropic_api_key
        self._base_url = (
            os.environ.get("ANTHROPIC_API_BASE_URL")
            or app_settings.anthropic_api_base_url
            or ""
        )
        self._model = (
            os.environ.get("ANTHROPIC_API_MODEL")
            or app_settings.anthropic_api_model
            or "claude-opus-4-5-20250501"
        )
        self._permission_mode = self._settings.get("permission_mode", "dontAsk")
        self._enable_user_settings = self._settings.get("enable_user_setting_sources", True)
        self._allow_builtin_read_tools = self._settings.get("allow_builtin_read_tools", False)
        self._workspace_root = Path(self._settings.get("workspace_root", "./workspaces"))
        self._active_runtime_context: dict[str, str] = {}
        self._executed_tool_calls: list[dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return HAS_CLAUDE_AGENT_SDK and bool(self._api_key)

    def create_session(self, project_id: str) -> str:
        if not self.available:
            return self._create_mock_session(project_id)

        external_session_id = str(uuid.uuid4())
        workspace_path = self._workspace_root / project_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        self._sessions[external_session_id] = {
            "project_id": project_id,
            "workspace_path": str(workspace_path),
            "has_started": False,
            "interrupted": False,
        }
        return external_session_id

    def _create_mock_session(self, project_id: str) -> str:
        session_id = f"mock_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = {"project_id": project_id, "interrupted": False}
        return session_id

    def resume_session(self, session_id: str, project_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "project_id": project_id,
                "workspace_path": str(self._workspace_root / project_id),
                "has_started": True,
                "interrupted": False,
            }

    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        if session_id in self._interrupted:
            self._interrupted.discard(session_id)
            return

        if not self.available or session_id.startswith("mock_"):
            yield from self._mock_send_message(session_id, message, context)
            return

        try:
            events = asyncio.run(self._send_message_async(session_id, message, context))
        except RuntimeError as exc:
            if "asyncio.run() cannot be called from a running event loop" not in str(exc):
                yield {"type": "error", "error": str(exc)}
                return
            loop = asyncio.new_event_loop()
            try:
                events = loop.run_until_complete(self._send_message_async(session_id, message, context))
            except Exception as nested_exc:
                yield {"type": "error", "error": str(nested_exc)}
                return
            finally:
                loop.close()
        except Exception as exc:
            yield {"type": "error", "error": str(exc)}
            return

        for event in events:
            yield event

    async def _send_message_async(self, session_id: str, message: str, context: dict) -> list[dict]:
        events: list[dict] = []
        session = self._sessions.setdefault(
            session_id,
            {
                "project_id": context.get("project_id", ""),
                "workspace_path": str(self._workspace_root / context.get("project_id", "")),
                "has_started": True,
                "interrupted": False,
            },
        )
        project_id = context.get("project_id") or session.get("project_id")
        runtime_session_id = context.get("runtime_session_id", "")
        runtime_turn_id = context.get("runtime_turn_id", "")
        tool_uses: dict[str, dict[str, Any]] = {}

        options = self._build_options(session_id, session)
        prompt = self._build_prompt(context, message)

        self._active_runtime_context = {
            "project_id": project_id,
            "runtime_session_id": runtime_session_id,
            "runtime_turn_id": runtime_turn_id,
        }
        self._executed_tool_calls = []
        async for sdk_message in query(prompt=prompt, options=options):
            for event in self._map_sdk_message(
                sdk_message,
                tool_uses=tool_uses,
                project_id=project_id,
                runtime_session_id=runtime_session_id,
                runtime_turn_id=runtime_turn_id,
            ):
                events.append(event)

            sdk_session_id = getattr(sdk_message, "session_id", None)
            if sdk_session_id and sdk_session_id != session_id:
                events.append({"type": "external_session_updated", "external_session_id": sdk_session_id})
                self._sessions[sdk_session_id] = {**session, "has_started": True}

        session["has_started"] = True
        self._active_runtime_context = {}
        return events

    def _build_options(self, session_id: str, session: dict[str, Any]):
        mcp_server = self._create_business_analysis_mcp_server()
        allowed_tools = [SDK_ALLOWED_TOOL]
        builtins = READ_ONLY_BUILTINS if self._allow_builtin_read_tools else []
        allowed_tools.extend(builtins)

        env = {}
        if self._api_key:
            env["ANTHROPIC_API_KEY"] = self._api_key
        if self._base_url:
            env["ANTHROPIC_API_BASE_URL"] = self._base_url
            env["ANTHROPIC_BASE_URL"] = self._base_url

        kwargs = {
            "cwd": session.get("workspace_path"),
            "model": self._model,
            "tools": builtins,
            "allowed_tools": allowed_tools,
            "mcp_servers": {SDK_MCP_SERVER_NAME: mcp_server},
            "permission_mode": self._permission_mode,
            "env": env,
            "max_turns": 8,
        }
        if not self._enable_user_settings:
            kwargs["setting_sources"] = []
        if session.get("has_started"):
            kwargs["resume"] = session_id
        else:
            kwargs["session_id"] = session_id
        return ClaudeAgentOptions(**kwargs)

    def _create_business_analysis_mcp_server(self):
        server = BusinessAnalysisMCPServer(self._gateway)

        @tool(
            SDK_TOOL_NAME,
            "Run controlled business analysis actions inside the current project workspace.",
            {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": [action.value for action in BusinessAnalysisAction],
                    },
                    "payload": {"type": "object"},
                    "reason": {"type": "string"},
                },
                "required": ["project_id", "action", "payload", "reason"],
            },
        )
        async def business_analysis(args: dict[str, Any]) -> dict[str, Any]:
            tool_call_id = args.get("_runtime_tool_call_id") or f"tc_{uuid.uuid4().hex[:12]}"
            project_id = args["project_id"]
            action = args["action"]
            payload = args.get("payload") or {}
            reason = args.get("reason") or ""
            runtime_context = self._active_runtime_context
            runtime_session_id = args.get("_runtime_session_id") or runtime_context.get("runtime_session_id", "")
            runtime_turn_id = args.get("_runtime_turn_id") or runtime_context.get("runtime_turn_id", "")
            if not args.get("_runtime_tool_call_id") and runtime_session_id and runtime_turn_id:
                tool_call_id = self._persist_sdk_tool_call(
                    project_id=project_id,
                    action=action,
                    payload=payload,
                    reason=reason,
                    runtime_session_id=runtime_session_id,
                    runtime_turn_id=runtime_turn_id,
                )

            body = server.handle_tool_call(
                SDK_TOOL_NAME,
                {
                    "project_id": project_id,
                    "action": action,
                    "payload": payload,
                    "reason": reason,
                },
                tool_call_id=tool_call_id,
                session_id=runtime_session_id,
                turn_id=runtime_turn_id,
            )
            self._executed_tool_calls.append(
                {
                    "tool_call_id": tool_call_id,
                    "project_id": project_id,
                    "action": action,
                    "payload": payload,
                    "result": body,
                }
            )
            return BusinessAnalysisMCPServer.to_sdk_content(body)

        return create_sdk_mcp_server(SDK_MCP_SERVER_NAME, version="1.0.0", tools=[business_analysis])

    def _map_sdk_message(
        self,
        sdk_message: Any,
        tool_uses: dict[str, dict[str, Any]],
        project_id: str,
        runtime_session_id: str,
        runtime_turn_id: str,
    ) -> list[dict]:
        events: list[dict] = []

        if StreamEvent is not None and isinstance(sdk_message, StreamEvent):
            delta = self._stream_delta_text(sdk_message.event)
            if delta:
                events.append({"type": "assistant_message_delta", "delta": delta})
            return events

        if AssistantMessage is not None and isinstance(sdk_message, AssistantMessage):
            for block in sdk_message.content:
                if ToolUseBlock is not None and isinstance(block, ToolUseBlock):
                    tool_input = dict(block.input or {})
                    runtime_tool_call_id = self._claim_executed_tool_call(
                        action=tool_input.get("action", SDK_TOOL_NAME),
                        payload=tool_input.get("payload") or {},
                    )
                    if not runtime_tool_call_id:
                        runtime_tool_call_id = self._persist_sdk_tool_call(
                            project_id=tool_input.get("project_id") or project_id,
                            action=tool_input.get("action", SDK_TOOL_NAME),
                            payload=tool_input.get("payload") or {},
                            reason=tool_input.get("reason", ""),
                            runtime_session_id=runtime_session_id,
                            runtime_turn_id=runtime_turn_id,
                        )
                    tool_input["_runtime_tool_call_id"] = runtime_tool_call_id
                    tool_input["_runtime_session_id"] = runtime_session_id
                    tool_input["_runtime_turn_id"] = runtime_turn_id
                    block.input = tool_input
                    tool_uses[block.id] = {
                        "tool": block.name,
                        "action": tool_input.get("action", block.name),
                        "payload": tool_input,
                        "tool_call_id": runtime_tool_call_id,
                        "persisted": bool(runtime_session_id and runtime_turn_id),
                    }
                    events.append(
                        {
                            "type": "tool_call_started",
                            "tool": block.name,
                            "action": tool_input.get("action", block.name),
                            "payload": self._public_tool_payload(tool_input),
                            "tool_call_id": runtime_tool_call_id,
                            "sdk_executed": True,
                        }
                    )
                elif hasattr(block, "text"):
                    events.append({"type": "assistant_message_delta", "delta": block.text})
            return events

        if UserMessage is not None and isinstance(sdk_message, UserMessage):
            for block in sdk_message.content if isinstance(sdk_message.content, list) else []:
                if ToolResultBlock is not None and isinstance(block, ToolResultBlock):
                    event = self._tool_result_event(block, tool_uses)
                    if event:
                        events.append(event)
            return events

        if ResultMessage is not None and isinstance(sdk_message, ResultMessage):
            if sdk_message.is_error:
                events.append(
                    {
                        "type": "error",
                        "error": self._result_error_message(sdk_message),
                        "external_session_id": sdk_message.session_id,
                    }
                )
            else:
                events.append(
                    {
                        "type": "final_answer",
                        "message": sdk_message.result or "",
                        "external_session_id": sdk_message.session_id,
                    }
                )
            return events

        return events

    def _claim_executed_tool_call(self, action: str, payload: dict) -> str | None:
        for index, call in enumerate(self._executed_tool_calls):
            if call.get("action") == action and call.get("payload") == payload:
                return self._executed_tool_calls.pop(index)["tool_call_id"]
        return None

    def _persist_sdk_tool_call(
        self,
        project_id: str,
        action: str,
        payload: dict,
        reason: str,
        runtime_session_id: str,
        runtime_turn_id: str,
    ) -> str:
        tool_call_id = f"tc_{uuid.uuid4().hex[:12]}"
        if not runtime_session_id or not runtime_turn_id:
            return tool_call_id

        try:
            required_permission = action_to_permission_level(BusinessAnalysisAction(action))
        except ValueError:
            required_permission = PermissionLevel.SAFE_COMPUTE

        db = get_session()
        try:
            tc = ToolCall(
                id=tool_call_id,
                session_id=runtime_session_id,
                turn_id=runtime_turn_id,
                project_id=project_id,
                tool_name=SDK_TOOL_NAME,
                action=action,
                payload_json=json.dumps(payload, ensure_ascii=False),
                payload_hash=f"sha256:{uuid.uuid4().hex}",
                reason=reason,
                status="pending",
                permission_level=required_permission,
                created_at=datetime.now().isoformat(),
            )
            db.add(tc)
            db.commit()
        finally:
            db.close()
        return tool_call_id

    def _tool_result_event(self, block: Any, tool_uses: dict[str, dict[str, Any]]) -> dict | None:
        tool_use = tool_uses.get(block.tool_use_id)
        if not tool_use:
            return None

        result = self._parse_tool_result(block.content)
        ok = not bool(block.is_error)
        if isinstance(result, dict) and "ok" in result:
            ok = bool(result.get("ok"))

        action = tool_use.get("action", SDK_TOOL_NAME)
        summary = result.get("summary", "") if isinstance(result, dict) else ""
        event = {
            "type": "tool_call_finished" if ok else "tool_call_failed",
            "tool": tool_use.get("tool", SDK_TOOL_NAME),
            "action": action,
            "ok": ok,
            "summary": summary,
            "tool_call_id": tool_use.get("tool_call_id"),
            "sdk_executed": True,
        }
        approval = self._pending_approval(tool_use.get("tool_call_id")) if tool_use.get("persisted") else None
        if approval:
            event["approval_required"] = True
            event["approval_id"] = approval.id
        return event

    def _pending_approval(self, tool_call_id: str | None):
        if not tool_call_id:
            return None
        db = get_session()
        try:
            return (
                db.query(ApprovalRequest)
                .filter(ApprovalRequest.tool_call_id == tool_call_id, ApprovalRequest.status == "pending")
                .first()
            )
        finally:
            db.close()

    @staticmethod
    def _parse_tool_result(content: Any) -> Any:
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(
                item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"
            )
        else:
            text = ""
        try:
            return json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return {"summary": text}

    @staticmethod
    def _public_tool_payload(payload: dict) -> dict:
        return {key: value for key, value in payload.items() if not key.startswith("_runtime_")}

    @staticmethod
    def _stream_delta_text(event: dict) -> str:
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                return delta.get("text", "")
        return ""

    @staticmethod
    def _result_error_message(message: Any) -> str:
        if getattr(message, "errors", None):
            return "; ".join(str(error) for error in message.errors)
        return message.result or "Claude Agent SDK runtime failed."

    def _mock_send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        from app.agent.claude_adapter import MockClaudeRuntimeAdapter

        mock = MockClaudeRuntimeAdapter()
        yield from mock.send_message(session_id, message, context)

    def interrupt(self, session_id: str) -> None:
        self._interrupted.add(session_id)
        if session_id in self._sessions:
            self._sessions[session_id]["interrupted"] = True

    def _build_prompt(self, context: dict, message: str) -> str:
        project_name = context.get("project_name", "unknown project")
        current_stage = context.get("current_stage", "unknown")
        data_quality = context.get("data_quality", "unknown")

        return f"""You are a business analysis assistant working in project "{project_name}".

Project state:
- current_stage: {current_stage}
- data_quality: {data_quality}

You may answer directly for discussion or clarification. When project state, data, analysis pipelines,
artifacts, reports, or memory candidates are needed, use exactly this tool:
business_analysis(project_id, action, payload, reason)

Only use project facts from the backend workspace context and tool results. Do not read local source
data files directly. For CSV directory ingest, first call business_analysis with action
"data.discover_source_files". Inspect filenames, headers, and previews, then call "data.ingest"
with selected_files: [{{"source_path": "...", "role": "order_info|exposure_info|activity_timeline|unknown", "reason": "..."}}].

User message:
{message}"""


def get_claude_adapter(settings: dict | None = None) -> ClaudeRuntimeAdapter:
    from app.agent.claude_adapter import MockClaudeRuntimeAdapter
    from app.core.config import settings as app_settings

    provider = (settings or {}).get("provider", "mock")
    api_key = os.environ.get("ANTHROPIC_API_KEY") or app_settings.anthropic_api_key

    if provider == "claude_agent_sdk" and api_key and HAS_CLAUDE_AGENT_SDK:
        return ClaudeAgentSDKAdapter(settings)
    return MockClaudeRuntimeAdapter()
