## Context

The harness now has real panel generation and a runnable demo flow. Report generation still mostly stitches available JSON into fixed prose, while the frontend reads Markdown sections through fragile title matching. The reference project's best ideas are not its exact prose, but its report discipline: summary first, evidence tables and figures, method notes, robustness caveats, and strategy implications.

## Goals / Non-Goals

**Goals:**

- Build a repeatable report skeleton that can be populated from tool results.
- Make report content explicit about confidence, assumptions, and limitations.
- Let the UI show evidence provenance instead of just a raw Markdown blob.
- Keep the single `business_analysis` gateway and current REST APIs compatible.

**Non-Goals:**

- Do not implement a full causal modeling suite in this change.
- Do not copy reference report wording, data values, or chart images.
- Do not add a rich text editor or export formats beyond current Markdown flow.

## Decisions

- Use a deterministic report plan object in backend code.
  - Rationale: reliable MVP behavior beats free-form LLM prose for generated reports.
  - Alternative: call an LLM directly for report text; rejected because demo/test outputs need deterministic verification.

- Treat prompts as design artifacts, not runtime dependency.
  - Rationale: the agent can use prompt/tool guidance to decide actions, while backend still owns facts and artifacts.

- Keep frontend resilient to partial data.
  - Rationale: users may open Dashboard before full pipeline completion.

- Use ASCII display text in edited UI/report templates.
  - Rationale: existing files show local encoding damage; stable English UI avoids another round of mojibake.

## Risks / Trade-offs

- [Risk] More structured reports may feel less conversational. -> Mitigation: include concise narrative interpretation in each section.
- [Risk] Some demo outputs remain stub-based. -> Mitigation: clearly label confidence and method status.
- [Risk] Browser review may reveal layout density issues. -> Mitigation: reserve a final self-review/fix pass.

## Migration Plan

1. Create report/display contracts.
2. Implement backend report plan and metadata.
3. Implement frontend evidence-led views.
4. Verify with tests/build and browser review.
5. Commit each coherent slice.
