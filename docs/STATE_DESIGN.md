# CreditPilot — State Design

## Status

Phase 0 — Approved and Frozen

Approved and frozen on 2026-09-15.

## Authority

This document defines the proposed logical CreditState structure for
CreditPilot V1. It resolves OQ-2 from `docs/ARCHITECTURE_SPEC_V1.md` only after
human approval.

`docs/ARCHITECTURE_SPEC_V1.md` remains the canonical architecture source of
truth. If this document conflicts with it, the architecture specification
takes precedence.

This design does not select a programming language, schema library, database,
storage format, verification provider, model, threshold, or human-review
interface.

## 1. Design Goals

CreditState must:

- represent the current state of one credit case;
- keep reported and verified information separate and traceable;
- enforce explicit ownership of protected fields;
- let agents propose actions and updates without unrestricted mutation;
- support deterministic validation and state-transition enforcement;
- preserve failures, retries, loop limits, and mandatory-review conditions;
- support model, policy, verification, workflow, decision, and audit
  traceability;
- exclude raw identity PII from the main state;
- provide only authorized, sanitized, minimum-necessary context to agents and
  LLMs.

## 2. Logical Structure

CreditState is one versioned record with these top-level domains:

```text
CreditState
├── state_metadata
├── identity_references
├── application_data
├── validation_state
├── quantitative_model_state
├── policy_state
├── verification_state
├── workflow_state
├── recommendation_state
├── explanation_state
├── escalation_state
└── governance_audit_references
```

A physical representation may use objects, records, tables, or another approved
storage mechanism, but it must preserve these logical domains and ownership
boundaries.

## 3. Common Record Conventions

Material records should carry applicable provenance fields:

| Field | Purpose |
| --- | --- |
| `record_id` | Opaque record identifier. |
| `status` | Explicit outcome or lifecycle state. |
| `created_at` | Creation timestamp. |
| `created_by` | Authorized component, agent, tool, or human that produced it. |
| `source_reference` | Originating application, policy, model, tool, or review reference. |
| `version` | Relevant model, policy, workflow, schema, or record version. |

Do not duplicate raw source payloads merely to satisfy this convention.
Missing, unavailable, failed, and unresolved must not be represented as a
successful result with an empty value.

## 4. Domain Definitions

### 4.1 `state_metadata`

Proposed fields:

- `schema_version`;
- `state_version`;
- `created_at`;
- `updated_at`.

Deterministic persistence and state-control components write this domain.
Agents may read authorized metadata but do not write it directly. Each
committed protected-state change advances `state_version` so stale proposals
can be rejected.

### 4.2 `identity_references`

Proposed fields:

- `application_id`;
- `case_id`, when a separate case reference exists;
- `customer_token`.

`customer_token` must be opaque. Raw names, emails, addresses, identity
identifiers, and token-to-identity mappings must not appear in CreditState.
Token mappings belong in the separately protected PII Vault.

Deterministic PII-governance and authorized ingestion components create these
references. Ordinary agents have read-only access only when authorized.

### 4.3 `application_data`

Proposed structure:

```text
application_data
├── reported_values
├── sanitized_attributes
└── source_reference
```

`reported_values` preserves reported applicant information.
`sanitized_attributes` contains only data approved to enter the main
workflow. Verification must never overwrite reported values.

Deterministic ingestion and PII-governance components write this domain.
Agents do not directly mutate source application data.

Income, employment information, credit bureau information, and verified
financial evidence are Sensitive Credit Data. They may enter CreditState only
in structured, minimum-necessary, access-controlled form.

Derived DTI and other approved risk features may enter protected CreditState
under explicit ownership and minimum-context controls.

### 4.4 `validation_state`

Proposed fields:

- `status`;
- `findings`;
- `failure`, when validation fails;
- `validated_at`;
- `validator_version`.

Deterministic validation components exclusively write validation results.
Agents may read authorized results. Validation failure must be explicit and
safely routed.

### 4.5 `quantitative_model_state`

Proposed structure:

