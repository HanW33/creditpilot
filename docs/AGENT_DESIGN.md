# CreditPilot — Agent Design

## Status

Phase 0 — Approved and Frozen

Approved and frozen on 2026-09-15.

## Authority

This document defines the proposed operating contracts for the five
LLM-enabled agents approved in `docs/ARCHITECTURE_SPEC_V1.md`.

The architecture specification remains the canonical source of truth.
`docs/STATE_DESIGN.md`, `docs/TOOL_DESIGN.md`, and `docs/WORKFLOW.md`
provide the related proposed state, tool, and workflow contracts. If this
document conflicts with them, the architecture specification takes precedence.

This document does not add agents, transfer deterministic authority to an LLM,
select a model or provider, define thresholds, or choose a human-review
interface.

## 1. Approved Agent Set

CreditPilot V1 contains exactly five specialized LLM-enabled agents:

1. Orchestrator Agent;
2. Policy Agent;
3. Verification Agent;
4. Explanation Agent;
5. Escalation Agent.

No additional agent may be introduced without an explicit architecture change
proposal and human approval.

## 2. Common Agent Contract

Every agent operates within this boundary:

```text
Authorized, sanitized, minimum-necessary state view
        ↓
Agent performs role-specific reasoning
        ↓
Structured output, action request, or state-update proposal
        ↓
Deterministic schema, permission, ownership, and workflow validation
        ↓
Designated owner writes protected fields
        ↓
Auditable state transition or explicit rejection
```

Agents reason and propose. They do not receive unrestricted authority to mutate
CreditState, enforce workflow transitions, execute arbitrary code, access
arbitrary systems, or replace deterministic and quantitative components.

## 3. Common Input Envelope

Each agent invocation should receive a logical envelope:

```text
AgentInvocation
├── invocation_id
├── agent_role
├── application_id
├── case_id
├── input_state_version
├── purpose
├── authorized_state_view
├── permitted_tools[]
├── workflow_constraints
└── invoked_at
```

Rules:

- `agent_role` must identify one of the five approved agents;
- `authorized_state_view` must be constructed from an allowlist;
- context must be sanitized and limited to what the role and task require;
- raw identity PII and PII Vault mappings must not enter ordinary agent context;
- `permitted_tools` must contain only approved least-privilege capabilities;
- workflow constraints, retry limits, and tool-call limits are enforced by
  deterministic controls, not by trusting the agent.

## 4. Common Output Envelope

Every agent must return valid structured output:

```text
AgentOutput
├── invocation_id
├── agent_role
├── status
├── reasoning_summary
├── evidence_references[]
├── structured_result
├── proposed_actions[]
├── proposed_state_updates[]
├── unresolved_items[]
├── created_at
└── failure
```

Rules:

- evidence references must support material findings;
- proposed actions and updates must identify their basis;
- unresolved uncertainty and conflicts must remain explicit;
- invalid structured output must be rejected;
- agent output remains proposed content until deterministic validation;
- an agent must not claim a tool call, state commit, external action, or human
  outcome that did not occur;
- failures must be explicit and safely routed.

The implementation may narrow an output for a specific agent but must preserve
the relevant provenance, validation, and authority boundaries.

## 5. Shared Agent Requirements

All five agents must:

- use only authorized, sanitized, minimum-necessary context;
- stay within their assigned role;
- preserve evidence provenance;
- distinguish source evidence from interpretation;
- produce structured, validateable output;
- expose missing, conflicting, or unresolved evidence;
- use only explicitly permitted tools;
- respect deterministic workflow decisions and protected state ownership;
- avoid unnecessary raw PII in prompts, outputs, logs, and notifications;
- stop and return explicit failure when required evidence or capability is
  unavailable;
- remain within configured retries, tool calls, iterations, and timeouts.

## 6. Shared Prohibitions

No LLM-enabled agent may:

- create, replace, or modify PD, risk band, SHAP output, model version, or model
  timestamp;
- write `recommendation`, `decision_rule`, or `decision_reason`;
- bypass Workflow Controller decisions or protected state controls;
- bypass mandatory human review;
- invent policy, thresholds, model outputs, verified facts, tool results, or
  human outcomes;
