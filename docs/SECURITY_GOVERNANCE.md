# CreditPilot — Security and Governance

## Status

Phase 0 — Approved and Frozen

Approved and frozen on 2026-09-15.

## Authority

This document derives from `docs/ARCHITECTURE_SPEC_V1.md` and applies its
security, privacy, state-protection, audit, and human-authority requirements.

The architecture specification remains authoritative. Credit data
classification, verification-request ownership, and mandatory-review ordering
were approved on 2026-09-15.

## 1. Security Objectives

CreditPilot V1 must:

- use synthetic, mock, simulated, or suitable public demo data only;
- keep raw identity PII outside the main AI workflow;
- minimize data and context exposed to agents and LLMs;
- enforce least privilege for state and tool access;
- protect quantitative outputs, verification state, workflow state, and
  recommendation fields;
- control and audit external actions;
- make failures and mandatory-review routing explicit;
- preserve traceability without placing unnecessary raw PII in logs.

## 2. Data Boundaries

### 2.1 Main Workflow Boundary

The main workflow should use:

- `application_id`;
- `case_id`;
- opaque `customer_token`;
- non-PII application attributes;
- sanitized evidence;
- model outputs;
- policy findings;
- workflow state.

Raw identity PII must not be unnecessarily exposed to agents or LLMs.

### 2.2 PII Vault Boundary

Identity information and token-to-identity mappings belong in a separately
protected PII Vault.

Agents must not directly access the PII Vault. Access must:

- use explicitly authorized capabilities;
- follow least privilege;
- be independently audited;
- remain unavailable to ordinary agent reasoning.

### 2.3 Credit Data Classification

CreditPilot V1 uses three information classes:

- Identity PII includes raw name, email, address, identity identifiers, and
  token mappings and remains in the protected PII Vault.
- Sensitive Credit Data includes income, employment information, credit bureau
  information, and verified financial evidence and may enter CreditState only
  in structured, minimum-necessary, access-controlled form.
- Derived Risk Features include DTI, approved derived features, PD, risk band,
  and SHAP and may enter protected CreditState under explicit ownership and
  minimum-context controls.

Raw identity documents and unnecessary identity PII must not enter CreditState
or ordinary agent and LLM context.

## 3. Deterministic PII Governance Layer

All incoming application data must pass through a deterministic PII Governance
Layer before entering the main workflow.

It is responsible for:

- schema-based PII classification;
- deterministic PII identification;
- tokenization;
- identity separation;
- context sanitization;
- access-control enforcement;
- PII-access auditing.

An LLM must not be the primary PII detection or protection mechanism.

## 4. Tokenization

Inside the AI workflow, customer identity is represented by opaque
`customer_token`.

The token must not contain meaningful identity information. Raw identity data
and token mappings must remain outside CreditState.

## 5. LLM Context Controls

Before context is sent to an LLM:

1. construct the context from an allowlist;
2. remove unnecessary PII;
3. apply deterministic PII redaction;
4. provide only the minimum information necessary for the agent's role.

Do not send complete CreditState to every agent. Use authorized role-specific
views.

LLM output is untrusted proposed content until it passes schema, permission,
ownership, and workflow validation.

## 6. Agent Boundaries

CreditPilot V1 contains exactly five LLM-enabled agents. Each receives only the
minimum state and tools required for its role.

Agents must not:

- gain direct PII Vault access;
- modify protected quantitative outputs;
- bypass workflow or state controls;
- fabricate policy, thresholds, PD, SHAP, or verified facts;
- directly write protected recommendation fields;
- bypass mandatory human review;
- call arbitrary external systems.

Additional agents require an approved architecture change.

## 7. Tool Security

Every tool is a typed, bounded capability with explicit permissions and
side-effect boundaries.

Before invocation, deterministic controls verify:

- caller authorization;
- tool permission;
- minimum-necessary arguments;
- workflow preconditions;
- state version and transition validity;
- retry and tool-call limits;
- side-effect and idempotency requirements.

Tool results do not grant unrestricted state mutation authority.

External actions require:

- explicit preconditions;
- permission checks;
- audit logging;
- sanitized inputs;
- deterministic workflow approval;
- idempotency where appropriate.

## 8. Protected State Governance

Every protected field has an explicit owner.

- quantitative components own PD and model outputs;
- Policy Agent owns policy findings;
- verification tools obtain raw evidence;
- Verification Agent interprets, structures, and proposes verification updates;
- deterministic controls validate and commit protected verification state;
- Orchestrator Agent owns the proposed next action;
- Decision Engine exclusively owns recommendation fields;
- Explanation Agent owns the analyst-facing explanation;
- Escalation Agent and controlled tools own escalation fields;
- Workflow Controller owns protected transitions and counters.

