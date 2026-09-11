# CreditPilot — Architecture Specification V1

## Status

Phase 0 — Architecture Definition

## Architecture Authority

This document is the canonical architecture source of truth for CreditPilot.

If implementation, derived documentation, prompts, agent behaviour,
or coding-agent output conflicts with this specification,
this specification takes precedence.

Material architectural changes require explicit human approval.

## 1. Project Definition

### Project Name

CreditPilot — Agentic AI Credit Risk Decision Support System

### Purpose

CreditPilot demonstrates how agentic AI can assist a Credit Risk Analyst
or Underwriter by combining:

- quantitative credit-risk modelling;
- explainable AI;
- policy retrieval and reasoning;
- adaptive investigation workflows;
- external evidence verification;
- human-in-the-loop review;
- controlled enterprise actions;
- auditability;
- AI and data governance.

CreditPilot is a decision-support system.

It is not an autonomous real-world lending system.

### Primary User

The primary user is a Credit Risk Analyst or Underwriter.

CreditPilot assists the analyst with:

- investigating credit applications;
- identifying missing or conflicting information;
- retrieving relevant synthetic credit policy;
- obtaining verification evidence;
- generating structured recommendations;
- explaining model, policy, and verification evidence;
- escalating unresolved cases for human review.

### Data Scope
CreditPilot V1 uses synthetic, mock, simulated, or suitable public demo data only.

It does not use real customer PII or proprietary bank underwriting policies.

## 2. Data Privacy and PII Architecture

### 2.1 Core Principle

Raw identity PII must be separated from the main AI and agent workflow.

Agents and LLMs should operate primarily on:

- application_id;
- opaque customer_token;
- non-PII application attributes;
- sanitized evidence;
- model outputs;
- policy findings;
- workflow state.

Raw identity PII must not be unnecessarily exposed to agents or LLMs.

### 2.2 PII Governance Layer

All incoming application data must pass through a deterministic PII Governance Layer before entering the main CreditPilot AI workflow.

The PII Governance Layer is responsible for:

- schema-based PII classification;
- deterministic PII identification;
- tokenization;
- identity separation;
- context sanitization;
- access-control enforcement;
- PII access auditing.

PII handling must not depend primarily on an LLM.

### 2.3 Identity Tokenization

Customer identity must be represented inside the AI workflow using an opaque customer_token.

For example:

Raw identity data may contain:

- name;
- email;
- address;
- synthetic identity identifiers.

The main workflow instead uses:

customer_token = opaque identifier

The customer_token must not itself contain meaningful identity information.

### 2.4 PII Vault

Identity information and token-to-identity mappings must be stored separately from the main CreditState in a protected PII Vault.

Agents must not directly access the PII Vault.

PII Vault access must:

- use explicitly authorized capabilities;
- follow least-privilege access;
- be independently audited;
- be unavailable to ordinary agent reasoning.

### 2.5 LLM Security Boundary

Before any context is sent to an LLM:

1. context must be constructed using an allowlist;
2. unnecessary PII must be removed;
3. deterministic PII redaction must be applied;
4. only the minimum necessary information may be provided.

The LLM must not be treated as the primary PII detection or protection mechanism.

### 2.6 Notification Boundary

Slack, email, or other external notifications must not contain unnecessary raw PII.

Notifications should normally reference controlled identifiers such as:

- application_id;
- case_id;
- customer_token.

Authorized users may retrieve identity information separately through controlled systems when required.

### 2.7 PII Auditability

PII access must be auditable separately from normal model, agent, and workflow activity.

PII access audit events should record:

- actor;
- timestamp;
- purpose;
- resource accessed;
- access outcome;
- related application or case reference.

## 3. Fundamental Architecture Principle

CreditPilot separates responsibilities across deterministic software,
quantitative machine learning, LLM-enabled agents, and human decision-making.

### 3.1 Deterministic Software

