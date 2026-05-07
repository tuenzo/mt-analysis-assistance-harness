## ADDED Requirements

### Requirement: Analysis Method Downgrade Metadata
The system SHALL expose method status and downgrade warnings for upgraded promotion analysis actions without changing action names.

#### Scenario: Existing action returns richer metadata
- **WHEN** `analysis.run_diagnostics`, `analysis.run_localgap`, or `analysis.run_gps_uplift` completes
- **THEN** the result artifacts preserve existing paths
- **AND** the JSON payload includes `method_status` and `warnings` fields where applicable
