# CreditPilot — Workflow

## Status

Phase 0 — Proposed Workflow Definition

Pending human review.

## Authority

This document expands the canonical CreditPilot V1 workflow defined in
`docs/ARCHITECTURE_SPEC_V1.md`.

`docs/ARCHITECTURE_SPEC_V1.md` remains the architecture source of truth.
`docs/STATE_DESIGN.md` defines the proposed CreditState structure, and
`docs/TOOL_DESIGN.md` defines proposed tool boundaries. If this document
conflicts with any of them, the architecture specification takes precedence.

This document does not add agents, choose technologies, define thresholds,
select providers, classify sensitive credit attributes, or choose a
human-review interface or quantitative model.

## 1. Workflow Principles

The workflow must preserve these responsibility boundaries:

- deterministic software validates data, calculates explicit features,
  enforces permissions and state transitions, applies recommendation rules,
  and controls retries and loop limits;
- quantitative ML produces credit-risk predictions and SHAP attribution;
- LLM-enabled agents perform only approved adaptive reasoning, investigation,
  tool selection, policy interpretation, explanation, and escalation work;
- authorized tools perform bounded capabilities;
- deterministic workflow and state controls validate and commit protected
  CreditState updates;
- human analysts retain authority wherever human review is required.

CreditPilot is decision support. The workflow must not produce autonomous
real-world lending decisions.

## 2. Core Participants

### 2.1 Deterministic Components

- PII Governance Layer;
- application validation;
- feature calculation;
- Workflow Controller;
- quantitative model execution and SHAP computation;
- Decision Engine;
- persistence;
- audit logging;
- permission, retry, and loop-limit enforcement.

These are not LLM-enabled agents.

### 2.2 Approved Agents

CreditPilot V1 contains exactly five specialized agents:

1. Orchestrator Agent;
2. Policy Agent;
3. Verification Agent;
4. Explanation Agent;
5. Escalation Agent.

No additional agent may be introduced without an approved architecture change.

### 2.3 Human Analyst

The human analyst performs mandatory human review and retains authority where
human judgment is required. Agents may prepare and coordinate the handoff but
must not make the human decision.

## 3. End-to-End Flow

The canonical workflow is:

```text
Application
  ↓
PII classification, separation, and tokenization
  ↓
Deterministic validation and feature calculation
  ↓
Quantitative model and SHAP
  ↓
Policy retrieval and interpretation
  ↓
Orchestrator evaluates current case state
  ↓
┌──────────────── Evidence missing? ────────────────┐
│ Yes                                               │ No
↓                                                   ↓
Workflow Controller authorizes verification     Decision eligibility
  ↓                                                   ↓
Verification Agent selects HOW                  Deterministic Decision Engine
  ↓                                                   ↓
Approved verification tool                     Recommendation
  ↓                                                   ↓
Deterministic evidence commit                   Human review if required
  ↓                                                   ↓
Feature/model/policy recalculation              Explanation / escalation
  └──────────── bounded investigation loop ──────────┘
                         ↓
                  Audit preservation
```

The diagram is a summary only. The numbered steps below are authoritative
within this derived workflow document.

## 4. Canonical Workflow Steps

### Step 1 — Receive a Synthetic Application

The workflow receives a synthetic, mock, simulated, or suitable public demo
credit application.

Constraints:

- do not use real customer PII;
- do not use proprietary bank underwriting policy;
- establish an application reference for traceability.

### Step 2 — Classify and Separate Identity PII

The deterministic PII Governance Layer performs schema-based classification,
PII identification, identity separation, context sanitization, access-control
enforcement, and PII-access auditing.

LLMs must not be the primary PII detection or protection mechanism.

### Step 3 — Tokenize Identity

Create an opaque `customer_token` and store identity data and token mappings
in the protected PII Vault.

Only controlled references such as `application_id`, `case_id`, and
`customer_token` enter the main workflow. Agents must not directly access the
PII Vault.

### Step 4 — Validate the Application

Deterministic validation checks the application and records explicit validation
and data-quality state.

Validation failure must be preserved and routed safely. An agent must not
invent or repair missing values by assumption.

### Step 5 — Compute Deterministic Features

Approved deterministic components calculate DTI and other explicit features.

Feature calculation must preserve input provenance and keep reported and
verified values distinguishable. An LLM must not replace deterministic
calculation logic.

### Step 6 — Run the Quantitative Model

The approved quantitative model produces PD, risk score, risk band, and other
approved model outputs.

Only quantitative components may write protected model outputs. Model failure
must not produce invented PD.

### Step 7 — Generate SHAP Attribution

An approved quantitative component computes SHAP attribution from the model.

Agents may read authorized SHAP output but must not create, replace, or modify
it. SHAP failure must remain explicit.