Use deterministic software when explicit rules or calculations are sufficient.

Deterministic components are responsible for:

- application validation;
- deterministic feature calculations;
- explicit policy gates;
- workflow safety rules;
- state-transition enforcement;
- decision rules;
- permission enforcement;
- retry limits;
- investigation loop limits.

### 3.2 Quantitative Machine Learning

Quantitative ML is responsible for credit-risk prediction.

This includes:

- Probability of Default (PD) prediction;
- risk scoring;
- model calibration;
- quantitative feature attribution using SHAP.

LLMs and agents must never generate, replace, or modify quantitative model outputs.

### 3.3 LLM-Enabled Agents

Agents are used only where adaptive reasoning or workflow adaptation is required.

Agents may perform activities such as:

- identifying unresolved evidence;
- planning investigation steps;
- selecting authorized tools;
- retrieving and interpreting policy;
- requesting verification;
- synthesizing evidence;
- generating explanations;
- preparing escalation.

Agents must not replace deterministic logic or quantitative models when those mechanisms are sufficient.

### 3.4 Human Authority

CreditPilot is a decision-support system.

Human review remains mandatory when required by policy, workflow rules,
model failure, unresolved ambiguity, verification failure, or other
configured review conditions.

Agents must not bypass mandatory human review.

### 3.5 Guiding Principle

Use deterministic software when explicit logic is sufficient.

Use quantitative ML for credit-risk prediction.

Use LLM-enabled agents only where adaptive reasoning, investigation,
tool selection, evidence gathering, or workflow adaptation is required.

Use human review where final authority or unresolved risk requires
human judgment.

## 4. Approved Agent Architecture

CreditPilot V1 contains exactly five specialized LLM-enabled agents:

1. Orchestrator Agent
2. Policy Agent
3. Verification Agent
4. Explanation Agent
5. Escalation Agent

Additional agents must not be introduced without an explicit architecture
change proposal and human approval.

### 4.1 Orchestrator Agent

Purpose:

Determine the next investigation step based on the current case state.

The Orchestrator Agent coordinates the investigation workflow but does not
calculate credit risk or make final lending decisions.

### 4.2 Policy Agent

Purpose:

Determine which synthetic credit policies are applicable to the current
case evidence.

The Policy Agent retrieves and interprets policy but must not invent policy,
thresholds, or final credit decisions.

### 4.3 Verification Agent

Purpose:

Gather approved external evidence when information is missing,
inconsistent, or insufficient.

Reported applicant information and verified information must remain separate.

### 4.4 Explanation Agent

Purpose:

Convert existing model, SHAP, policy, verification, and decision evidence
into a clear analyst-facing explanation.

The Explanation Agent is read-only relative to decision evidence and must
not modify model outputs, policy findings, or recommendations.

### 4.5 Escalation Agent

Purpose:

Prepare and execute a controlled handoff to a human analyst when human
review is required.

External actions such as creating a review case or sending notifications
must follow explicit preconditions, permissions, audit requirements,
and idempotency controls.

### 4.6 Non-Agent Components

The following are explicitly NOT LLM-enabled agents:

- application validation;
- PII classification and tokenization;
- feature engineering;
- DTI and other deterministic calculations;
- credit-risk model;
- SHAP computation;
- workflow state enforcement;
- deterministic Decision Engine;
- persistence;
- audit logging;
- permission enforcement;
- retry and loop-limit enforcement.

These components must not be converted into agents unless an approved
architecture change is made.

## 5. Verification Responsibility Boundary

Verification responsibility is deliberately separated across the Policy Agent,
Orchestrator Agent, and Verification Agent.

### 5.1 Policy Agent — WHAT Evidence Is Required

The Policy Agent determines what evidence is required based on applicable
synthetic policy.

For example:

> The applicable policy requires verified income.

The Policy Agent may identify required evidence but does not perform
external verification.

