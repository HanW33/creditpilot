# CreditPilot Phase 11 Plan

## Status

Phase 11 — Complete

Started and completed on 2026-09-20 after escalation and controlled action
tools were committed.

## Authority and Scope

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/AGENT_DESIGN.md`, `docs/STATE_DESIGN.md`,
`docs/WORKFLOW.md`, and `AGENTS.md` govern this phase.

Phase 11 implements a provider-independent, read-only Explanation Agent:

- allowlisted access to committed application references, model and SHAP
  output, policy findings, verification state, recommendation, workflow state,
  and escalation state;
- an injected reasoning-backend contract without selecting an LLM provider;
- deterministic structured-output validation;
- protected commit of the analyst-facing explanation only;
- reference-only Agent audit records.

## Grounding and Safety Requirements

- the Explanation Agent receives no tools;
- a committed deterministic recommendation is required;
- explanations must distinguish `Model`, `Policy`, `Verification`, and
  `Decision` evidence;
- committed PD, recommendation, decision rule, policy status and findings, and
  verified values cannot be omitted;
- policy conflicts, verification conflicts, limitations, and mandatory-review
  reasons cannot be concealed and must appear in the explanation text;
- evidence references must resolve to the approved minimum-context view;
- autonomous lending claims and raw email addresses are rejected;
- the Explanation Agent cannot modify model, policy, verification, workflow,
  recommendation, or escalation evidence.

The full governance-audit object remains excluded from Agent context. The Agent
receives only the minimum evidence references required for the explanation.

## Completion Evidence

- a grounded explanation commits without changing model or recommendation
  state;
- tool access, unknown evidence references, omitted recommendation evidence,
  and concealed mandatory-review reasons are rejected;
- explanation output and validation outcome are audited by reference;
- repository lint and test checks pass.
