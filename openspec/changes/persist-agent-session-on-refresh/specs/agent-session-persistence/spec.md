# Agent Session Persistence

## ADDED Requirements

### Requirement: Restore agent conversation after refresh

The project agent page SHALL restore the most recent valid agent session and message history after a browser refresh.

#### Scenario: Stored session is valid

- **GIVEN** the browser has a stored agent session id for the current project
- **WHEN** the user refreshes the project agent page
- **THEN** the page loads that session's messages
- **AND** subsequent messages reuse that session id

#### Scenario: Stored session is missing

- **GIVEN** the browser has no stored agent session id for the current project
- **AND** the backend has at least one session for that project
- **WHEN** the user opens or refreshes the project agent page
- **THEN** the page loads the newest project session and its messages

#### Scenario: User clears conversation

- **WHEN** the user clears the agent conversation
- **THEN** the stored project session id is removed
- **AND** a refresh does not immediately restore the cleared conversation from browser storage
