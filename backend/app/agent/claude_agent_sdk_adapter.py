import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional
from urllib.parse import urlparse

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        StreamEvent,
        ThinkingBlock,
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
    ThinkingBlock = None
    ToolResultBlock = None
    ToolUseBlock = None
    UserMessage = None
    create_sdk_mcp_server = None
    query = None
    tool = None
    HAS_CLAUDE_AGENT_SDK = False

from app.agent.claude_adapter import ClaudeRuntimeAdapter
from app.core.config import resolve_project_path, settings as app_settings
from app.core.database import get_session
from app.core.permissions import PermissionLevel, action_to_permission_level
from app.projects.models import ApprovalRequest, Project, ToolCall
from app.tools.gateway import get_gateway
from app.tools.schemas import BusinessAnalysisAction, ToolResult
from app.agent.python_env import apply_python_environment, discover_python_environment
from app.workspace.skills import ensure_project_skill_files, normalize_skill_names


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
        self._auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or self._api_key
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
        self._skills = normalize_skill_names(self._settings.get("skills"))
        self._isolate_claude_config = self._settings.get("isolate_claude_config", True)
        workspace_root_setting = self._settings.get("workspace_root")
        if workspace_root_setting in {None, "", "./workspaces", "workspaces"}:
            self._workspace_root = app_settings.workspace_root
        else:
            self._workspace_root = resolve_project_path(workspace_root_setting)
        self._active_runtime_context: dict[str, str] = {}
        self._executed_tool_calls: list[dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return HAS_CLAUDE_AGENT_SDK and bool(self._api_key)

    def _unavailable_reason(self) -> str:
        if not HAS_CLAUDE_AGENT_SDK:
            return "claude_agent_sdk is not installed or could not be imported."
        if not self._api_key:
            return "ANTHROPIC_API_KEY is not configured."
        return "Claude Agent SDK adapter is unavailable."

    def create_session(self, project_id: str) -> str:
        if not self.available:
            raise RuntimeError(self._unavailable_reason())

        external_session_id = str(uuid.uuid4())
        workspace_path = self._resolve_project_workspace_path(project_id)
        workspace_path.mkdir(parents=True, exist_ok=True)
        config_dir = self._ensure_claude_config_dir(workspace_path, external_session_id)
        self._sessions[external_session_id] = {
            "project_id": project_id,
            "workspace_path": str(workspace_path),
            "config_dir": str(config_dir),
            "skills": self._ensure_workspace_skills(workspace_path),
            "has_started": False,
            "interrupted": False,
        }
        return external_session_id

    def resume_session(self, session_id: str, project_id: str) -> None:
        if session_id not in self._sessions:
            workspace_path = self._resolve_project_workspace_path(project_id)
            workspace_path.mkdir(parents=True, exist_ok=True)
            config_dir = self._ensure_claude_config_dir(workspace_path, session_id)
            self._sessions[session_id] = {
                "project_id": project_id,
                "workspace_path": str(workspace_path),
                "config_dir": str(config_dir),
                "skills": self._ensure_workspace_skills(workspace_path),
                "has_started": True,
                "interrupted": False,
            }

    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        if session_id in self._interrupted:
            self._interrupted.discard(session_id)
            return

        if not self.available or session_id.startswith("mock_"):
            yield {"type": "error", "error": self._unavailable_reason()}
            return

        loop = asyncio.new_event_loop()
        async_generator = self._iter_message_events(session_id, message, context)
        try:
            while True:
                try:
                    event = loop.run_until_complete(async_generator.__anext__())
                except StopAsyncIteration:
                    break
                yield event
        except Exception as exc:
            yield {"type": "error", "error": str(exc)}
            return
        finally:
            try:
                loop.run_until_complete(async_generator.aclose())
            except Exception:
                pass
            loop.close()

    async def _send_message_async(self, session_id: str, message: str, context: dict) -> list[dict]:
        return [event async for event in self._iter_message_events(session_id, message, context)]

    async def _iter_message_events(self, session_id: str, message: str, context: dict):
        default_workspace_path = self._resolve_project_workspace_path(context.get("project_id", ""))
        default_workspace_path.mkdir(parents=True, exist_ok=True)
        session = self._sessions.setdefault(
            session_id,
            {
                "project_id": context.get("project_id", ""),
                "workspace_path": str(default_workspace_path),
                "config_dir": str(self._ensure_claude_config_dir(default_workspace_path, session_id)),
                "skills": self._ensure_workspace_skills(default_workspace_path),
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
        yield self._runtime_diagnostic_event(session)

        self._active_runtime_context = {
            "project_id": project_id,
            "runtime_session_id": runtime_session_id,
            "runtime_turn_id": runtime_turn_id,
        }
        self._executed_tool_calls = []
        try:
            async for sdk_message in query(prompt=prompt, options=options):
                for event in self._map_sdk_message(
                    sdk_message,
                    tool_uses=tool_uses,
                    project_id=project_id,
                    runtime_session_id=runtime_session_id,
                    runtime_turn_id=runtime_turn_id,
                ):
                    yield event

                sdk_session_id = getattr(sdk_message, "session_id", None)
                if sdk_session_id and sdk_session_id != session_id:
                    yield {"type": "external_session_updated", "external_session_id": sdk_session_id}
                    self._sessions[sdk_session_id] = {**session, "has_started": True}
        finally:
            session["has_started"] = True
            self._active_runtime_context = {}

    def _build_options(self, session_id: str, session: dict[str, Any]):
        mcp_server = self._create_business_analysis_mcp_server()
        allowed_tools = [SDK_ALLOWED_TOOL]
        builtins = READ_ONLY_BUILTINS if self._allow_builtin_read_tools else []
        allowed_tools.extend(builtins)

        env = {}
        forward_api_key_env = self._should_forward_api_key_env()
        if self._api_key and forward_api_key_env:
            env["ANTHROPIC_API_KEY"] = self._api_key
        if self._auth_token:
            env["ANTHROPIC_AUTH_TOKEN"] = self._auth_token
        if self._base_url:
            env["ANTHROPIC_API_BASE_URL"] = self._base_url
            env["ANTHROPIC_BASE_URL"] = self._base_url
        if self._isolate_claude_config:
            workspace_path = Path(session.get("workspace_path") or self._workspace_root)
            config_dir = session.get("config_dir") or str(
                self._ensure_claude_config_dir(workspace_path, session_id)
            )
            session["config_dir"] = config_dir
            env["CLAUDE_CONFIG_DIR"] = config_dir
        workspace_path = Path(session.get("workspace_path") or self._workspace_root)
        env = apply_python_environment(env, workspace_path)
        session["python_environment"] = discover_python_environment(workspace_path).as_dict()
        env.setdefault("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", "1")

        kwargs = {
            "cwd": session.get("workspace_path"),
            "model": self._model,
            "tools": builtins,
            "allowed_tools": allowed_tools,
            "mcp_servers": {SDK_MCP_SERVER_NAME: mcp_server},
            "permission_mode": self._permission_mode,
            "env": env,
            "max_turns": 8,
            "include_partial_messages": True,
        }
        if self._skills is not None:
            kwargs["skills"] = session.get("skills", self._skills)
        if not self._enable_user_settings:
            kwargs["setting_sources"] = ["project"] if self._skills else []
        if session.get("has_started"):
            kwargs["resume"] = session_id
        else:
            kwargs["session_id"] = session_id
        return ClaudeAgentOptions(**kwargs)

    def _runtime_diagnostic_event(self, session: dict[str, Any]) -> dict[str, Any]:
        parsed_base_url = urlparse(self._base_url) if self._base_url else None
        skills = session.get("skills", self._skills)
        return {
            "type": "runtime_diagnostic",
            "runtime": "claude_agent_sdk",
            "adapter": "ClaudeAgentSDKAdapter",
            "sdk_available": HAS_CLAUDE_AGENT_SDK,
            "api_key_present": bool(self._api_key),
            "api_key_env_forwarded": self._should_forward_api_key_env(),
            "auth_token_present": bool(self._auth_token),
            "model": self._model,
            "base_url_host": parsed_base_url.netloc if parsed_base_url else "",
            "mock_fallback": False,
            "claude_config_dir_isolated": bool(self._isolate_claude_config),
            "claude_config_dir": session.get("config_dir", ""),
            "skills": skills,
            "skill_allowed_tools": self._skill_allowed_tools(skills),
            "workspace_path": session.get("workspace_path", ""),
            "python_environment": session.get("python_environment", {}),
        }

    def _resolve_project_workspace_path(self, project_id: str) -> Path:
        if project_id:
            db = None
            try:
                db = get_session()
                project = db.query(Project).filter(Project.id == project_id).first()
                if project and project.workspace_path:
                    return resolve_project_path(project.workspace_path)
            except Exception:
                pass
            finally:
                if db is not None:
                    db.close()
        return self._workspace_root / "projects" / (project_id or "_runtime")

    def _should_forward_api_key_env(self) -> bool:
        """Custom Anthropic-compatible proxies often require bearer auth only."""
        if not self._base_url:
            return True
        host = urlparse(self._base_url).netloc.lower()
        if not host:
            return True
        if os.getenv("ANTHROPIC_FORWARD_API_KEY", "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
        return host.endswith("anthropic.com")

    def _ensure_claude_config_dir(self, workspace_path: Path, session_id: str) -> Path:
        safe_session_id = "".join(
            char if char.isalnum() or char in {"-", "_"} else "_" for char in session_id
        )
        config_dir = workspace_path / ".analysis" / "claude-sdk-config" / safe_session_id
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _ensure_workspace_skills(self, workspace_path: Path) -> list[str] | str:
        if self._skills == "all":
            ensure_project_skill_files(workspace_path, self._skills)
            return self._skills
        return ensure_project_skill_files(workspace_path, self._skills)

    @staticmethod
    def _skill_allowed_tools(skills: Any) -> list[str]:
        if skills == "all":
            return ["Skill"]
        if not skills:
            return []
        return [f"Skill({name})" for name in skills]

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
            runtime_context = self._active_runtime_context
            project_id = runtime_context.get("project_id") or args["project_id"]
            args["project_id"] = project_id
            action = args["action"]
            payload = args.get("payload") or {}
            reason = args.get("reason") or ""
            runtime_session_id = args.get("_runtime_session_id") or runtime_context.get("runtime_session_id", "")
            runtime_turn_id = args.get("_runtime_turn_id") or runtime_context.get("runtime_turn_id", "")
            if not args.get("_runtime_tool_call_id") and runtime_session_id and runtime_turn_id:
                tool_call_id = self._claim_pending_sdk_tool_call(
                    project_id=project_id,
                    action=action,
                    payload=payload,
                    runtime_session_id=runtime_session_id,
                    runtime_turn_id=runtime_turn_id,
                ) or self._persist_sdk_tool_call(
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
            thought_delta = self._stream_thought_delta_text(sdk_message.event)
            if thought_delta:
                events.append(
                    {
                        "type": "assistant_thought_delta",
                        "delta": thought_delta,
                        "phase": "provider_thinking",
                        "visibility": "provider",
                        "source": "claude_agent_sdk",
                    }
                )
            delta = self._stream_delta_text(sdk_message.event)
            if delta:
                events.append({"type": "assistant_message_delta", "delta": delta})
            return events

        if AssistantMessage is not None and isinstance(sdk_message, AssistantMessage):
            for block in sdk_message.content:
                if ToolUseBlock is not None and isinstance(block, ToolUseBlock):
                    tool_input = dict(block.input or {})
                    if project_id:
                        tool_input["project_id"] = project_id
                    tool_name = self._display_tool_name(block.name)
                    action = tool_input.get("action") or SDK_TOOL_NAME
                    runtime_tool_call_id = self._claim_executed_tool_call(
                        action=action,
                        payload=tool_input.get("payload") or {},
                    )
                    if not runtime_tool_call_id:
                        runtime_tool_call_id = self._persist_sdk_tool_call(
                            project_id=tool_input.get("project_id") or project_id,
                            action=action,
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
                        "tool": tool_name,
                        "action": action,
                        "payload": tool_input,
                        "tool_call_id": runtime_tool_call_id,
                        "persisted": bool(runtime_session_id and runtime_turn_id),
                        "runtime_session_id": runtime_session_id,
                        "runtime_turn_id": runtime_turn_id,
                    }
                    events.append(
                        {
                            "type": "tool_call_started",
                            "tool": tool_name,
                            "action": action,
                            "payload": self._public_tool_payload(tool_input),
                            "tool_call_id": runtime_tool_call_id,
                            "sdk_executed": True,
                        }
                    )
                elif ThinkingBlock is not None and isinstance(block, ThinkingBlock):
                    thinking = getattr(block, "thinking", "")
                    if thinking:
                        events.append(
                            {
                                "type": "assistant_thought_delta",
                                "delta": thinking,
                                "phase": "provider_thinking",
                                "visibility": "provider",
                                "source": "claude_agent_sdk",
                            }
                        )
                elif hasattr(block, "thinking"):
                    thinking = getattr(block, "thinking", "")
                    if thinking:
                        events.append(
                            {
                                "type": "assistant_thought_delta",
                                "delta": thinking,
                                "phase": "provider_thinking",
                                "visibility": "provider",
                                "source": "claude_agent_sdk",
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
                        approval_event = self._approval_requested_event(event)
                        if approval_event:
                            events.append(approval_event)
            return events

        if ResultMessage is not None and isinstance(sdk_message, ResultMessage):
            events.append(self._result_usage_event(sdk_message))
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

    @staticmethod
    def _result_usage_event(message: Any) -> dict[str, Any]:
        return {
            "type": "runtime_usage",
            "runtime": "claude_agent_sdk",
            "external_session_id": getattr(message, "session_id", None),
            "duration_ms": getattr(message, "duration_ms", None),
            "duration_api_ms": getattr(message, "duration_api_ms", None),
            "num_turns": getattr(message, "num_turns", None),
            "total_cost_usd": getattr(message, "total_cost_usd", None),
            "usage": getattr(message, "usage", None) or {},
            "model_usage": getattr(message, "model_usage", None) or {},
        }

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

    def _claim_pending_sdk_tool_call(
        self,
        project_id: str,
        action: str,
        payload: dict,
        runtime_session_id: str,
        runtime_turn_id: str,
    ) -> str | None:
        db = get_session()
        try:
            rows = (
                db.query(ToolCall)
                .filter(
                    ToolCall.project_id == project_id,
                    ToolCall.session_id == runtime_session_id,
                    ToolCall.turn_id == runtime_turn_id,
                    ToolCall.action == action,
                    ToolCall.status == "pending",
                )
                .order_by(ToolCall.created_at.asc(), ToolCall.id.asc())
                .all()
            )
            for row in rows:
                try:
                    row_payload = json.loads(row.payload_json or "{}")
                except json.JSONDecodeError:
                    row_payload = {}
                if row_payload == payload:
                    return row.id
            return None
        finally:
            db.close()

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
        approval = (
            self._pending_approval(
                tool_use.get("tool_call_id"),
                session_id=tool_use.get("runtime_session_id"),
                turn_id=tool_use.get("runtime_turn_id"),
                action=action,
            )
            if tool_use.get("persisted")
            else None
        )
        if approval:
            event["approval_required"] = True
            event["approval_id"] = approval["id"]
            event["approval_reason"] = approval["reason"]
            event["risk_level"] = approval["risk_level"]
            event["approval_payload"] = approval["payload"]
            event["tool_call_id"] = approval["tool_call_id"]
        if tool_use.get("persisted"):
            self._sync_sdk_tool_call_result(event, result, approval)
        return event

    def _sync_sdk_tool_call_result(
        self,
        event: dict[str, Any],
        result: Any,
        approval: dict[str, Any] | None,
    ) -> None:
        tool_call_id = event.get("tool_call_id")
        if not tool_call_id:
            return

        db = get_session()
        try:
            tool_call = db.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
            if not tool_call:
                return
            if approval:
                tool_call.status = "waiting_approval"
                tool_call.approval_request_id = approval["id"]
            else:
                tool_call.status = "succeeded" if event.get("ok") else "failed"
                tool_call.completed_at = datetime.now().isoformat()

            if isinstance(result, dict):
                tool_call.result_json = json.dumps(result, ensure_ascii=False)
                error = result.get("error")
                tool_call.error_message = json.dumps(error, ensure_ascii=False) if error else None
            elif not event.get("ok"):
                tool_call.error_message = event.get("summary") or "SDK tool call failed."
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _approval_requested_event(event: dict) -> dict | None:
        if not event.get("approval_required") or not event.get("approval_id"):
            return None
        return {
            "type": "approval_requested",
            "approval_id": event["approval_id"],
            "action": event.get("action", ""),
            "reason": event.get("approval_reason") or event.get("summary") or "",
            "risk_level": event.get("risk_level", "medium"),
            "payload": event.get("approval_payload") or {},
            "tool_call_id": event.get("tool_call_id"),
            "sdk_executed": True,
        }

    def _pending_approval(
        self,
        tool_call_id: str | None,
        *,
        session_id: str | None = None,
        turn_id: str | None = None,
        action: str | None = None,
    ):
        if not tool_call_id:
            return None
        db = get_session()
        try:
            approval = (
                db.query(ApprovalRequest)
                .filter(ApprovalRequest.tool_call_id == tool_call_id, ApprovalRequest.status == "pending")
                .first()
            )
            if not approval and session_id and turn_id and action:
                approval = (
                    db.query(ApprovalRequest)
                    .filter(
                        ApprovalRequest.session_id == session_id,
                        ApprovalRequest.turn_id == turn_id,
                        ApprovalRequest.action == action,
                        ApprovalRequest.status == "pending",
                    )
                    .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
                    .first()
                )
            if not approval:
                return None
            try:
                payload = json.loads(approval.payload_json or "{}")
            except json.JSONDecodeError:
                payload = {}
            return {
                "id": approval.id,
                "tool_call_id": approval.tool_call_id,
                "reason": approval.reason or "",
                "risk_level": approval.risk_level or "medium",
                "payload": payload,
            }
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
    def _display_tool_name(tool_name: str | None) -> str:
        if not tool_name or tool_name == SDK_ALLOWED_TOOL:
            return SDK_TOOL_NAME
        return tool_name

    @staticmethod
    def _stream_delta_text(event: dict) -> str:
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                return delta.get("text", "")
        return ""

    @staticmethod
    def _stream_thought_delta_text(event: dict) -> str:
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "thinking_delta":
                return delta.get("thinking", "") or delta.get("text", "")
        return ""

    @staticmethod
    def _result_error_message(message: Any) -> str:
        if getattr(message, "errors", None):
            return "; ".join(str(error) for error in message.errors)
        return message.result or "Claude Agent SDK runtime failed."

    def interrupt(self, session_id: str) -> None:
        self._interrupted.add(session_id)
        if session_id in self._sessions:
            self._sessions[session_id]["interrupted"] = True

    def _build_prompt(self, context: dict, message: str) -> str:
        project_id = context.get("project_id", "unknown")
        project_name = context.get("project_name", "unknown project")
        current_stage = context.get("current_stage", "unknown")
        data_quality = context.get("data_quality", "unknown")
        latest_result_available = context.get("latest_result_available") or []
        latest_pipeline = context.get("latest_pipeline") or {}
        recent_artifacts = context.get("recent_artifacts") or []
        python_environment = context.get("python_environment") or {}
        project_facts = {
            "latest_result_available": latest_result_available,
            "latest_pipeline": latest_pipeline,
            "recent_artifacts": recent_artifacts,
            "python_environment": python_environment,
        }

        return f"""You are a business analysis assistant working in project "{project_name}".

Project state:
- project_id: {project_id}
- current_stage: {current_stage}
- data_quality: {data_quality}
- project_facts: {json.dumps(project_facts, ensure_ascii=False)}
- python_environment: {json.dumps(python_environment, ensure_ascii=False)}

You may answer directly for discussion or clarification. When project state, data, analysis pipelines,
artifacts, reports, or memory candidates are needed, use exactly this tool:
business_analysis(project_id, action, payload, reason)
In the Claude Agent SDK this tool is exposed to you as
mcp__business_analysis__business_analysis. When you need business_analysis,
invoke mcp__business_analysis__business_analysis with project_id, action,
payload, and reason. Do not merely describe the planned call.

When calling business_analysis, always pass exactly this project_id: "{project_id}".
Do not use the route name, page name, project name, or any guessed identifier as project_id.

Python/runtime rule:
When Python/package commands are needed during agent analysis, use the discovered virtual environment.
If python_environment.available is true, prefer python_environment.python_executable over bare python,
and assume child runtime PATH/VIRTUAL_ENV already point at that venv. Do not suggest global Python
unless the venv is unavailable.

Only use project facts from the backend workspace context and tool results. Do not read local source
data files directly. For CSV directory ingest, first call business_analysis with action
"data.discover_source_files". Inspect filenames, headers, and previews, then call "data.ingest"
with selected_files: [{{"source_path": "...", "role": "order_info|exposure_info|activity_timeline|unknown", "reason": "..."}}].
For data-load requests, use a Claude Code style loop:
project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate.
Use the same source_path in discovery and ingest when the user gives an absolute directory. If any step
fails or validation does not pass, explain the partial state, list the blocking files/roles/issues, and
ask for the smallest concrete correction. Do not call data load complete until data.validate succeeds.
If latest_pipeline.steps contains analysis.run_gps_uplift with ok=true, say the GPS-Uplift step has run.
If latest_result_available contains "uplift", say uplift_result.json is available. Do not claim uplift has not run
when either of those facts is true.
Before citing metrics or recommendations, call result.get_latest or artifact.read and cite artifact paths.
Use observed/descriptive language for diagnostics-only claims, directional language for LocalGap or PSM-DID,
and exploratory language for stub outputs. When generating reports, use report.generate and treat
.analysis/report_plan.json as the evidence skeleton.
When the user asks to refresh or regenerate result-dashboard images, call chart.render_dashboard with
payload {{"charts": "all"}} or {{"chart_ids": [...]}} for a subset.

When the user explicitly asks to run, rerun, recompute, or refresh the full analysis/full pipeline/
完整分析/全流程分析, call business_analysis with action "analysis.run_full_pipeline" even if
project_facts.latest_pipeline already says succeeded. Treat the user request as a new run request,
not as a status question. Do not answer from cached results until that tool call has completed or
returned an approval request. Use payload {{"requested_by": "user_message"}} unless the user asks
for a narrower scope.

When the user asks you to design or rethink the analysis strategy, you may lead that work through
strategy-design actions instead of only running the fixed pipeline:
- strategy.design_blueprint creates objectives, decision questions, assumptions, methods, and success criteria.
- strategy.design_flow creates ordered stages; each stage must include an existing action or proposed_backend_change.
- strategy.propose_backend_change creates an isolated backend framework proposal artifact.
These actions create review artifacts under .analysis/strategy_lab/. They do not edit backend source code directly.

Final answers, tool-result summaries, reports, and business-facing replies must default to Chinese unless
the user explicitly requests another language. If a backend tool returns an English summary, translate and
explain it in Chinese instead of copying the English wording.

User message:
{message}"""


def get_claude_adapter(settings: dict | None = None) -> ClaudeRuntimeAdapter:
    from app.agent.claude_adapter import MockClaudeRuntimeAdapter
    from app.core.config import settings as app_settings

    provider = (settings or {}).get("provider", "mock")
    api_key = os.environ.get("ANTHROPIC_API_KEY") or app_settings.anthropic_api_key

    if provider == "claude_agent_sdk":
        if not HAS_CLAUDE_AGENT_SDK:
            raise RuntimeError(
                "APP_AGENT_RUNTIME_PROVIDER=claude_agent_sdk but claude_agent_sdk is not installed."
            )
        if not api_key:
            raise RuntimeError(
                "APP_AGENT_RUNTIME_PROVIDER=claude_agent_sdk but ANTHROPIC_API_KEY is not configured."
            )
        return ClaudeAgentSDKAdapter(settings)

    return MockClaudeRuntimeAdapter()