- access the PII Vault directly;
- expose unnecessary raw PII;
- call arbitrary external systems or use unapproved tools;
- create uncontrolled recursive execution or retry loops;
- convert a missing, failed, or unavailable result into success.

## 7. Orchestrator Agent

### 7.1 Purpose

Determine and propose the next investigation step based on the authorized
current case state.

The Orchestrator coordinates investigation. It does not calculate credit risk,
perform verification, enforce workflow transitions, or make the final
recommendation.

### 7.2 Authorized Inputs

The Orchestrator may receive the minimum authorized view of:

- application and case references;
- sanitized application evidence;
- validation and data-quality state;
- quantitative model status and outputs;
- policy findings, required evidence, and conflicts;
- verification status and committed evidence;
- current workflow state;
- retry, tool-call, and investigation-limit status;
- mandatory-review conditions.

### 7.3 Structured Output

The Orchestrator owns the proposed next workflow action.

A logical output contains:

```text
OrchestratorOutput
├── proposed_next_action
├── reason
├── evidence_references[]
├── prerequisites[]
├── unresolved_items[]
└── status
```

The proposed action does not become a transition until the deterministic
Workflow Controller validates it.

### 7.4 Permissions

The Orchestrator may:

- identify unresolved evidence;
- compare required evidence with current state;
- propose verification, reevaluation, decision, explanation, escalation, or
  another architecture-approved next step;
- coordinate the bounded investigation loop.

The Orchestrator must not receive verification or external-action tools merely
to perform those roles itself.

### 7.5 Prohibitions

The Orchestrator must not:

- decide WHAT policy requires independently of Policy Agent findings;
- perform HOW verification is obtained;
- invoke unauthorized tools;
- enforce or commit workflow transitions;
- change protected evidence or model state;
- write recommendation fields;
- bypass limits or mandatory human review.

## 8. Policy Agent

### 8.1 Purpose

Determine which synthetic credit policies apply to the current case evidence
and identify policy-required evidence and constraints.

The Policy Agent determines WHAT evidence is required.

### 8.2 Authorized Inputs

The Policy Agent may receive:

- application and case references;
- sanitized, minimum-necessary case evidence;
- retrieved synthetic policy evidence;
- source, section or chunk, policy version, retrieval score where available,
  and effective date where applicable;
- current relevant policy state.

### 8.3 Permitted Tools

The Policy Agent may use:

- `search_credit_policy()`.

No unrelated or external side-effect capability is implied.

### 8.4 Structured Output

The Policy Agent owns structured policy findings:

```text
PolicyAgentOutput
├── status
├── applicable_policy_evidence[]
├── interpretation
├── required_evidence[]
├── policy_constraints[]
├── conflicts[]
├── unresolved_items[]
└── source_references[]
```

### 8.5 Requirements

The Policy Agent must:

- ground material findings in retrieved synthetic policy;
- preserve citations and policy versions;
- distinguish retrieved evidence from interpretation;
- identify missing or conflicting policy evidence;
- make retrieval failure explicit.

### 8.6 Prohibitions

The Policy Agent must not:

- invent policy or thresholds;
- represent synthetic policy as real bank policy;
- perform external verification;
- decide WHETHER the workflow should verify now;
- decide HOW verification is performed;
- write quantitative, workflow-transition, verification, or recommendation
  fields;
- treat retrieval failure as policy approval.

## 9. Verification Agent

### 9.1 Purpose

Determine HOW to obtain requested evidence using only approved verification
tools.

It acts only after the Policy Agent identifies the evidence requirement, the
Orchestrator proposes request creation, and deterministic workflow and state
controls validate, create, and commit the protected verification request.

### 9.2 Authorized Inputs

The Verification Agent may receive:

- approved committed verification request ID;
- application and case references;
- opaque customer reference;
- required-evidence finding;
- sanitized minimum context needed for tool selection;
- current verification status;
- permitted verification tools;
- workflow limits and authorization outcome.

### 9.3 Permitted Tools

The Verification Agent may use:

- `verify_income()`;
- `verify_employment()`;
- `get_credit_report()`.

The selected provider remains unresolved under OQ-4.

### 9.4 Structured Output

```text
VerificationAgentOutput
├── status
├── selected_tool
├── selection_reason
├── tool_result_references[]
├── structured_evidence
├── proposed_state_update
├── conflicts[]
└── unresolved_items[]
```