### 5.2 Orchestrator Agent — WHETHER Verification Is Needed Now

The Orchestrator Agent compares required evidence with the current case state.

It determines whether the workflow should proceed to verification.

For example:

- required evidence: verified_income;
- current evidence: verified_income is missing;
- next workflow action: verification.

The Orchestrator does not itself perform the verification.

### 5.3 Verification Agent — HOW Evidence Is Obtained

The Verification Agent determines how to obtain the requested evidence
using only approved verification tools.

Examples of approved verification capabilities may include:

- verify_income();
- verify_employment();
- get_credit_report().

The Verification Agent must not invent missing evidence.

Reported applicant information must not be overwritten by verified evidence.
Both must remain separately traceable.

### 5.4 Responsibility Principle

The responsibility boundary is:

Policy Agent → WHAT evidence is required.

Orchestrator Agent → WHETHER the current workflow requires verification.

Verification Agent → HOW the required evidence is obtained.

Deterministic workflow controls enforce whether the requested transition
and tool invocation are permitted.

No single agent owns the entire verification decision chain.

## 6. Workflow Controller and CreditState

CreditPilot uses a shared CreditState to represent the current state of a credit case.

The CreditState is protected by deterministic workflow controls.

Agents may reason about the current state and propose permitted updates,
but they must not have unrestricted authority to mutate protected state.

### 6.1 Workflow Controller

The Workflow Controller is a deterministic, non-agent component.

It is responsible for:

- enforcing valid state transitions;
- validating requested workflow actions;
- enforcing agent and tool permissions;
- enforcing retry limits;
- enforcing investigation loop limits;
- enforcing mandatory human-review conditions;
- preventing unauthorized state mutation;
- coordinating auditable state transitions.

The Workflow Controller does not perform credit-risk reasoning and does not
replace the Orchestrator Agent.

The Orchestrator determines what should happen next.

The Workflow Controller determines whether that transition is permitted.

### 6.2 CreditState Domains

The conceptual CreditState contains the following domains:

- identity references;
- application data;
- validation state;
- quantitative model state;
- policy state;
- verification state;
- workflow state;
- recommendation state;
- explanation state;
- escalation state;
- governance and audit references.

Raw identity PII must not be stored directly in the main CreditState.

Identity must normally be represented using controlled references such as:

- application_id;
- customer_token.

### 6.3 State Ownership Principle

Every protected state field must have an explicit owner.

Agents and components may read fields when authorized,
but only the designated owner may write protected fields.

Examples:

- quantitative model components own PD and model outputs;
- Policy Agent owns policy findings;
- Verification Agent and approved verification tools own verification evidence;
- Orchestrator Agent owns proposed next workflow action;
- Decision Engine exclusively owns recommendation fields;
- Explanation Agent owns analyst-facing explanation;
- Escalation Agent and controlled action tools own escalation fields;
- Workflow Controller owns protected workflow transitions and counters.

### 6.4 Quantitative State Protection

LLM-enabled agents may read authorized quantitative model outputs but must not
directly write or modify:

- pd_score;
- risk_band;
- SHAP risk factors;
- model_version;
- model_timestamp.

Only approved quantitative components may write these fields.

### 6.5 Recommendation State Protection

The deterministic Decision Engine exclusively writes:

- recommendation;
- decision_rule;
- decision_reason.

No LLM-enabled agent may directly modify these fields.

### 6.6 Reported and Verified Data Separation

Reported applicant data must remain separate from externally verified evidence.

For example:

reported_income = 150000

verified_income = 98000

Verification must not overwrite the original reported value.

Any downstream recalculation must use explicitly defined feature logic
to determine which evidence is applicable.

### 6.7 Core Control Principle

Agents propose actions.

Authorized tools perform bounded capabilities.

Component owners write their protected state.

The Workflow Controller enforces valid transitions.

The Decision Engine owns deterministic recommendation logic.

Human analysts retain authority where human review is required.

