# CreditPilot — Evaluation

## Status

Phase 0 — Approved and Frozen

Approved and frozen on 2026-09-15.

## Authority

This document derives from `docs/ARCHITECTURE_SPEC_V1.md`. It defines what
CreditPilot V1 must evaluate without selecting acceptance thresholds, a model,
a verification provider, or a human-review interface.

The architecture specification remains authoritative.

## 1. Evaluation Purpose

Evaluation must show that CreditPilot:

- supports analysts with traceable decision evidence;
- preserves deterministic, ML, agent, tool, and human boundaries;
- produces quantitative model outputs only through approved model components;
- grounds policy findings in retrieved synthetic policy;
- obtains verification evidence without fabrication;
- protects CreditState ownership;
- routes failures and unresolved cases safely;
- explains recommendations from existing evidence;
- preserves auditability and PII boundaries;
- supports the three Golden Demo scenarios.

Evaluation is for a synthetic portfolio and learning system, not validation of
a production lending system.

## 2. Evaluation Layers

Evaluate five layers separately and end to end:

1. deterministic controls;
2. quantitative model and SHAP;
3. agent reasoning and structured outputs;
4. tool execution and evidence handling;
5. workflow, recommendation, explanation, escalation, and audit outcomes.

A strong result in one layer must not hide a failure in another.

## 3. Deterministic Control Evaluation

Verify that:

- application validation is deterministic;
- feature calculations are reproducible for identical inputs and versions;
- invalid transitions are rejected;
- unauthorized tool calls and state mutations are rejected;
- retry, tool-call, investigation, and timeout limits are enforced;
- mandatory human-review conditions cannot be bypassed;
- only the Decision Engine writes recommendation fields;
- stale or invalid protected updates fail explicitly.

No numeric acceptance threshold is defined here.

## 4. Quantitative Model Evaluation

Evaluate the approved model for:

- PD output correctness and reproducibility;
- risk scoring and calibration;
- model-version and timestamp traceability;
- input-state-version traceability;
- SHAP attribution generated from the model;
- explicit handling of model and SHAP failures;
- protection against agent modification.

The exact baseline model, challenger model, dataset split, metrics, and
acceptance thresholds require later approval.

## 5. Policy Evaluation

Evaluate whether:

- retrieval returns relevant synthetic policy evidence;
- evidence preserves source, section or chunk, and policy version;
- retrieval score and effective date are preserved where available;
- the Policy Agent separates evidence from interpretation;
- required evidence and conflicts are grounded and cited;
- policy and thresholds are never invented;
- retrieval failure never becomes approval;
- invalid Policy Agent output is rejected and routed safely.

## 6. Verification Evaluation

Evaluate the complete boundary:

- Policy Agent identifies WHAT evidence is required;
- Orchestrator determines WHETHER verification is needed;
- Verification Agent determines HOW to obtain it;
- approved tools obtain and return raw evidence;
- the Verification Agent interprets, structures, and proposes updates;
- deterministic controls validate, create, and commit the protected
  verification request;
- the Verification Agent acts only on an approved committed request;
- deterministic controls validate and commit protected verification state.

Verify that reported and verified values remain separate, raw evidence is not
fabricated, failures remain explicit, and raw identity PII is not copied into
CreditState.

Provider-specific evaluation remains open under OQ-4.

## 7. Agent Evaluation

For each approved agent, test:

- role adherence;
- authorized-input and minimum-context use;
- valid structured output;
- grounded reasoning;
- refusal to exceed authority;
- explicit uncertainty and conflict handling;
- safe behaviour when evidence or tools fail;
- preservation of protected state boundaries.

Agent-specific checks:

| Agent | Required behaviour |
| --- | --- |
| Orchestrator | Proposes the next step but does not enforce transitions or make recommendations. |
| Policy Agent | Interprets retrieved policy without inventing rules or thresholds. |
| Verification Agent | Selects approved verification methods without fabricating facts or committing protected state directly. |
| Explanation Agent | Explains existing evidence without altering it. |
| Escalation Agent | Prepares controlled handoff without making the human decision. |

## 8. Tool Evaluation

For each tool, verify:

- typed input and structured output validation;
- caller authorization and least privilege;
- bounded capability and result;
- explicit status and failure;
- provenance and timestamps;
- audit linkage;
- retry and timeout control;
- state-commit separation.