### 9.5 Evidence Ownership

Approved verification tools obtain and return raw evidence.

The Verification Agent may act only on an approved committed request. It may:

- select an approved method;
- interpret returned evidence;
- structure evidence;
- identify conflicts;
- propose evidence or verification-state updates.

Deterministic workflow and state controls validate and commit protected
verification-state updates.

### 9.6 Prohibitions

The Verification Agent must not:

- decide WHAT policy requires;
- decide WHETHER the workflow should verify without authorization;
- fabricate verified facts;
- overwrite reported applicant information;
- directly commit protected verification state;
- bypass tool permissions, state controls, or workflow limits;
- copy unnecessary raw identity PII into CreditState;
- write model or recommendation fields.

## 10. Explanation Agent

### 10.1 Purpose

Convert existing approved model, SHAP, policy, verification, workflow, and
recommendation evidence into a clear analyst-facing explanation.

### 10.2 Authorized Inputs

The Explanation Agent may receive read-only access to:

- application and case references;
- sanitized application summary;
- approved model output and version;
- SHAP risk factors;
- grounded policy findings and citations;
- committed verification evidence and conflicts;
- deterministic recommendation, rule, and reason;
- escalation reason and relevant workflow state;
- audit references needed for traceability.

### 10.3 Tool Permissions

The Explanation Agent has read-only access to approved state and no external
side-effect tools.

### 10.4 Structured Output

```text
ExplanationAgentOutput
├── status
├── explanation
├── evidence_references[]
├── input_state_version
├── limitations[]
└── unresolved_items[]
```

### 10.5 Requirements

The explanation must:

- accurately reflect existing evidence;
- distinguish model, policy, verification, and decision evidence;
- communicate conflicts, limitations, and mandatory-review reasons;
- remain traceable to approved inputs;
- avoid autonomous lending claims.

### 10.6 Prohibitions

The Explanation Agent must not:

- modify model outputs, policy findings, verification evidence, workflow state,
  or recommendations;
- invent evidence, policy, thresholds, or reasons;
- conceal material uncertainty or failure;
- trigger arbitrary external actions;
- expose unnecessary raw PII.

## 11. Escalation Agent

### 11.1 Purpose

Prepare and coordinate a controlled handoff to an authorized human analyst when
human review is required.

### 11.2 Authorized Inputs

The Escalation Agent may receive:

- application or case reference;
- sanitized application summary;
- approved model output and version;
- SHAP risk factors;
- policy findings and citations;
- verification evidence and conflicts;
- deterministic recommendation;
- mandatory-review or escalation reasons;
- relevant audit references;
- permitted external actions.

### 11.3 Permitted Tools

The Escalation Agent may use:

- `create_review_case()`;
- `send_notification()`.

These tools remain subject to deterministic preconditions, permissions,
sanitization, audit, and idempotency controls where appropriate.

### 11.4 Structured Output

```text
EscalationAgentOutput
├── status
├── escalation_reason
├── review_package
├── requested_actions[]
├── evidence_references[]
├── unresolved_items[]
└── action_result_references[]
```

### 11.5 Requirements

The Escalation Agent may:

- summarize the case and approved evidence;
- identify unresolved issues;
- explain why human review is required;
- prepare a sanitized review package;
- request approved external actions.

### 11.6 Prohibitions

The Escalation Agent must not:

- make the human decision;
- modify the deterministic recommendation;
- bypass mandatory review or escalation transitions;
- directly call arbitrary external systems;
- claim an external action succeeded before its tool result;
- include unnecessary raw PII in review packages or notifications.

The human-review interface remains unresolved under OQ-5.

## 12. Responsibility Matrix

| Responsibility | Owner |
| --- | --- |
| Next investigation proposal | Orchestrator Agent |
| Applicable policy interpretation | Policy Agent |
| WHAT evidence is required | Policy Agent |
| WHETHER verification is needed now and request creation is proposed | Orchestrator Agent |
| Protected verification-request validation, creation, and commit | Deterministic workflow and state controls |
| HOW approved verification evidence is obtained | Verification Agent |
| Raw verification evidence retrieval | Approved verification tools |
| Protected verification-state validation and commit | Deterministic workflow/state controls |
| PD, risk band, and SHAP | Approved quantitative components |
| Workflow transitions and counters | Workflow Controller |
| Recommendation, decision rule, and decision reason | Decision Engine |
| Analyst-facing explanation | Explanation Agent |
| Escalation preparation | Escalation Agent |
| Controlled external actions | Approved action tools |
| Mandatory human decision | Authorized human analyst |