Unauthorized or stale state updates must be rejected explicitly and recorded
when material.

## 9. Verification Governance

Reported and verified information must remain separate and traceable.

The Orchestrator proposes verification-request creation. Deterministic workflow
and state controls validate, create, and commit the protected request. The
Verification Agent may act only on an approved committed request.

Approved verification tools obtain and return raw evidence. The Verification
Agent may interpret and structure evidence and propose updates, but it must not
fabricate verified facts or bypass protected state controls.

Deterministic workflow and state controls validate and commit protected
verification-state updates. Raw identity PII must not be copied into
CreditState.

Verification provider selection remains open under OQ-4.

## 10. Quantitative and Decision Protection

Only approved quantitative components may write:

- `pd_score`;
- `risk_band`;
- SHAP risk factors;
- `model_version`;
- `model_timestamp`.

Only the deterministic Decision Engine may write:

- `recommendation`;
- `decision_rule`;
- `decision_reason`.

LLM-enabled agents may not override these fields.

## 11. Human Authority

Human review is a protected workflow state. Before Decision Engine entry, the
Workflow Controller routes ineligible mandatory-review cases safely. For
eligible cases, the Decision Engine writes the recommendation, after which the
Workflow Controller enforces every applicable mandatory-review condition
without rewriting that recommendation. Human review cannot be bypassed by an
agent or recommendation.

The Escalation Agent may prepare a sanitized review package and request
approved external actions. It must not make the human decision.

Notifications and review packages must avoid unnecessary raw PII and normally
use controlled references.

## 12. Auditability

Preserve traceable records for:

- case references;
- model versions, timestamps, and outputs;
- SHAP results;
- retrieved policy evidence and versions;
- agent outputs;
- tool calls and outcomes;
- workflow transitions;
- verification evidence;
- Decision Engine rules and recommendations;
- escalation reasons and action outcomes;
- human-review outcomes where captured;
- relevant timestamps.

PII-access auditing must remain separately identifiable from ordinary model,
agent, tool, and workflow auditing.

## 13. Failure and Abuse-Safe Routing

Failures must be explicit. The system must not turn missing, failed, malformed,
or unavailable results into successful evidence.

Enforce deterministic:

- input and output validation;
- permission checks;
- maximum retries;
- maximum tool calls;
- maximum investigation iterations;
- timeout handling;
- safe fallback and human-review routing.

Reject invalid agent output. Do not allow uncontrolled recursive execution.

## 14. Secret Management

Credentials, provider tokens, signing material, database credentials, and other
secrets must not appear in source code, prompts, CreditState, synthetic demo
data, logs, traces, notifications, or review packages.

Only the component or typed capability that requires a secret may receive it,
using least privilege and minimum scope. Agents and LLMs must not receive raw
secrets. Secret access and use must remain separate from ordinary reasoning
context and must be auditable where material.

The concrete secret store, rotation process, credential lifetime, and
deployment integration require later implementation approval.

## 15. Governance Invariants

1. CreditPilot uses no real customer PII or proprietary bank policy.
2. Raw identity PII remains outside the main workflow and CreditState.
3. LLM context is allowlisted, sanitized, and minimum necessary.
4. Agents receive least-privilege state and tool access.
5. Deterministic components enforce permissions, transitions, and limits.
6. Agents cannot alter quantitative outputs or recommendations.
7. Verification evidence ownership and commit boundaries remain enforced.
8. Reported and verified evidence remain separate.
9. External side effects are controlled and audited.
10. Mandatory human review cannot be bypassed.
11. Failures remain explicit and safely routed.
12. Material activity and versions remain traceable.

## 16. Decisions Not Made Here

This document does not resolve:

- physical security or deployment architecture;
- authentication implementation;
- concrete authorization model;
- key or secret management implementation;
- verification providers;
- thresholds;
- model choice;
- human-review interface;
- retention periods.

These require explicit later design approval.

## 17. Review Gate

The approved document must continue to satisfy:

- confirm the PII Vault and main-workflow boundary;
- approve sensitive-attribute classification separately;
- confirm role-specific minimum context;
- confirm tool and state permissions;
- confirm verification and recommendation protections;
- confirm external-action controls;
- confirm audit separation and failure routing;
- confirm no open architecture question was resolved implicitly;
- record human approval.