## 7. Deterministic Decision Engine

The Decision Engine is a deterministic, non-agent component.

It produces a structured decision-support recommendation using approved
model signals, policy findings, verification evidence, data-quality state,
and explicit decision rules.

The Decision Engine must not use unrestricted LLM reasoning to determine
the final recommendation.

### 7.1 Decision Inputs

Conceptual inputs may include:

- Probability of Default (PD);
- risk band;
- quantitative risk factors;
- policy findings;
- policy conflicts;
- required evidence status;
- verification results;
- validation and data-quality status;
- mandatory human-review conditions;
- explicit synthetic decision rules.

### 7.2 Decision Outputs

The Decision Engine exclusively writes:

- recommendation;
- decision_rule;
- decision_reason.

Possible V1 decision-support recommendations include:

- APPROVAL_RECOMMENDATION;
- MANUAL_REVIEW;
- REQUEST_MORE_INFORMATION;
- HIGH_RISK_REVIEW.

These are synthetic portfolio workflow states.

They do not represent autonomous real-world lending decisions.

### 7.3 Decision Authority

The quantitative model predicts credit risk.

The Policy Agent interprets applicable synthetic policy.

The Verification Agent gathers approved evidence.

The Orchestrator coordinates investigation.

The Decision Engine applies explicit deterministic recommendation logic.

No LLM-enabled agent may directly produce or modify the protected
recommendation fields.

### 7.4 Mandatory Review Overrides

Mandatory human-review conditions take precedence over an otherwise
eligible automated recommendation.

Examples may include:

- unresolved policy conflict;
- critical missing evidence;
- verification failure;
- model failure;
- unresolved ambiguity;
- investigation limits exhausted;
- configured high-risk workflow conditions;
- explicit mandatory-review rules.

The system must not allow an agent to bypass these conditions.

### 7.5 Synthetic Thresholds

Any risk thresholds used in CreditPilot must be clearly identified as
synthetic demonstration thresholds.

No threshold may be represented as a real bank underwriting rule.

Thresholds must be configurable rather than silently embedded in
LLM prompts.

### 7.6 Core Decision Principle

Credit risk prediction and credit recommendation are separate responsibilities.

The ML model predicts risk.

The Decision Engine applies controlled recommendation logic.

Agents provide reasoning, investigation, policy interpretation,
verification, explanation, and escalation support.

Human analysts retain final authority wherever human review is required.

## 8. Human-in-the-Loop and Escalation

CreditPilot uses human-in-the-loop controls for cases that require
human judgment, mandatory review, or controlled escalation.

Human review is a protected workflow state and must not be bypassed
by an LLM-enabled agent.

### 8.1 Human Review Triggers

Human review may be required when:

- policy explicitly requires human review;
- critical evidence remains unresolved;
- verification fails or produces conflicting evidence;
- model execution fails;
- policy retrieval or interpretation remains unresolved;
- investigation limits are reached;
- workflow safety controls require escalation;
- the deterministic Decision Engine produces MANUAL_REVIEW;
- another configured mandatory-review condition is triggered.

### 8.2 Escalation Agent Responsibility

The Escalation Agent prepares a structured handoff to an authorized
human analyst.

It may:

- summarize the case;
- summarize model evidence;
- summarize policy findings;
- summarize verification evidence;
- identify unresolved issues;
- explain why human review is required;
- prepare an escalation package;
- request approved external actions through authorized tools.

The Escalation Agent must not make the human decision.

### 8.3 Human Review Package

A human-review package should contain sufficient decision evidence
without unnecessarily exposing raw PII.

Conceptual contents include:

- application or case reference;
- sanitized application summary;
- model output and model version;
- SHAP risk factors;
- applicable policy findings;
- verification evidence;
- unresolved conflicts;
- deterministic recommendation;
- reason for escalation;
- relevant audit references.

Identity information must be accessed separately through authorized
PII controls when genuinely required.

