## Why

MVP1 proves the real agent runtime can complete the existing analysis pipeline, but the analysis strategy itself is still mostly fixed by backend code. The next isolated version needs a controlled lab where the model can propose, revise, and persist analysis strategy and flow designs without contaminating the MVP1 stable framework.

## What Changes

- Add a version-isolated Agent Strategy Framework Lab for model-led analysis strategy design.
- Let the model use `business_analysis` actions to create and update strategy blueprints, pipeline flow designs, and backend change proposals as workspace artifacts.
- Keep generated strategy/framework changes out of the MVP1 runtime path until a user explicitly promotes or implements them.
- Add audit-friendly storage under `.analysis/strategy_lab/` so every model-led design has version metadata, status, and rationale.
- Do not grant the model arbitrary filesystem write access or direct backend code mutation in this phase.

## Capabilities

### New Capabilities

- `agent-strategy-framework-lab`: Model-led strategy and flow blueprint generation in an isolated project workspace area.

### Modified Capabilities

- `business-analysis-system`: Add controlled `strategy.*` business_analysis actions while preserving the single external tool gateway.

## Impact

- Backend tool registry and gateway action surface.
- New strategy lab service for validating and storing blueprint artifacts.
- Project workspace `.analysis/strategy_lab/` files.
- Prompt/skill guidance so the model can lead analysis strategy design through approved actions.
- Tests for action contracts, isolation boundaries, and artifact persistence.
