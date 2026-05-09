# persist-agent-session-on-refresh

## What

Restore the active agent conversation after a browser refresh by remembering the last session per project and falling back to the backend's latest project session.

## Why

The agent page currently keeps `sessionId` and messages in in-memory React/Zustand state. Refreshing the page clears that state, and the page only attempts demo-session recovery, so normal live conversations appear reset.

## Scope

- Persist the latest agent session id per project in browser storage.
- On page load, restore that session and message history when it still belongs to the current project.
- If no stored session exists, fetch the latest backend project session and load its messages.
- Clear the stored session when the user intentionally clears the conversation.
