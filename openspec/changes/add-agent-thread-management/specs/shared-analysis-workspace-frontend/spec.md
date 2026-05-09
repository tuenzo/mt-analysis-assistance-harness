## MODIFIED Requirements

### Requirement: Agent Analysis Workspace
The frontend SHALL let users manage project Agent conversation threads from the existing Agent analysis page.

#### Scenario: User continues a previous thread
- **WHEN** a project has persisted Agent sessions
- **THEN** the Agent page shows available threads and lets the user continue one without creating a new project or losing artifacts

#### Scenario: User starts a new thread
- **WHEN** the user chooses to start a new Agent thread
- **THEN** the page clears the active conversation context while keeping the current project selected

#### Scenario: User deletes a thread
- **WHEN** the user confirms deletion of a thread
- **THEN** the thread is removed from the thread list and the current project analysis outputs remain available