### 8.4 External Escalation Actions

External actions must occur only through approved tools.

Examples may include:

- create_review_case();
- send_notification().

External actions must be:

- permission controlled;
- auditable;
- idempotent where appropriate;
- sanitized for unnecessary PII;
- subject to deterministic preconditions.

An agent must not directly call arbitrary external systems.

### 8.5 Human Decision Authority

When a case enters mandatory human review, an authorized human analyst
retains decision authority.

The system may provide:

- quantitative risk evidence;
- policy evidence;
- verification evidence;
- explanations;
- structured recommendations.

These outputs support human judgment but do not replace it.

### 8.6 Auditability

Human-review and escalation activity must be auditable.

The system should preserve:

- why escalation occurred;
- which evidence was available;
- which recommendation was produced;
- which external actions were requested;
- action outcomes;
- relevant timestamps;
- human-review outcome where captured;
- relevant model, policy, and workflow versions.

### 8.7 Core Human-in-the-Loop Principle

Agents may prepare and coordinate escalation.

Authorized tools may perform controlled external actions.

The Workflow Controller enforces valid escalation transitions.

The human analyst performs the human review.

Mandatory human review cannot be bypassed by an agent.

## 9. End-to-End Workflow

The canonical CreditPilot V1 workflow is:

1. Receive a synthetic credit application.
2. Classify and separate identity PII.
3. Tokenize identity and store protected identity mappings separately.
4. Validate the application using deterministic validation logic.
5. Compute deterministic features.
6. Run the quantitative credit-risk model.
7. Generate quantitative model explanation using SHAP.
8. Retrieve and interpret applicable synthetic policy.
9. Identify required evidence and policy constraints.
10. Let the Orchestrator evaluate the current case state.
11. If evidence is missing, route through deterministic workflow controls
    to the Verification Agent.
12. Execute approved verification tools.
13. Store verified evidence separately from reported applicant information.
14. Recalculate affected deterministic features where required.
15. Rerun the quantitative model when relevant inputs materially change.
16. Rerun policy evaluation when relevant evidence changes.
17. Continue the investigation loop within configured limits.
18. Pass eligible case evidence to the deterministic Decision Engine.
19. Produce a structured recommendation.
20. Route mandatory-review cases to human review.
21. Generate an analyst-facing explanation.
22. Preserve model, policy, workflow, tool, escalation, and audit evidence.

The workflow must support bounded loops.

It must not allow uncontrolled recursive agent execution.


## 10. Tool and Permission Architecture

Tools are typed capabilities with explicit permissions and side-effect boundaries.

Agents must not receive unrestricted access to application code,
databases, identity stores, external systems, or arbitrary APIs.

### 10.1 Tool Categories

Conceptual V1 tool categories include:

Data tools:

- get_application();
- get_customer_profile();

Model tools:

- calculate_dti();
- run_credit_risk_model();
- explain_model();

Policy tools:

- search_credit_policy();

Verification tools:

- verify_income();
- verify_employment();
- get_credit_report();

Action tools:

- create_review_case();
- send_notification();

### 10.2 Tool Permissions

Each agent must receive only the minimum tools required for its role.

Example:

Policy Agent:
- search_credit_policy();

Verification Agent:
- verify_income();
- verify_employment();
- get_credit_report();

Explanation Agent:
- read-only access to approved state;
- no external side-effect tools.

Escalation Agent:
- create_review_case();
- send_notification();

### 10.3 Side-Effect Controls

External side-effect tools require:

- explicit preconditions;
- permission checks;
- audit logging;
- sanitized inputs;
- idempotency controls where appropriate;
- deterministic workflow approval.

Agents must not directly execute arbitrary external actions.


## 11. Policy Retrieval and RAG Architecture

CreditPilot uses synthetic credit-policy documents for demonstration.

Policy retrieval must be evidence-based and traceable.

