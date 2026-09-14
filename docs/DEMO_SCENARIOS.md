# CreditPilot — Demo Scenarios

## Status

Phase 0 — Proposed Demo Scenario Definition

Pending human review.

## Authority

This document expands the three Golden Demo scenarios required by
`docs/ARCHITECTURE_SPEC_V1.md`. The architecture specification remains
authoritative.

All demo data and policies are synthetic. Values illustrate workflow behaviour
and must not be represented as real underwriting policy or lending thresholds.

## 1. Demo Objectives

Together, the scenarios demonstrate:

- a short path without unnecessary investigation;
- adaptive verification and evidence-driven rerouting;
- safe handling of conflict and uncertainty;
- deterministic model and recommendation boundaries;
- grounded synthetic policy reasoning;
- protected CreditState updates;
- mandatory human review;
- analyst-facing explanation and controlled escalation;
- end-to-end auditability.

## 2. Common Demo Rules

Every scenario must:

- use synthetic, mock, simulated, or suitable public demo data;
- keep raw identity PII outside the main workflow;
- use opaque controlled identity references;
- preserve model, policy, tool, workflow, and state versions;
- keep reported and verified values separate;
- use only approved agents and tools;
- enforce deterministic transitions and limits;
- preserve explicit failures and audit evidence.

No scenario authorizes a real lending decision.

## 3. Scenario 1 — Straightforward Low-Risk Case

### Scenario 1 Contract

| Required item | Expected definition |
| --- | --- |
| Starting data | A valid synthetic application with sufficient policy-required evidence and no configured mandatory-review condition. Exact values remain pending approval. |
| Expected model state | Successful approved quantitative model run with traceable PD, risk band where applicable, SHAP, model version, timestamp, and input state version. |
| Expected policy behaviour | Grounded synthetic policy finding with citations and no missing required evidence. |
| Expected agent actions | Policy Agent interprets policy; Orchestrator proposes the eligible next step; Explanation Agent explains the result. |
| Expected tool calls | Approved data, deterministic calculation, model, SHAP, and policy retrieval capabilities only; no verification or escalation action call unless an explicit failure changes the path. |
| Expected workflow path | The short path documented below, with deterministic transition approval. |
| Expected final state | A Decision Engine recommendation with explanation and audit evidence; no mandatory human review when no review condition exists. The exact recommendation is not selected here. |
| Must not occur | Unnecessary verification, invented policy or thresholds, agent-written model or recommendation fields, uncontrolled loops, or unnecessary PII exposure. |

### Purpose

Demonstrate the shortest valid path when the application is valid, required
evidence is already sufficient, and no mandatory-review condition is present.

### Expected Path

```text
Application
→ PII governance and tokenization
→ Deterministic validation
→ Deterministic features
→ Quantitative model
→ SHAP
→ Synthetic policy retrieval and interpretation
→ Orchestrator state evaluation
→ Deterministic Decision Engine
→ Explanation Agent
→ Audit preservation
```

### Expected Behaviour

- validation succeeds;
- deterministic features are calculated;
- the quantitative model produces traceable outputs;
- SHAP is produced from the model;
- policy findings are grounded and cited;
- the Policy Agent identifies no missing required evidence;
- the Orchestrator does not propose unnecessary verification;
- the Workflow Controller permits the eligible transition;
- the Decision Engine writes the structured recommendation;
- no LLM writes quantitative or recommendation fields;
- the Explanation Agent explains only existing evidence.

### Evidence to Display

- sanitized application summary;
- deterministic feature results;
- model output and version;
- SHAP risk factors;
- policy sources and findings;
- workflow transitions;
- Decision Engine rule and recommendation;
- analyst-facing explanation;
- audit references.

### Prohibited Behaviour

- unnecessary tool calls or investigation loops;
- invented thresholds or policy;
- autonomous lending language;
- unnecessary raw PII exposure.

The exact synthetic inputs and decision thresholds require separate approval.

## 4. Scenario 2 — Verification Changes the Risk Assessment

### Scenario 2 Contract

| Required item | Expected definition |
| --- | --- |
| Starting data | Synthetic application with `reported_income = 150000` and missing verified income. |
| Expected model state | An initial traceable model result followed by deterministic feature recalculation and a new model result after committed `verified_income = 98000`. |
| Expected policy behaviour | Policy Agent grounds the requirement for verified income, then reruns evaluation when the relevant committed evidence changes. |
| Expected agent actions | Orchestrator proposes verification; Verification Agent selects an approved method and interprets tool evidence; Explanation and Escalation Agents prepare their approved outputs after the recommendation. |
| Expected tool calls | `verify_income()` plus approved data, calculation, model, SHAP, policy, and controlled escalation tools required by the path. |
| Expected workflow path | Verification-request creation, deterministic commit, evidence acquisition, state update, recalculation, model rerun, policy rerun, eligibility check, Decision Engine, mandatory-review enforcement, and controlled escalation. |
| Expected final state | Reported and verified incomes remain separate; the architecture-defined synthetic outcome is `MANUAL_REVIEW`; human review remains required. |
| Must not occur | Overwriting reported income, fabricated verification, direct agent commit, skipped required reruns, agent-written recommendation, or bypassed human review. |

### Purpose

Demonstrate that external verification can materially change inputs, trigger
deterministic recalculation, and reroute the case safely.

### Synthetic Example

```text
reported_income = 150000
verified_income = 98000
```

These values are demonstration data, not policy thresholds.

### Expected Path

