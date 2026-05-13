## MODIFIED Requirements

### Requirement: Result Dashboard Workspace
The frontend SHALL keep the existing result dashboard workflow while surfacing important updated-report results and interpretation caveats.

#### Scenario: Updated report results are visible
- **WHEN** a user opens `/projects/{project_id}/dashboard`
- **THEN** the existing dashboard layout exposes or links to data quality, causal direction, increment attribution, mechanism/resource response, allocation strategy, user state path, and business recommendations when those artifacts exist

#### Scenario: Method status and downgrade context are visible
- **WHEN** an artifact reports limited support, warnings, or method-status downgrades
- **THEN** the dashboard surfaces that context near the relevant section rather than presenting the result as a final causal claim

#### Scenario: No large page-function rewrite
- **WHEN** the updated reference display alignment is implemented
- **THEN** it reuses existing dashboard/report components and avoids adding unrelated navigation, workflows, or major page redesigns unless separately proposed