### 11.1 Retrieval Flow

The conceptual policy retrieval flow is:

Synthetic Policy Documents
→ Chunking
→ Embeddings
→ Vector Store
→ Retrieval
→ Policy Agent
→ Structured Policy Finding

### 11.2 Retrieval Requirements

Policy retrieval should preserve:

- source document;
- section or chunk reference;
- policy version;
- retrieval score where available;
- effective date where applicable.

### 11.3 Policy Agent Constraints

The Policy Agent must:

- distinguish retrieved policy from its interpretation;
- preserve policy citations;
- identify missing or conflicting policy evidence;
- avoid inventing policy;
- avoid inventing thresholds;
- avoid presenting synthetic policy as real bank policy.

Policy retrieval failure must not silently become policy approval.


## 12. Failure Handling and Safe Routing

Failure handling is part of the architecture.

Failures must not be silently ignored.

### 12.1 Model Failure

If the quantitative model fails:

- set explicit model failure state;
- do not invent PD;
- do not invent SHAP output;
- route to safe review or escalation.

### 12.2 Policy Retrieval Failure

If policy retrieval fails:

- record the retrieval failure;
- do not fabricate policy;
- retry only within configured limits;
- route unresolved cases to human review.

### 12.3 Verification Failure

If verification fails:

- preserve the failure result;
- preserve reported data separately;
- do not fabricate verified evidence;
- retry only within configured limits;
- route unresolved cases appropriately.

### 12.4 Tool Failure

Tool failures must be captured in structured state.

The system must support:

- bounded retry;
- explicit failure status;
- audit logging;
- safe fallback routing.

### 12.5 Agent Failure

If an agent returns invalid structured output:

- reject invalid output;
- retry only within configured limits;
- preserve the error;
- route to safe fallback or human review.

### 12.6 Loop Protection

CreditPilot must enforce:

- maximum investigation iterations;
- maximum tool calls;
- maximum retry count;
- timeout handling.

When limits are reached, the workflow must stop safely
and route according to configured rules.


## 13. Auditability and Observability

Every material decision-support step must be traceable.

The system should preserve:

- application or case reference;
- model version;
- model timestamp;
- PD and approved model outputs;
- SHAP explanation;
- retrieved policy evidence;
- policy version;
- agent outputs;
- tool calls;
- tool outcomes;
- workflow transitions;
- verification evidence;
- Decision Engine rule;
- recommendation;
- escalation reason;
- human-review outcome where captured;
- relevant timestamps.

PII-access auditing must remain separately identifiable from ordinary
workflow auditing.

Logs and traces must avoid unnecessary raw PII.


## 14. Security and Governance

CreditPilot V1 follows least-privilege and least-context principles.

Security controls include:

- synthetic/demo data only;
- deterministic PII classification;
- identity tokenization;
- PII Vault separation;
- LLM context sanitization;
- allowlist-based prompt context;
- role-based tool permissions;
- protected CreditState ownership;
- controlled external actions;
- immutable or append-only audit concepts;
- bounded retries and loops;
- mandatory human review;
- versioned model and policy artefacts.

No agent receives unrestricted access to raw PII.

No agent receives unrestricted authority over workflow state.

No LLM-enabled agent may override protected quantitative outputs
or deterministic recommendation logic.


## 15. V1 Scope and Non-Goals

CreditPilot V1 is designed as a portfolio and learning system.

It is not:

- a production lending platform;
- an autonomous approval engine;
- a real bank underwriting system;
- a substitute for legal or regulatory advice;
- a system using real customer PII;
- a system using proprietary bank underwriting policies.

V1 prioritizes architectural clarity, explainability, governance,
evaluation, and reproducibility over production scale.


## 16. Golden Demo Scenarios

CreditPilot V1 must support at least three demonstrable scenarios.

### 16.1 Straightforward Low-Risk Case

Expected path:

