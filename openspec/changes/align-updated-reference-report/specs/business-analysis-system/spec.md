## MODIFIED Requirements

### Requirement: Data Analysis Pipeline
The backend SHALL run the standard promotion analysis pipeline in the updated reference-report order while preserving the existing single gateway and artifact registration contracts.

#### Scenario: Full pipeline follows updated report logic
- **WHEN** `business_analysis` executes the full pipeline for a project with raw order, exposure, and activity tables
- **THEN** it builds the reference-aligned category-day panel, runs descriptive diagnostics before causal language, runs PSM-DID as directional support, runs LocalGap/LMDI as the main increment layer, runs mechanism/conversion and GPS/uplift allocation modules, runs four-state user path analysis when data supports it, and makes all method statuses available to report generation

#### Scenario: Artifact compatibility is preserved
- **WHEN** existing clients read prior artifact names or fields
- **THEN** the system keeps compatibility keys such as `gmv`, `order_count`, `localgap_result.json`, `psm_did_result.json`, and `gps_uplift_result.json` while adding updated reference-report fields and summaries
