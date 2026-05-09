## MODIFIED Requirements

### Requirement: Agent Message Sessions
The backend SHALL persist Agent conversation sessions per project and expose explicit session management operations without changing the message-first runtime contract.

#### Scenario: Project session summaries are listed
- **WHEN** the frontend requests sessions for a project
- **THEN** the backend returns session summaries containing session id, project id, status, runtime provider, last activity, preview text, and message count

#### Scenario: Agent session is deleted
- **WHEN** a user deletes an obsolete Agent session
- **THEN** the backend removes only the conversation/session records and keeps project data, artifacts, reports, and workspace files intact

#### Scenario: Ordinary messages still use MessageRuntime
- **WHEN** a user sends a natural-language Agent message
- **THEN** the request still flows through `POST /api/agent/messages` and the existing `MessageRuntime`
