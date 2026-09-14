# CreditPilot

CreditPilot is an agentic AI credit risk decision-support system for a Credit
Risk Analyst or Underwriter. It is currently in Phase 0: architecture and
harness documentation.

No application functionality has been implemented yet.

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

Phase 0 documentation is under consistency review and pending human approval.
The architecture must be reviewed and frozen before implementation begins.

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