```text
quantitative_model_state
├── status
├── pd_score
├── risk_band
├── shap_risk_factors
├── model_version
├── model_timestamp
├── input_state_version
└── failure
```

Only approved quantitative components may write `pd_score`, `risk_band`,
`shap_risk_factors`, `model_version`, or `model_timestamp`. Agents and
LLMs must not generate, replace, or modify these outputs.
`input_state_version` identifies the committed state used for the model run.
Failure must not produce invented PD or SHAP output. This design does not
choose the model or any risk threshold.

### 4.6 `policy_state`

Proposed structure:

```text
policy_state
├── status
├── retrieved_evidence[]
│   ├── source_document
│   ├── section_or_chunk_reference
│   ├── policy_version
│   ├── retrieval_score
│   └── effective_date
├── findings[]
├── required_evidence[]
├── conflicts[]
├── evaluated_at
└── failure
```

Retrieved policy evidence remains separate from Policy Agent interpretation.
Findings must be grounded in retrieved synthetic policy and preserve citations.
The Policy Agent must not invent policy or thresholds. Retrieval failure must
not become policy approval. Record retrieval score and effective date where
available.

Approved retrieval capabilities write raw retrieval results. The Policy Agent
owns structured policy findings, required-evidence findings, and identified
conflicts. Deterministic controls validate protected updates before commit.

### 4.7 `verification_state`

Proposed structure:

```text
verification_state
├── requests[]
│   ├── request_id
│   ├── evidence_required
│   ├── requested_by
│   ├── requested_at
│   └── status
├── tool_results[]
│   ├── result_id
│   ├── request_id
│   ├── tool_name
│   ├── raw_evidence_reference
│   ├── status
│   ├── returned_at
│   └── failure
├── interpretations[]
│   ├── interpretation_id
│   ├── result_id
│   ├── structured_evidence
│   ├── proposed_state_update
│   └── created_at
├── verified_values
└── conflicts[]
```

The Orchestrator proposes creation of a verification request. Deterministic
workflow and state controls validate, create, and commit the protected request.
The Verification Agent may act only on an approved committed request.

Approved verification tools obtain and return raw verification evidence. The
Verification Agent may interpret and structure evidence and propose evidence or
state updates. It must not fabricate verified facts or bypass protected state
controls.

Deterministic workflow and state controls validate and commit protected
verification-state updates, including `verified_values`. Reported values
remain in `application_data.reported_values`. Failures and conflicts remain
explicit and traceable.

`raw_evidence_reference` points to the authorized stored tool result. Raw
identity PII must not be copied into CreditState.

### 4.8 `workflow_state`

Proposed structure:

```text
workflow_state
├── current_stage
├── proposed_next_action
├── mandatory_human_review
├── mandatory_review_reasons[]
├── investigation_iteration_count
├── tool_call_count
├── retry_count
├── active_request_ids[]
├── last_transition
│   ├── from_stage
│   ├── to_stage
│   ├── permitted
│   ├── reason
│   └── timestamp
└── failure
```

The Orchestrator owns `proposed_next_action`. The deterministic Workflow
Controller owns protected transitions, counters, permissions, loop limits,
retry limits, and mandatory-review enforcement. The Orchestrator proposes what
should happen next but does not enforce the transition.

Configured limits are enforced deterministically. Reaching a limit stops the
loop safely and routes according to configured rules. This design does not
choose workflow stages, numeric limits, or thresholds.

### 4.9 `recommendation_state`

Proposed structure:

```text
recommendation_state
├── recommendation
├── decision_rule
├── decision_reason
├── input_state_version
└── decided_at
```

The deterministic Decision Engine exclusively writes `recommendation`,
`decision_rule`, and `decision_reason`. No LLM-enabled agent may directly
produce or modify them. `input_state_version` identifies the committed
evidence used.

Recommendation values may include those defined in the architecture
specification. This design does not select synthetic thresholds. Mandatory
human-review conditions take precedence over an otherwise eligible automated
recommendation.

### 4.10 `explanation_state`

Proposed fields:

- `explanation`;
- `input_state_version`;
- `created_at`;
- `created_by`.