No single agent owns the complete verification, workflow, or decision chain.

## 13. Agent Invocation Lifecycle

1. Deterministic workflow logic establishes that an agent step is permitted.
2. An allowlisted, sanitized, minimum-necessary state view is created.
3. The agent receives only its permitted tools and workflow constraints.
4. The agent returns structured output.
5. Deterministic controls validate schema, role, evidence, permissions, state
   ownership, transition validity, and limits.
6. Invalid output is rejected and preserved as an explicit failure.
7. Valid actions or updates proceed through the designated owner and protected
   state-commit path.
8. Invocation, output, tool activity, validation, transition, and commit
   outcomes are linked to audit records.

## 14. Failure Handling

If an agent returns invalid structured output:

- reject it;
- preserve the error;
- retry only within configured limits;
- route to safe fallback or human review.

If evidence, policy retrieval, verification, or a tool fails, the agent must
not fill the gap with invented content.

When retry, tool-call, investigation, or timeout limits are reached, execution
must stop safely and route according to deterministic workflow rules.

## 15. Audit Requirements

Preserve:

- invocation and agent role;
- application or case reference;
- purpose;
- input state version;
- authorized context reference;
- permitted tools;
- structured output;
- evidence references;
- proposed actions and updates;
- validation result;
- tool calls and outcomes;
- workflow transition;
- failure and retry information;
- timestamps and relevant versions.

Logs and traces must avoid unnecessary raw PII. PII-access auditing remains
separately identifiable.

## 16. Evaluation Requirements

Evaluate each agent for:

- role adherence;
- grounded use of evidence;
- valid structured output;
- correct use of permitted tools;
- refusal to exceed authority;
- explicit treatment of uncertainty and conflict;
- safe failure behaviour;
- protected state compliance;
- PII and minimum-context compliance.

Architecture-invariant violations are failures regardless of other output
quality.

## 17. Approved Critical Decisions

The following architecture decisions were approved on 2026-09-15:

- Identity PII remains in the PII Vault; Sensitive Credit Data may enter
  CreditState only in structured, minimum-necessary, access-controlled form;
  Derived Risk Features may enter protected state under explicit ownership.
- The Orchestrator proposes verification-request creation; deterministic
  workflow and state controls validate, create, and commit the request; the
  Verification Agent acts only on an approved committed request.
- The Workflow Controller checks evidence eligibility before Decision Engine
  entry and enforces mandatory review after recommendation without rewriting
  the recommendation.

## 18. Design Invariants

1. Exactly five LLM-enabled agents exist in V1.
2. Agents reason and propose; deterministic controls protect state.
3. Agents do not replace deterministic or quantitative components.
4. Policy Agent = WHAT.
5. Orchestrator Agent = WHETHER.
6. Verification Agent = HOW.
7. Verification tools obtain raw evidence.
8. Reported and verified values remain separate.
9. The Decision Engine alone writes recommendation fields.
10. The Explanation Agent is read-only relative to decision evidence.
11. The Escalation Agent does not make the human decision.
12. Mandatory human review cannot be bypassed.
13. Tools and context remain least-privilege and minimum-necessary.
14. Failures and limits remain explicit and safely routed.
15. Material agent activity remains auditable.

## 19. Decisions Not Made Here

This document does not select:

- LLM or model provider;
- prompt framework;
- orchestration framework;
- physical agent runtime;
- synthetic thresholds;
- verification provider;
- retry or loop counts;
- human-review interface;
- baseline or challenger quantitative model.

These require separate approval.

## 20. Review Gate

The approved document must continue to satisfy:

- confirm all five roles, inputs, outputs, permissions, and prohibitions;
- confirm the WHAT / WHETHER / HOW verification boundary;
- confirm protected state and recommendation ownership;
- confirm PII and minimum-context controls;
- confirm failure, limit, and audit requirements;
- confirm no additional agent or authority was introduced;
- record human approval.