For action tools, additionally verify deterministic preconditions, sanitized
payloads, permission checks, audit records, and idempotency where appropriate.

## 9. Security and Privacy Evaluation

Verify that:

- real customer PII is absent from test data;
- raw identity PII and token mappings remain outside CreditState;
- `customer_token` is opaque;
- agents cannot directly access the PII Vault;
- LLM contexts are allowlisted, redacted, and minimum necessary;
- prompts, logs, traces, notifications, and review packages avoid unnecessary
  raw PII;
- PII-access audit records remain separately identifiable.

Identity PII must remain in the PII Vault. Evaluation must verify that
Sensitive Credit Data enters CreditState only in structured, minimum-necessary,
access-controlled form and that Derived Risk Features retain protected
ownership and minimum-context controls.

## 10. Decision and Explanation Evaluation

Verify that:

- the Workflow Controller blocks Decision Engine entry for ineligible evidence
  and routes those cases safely to human review;
- the Decision Engine uses eligible approved committed evidence;
- recommendation, decision rule, and reason are deterministic and traceable;
- agents cannot modify recommendation fields;
- after recommendation, the Workflow Controller enforces mandatory-review
  conditions without rewriting the recommendation;
- the Explanation Agent accurately reflects model, SHAP, policy,
  verification, and recommendation evidence;
- explanations do not add unsupported facts or policy.

## 11. Failure and Recovery Evaluation

Test at least:

- invalid application;
- model failure;
- SHAP failure;
- policy retrieval failure;
- conflicting policy evidence;
- verification failure;
- conflicting reported and verified evidence;
- tool failure;
- invalid agent structured output;
- unauthorized action;
- stale state-update proposal;
- retry or investigation limit exhaustion;
- external action failure.

Expected behaviour is explicit failure state, bounded retry where configured,
auditable handling, and safe fallback or human-review routing.

## 12. Golden Demo Evaluation

The evaluation suite must cover:

1. straightforward low-risk case;
2. verification changes the risk assessment;
3. policy or evidence conflict.

For each scenario, capture:

- initial synthetic inputs;
- expected workflow path;
- expected agents and tools used;
- expected state-domain changes;
- expected recommendation category where already specified by architecture;
- expected human-review behaviour;
- expected audit evidence;
- prohibited behaviours.

## 13. Golden Demos as Future Executable Tests

In later implementation phases, each Golden Demo must become a versioned
end-to-end test fixture with:

- synthetic starting data;
- expected model-state conditions without inventing unapproved thresholds;
- expected policy findings and citations;
- expected agent actions and prohibited actions;
- expected tool calls and explicit non-calls;
- expected workflow transitions;
- expected protected state ownership;
- expected final decision-support or human-review state;
- expected audit records;
- injected failure variants.

The tests must assert architecture invariants, not merely compare narrative
text. They should verify structured outputs, state transitions, ownership,
provenance, failure routing, and prohibited behaviour.

Executable test implementation begins only in the appropriate later phase after
the relevant modules and open decisions have been approved.

## 14. Evaluation Record

Each evaluation run should preserve:

- evaluation ID and scenario;
- test-data version;
- model and policy versions;
- workflow and state-schema versions;
- agent and tool versions where available;
- inputs or authorized input references;
- expected results;
- actual results;
- pass, fail, or unresolved status;
- failure details;
- timestamps;
- evidence and audit references.

## 15. Acceptance Rules

Architecture invariants are hard requirements. A violation of protected
ownership, PII separation, recommendation authority, mandatory review, evidence
fabrication, or uncontrolled looping is a failed evaluation regardless of
other quality results.

Quantitative targets and quality thresholds are not set in this document.
They must be configurable, clearly identified as synthetic where applicable,
and approved separately.

## 16. Decisions Not Made Here

This document does not select:

- evaluation dataset;
- model metrics or thresholds;
- retrieval thresholds;
- agent-quality scoring thresholds;
- latency or cost targets;
- verification provider;
- human-review interface;
- baseline or challenger model.

## 17. Review Gate

The approved document must continue to satisfy:

- confirm evaluation coverage for every architecture layer;
- confirm all three Golden Demo scenarios;
- confirm hard invariant failures;
- confirm security, audit, and failure tests;
- approve metrics and thresholds separately;
- record human approval.
