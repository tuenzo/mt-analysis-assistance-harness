## 1. Strategy Lab Service

- [x] 1.1 Create backend strategy lab schemas for blueprint, flow, stage, and backend change proposal payloads
- [x] 1.2 Implement a service that validates payloads and writes JSON artifacts under `.analysis/strategy_lab/`
- [x] 1.3 Generate stable ids, versions, timestamps, source turn metadata, and workspace-relative paths
- [x] 1.4 Ensure service path handling prevents writes outside the current project workspace

## 2. Tool Gateway Integration

- [x] 2.1 Add `strategy.design_blueprint`, `strategy.design_flow`, and `strategy.propose_backend_change` to the business analysis action enum/registry
- [x] 2.2 Register strategy lab tool handlers through the existing registry
- [x] 2.3 Return ToolResult summaries, state patches, and artifact refs for created strategy lab artifacts
- [x] 2.4 Keep strategy lab actions project-local and out of external sync paths

## 3. Agent Guidance

- [x] 3.1 Update the project skill prompt so the model understands when and how to design strategies
- [x] 3.2 Add payload examples for strategy blueprint, flow, and backend change proposal actions
- [x] 3.3 Make clear that generated backend framework changes are proposals, not direct code edits

## 4. Tests

- [x] 4.1 Add unit tests for successful strategy blueprint, flow, and backend change proposal creation
- [x] 4.2 Add rejection tests for missing required fields and invalid paths
- [x] 4.3 Add gateway tests proving strategy actions flow through `business_analysis`
- [x] 4.4 Run targeted pytest suite and update task status
