# CreditPilot

CreditPilot is an agentic AI credit risk decision-support system for a Credit
Risk Analyst or Underwriter. Phase 0 architecture and harness documentation was
approved and frozen on 2026-09-15. Phases 1 through 10 are complete, and the
next planned phase is Phase 11: Explanation Agent.

## Purpose

The project demonstrates how deterministic software, quantitative credit-risk
modelling, synthetic policy retrieval, bounded LLM-enabled agents, approved
verification tools, human review, and audit controls can work together.

CreditPilot supports analyst judgment. It is not an autonomous approval engine
or a production lending platform.

## Architecture Summary

CreditPilot separates responsibilities across:

- deterministic validation, feature calculation, workflow control, permissions,
  limits, and recommendation rules;
- quantitative ML for PD prediction, risk scoring, calibration, and SHAP;
- five LLM-enabled agents for orchestration, policy interpretation,
  verification planning, explanation, and escalation;
- typed tools with bounded permissions and side effects;
- authorized human analysts for mandatory review.

The deterministic Decision Engine exclusively owns recommendation fields.
Agents cannot modify quantitative outputs, bypass protected CreditState, or
bypass mandatory human review.

## Five Approved Agents

1. Orchestrator Agent;
2. Policy Agent;
3. Verification Agent;
4. Explanation Agent;
5. Escalation Agent.

No additional agent is approved for V1.

## Verification Responsibility

- Policy Agent determines WHAT evidence is required.
- Orchestrator Agent determines WHETHER verification is needed now.
- Verification Agent determines HOW evidence is obtained.
- The Orchestrator proposes verification-request creation.
- Deterministic workflow and state controls validate, create, and commit the
  protected request.
- Approved verification tools return raw evidence.
- Deterministic controls validate and commit protected verification state.

Reported and verified information remain separate and traceable.

## Security and Data Scope

V1 uses synthetic, mock, simulated, or suitable public demo data only. It does
not use real customer PII or proprietary bank underwriting policies.

Raw identity PII and token mappings remain outside the main workflow in a
protected PII Vault. LLM context must be allowlisted, sanitized, redacted, and
limited to the minimum required.

## Documentation

The canonical source of truth is
[`docs/ARCHITECTURE_SPEC_V1.md`](docs/ARCHITECTURE_SPEC_V1.md).

Supporting Phase 0 documents:

- [Architecture overview](docs/ARCHITECTURE.md)
- [Business requirements](docs/BUSINESS_REQUIREMENTS.md)
- [Agent design](docs/AGENT_DESIGN.md)
- [State design](docs/STATE_DESIGN.md)
- [Tool design](docs/TOOL_DESIGN.md)
- [Workflow](docs/WORKFLOW.md)
- [Credit policy design](docs/CREDIT_POLICY_DESIGN.md)
- [Security and governance](docs/SECURITY_GOVERNANCE.md)
- [Evaluation](docs/EVALUATION.md)
- [Demo scenarios](docs/DEMO_SCENARIOS.md)

Repository-level instructions for future Codex work are in
[`AGENTS.md`](AGENTS.md).

## Current Status

Phase 0 documentation is approved and frozen as of 2026-09-15.

Phases 1 through 3 are complete. CreditPilot now has the synthetic quantitative
baseline, typed protected CreditState, and permission-controlled internal data,
feature, model, SHAP, audit, and state-commit tools. The next planned phase is
Phase 4 - synthetic policy knowledge base and RAG. The approved quantitative
baseline remains scikit-learn Logistic Regression.

Phase 4 is complete with a fully synthetic, versioned policy corpus, stable
section citations, local TF-IDF retrieval, permission-controlled policy search,
and raw-evidence state commit. Phase 5 is also complete with a provider-neutral,
grounded Policy Agent boundary and deterministic structured-output validation.
Phase 6 is complete with offline synthetic verification evidence, three
permission-controlled verification tools, and a bounded Verification Agent
proposal flow. Phase 7 is complete with a provider-independent Orchestrator,
deterministic next-action validation, protected proposal conversion, and
reference-only audit. Phase 8 is complete with an explicit bounded integration
cycle connecting policy, orchestration, verification, protected state, audit,
and workflow limits. Phase 9 is complete with pre-decision eligibility checks,
an explicitly configured deterministic Decision Engine, protected recommendation
commit, decision audit, and post-decision human-review routing. Phase 10 is
complete with a bounded Escalation Agent, offline idempotent review-case and
notification tools, protected action-result references, and audit. The next
planned phase is Phase 11 - Explanation Agent.

## Phase 1 Baseline

The current implementation provides:

- deterministic synthetic credit-risk data with no real PII;
- validated numeric and categorical model features;
- stratified training, validation, and test splits;
- an sklearn Logistic Regression probability-of-default baseline;
- ROC-AUC, PR-AUC, Precision, Recall, F1, KS, Brier score, confusion matrix,
  and calibration evaluation;
- quantitative SHAP attribution;
- tests for reproducibility, schema protection, model output, and SHAP.

Install the package and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
python -m ruff check .
python -m pytest
```

Generate the reproducible baseline report:

```bash
python -m creditpilot.ml.cli \
  --output reports/phase1_baseline_metrics.json
```

The configured cutoff is for model diagnostics only. It is not a lending,
policy, risk-band, or recommendation threshold.

## Planned Development Sequence

1. Phase 0 - architecture and harness documentation;
2. Phase 1 - dataset and quantitative credit-risk model;
3. Phase 2 - schemas and CreditState;
4. Phase 3 - internal deterministic tools;
5. Phase 4 - synthetic policy knowledge base and RAG;
6. Phase 5 - Policy Agent;
7. Phase 6 - verification tools and Verification Agent;
8. Phase 7 - Orchestrator Agent;
9. Phase 8 - workflow integration;
10. Phase 9 - deterministic Decision Engine;
11. Phase 10 - escalation and external action tools;
12. Phase 11 - Explanation Agent;
13. Phase 12 - ML, RAG, agent, safety, and end-to-end evaluation;
14. Phase 13 - API and analyst interface;
15. Phase 14 - deployment and monitoring.

Credit data classification, verification-request ownership, and mandatory
review ordering were approved on 2026-09-15. Remaining technology choices and
open design questions remain subject to human approval.

## Golden Demo Scenarios

V1 is designed to demonstrate:

- a straightforward low-risk path;
- a case where verified income changes the risk assessment;
- a policy or evidence conflict that routes safely to human review.

See [`docs/DEMO_SCENARIOS.md`](docs/DEMO_SCENARIOS.md) for the proposed
scenario definitions.

## Disclaimer

CreditPilot uses synthetic/demo data and synthetic policy for portfolio and
learning purposes. It does not make real lending decisions and is not legal,
regulatory, or underwriting advice.