The Explanation Agent owns the analyst-facing explanation and remains read-only
relative to model outputs, policy findings, verification evidence, and
recommendations. An explanation must not alter or invent decision evidence.

### 4.11 `escalation_state`

Proposed structure:

```text
escalation_state
├── status
├── reasons[]
├── review_package_reference
├── requested_actions[]
├── action_results[]
├── human_review_outcome_reference
└── timestamps
```

The Escalation Agent may prepare the review package and request approved
actions. Controlled action tools record action results. Deterministic workflow
controls enforce escalation preconditions and transitions.

External actions must be permission controlled, auditable, sanitized, and
idempotent where appropriate. The Escalation Agent must not make the human
decision. This design does not choose the human-review interface.

### 4.12 `governance_audit_references`

Proposed fields:

- `workflow_event_references[]`;
- `agent_output_references[]`;
- `tool_call_references[]`;
- `model_run_references[]`;
- `policy_evidence_references[]`;
- `verification_evidence_references[]`;
- `decision_references[]`;
- `escalation_references[]`;
- `human_review_references[]`;
- `pii_audit_references[]`.

Every material decision-support step must remain traceable. PII-access auditing
remains separately identifiable from ordinary workflow auditing. Logs and
traces avoid unnecessary raw PII. References preserve relevant timestamps and
versions.

## 5. State Ownership Matrix

| State domain or field | Reads | Proposes or produces | Protected writer or commit authority |
| --- | --- | --- | --- |
| State metadata | Authorized components and agents | Deterministic state controls | Deterministic persistence and state-control components |
| Identity references | Authorized components and agents | PII Governance and authorized ingestion | Deterministic PII-governance and ingestion components |
| Reported application data | Authorized components and agents | Authorized ingestion | Deterministic ingestion and PII-governance components |
| Validation state | Authorized components and agents | Deterministic validation | Deterministic validation components |
| PD, risk band, SHAP, model metadata | Authorized components and agents | Approved quantitative components | Approved quantitative components |
| Raw policy retrieval evidence | Policy Agent and authorized components | Approved policy retrieval capability | Controlled policy-state update path |
| Structured policy findings | Authorized components and agents | Policy Agent | Policy Agent through deterministic validation and commit controls |
| Raw verification evidence | Verification Agent and authorized components | Approved verification tools | Stored through the controlled verification evidence path |
| Verification interpretation and proposed update | Authorized components | Verification Agent | Not a committed protected value until deterministic validation |
| Protected verification request | Verification Agent and authorized components | Orchestrator Agent proposes creation | Deterministic workflow and state controls validate, create, and commit |
| Committed verified values | Authorized components and agents | Verification Agent proposes from tool evidence | Deterministic workflow and state controls validate and commit |
| Proposed next workflow action | Workflow Controller and authorized components | Orchestrator Agent | Orchestrator-owned proposal field through controlled update |
| Workflow transitions and counters | Authorized components and agents | Workflow Controller | Workflow Controller |
| Recommendation, decision rule, decision reason | Authorized components and agents | Decision Engine | Decision Engine exclusively |
| Analyst-facing explanation | Authorized components and agents | Explanation Agent | Explanation Agent through controlled update |
| Escalation fields | Authorized components and agents | Escalation Agent and controlled action tools | Escalation Agent and controlled tools through deterministic controls |
| Audit references | Authorized audit and governance components | Material workflow participants | Controlled audit and persistence components |

Read access remains subject to authorization, least privilege, PII controls,
and minimum-context construction. A proposal does not grant commit authority.

## 6. Protected Update Protocol

Agents do not directly commit protected state updates.

A proposed update has this logical shape:

```text
StateUpdateProposal
├── proposal_id
├── target_domain
├── proposed_changes
├── basis_references[]
├── proposed_by
├── expected_state_version
└── proposed_at
```

The deterministic update path is:

1. An authorized agent or component reads permitted state.
2. It produces a structured action or `StateUpdateProposal`.
3. The Workflow Controller or applicable deterministic state control verifies
   the proposer, permissions, target ownership, evidence references, expected
   state version, transition validity, and configured limits.
