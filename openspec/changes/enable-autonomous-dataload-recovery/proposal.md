## Why

Local data load can stay in a partial state even when the user provides a valid directory, because the agent is not consistently guided to discover files, classify them, ingest selected CSVs, infer schema, validate, and explain failures as a single autonomous loop. This change gives the model a Claude Code style tool-call loop for data load completion while keeping `business_analysis` as the only business tool.

## What Changes

- Add explicit autonomous data-load behavior: discover source files, reason over headers/previews, ingest classified CSVs, then run schema inference and validation.
- Add recoverable diagnostics when discovery, ingest, schema inference, or validation cannot complete, so the assistant can propose concrete fixes instead of leaving the user at "partial".
- Update mock and SDK prompt scaffolding so MVP/test mode demonstrates multi-step tool calls without needing the real SDK.
- Keep workspace writes behind the existing `data.ingest` gateway action and do not let the agent read arbitrary external data files directly.

## Capabilities

### New Capabilities
- `autonomous-data-load`: Agent-directed data-load loops that can complete or diagnose local CSV ingestion through controlled `business_analysis` actions.

### Modified Capabilities
- `business-analysis-system`: Clarify that natural-language data-load requests must use discover-first, selected-file ingest, schema inference, and validation before reporting completion.

## Impact

- Modified: `backend/app/agent/prompt_composer.py`
- Modified: `backend/app/agent/claude_agent_sdk_adapter.py`
- Modified: `backend/app/agent/claude_adapter.py`
- Modified: `backend/app/tools/data_tools.py`
- Modified: backend tests for agent prompt/tool-call contracts and data-load diagnostics
- No new external dependencies.
