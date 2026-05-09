# prefer-chinese-agent-replies

## What

Make agent-facing completion summaries default to Chinese, including the approved full-pipeline final answer and its associated job/tool summaries.

## Why

The product is a Chinese business analysis workspace. A successful full pipeline currently surfaces an English final answer (`Full pipeline completed: validation, panel, diagnostics, causal checks, charts, and report are ready.`), which breaks the expected user experience even though prompts already ask for Chinese business summaries.

## Scope

- Strengthen runtime prompts so LLM final answers and business summaries reply in Chinese unless the user explicitly requests another language.
- Localize deterministic full-pipeline completion and failure summaries emitted by the backend.
- Add regression tests for the full-pipeline approval final answer.
