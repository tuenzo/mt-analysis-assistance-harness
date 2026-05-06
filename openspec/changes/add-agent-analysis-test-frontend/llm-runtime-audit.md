# LLM Runtime Audit

## Why this audit exists

The browser harness showed `runtime_usage`, but the external API credit balance did not move. That made `runtime_usage` insufficient as proof. We audited the real `claude_agent_sdk` path with negative controls that cannot be satisfied by a real remote LLM:

- local fake API base URL
- invalid API key
- request capture on `127.0.0.1`

## Exact request chain

1. `frontend/src/app/agent-analysis-test/page.tsx`
2. `frontend/src/features/agent/agent-analysis-test-harness.tsx`
3. `frontend/src/lib/api-client.ts`
4. `POST /api/agent/messages`
5. `backend/app/agent/message_runtime.py`
6. `backend/app/agent/claude_agent_sdk_adapter.py`
7. `claude_agent_sdk.query(prompt=..., options=ClaudeAgentOptions(...))`
8. `claude_agent_sdk._internal.client.InternalClient.process_query`
9. `claude_agent_sdk._internal.transport.subprocess_cli.SubprocessCLITransport`
10. bundled `claude.exe` from `backend/.venv/Lib/site-packages/claude_agent_sdk/_bundled/claude.exe`
11. HTTP requests to the configured Anthropic-compatible base URL:
    - `GET {base}/v1/models?limit=1000`
    - `POST {base}/v1/messages?beta=true`

## Root cause found

The SDK launches the bundled Claude Code CLI. If `CLAUDE_CONFIG_DIR` is not explicitly isolated, that CLI can read the local user Claude Code account/config from `C:\Users\ASUS\.claude` / `C:\Users\ASUS\.claude.json`.

Negative control result:

- With an isolated temporary `CLAUDE_CONFIG_DIR`, the SDK hit the fake local API and emitted retry events. Captured requests included `x-api-key` and `/anthropic/v1/messages?beta=true`.
- Without `CLAUDE_CONFIG_DIR`, the same SDK query returned success and the fake local API captured 0 requests.

That means the previous adapter could be satisfied by the local Claude Code login instead of the `.env` API credentials. This explains why the configured external API credit did not move.

## Fix applied

`ClaudeAgentSDKAdapter` now creates a per-session SDK config directory inside the project workspace:

```text
{project_workspace}/.analysis/claude-sdk-config/{external_session_id}
```

Every SDK subprocess receives:

```text
ANTHROPIC_API_KEY=<from env/app settings>
ANTHROPIC_AUTH_TOKEN=<same credential unless explicitly set>
ANTHROPIC_API_BASE_URL=<from env/app settings>
ANTHROPIC_BASE_URL=<same base URL>
CLAUDE_CONFIG_DIR=<project isolated config dir>
CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1
```

The key value is never logged or shown in diagnostics.

## Skill loading

The project skill is written to:

```text
{project_workspace}/.claude/skills/business-analysis/SKILL.md
```

The SDK options include:

```text
skills=["business-analysis"]
```

The Python SDK then adds the matching CLI tool permission internally as:

```text
Skill(business-analysis)
```

## Diagnostic signals

`runtime_diagnostic` now reports:

- `runtime: claude_agent_sdk`
- `mock_fallback: false`
- `base_url_host`
- `model`
- `skills`
- `skill_allowed_tools`
- `workspace_path`
- `claude_config_dir_isolated`
- `claude_config_dir`

These fields prove the configured code path, but the strongest proof remains the fake-base negative control above.

## LongCat authentication note

The Claude Code CLI sends `x-api-key` when only `ANTHROPIC_API_KEY` is set. A local capture test showed that setting `ANTHROPIC_AUTH_TOKEN` makes the CLI send `Authorization: Bearer ...`.

The isolated real request returned:

```text
401 missing_api_key
```

So the adapter now mirrors the configured API key into `ANTHROPIC_AUTH_TOKEN` by default. This keeps the Anthropic-style key available while also supporting Bearer-token gateways.

## Browser validation after fixes

Route:

```text
http://localhost:3010/agent-analysis-test?api_base=http%3A%2F%2F127.0.0.1%3A8017
```

Real LLM tool-call smoke marker:

```text
real-llm-bearer-20260506-2
```

Observed backend evidence:

- `runtime: claude_agent_sdk`
- `model: LongCat-2.0-Preview`
- `base_url_host: api.longcat.chat`
- `mock_fallback: false`
- `api_key_present: true`
- `auth_token_present: true`
- `claude_config_dir_isolated: true`
- `skills: ["business-analysis"]`
- `skill_allowed_tools: ["Skill(business-analysis)"]`
- `tool_call_started: project.get_state`
- `tool_call_finished: project.get_state ok=true`
- `runtime_usage.total_cost_usd: 0.0259422`

Full pipeline browser marker:

```text
real-pipeline-20260506-3
```

Observed after approval:

- `approval_requested: analysis.run_full_pipeline`
- `job_started: 1`
- `job_progress: 20`
- `job_finished: 1`
- `tool_call_started: 12`
- `tool_call_finished: 13`
- `artifact_created: 16`
- final summary: `Full pipeline completed: validation, panel, diagnostics, causal checks, charts, and report are ready.`