4. The designated component owner writes protected fields.
5. Persistence commits the new state version.
6. The transition and outcome are recorded for audit.
7. Invalid or stale proposals are rejected explicitly and preserved as an
   auditable failure where material.

This does not transfer field ownership to the Workflow Controller. The
controller validates and enforces the update; the designated owner remains
responsible for the protected field.

## 7. Role-Specific Read Views

Do not pass complete CreditState to every agent. Construct role-specific views
from an allowlist and expose only authorized, minimum-necessary, sanitized
fields.

- Policy Agent: case evidence needed to retrieve and interpret synthetic policy.
- Orchestrator: authorized case, evidence, and workflow state needed to propose
  the next investigation step.
- Verification Agent: the required-evidence request and context needed to
  select approved verification tools and interpret results.
- Explanation Agent: read-only approved model, SHAP, policy, verification,
  recommendation, and workflow evidence needed for explanation.
- Escalation Agent: sanitized evidence needed to prepare a human-review package
  and request approved actions.

These views do not permit bypassing tool, PII, state, or workflow controls.

## 8. Recalculation After Evidence Changes

When verified evidence materially changes relevant inputs:

1. commit verified evidence separately from reported information;
2. recalculate affected deterministic features using explicitly defined logic;
3. rerun the quantitative model when relevant inputs materially change;
4. rerun policy evaluation when relevant evidence changes;
5. continue the bounded investigation workflow;
6. send eligible committed evidence to the deterministic Decision Engine.

Derived results identify the committed state version used so outdated outputs
can be detected.

This design does not decide whether a feature uses a reported or verified
value. That requires explicit deterministic feature logic while preserving the
approved Sensitive Credit Data classification and protected ownership.

## 9. Failure Representation

Each domain that can fail preserves:

- an explicit failure status;
- the failed component, tool, or operation;
- a sanitized reason;
- the timestamp;
- the relevant attempt or request reference;
- retry information where applicable;
- the safe routing outcome.

A failure must never be represented by fabricated evidence or a successful
empty result. Model failure, unresolved policy retrieval, verification failure,
invalid agent output, tool failure, unresolved ambiguity, and exhausted limits
route according to deterministic workflow rules and mandatory-review
conditions.

## 10. State Invariants

Every implementation must preserve these invariants:

1. Raw identity PII and token mappings do not enter CreditState.
2. Reported and verified evidence remain separate and traceable.
3. Agents propose actions or updates and do not bypass protected controls.
4. PD, risk band, SHAP factors, and model metadata are written only by approved
   quantitative components.
5. Recommendation fields are written only by the deterministic Decision Engine.
6. The Orchestrator proposes transitions; the Workflow Controller enforces
   them.
7. Verification tools return raw evidence; the Verification Agent interprets
   and proposes; deterministic controls validate and commit protected updates.
8. Policy findings remain grounded in retrieved synthetic policy.
9. Mandatory human review cannot be bypassed.
10. Failures, retries, tool calls, and transitions remain explicit and
    auditable.
11. Investigation and retry loops remain bounded.
12. Material records preserve relevant provenance and versions.
13. LLM context remains allowlisted, sanitized, and minimum necessary.
14. Human analysts retain authority wherever human review is required.

## 11. Decisions Not Made Here

This document proposes the CreditState logical schema for OQ-2. It does not
resolve:

- OQ-3: synthetic PD and workflow thresholds;
- OQ-4: verification providers;
- OQ-5: human-review interface;
- OQ-6: baseline or challenger model choice.

It also does not choose a physical storage technology, serialization format,
schema framework, or deployment design.

## 12. Approval Gate

The approved state design must continue to satisfy:

- confirm that each proposed domain and field is necessary for V1;
- confirm protected-field ownership and mutation paths;
- confirm the verification evidence structure and commit boundary;
- confirm that raw identity PII is excluded;
- confirm that reported and verified values remain separate;
- confirm that no other architecture open question was resolved implicitly;
- record explicit human approval.

Approved architecture is frozen. Explicitly unresolved choices remain deferred
until their relevant approved design phase.
