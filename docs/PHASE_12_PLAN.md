# Phase 12 — Comprehensive Evaluation

## Status

Complete.

## Scope

Phase 12 adds a deterministic evaluation harness for the three approved Golden
Demo contracts. It evaluates architecture invariants, policy grounding,
verification evidence, agent boundaries, workflow limits, recommendation
ownership, mandatory review, explanation grounding, security, and auditability.

The harness records data, model, policy, workflow, and schema versions. A failed
hard invariant fails the relevant scenario and the overall report; passing
checks cannot average it away.

## Quantitative Evaluation

Existing Phase 1 model metrics are carried into the Phase 12 report as evidence,
but Phase 12 does not invent acceptance
thresholds. Quantitative acceptance thresholds remain `not_approved` until a
human approves them separately.

## Golden Demo Interpretation

- Scenario 1 requires a grounded short path without unnecessary verification.
- Scenario 2 requires separate `reported_income = 150000` and
  `verified_income = 98000`, model and policy reruns, a Decision Engine
  `MANUAL_REVIEW` outcome, and enforced human review.
- Scenario 3 requires the unresolved conflict to remain explicit and route to
  mandatory human review. Under the approved eligibility boundary, an
  ineligible conflicted case may be routed by the Workflow Controller without
  running the normal Decision Engine; it must never become an approval.

## Reproduce

```bash
python -m creditpilot.evaluation.cli --output reports/phase12_evaluation.json
python -m pytest
```

The checked-in report uses synthetic reference trace fixtures. It is an
architecture-contract evaluation, not a production credit decision or a claim
that a live provider was called.
