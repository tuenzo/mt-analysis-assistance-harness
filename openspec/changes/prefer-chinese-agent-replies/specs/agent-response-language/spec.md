# Agent Response Language

## ADDED Requirements

### Requirement: Chinese by default for agent replies

Agent final answers and business-facing summaries SHALL be in Chinese unless the user explicitly requests another language.

#### Scenario: Approved full pipeline completes

- **WHEN** an approved full pipeline finishes successfully
- **THEN** the emitted `final_answer.message`, job completion message, tool summary, and tool result summary are Chinese
- **AND** they do not use the English phrase "Full pipeline completed"

#### Scenario: Approved full pipeline partially fails

- **WHEN** an approved full pipeline finishes with one or more failed steps
- **THEN** the emitted final answer and summaries explain the partial state in Chinese
