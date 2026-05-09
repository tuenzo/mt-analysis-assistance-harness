# Design

## Backend Deterministic Events

`run_approved_full_pipeline()` creates the final pipeline summary before the LLM sees anything. This must be localized at the source so the UI, persisted tool result, job event, tool event, and final answer are all consistent.

## LLM Prompting

The SDK prompt and composed prompt should say that final answers, tool-result summaries, and business-facing replies must be in Chinese by default. This is a stronger instruction than only saying "reports and business-facing summaries".

## Tests

Update the full-pipeline approval test to assert the final answer is Chinese and does not contain the old English phrase.