```text
Application reports income = 150000
→ PII governance, validation, and features
→ Quantitative model and SHAP
→ Policy requires verified income
→ Orchestrator identifies missing evidence and proposes request creation
→ deterministic controls validate, create, and commit the verification request
→ Verification Agent selects HOW to execute the approved request
→ approved verify_income() tool
→ raw verification evidence returned
→ Verification Agent interprets and proposes update
→ deterministic controls commit verified_income = 98000
→ affected deterministic features recalculated
→ quantitative model rerun
→ policy evaluation rerun
→ bounded investigation continues
→ deterministic Decision Engine
→ MANUAL_REVIEW
→ Explanation Agent / Escalation Agent
→ Human review
→ Audit preservation
```

### Ownership Checks

- Policy Agent determines WHAT evidence is required;
- Orchestrator determines WHETHER verification is needed and proposes request
  creation;
- deterministic controls validate, create, and commit the protected request;
- Verification Agent determines HOW the approved request is executed;
- the tool returns raw evidence;
- deterministic controls commit protected verification state;
- the Decision Engine writes the recommendation;
- the human analyst performs required review.

### State Checks

- `reported_income` remains unchanged and traceable;
- `verified_income` is stored separately;
- raw evidence and interpretation remain distinguishable;
- recalculated features identify their inputs;
- rerun model and policy outputs identify the relevant state version;
- prior evidence remains auditable.

### Expected Outcome

The architecture's Golden Demo outcome is `MANUAL_REVIEW`. This is a
synthetic workflow outcome, not a real lending decision.

### Prohibited Behaviour

- overwriting reported income;
- the Verification Agent inventing or directly committing verified income;
- an LLM recalculating deterministic features or modifying model output;
- skipping required model or policy reevaluation;
- bypassing human review.

## 5. Scenario 3 — Policy or Evidence Conflict

### Scenario 3 Contract

| Required item | Expected definition |
| --- | --- |
| Starting data | A synthetic application whose retrieved policy evidence or case evidence contains a material conflict or remains unresolved. Exact values remain pending approval. |
| Expected model state | Approved traceable quantitative result where model execution succeeds; explicit model failure state if the injected path tests model failure. |
| Expected policy behaviour | Policy sources and interpretations remain separate; conflicts and missing evidence remain explicit; retrieval failure never becomes approval. |
| Expected agent actions | Policy Agent records the conflict; Orchestrator proposes bounded investigation; Verification Agent acts only if approved evidence acquisition is required; Escalation Agent prepares controlled handoff. |
| Expected tool calls | Only tools permitted by the chosen conflict path, with bounded retries; controlled review-case or notification actions after deterministic approval. |
| Expected workflow path | Bounded investigation followed by safe routing when the conflict remains unresolved. |
| Expected final state | `MANUAL_REVIEW`, preserved unresolved conflict, sanitized escalation evidence, and human-controlled review. |
| Must not occur | Silent conflict resolution, invented evidence or policy, unlimited retries, arbitrary external action, agent-written recommendation, or unnecessary PII disclosure. |

### Purpose

Demonstrate safe handling when policy evidence or case evidence remains
conflicting or unresolved after bounded investigation.

### Expected Path

```text
Application
→ PII governance and validation
→ Quantitative model and SHAP
→ Synthetic policy retrieval
→ conflicting or unresolved evidence
→ Policy Agent records conflict
→ Orchestrator proposes bounded investigation
→ Workflow Controller permits only valid actions
→ approved tools used where applicable
→ conflict remains unresolved
→ investigation limit or review rule reached
→ deterministic Decision Engine / workflow rule
→ MANUAL_REVIEW
→ Escalation Agent
→ controlled review-case action
→ Human review
→ Audit preservation
```

### Expected Behaviour

- retrieved policy remains separate from interpretation;
- policy sources, versions, and conflicts remain traceable;
- missing evidence is not invented;
- tool and verification failures remain explicit;
- retries and investigation steps remain within configured limits;
- unresolved conflict does not silently become approval;
- mandatory review cannot be bypassed;
- the Escalation Agent prepares but does not decide the case.

### Human-Review Package

The sanitized package should include:

- application or case reference;
- sanitized application summary;
- model output and model version;
- SHAP risk factors;
- applicable policy findings and citations;
- verification evidence;
- unresolved conflicts;
- deterministic recommendation;
- escalation reason;
- relevant audit references.

Identity data is accessed separately through authorized PII controls only when
genuinely required.

### Prohibited Behaviour

- selecting one conflicting source without a governed basis;
- inventing policy or verified evidence;
- unlimited retries or recursive agent execution;
- arbitrary external actions;
- unnecessary raw PII in notifications or review packages.

## 6. Demo Observability

For every scenario, present a trace that answers:

- what evidence entered the workflow;
- which component, agent, or tool acted;
- what was proposed;
- what deterministic controls permitted or rejected;
- which protected owner wrote each result;
- which versions and timestamps apply;
- why the recommendation or escalation occurred;
- whether human review was required;
- what failures or conflicts remained.

PII-access events must remain separately identifiable from ordinary workflow
events.

## 7. Demo Acceptance Conditions

A scenario passes only when:

- its expected path completes or fails safely;
- role and ownership boundaries remain intact;
- policy and verification evidence are grounded;
- reported and verified data remain separate;
- protected fields are written only by their owners;
- mandatory review and limits are enforced;
- explanation matches existing evidence;
- material activity remains auditable.

Any fabricated evidence, unauthorized mutation, unbounded loop, PII-boundary
violation, or agent-written recommendation fails the demo.

## 8. Decisions Not Made Here

This document does not select:

- final synthetic application records;
- policy or model thresholds;
- verification provider;
- quantitative model;
- retry or loop counts;
- human-review interface.

Those choices require separate approval.
