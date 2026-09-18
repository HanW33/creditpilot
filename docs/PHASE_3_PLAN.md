# CreditPilot Phase 3 Plan

## Status

Phase 3 — In Progress

Started on 2026-09-18 after completion of the protected CreditState schemas.

## Authority and Scope

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/TOOL_DESIGN.md`, and `AGENTS.md` govern
this phase. Phase 3 implements typed, permission-controlled internal READ and
COMPUTE tools without external side effects.

The initial increment includes:

- common typed `ToolInvocation` and `ToolResult` contracts;
- configurable caller permissions and scope checks;
- minimum-field `get_application()` reads from committed CreditState;
- deterministic `calculate_dti()` with explicit provenance and failure;
- tests for authorization, state-version, scope, calculation, and missing data.

Later Phase 3 increments may wrap the approved Phase 1 quantitative model and
SHAP implementation. This phase does not implement policy retrieval,
verification providers, action tools, agents, thresholds, or external side
effects. Exact data-tool callers remain configuration rather than an embedded
architecture decision.
