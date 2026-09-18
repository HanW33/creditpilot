# CreditPilot Phase 3 Plan

## Status

Phase 3 — Complete

Started on 2026-09-18 after completion of the protected CreditState schemas.
Completed on 2026-09-18.

The common contracts, configurable permissions, bounded application and
profile reads, deterministic DTI calculation, quantitative model and SHAP
wrappers, protected quantitative commit bridge, and reference-only audit path
satisfy the Phase 3 scope. No external provider, external side effect, policy
retrieval, decision threshold, or new agent was introduced.

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

The quantitative-tool increment wraps the approved Logistic Regression and
SHAP components with version, permission, scope, state-version, application,
and provenance checks. Model tools return PD and model-derived attribution but
never recommendation fields and never commit protected CreditState directly.

The final internal-tool increment adds sanitized customer-profile reads,
reference-only tool auditing, and a deterministic bridge that atomically
validates and commits matching PD and SHAP results through protected state
controls. DTI remains a tool result because the approved CreditState design
does not yet designate a committed derived-feature field or writer.
