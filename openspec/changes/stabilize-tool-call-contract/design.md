## Context

The system intentionally exposes one external tool, `business_analysis(project_id, action, payload, reason)`, and relies on the LLM to choose actions. In real runs, the LLM can produce the right intent with a payload shape that differs from a handler's internal assumptions. The current gateway validates the action enum but forwards payloads directly to each tool, so each handler must independently decide how tolerant it is.

The observed failure is `chart.render_dashboard` with payload `{"charts":["all"]}`. The handler accepts `"all"` as a string and lists of chart IDs, but it treats list item `"all"` as an unknown chart ID. Similar drift can happen across actions through aliases, scalar-vs-list differences, missing optional objects, casing, or text-tool-call parsing.

## Goals / Non-Goals

**Goals:**
- Make the gateway boundary deterministic: raw LLM input is normalized once, validated once, then executed as a canonical payload.
- Keep `business_analysis` as the only externally exposed custom tool.
- Preserve auditability by recording raw and normalized payloads instead of hiding model drift.
- Give the model useful repair guidance for invalid payloads without executing unsafe guesses.
- Add reusable tests so new actions cannot silently reintroduce brittle payload handling.

**Non-Goals:**
- This does not expose internal tools directly to the LLM.
- This does not make arbitrary malformed JSON acceptable.
- This does not remove action-level business validation or permission checks.
- This does not change the project workspace as the source of truth.

## Decisions

### Decision 1: Add a central normalization layer before gateway execution

Create a `ToolCallContract` module owned by `backend/app/tools/` that accepts the raw envelope and returns a `NormalizedToolCall`:

- `project_id`: pinned to runtime context when available, not trusted from model text.
- `action`: canonical `BusinessAnalysisAction`.
- `payload`: canonical dict for that action.
- `reason`: string with a safe default.
- `warnings`: non-fatal normalization notes for audit.

Rationale: this avoids scattering alias handling across every tool and lets tests target the contract boundary directly.

Alternative considered: make every handler more permissive. That keeps fixing symptoms one action at a time and makes behavior inconsistent.

### Decision 2: Use action-specific Pydantic schemas plus small normalizers

Each action that receives structured payloads gets a request schema and optional `normalize_<action>` function. Normalizers are allowed to handle semantically equivalent forms, such as:

- `charts: "all"`, `charts: ["all"]`, `chart_ids: "all"`, or omitted chart list for all dashboard charts.
- comma-separated strings where the UI or LLM naturally emits compact lists.
- benign alias names documented in the action contract.

After normalization, Pydantic validation runs in strict-enough mode to reject unsafe or unknown shapes. The executed tool sees only the canonical payload.

Alternative considered: rely only on JSON Schema passed to the SDK. JSON Schema improves model guidance but does not protect textual LongCat tool calls, legacy sessions, or future provider quirks.

### Decision 3: Generate SDK tool schema from the same contract source

The MCP `business_analysis` tool schema should continue to expose the stable outer envelope, while the prompt and action registry can derive allowed action names and action payload hints from the same contract metadata. This avoids manual drift between prompt examples, SDK schema, and gateway behavior.

Alternative considered: keep prompt examples as the source of truth. Prompt-only contracts are advisory; the backend still needs executable validation.

### Decision 4: Treat invalid normalized calls as recoverable tool results

When normalization or validation fails, the gateway returns `ToolResult(ok=false)` with:

- `error.code`: `INVALID_PAYLOAD`
- `error.details`: validation path and accepted shapes
- `assistant_hint`: a minimal corrected example JSON

The adapter streams a normal `tool_call_failed` event, persists the failed state, and lets the LLM decide whether to retry. Repeated identical invalid calls in one turn are deduplicated and bounded by existing SDK max-turn/tool-call budgets.

Alternative considered: silently coerce every invalid call. That risks running the wrong analysis when the intent is ambiguous.

### Decision 5: Add a contract corpus and browser lifecycle checks

Maintain JSON fixtures of observed LLM payload variants for key actions. Each fixture asserts whether the call normalizes, fails with useful feedback, or requires approval. Browser checks verify that tool calls progress through visible states and that results/approval/error events arrive instead of hanging.

Alternative considered: only unit test individual helpers. That misses integration bugs between adapter event mapping, gateway persistence, and frontend state.

## Risks / Trade-offs

- [Risk] Over-tolerant normalization could execute a different action than intended. -> Mitigation: only normalize documented aliases; ambiguous calls fail with repair guidance.
- [Risk] More schemas add maintenance overhead when actions change. -> Mitigation: register schema metadata next to the action and require fixture updates in action tasks.
- [Risk] Existing DB rows do not contain normalized payload fields. -> Mitigation: add nullable columns or JSON fields and keep backward-compatible reads.
- [Risk] Tool failures can still be visible in historical turns. -> Mitigation: keep audit history immutable, but ensure new turns and replay tests no longer produce the preventable failure.

## Migration Plan

1. Add the contract module and tests without changing tool behavior.
2. Wire gateway execution through normalization, persisting raw and normalized payloads.
3. Add `chart.render_dashboard` schema/normalizer and fix the observed `["all"]` variant.
4. Move high-traffic actions into the contract registry in priority order: project state, result read, artifact read, data discovery/ingest, schema infer/validate, full pipeline, report generation.
5. Run backend tests, frontend build, and browser smoke checks against the real Agent page.

Rollback is straightforward: keep action handlers compatible, then disable gateway normalization behind a config flag if an unexpected regression appears.

## Open Questions

- Should raw/normalized payload audit fields be new DB columns on `ToolCall`, or stored inside `result_json`/log metadata for MVP?
- Should the frontend display normalization warnings to developers only, or keep them hidden unless a call fails?
