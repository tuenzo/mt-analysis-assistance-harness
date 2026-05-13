## Tasks

- [x] Add a message-runtime terminal fallback for no-tool clarification turns that stream assistant text without a provider `final_answer`.
- [x] Preserve streamed assistant text when the provider emits an empty `final_answer`, so the frontend can close the run without blanking the reply.
- [x] Update the Agent thinking card copy so completed turns are shown as finished trace records instead of active thinking.
- [ ] Add a `backend/app/tools/contracts.py` module with `NormalizedToolCall`, action contract metadata, envelope normalization, and reusable validation errors.
- [ ] Add action-specific payload schemas/normalizers for `chart.render_dashboard`, including `charts:["all"]`, `chart_ids:["all"]`, omitted chart list, comma strings, and known chart ID lists.
- [ ] Route `AnalysisToolGateway.execute` through the contract layer before permission checks and handler execution, while preserving project ID pinning from the runtime context.
- [ ] Persist raw payload, canonical payload, normalization warnings, and validation error details in tool-call audit data without breaking existing rows.
- [ ] Update `ClaudeAgentSDKAdapter` so SDK tool calls and LongCat textual tool calls share the same contract path and produce identical started/finished/failed events.
- [ ] Add contract-corpus fixtures and tests for observed LLM variants, beginning with the failed `{"charts":["all"]}` dashboard payload.
- [ ] Add gateway tests for terminal failed states on invalid payloads and successful artifact persistence after normalization.
- [ ] Add/update browser smoke tests for the Agent page to verify tool call status updates, result return, and no mock fallback when `APP_AGENT_RUNTIME_PROVIDER=claude_agent_sdk`.
- [ ] Update prompt/tool metadata generation so accepted action payload examples come from contract metadata instead of hand-maintained prompt strings.
- [ ] Run `pytest`, `npm run build`, OpenSpec validation, and a real backend/frontend smoke check before marking the change complete.