Application
→ Validation
→ Model
→ Policy
→ Decision Engine
→ Explanation

The case should demonstrate a short path with no unnecessary investigation.

### 16.2 Verification Changes the Risk Assessment

Example conceptual path:

Application reports income = 150000
→ Model
→ Policy requires verified income
→ Orchestrator identifies missing evidence
→ Verification Agent
→ verified_income = 98000
→ deterministic feature recalculation
→ model rerun
→ policy rerun
→ Decision Engine
→ MANUAL_REVIEW
→ Explanation / Escalation

This scenario demonstrates adaptive investigation and evidence-driven rerouting.

### 16.3 Policy or Evidence Conflict

Expected path:

Application
→ Model
→ Policy retrieval
→ conflicting or unresolved evidence
→ bounded investigation
→ unresolved conflict
→ Decision Engine / workflow rule
→ MANUAL_REVIEW
→ Escalation Agent
→ Human Review

This scenario demonstrates safe handling of uncertainty.


## 17. Architecture Invariants

The following rules must remain true throughout V1 implementation:

1. CreditPilot is decision support, not autonomous lending.
2. Raw identity PII is separated from the main AI workflow.
3. LLMs receive minimum necessary sanitized context.
4. Validation and deterministic calculations remain deterministic.
5. PD is produced only by the quantitative model.
6. SHAP is produced only from the quantitative model.
7. Agents cannot modify protected quantitative outputs.
8. Reported and verified evidence remain separately traceable.
9. Policy findings must be grounded in retrieved synthetic policy.
10. Agents cannot invent policy or thresholds.
11. The Orchestrator proposes workflow actions but does not enforce transitions.
12. The Workflow Controller enforces valid transitions.
13. Tools are typed and permission controlled.
14. External side effects are audited and controlled.
15. Recommendation fields are written only by the Decision Engine.
16. Mandatory human review cannot be bypassed.
17. Investigation loops and retries are bounded.
18. Failures are explicit and safely routed.
19. Model, policy, workflow, and decision versions remain traceable.
20. Material architecture changes require explicit human approval.


## 18. Open Questions

The following questions remain open for later design approval:

### OQ-1 — Sensitive Credit Attributes

Which credit attributes should be classified as PII,
sensitive personal information, or ordinary credit-risk features?

Examples requiring explicit classification include:

- income;
- employment information;
- credit bureau information;
- verified financial evidence.

### OQ-2 — CreditState Physical Schema

What exact fields and nested structures will implement the conceptual
CreditState domains?

This will be resolved during State Design.

### OQ-3 — Synthetic Decision Thresholds

What synthetic PD and workflow thresholds should be used for the demo?

These must be configurable and clearly identified as synthetic.

### OQ-4 — Verification Providers

Which verification tools will be mocked in V1 and which, if any,
will use public or sandbox APIs?

### OQ-5 — Human Review Interface

How will the V1 human analyst review and record an outcome?

### OQ-6 — Model Choice

The baseline should remain interpretable.

The exact baseline model and any challenger model will be selected
during Phase 1.


## 19. Phase 0 Architecture Exit Criteria

The architecture specification is ready to freeze when:

- project purpose and non-goals are explicit;
- deterministic, ML, agent, and human responsibilities are separated;
- the five approved agents are defined;
- verification responsibility is unambiguous;
- CreditState ownership principles are defined;
- PII and LLM security boundaries are defined;
- Workflow Controller authority is defined;
- Decision Engine authority is defined;
- tool permissions and side effects are bounded;
- policy retrieval is traceable;
- failure handling is explicit;
- human-review controls are explicit;
- audit requirements are defined;
- golden demo scenarios are defined;
- architecture invariants are documented;
- remaining unresolved design questions are explicitly listed.

After the architecture consistency review is completed and approved,
this document becomes the frozen V1 architecture source of truth.

Implementation must not begin before Phase 0 documentation and review
requirements are complete.