### Step 8 — Retrieve and Interpret Synthetic Policy

The approved policy retrieval capability retrieves traceable synthetic policy
evidence. The Policy Agent interprets the retrieved evidence.

Retrieved policy and interpretation remain distinguishable. Preserve source,
section or chunk reference, policy version, retrieval score where available,
and effective date where applicable.

### Step 9 — Identify Required Evidence and Policy Constraints

The Policy Agent produces grounded policy findings, including required evidence
and identified conflicts.

The Policy Agent determines WHAT evidence is required. It must not invent
policy, thresholds, or final credit decisions. Retrieval failure must not
silently become policy approval.

### Step 10 — Orchestrator Evaluates Current State

The Orchestrator compares required evidence and policy constraints with the
authorized current CreditState.

It proposes the next workflow action. It does not enforce the transition,
perform verification, calculate risk, or make the final recommendation.

### Step 11 — Route Missing Evidence Through Controls

If required evidence is missing, the Orchestrator proposes verification.

The deterministic Workflow Controller decides whether the transition and tool
invocation are permitted. It validates permissions, state, preconditions,
retry limits, investigation limits, and mandatory-review conditions.

### Step 12 — Execute Approved Verification Tools

The Verification Agent determines HOW to obtain the required evidence and may
select only approved verification tools.

Approved tools obtain and return raw verification evidence. The Verification
Agent may interpret and structure that evidence and propose evidence or state
updates. It must not fabricate verified facts or bypass protected state
controls.

### Step 13 — Commit Verified Evidence Separately

Deterministic workflow and state controls validate proposed protected
verification-state updates before commit.

Reported applicant information remains in reported application data. Verified
evidence remains separately traceable and must not overwrite reported values.
Raw identity PII must not be copied into CreditState.

### Step 14 — Recalculate Affected Features

When committed verified evidence changes a relevant input, approved
deterministic components recalculate affected features using explicit feature
logic.

The workflow must not implicitly choose between reported and verified values.
The applicable value must be determined by approved deterministic feature
logic.

### Step 15 — Rerun the Quantitative Model When Required

Rerun the approved quantitative model when relevant committed inputs materially
change.

New outputs must identify the relevant model version, timestamp, and input state
version. Agents must not modify the rerun result.

### Step 16 — Rerun Policy Evaluation When Required

Rerun policy retrieval or Policy Agent evaluation when relevant committed
evidence changes.

Updated findings remain grounded, cited, versioned, and distinguishable from
retrieved policy evidence.

### Step 17 — Continue the Bounded Investigation Loop

The Orchestrator reevaluates the authorized current state and may propose
another investigation step.

The Workflow Controller deterministically enforces:

- maximum investigation iterations;
- maximum tool calls;
- maximum retry count;
- timeout handling;
- permitted transitions;
- mandatory-review conditions.

Uncontrolled recursive agent execution is prohibited. When limits are reached,
the workflow stops safely and routes according to configured rules.

### Step 18 — Pass Eligible Evidence to the Decision Engine

When deterministic workflow controls determine that the case is eligible,
provide the committed approved model, policy, verification, validation, and
workflow evidence to the deterministic Decision Engine.

Only committed, authorized evidence may be used.

### Step 19 — Produce a Structured Recommendation

The deterministic Decision Engine applies explicit recommendation logic.

It exclusively writes:

- `recommendation`;
- `decision_rule`;
- `decision_reason`.

No LLM-enabled agent may directly produce or modify these protected fields.
Credit-risk prediction and recommendation remain separate responsibilities.

### Step 20 — Route Mandatory-Review Cases

Mandatory human-review conditions take precedence over an otherwise eligible
automated recommendation.

Triggers may include those defined by the architecture specification, such as
unresolved policy conflict, critical missing evidence, verification failure,
model failure, unresolved ambiguity, exhausted investigation limits, configured
high-risk conditions, or explicit mandatory-review rules.

No agent may bypass mandatory human review.

### Step 21 — Generate Analyst-Facing Explanation

The Explanation Agent converts existing approved model, SHAP, policy,
verification, workflow, and recommendation evidence into a clear explanation.

The Explanation Agent is read-only relative to decision evidence. It must not
alter or invent model outputs, policy findings, verification facts, or
recommendations.

When human review is required, the Escalation Agent may prepare a sanitized
review package and request approved external actions. It must not make the human
decision.

### Step 22 — Preserve Audit Evidence

Preserve traceable references for material workflow activity, including:

- application or case reference;
- model version, timestamp, PD, and approved outputs;
- SHAP attribution;
- retrieved policy evidence and policy version;
- agent outputs;
- tool calls and outcomes;
- workflow transitions;
- verification evidence;
- Decision Engine rule and recommendation;
- escalation reason and external action outcomes;
- human-review outcome where captured;
- relevant timestamps.

