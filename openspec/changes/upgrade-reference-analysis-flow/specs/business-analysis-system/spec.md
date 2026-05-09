## ADDED Requirements

### Requirement: Reference-aligned full analysis sequence
The standard full pipeline SHALL evolve toward the reference promotion-analysis sequence while preserving Message-first entry, the single `business_analysis` gateway, and workspace-backed artifact persistence.

#### Scenario: Full pipeline keeps gateway execution
- **WHEN** a user asks the agent to run a full promotion analysis
- **THEN** the backend executes all analytical steps through registered `business_analysis` actions rather than bypassing the gateway with direct SDK or frontend workflow routing

#### Scenario: Pipeline includes staged method status
- **WHEN** a full-pipeline step lacks enough data, support, or dependency coverage
- **THEN** the step records a structured limited-status result with warnings and the pipeline continues when the missing capability is non-critical

#### Scenario: Existing artifact consumers remain compatible
- **WHEN** upgraded modules emit richer outputs
- **THEN** existing artifact names and top-level result keys used by dashboard/report consumers remain available unless an OpenSpec migration explicitly changes them
