## MODIFIED Requirements

### Requirement: Single business analysis gateway
The system SHALL expose project analysis execution to the model only through the
controlled `business_analysis(project_id, action, payload, reason)` gateway.

#### Scenario: LongCat emits a textual tool call
- **WHEN** the real SDK runtime receives assistant text containing a complete
  `<longcat_tool_call>` block for `business_analysis`
- **THEN** the adapter parses the block and executes the requested action through
  the existing `AnalysisToolGateway`
- **AND** the event stream exposes the execution as standard
  `tool_call_started` and `tool_call_finished` or `tool_call_failed` events
- **AND** the raw textual tool markup is not shown as assistant answer text
- **AND** repeated identical textual tool blocks in the same turn do not execute
  duplicate gateway calls