PII-access auditing remains separately identifiable. Logs, traces, review
packages, and notifications must avoid unnecessary raw PII.

## 5. Verification Subflow

The verification chain must remain:

```text
Policy Agent
  WHAT evidence is required
        ↓
Orchestrator Agent
  WHETHER verification is needed now
        ↓
Workflow Controller
  WHETHER the transition and tool call are permitted
        ↓
Verification Agent
  HOW the evidence is obtained
        ↓
Approved verification tool
  obtains and returns raw evidence
        ↓
Verification Agent
  interprets, structures, and proposes an update
        ↓
Deterministic workflow/state controls
  validate and commit protected verification state
        ↓
CreditState
  reported and verified values remain separate
```

No single agent owns the full verification decision chain.

## 6. Decision and Human-Review Subflow

```text
Committed eligible evidence
        ↓
Deterministic Decision Engine
        ↓
recommendation + decision_rule + decision_reason
        ↓
Mandatory-review check
   ┌────┴────┐
   │         │
Review     No mandatory review
   ↓         ↓
Escalation  Explanation
package
   ↓
Approved action tools
   ↓
Human analyst
```

The Decision Engine produces a decision-support recommendation. A human analyst
retains authority wherever human review is required.

External actions such as creating a review case or sending a notification must
use approved tools and satisfy deterministic preconditions, permissions,
sanitization, audit, and idempotency controls where appropriate.

## 7. Failure Routing

Failures must be explicit and must not be silently converted into success.

| Failure | Required handling |
| --- | --- |
| Validation failure | Preserve failure state and route safely. |
| Model failure | Do not invent PD or SHAP; route to safe review or escalation. |
| Policy retrieval failure | Record failure, retry only within limits, and route unresolved cases to human review. |
| Verification failure | Preserve the failure and reported data separately; do not fabricate verified evidence. |
| Tool failure | Record structured failure, apply bounded retry, and use safe fallback routing. |
| Invalid agent output | Reject it, preserve the error, retry only within limits, and route safely. |
| Loop or retry limit reached | Stop safely and route according to configured rules. |

The architecture specification determines when human review is mandatory.
This document does not add thresholds or new routing conditions.

## 8. State-Update Rules

For every protected update:

1. read only authorized, sanitized state;
2. produce a structured action or update proposal;
3. validate caller, permission, evidence basis, current state version,
   transition, and configured limits deterministically;
4. let the designated owner write protected fields;
5. commit the state change through controlled persistence;
6. record the transition and outcome for audit.

The Workflow Controller validates and enforces state transitions. It does not
replace the Orchestrator's reasoning or take ownership of every protected
field.

## 9. Minimum-Context Rules

Construct agent context with an allowlist. Remove unnecessary PII, apply
deterministic redaction, and provide only the minimum information required for
the current role and step.

Do not pass complete CreditState to every agent. Do not expose raw identity PII,
PII Vault mappings, unrestricted databases, arbitrary APIs, secrets, or
unnecessary raw tool payloads.

## 10. Workflow Invariants

1. CreditPilot remains decision support, not autonomous lending.
2. Raw identity PII remains outside the main AI workflow.
3. Validation and explicit calculations remain deterministic.
4. Only quantitative components produce PD and SHAP.
5. The Policy Agent determines WHAT evidence is required.
6. The Orchestrator determines WHETHER verification is needed.
7. The Verification Agent determines HOW to obtain evidence.
8. Tools obtain facts; agents may interpret and propose; deterministic controls
   protect state.
9. Reported and verified evidence remain separate.
10. The Orchestrator proposes transitions; the Workflow Controller enforces
    them.
11. Only the Decision Engine writes recommendation fields.
12. Mandatory human review cannot be bypassed.
13. Investigation loops and retries remain bounded.
14. Failures remain explicit and safely routed.
15. Material workflow activity remains traceable.

## 11. Decisions Not Made Here

This workflow does not resolve:

- classification of sensitive credit attributes;
- physical implementation technology for CreditState;
- synthetic PD or workflow thresholds;
- verification providers;
- human-review interface;
- baseline or challenger model choice;
- numeric retry, loop, tool-call, or timeout limits;
- concrete workflow-stage enum values.

These decisions require their own approved design process.

## 12. Review Gate

Before this workflow definition is treated as frozen:

- confirm that all 22 canonical architecture steps are represented;
- confirm deterministic, ML, agent, tool, and human responsibilities;
- confirm verification ownership and protected-state commit boundaries;
- confirm failure and mandatory-review routing;
- confirm PII and minimum-context controls;
- confirm bounded loops and audit requirements;
- confirm that no open architecture question was resolved implicitly;
- record human approval.
