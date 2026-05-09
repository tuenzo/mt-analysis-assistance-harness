# Tasks

- [x] Publish post-approval events for approved or rejected tool calls.
- [x] Add a deterministic MVP full-pipeline runner with job progress events.
- [x] Persist generated artifacts and reports from pipeline tool results.
- [x] Keep pipeline progress visible in the Agent UI after approval.
- [x] Derive Agent UI plan-step states from live tool, job, approval, and artifact events instead of a static running mock.
- [x] Avoid double-applying returned approval events to frontend runtime state.
- [x] Render assistant messages in the Agent UI through the shared Markdown renderer.
- [x] Fix artifact.read so Agent-provided artifact_path payloads can read pipeline output files safely.
- [x] Ignore unsupported Claude SDK null tool-use blocks so they do not appear as business_analysis failures.
- [x] Guard MessageRuntime against concurrent turns in the same SDK session.
- [x] Add a minimal Dashboard view backed by project state and artifacts.
- [x] Run backend pytest and frontend build.
