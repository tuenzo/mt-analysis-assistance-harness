## MODIFIED Requirements

### Requirement: Project List Management
The frontend SHALL allow users to delete obsolete projects from the project list with an explicit confirmation step.

#### Scenario: Delete action is visible
- **WHEN** the project list is displayed
- **THEN** each project row exposes a delete control that is visually distinct from opening the project

#### Scenario: User confirms deletion
- **WHEN** the user confirms project deletion
- **THEN** the frontend calls the project delete API, refreshes the project list, and clears the current project state when the deleted project was selected

#### Scenario: User cancels deletion
- **WHEN** the user cancels the confirmation dialog
- **THEN** no API delete request is sent and the project list remains unchanged
