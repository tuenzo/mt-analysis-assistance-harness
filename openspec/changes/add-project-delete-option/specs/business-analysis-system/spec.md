## MODIFIED Requirements

### Requirement: Project Lifecycle Management
The backend SHALL support explicit deletion of analysis projects with workspace safety checks.

#### Scenario: Project is deleted
- **WHEN** a user requests deletion of a project
- **THEN** the backend removes the project database record and its project workspace directory when the resolved workspace path stays within the configured workspace root

#### Scenario: Workspace safety blocks unsafe deletion
- **WHEN** a project workspace path cannot be resolved inside the configured workspace root
- **THEN** the backend refuses deletion and leaves filesystem contents unchanged

#### Scenario: Deleting a missing project is reported clearly
- **WHEN** a deletion request targets an unknown project id
- **THEN** the API returns the standard response shape with an error instead of silently succeeding
