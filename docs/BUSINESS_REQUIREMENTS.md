# CreditPilot — Business Requirements

## Status

Phase 0 — Proposed High-Level Business Requirements

Pending human review.

## Authority

This document provides high-level business framing derived from
`docs/ARCHITECTURE_SPEC_V1.md`. The architecture specification remains the
canonical source of truth.

This document does not create production lending requirements, real credit
policy, or autonomous decision authority.

## 1. Product Definition

CreditPilot is an Agentic AI Credit Risk Decision Support System for portfolio
and learning purposes.

It demonstrates how an AI-enabled system can assist a Credit Risk Analyst or
Underwriter by combining:

- quantitative credit-risk modelling;
- explainable AI;
- synthetic policy retrieval and reasoning;
- adaptive investigation workflows;
- external evidence verification;
- human-in-the-loop review;
- controlled enterprise actions;
- auditability;
- AI and data governance.

CreditPilot supports decisions. It does not autonomously make real-world
lending decisions.

## 2. Primary User

The primary user is a Credit Risk Analyst or Underwriter.

The user needs to understand:

- the application evidence available;
- data that is missing, inconsistent, or unverified;
- quantitative model output and risk factors;
- applicable synthetic policy and its sources;
- verification evidence and conflicts;
- the deterministic recommendation and reason;
- why human review or escalation is required;
- the trace of material actions and decisions.

## 3. Business Problem

Credit analysis can require evidence from several sources and repeated
investigation when information is incomplete or conflicting.

CreditPilot must demonstrate a controlled way to:

- assemble sanitized case evidence;
- calculate and predict risk through appropriate deterministic and
  quantitative components;
- retrieve and interpret relevant synthetic policy;
- determine whether additional evidence is required;
- obtain approved verification evidence;
- recalculate when evidence changes;
- generate a traceable recommendation;
- explain the result to an analyst;
- escalate unresolved cases safely.

## 4. Business Objectives

CreditPilot V1 should:

1. demonstrate clear separation between deterministic logic, quantitative ML,
   agent reasoning, tools, and human authority;
2. provide traceable model, policy, and verification evidence;
3. adapt the investigation path when evidence is missing or conflicting;
4. preserve reported information while adding separately traceable verified
   evidence;
5. generate controlled, structured decision-support recommendations;
6. provide clear analyst-facing explanations;
7. route mandatory-review cases to a human analyst;
8. protect identity PII and minimize LLM context;
9. make material workflow activity auditable;
10. demonstrate safe handling of failures and bounded investigation.

## 5. Functional Requirements

### BR-F01 — Application Intake

The system must receive synthetic credit applications and establish controlled
case and customer references.

### BR-F02 — PII Governance

All incoming application data must pass through deterministic PII
classification, tokenization, separation, sanitization, access control, and
audit before entering the main AI workflow.

### BR-F03 — Validation and Features

The system must validate applications and calculate explicit features using
deterministic software.

### BR-F04 — Quantitative Risk Assessment

The system must use an approved quantitative model to produce PD and related
risk outputs and must use SHAP for quantitative feature attribution.

### BR-F05 — Policy Support

The system must retrieve traceable synthetic policy evidence and allow the
Policy Agent to produce grounded structured findings.

### BR-F06 — Investigation Coordination

The Orchestrator Agent must evaluate authorized current state and propose the
next investigation action without enforcing transitions or making the final
recommendation.

### BR-F07 — Verification

When required evidence is missing, the system must route through deterministic
controls to the Verification Agent and approved verification tools.

The Orchestrator proposes verification-request creation. Deterministic workflow
and state controls validate, create, and commit the protected request. Tools
obtain raw evidence, the Verification Agent interprets and proposes updates,
and deterministic controls commit protected verification state.

### BR-F08 — Evidence Recalculation

When relevant verified evidence changes, the system must recalculate affected
deterministic features and rerun model or policy evaluation where required.

### BR-F09 — Recommendation

Before Decision Engine entry, the Workflow Controller checks whether committed
evidence is eligible and safely routes ineligible mandatory-review cases. For
eligible cases, the deterministic Decision Engine produces the structured
recommendation, decision rule, and decision reason. The Workflow Controller
then enforces mandatory review without rewriting the recommendation.

### BR-F10 — Explanation

The Explanation Agent must produce a clear analyst-facing explanation from
existing approved evidence without modifying it.

### BR-F11 — Human Review and Escalation

The system must route mandatory-review cases to an authorized human analyst.
The Escalation Agent may prepare a sanitized handoff and request approved
external actions but must not make the human decision.

### BR-F12 — Audit

The system must preserve traceable model, policy, agent, tool, workflow,
verification, decision, escalation, and human-review evidence.

## 6. Business Rules

- CreditPilot is decision support, not autonomous lending.
- Real customer PII and proprietary bank policy are out of scope.
- Raw identity PII remains outside the main workflow and CreditState.
- Reported and verified information remain separate.
- PD and SHAP are produced only by quantitative components.
- Policy findings remain grounded in retrieved synthetic policy.
- Agents must not invent policy, thresholds, or verified facts.
- The Orchestrator proposes; the Workflow Controller permits or rejects.
- Recommendation fields are written only by the Decision Engine.
- Mandatory human review cannot be bypassed.
- External actions use approved, controlled, audited tools.
- Failures and investigation limits route safely and explicitly.

## 7. Non-Functional Requirements

### Explainability

The system must expose model, SHAP, policy, verification, and recommendation
evidence in a form suitable for analyst understanding.

### Traceability

Relevant source references, versions, timestamps, state transitions, tool
outcomes, rules, recommendations, and review outcomes must remain traceable.

### Privacy and Security

The system must apply least privilege, least context, identity separation,
deterministic redaction, controlled tool access, protected state ownership, and
separate PII auditing.

### Reliability and Safety

Failures must be explicit. Retries, tool calls, investigation loops, and
timeouts must be bounded. Mandatory human-review conditions must take
precedence.

### Reproducibility

Model, policy, workflow, and decision versions must remain identifiable.
Deterministic calculations and rules should be reproducible from their approved
inputs and versions.

## 8. In-Scope V1 Capabilities

- synthetic application handling;
- deterministic validation and features;
- quantitative PD prediction and SHAP;
- synthetic policy retrieval and interpretation;
- adaptive but bounded investigation;
- approved verification capability;
- protected CreditState;
- deterministic recommendation;
- analyst-facing explanation;
- controlled escalation and human review;
- audit and governance evidence;
- three Golden Demo scenarios.

## 9. Out of Scope

CreditPilot V1 is not:

- a production lending platform;
- an autonomous approval engine;
- a real bank underwriting system;
- a substitute for legal or regulatory advice;
- a system using real customer PII;
- a system using proprietary bank underwriting policies.

V1 prioritizes architectural clarity, explainability, governance, evaluation,
and reproducibility over production scale.

## 10. Golden Demo Requirements

V1 must demonstrate:

1. a straightforward low-risk path with no unnecessary investigation;
2. a case where verified income differs from reported income, causing
   recalculation and rerouting to `MANUAL_REVIEW`;
3. a policy or evidence conflict that remains unresolved and routes safely to
   human review.

The scenarios must demonstrate evidence provenance, role boundaries, state
protection, bounded workflow, explanation, and auditability.

## 11. Business Success Conditions

V1 is successful when it can demonstrate that:

- an analyst receives a coherent, traceable case assessment;
- quantitative risk is produced only by the approved model;
- policy findings cite synthetic source evidence;
- verification can alter the investigation without overwriting reported data;
- deterministic controls prevent unauthorized transitions and state writes;
- the Decision Engine produces the protected recommendation;
- explanations reflect existing evidence;
- unresolved or mandatory-review cases reach a human safely;
- material actions and failures can be reconstructed from audit evidence;
- no real PII or proprietary policy is used.

Specific quantitative acceptance thresholds are not defined here.

## 12. Stakeholder Authority

- quantitative components own risk prediction;
- Policy Agent owns grounded policy findings;
- Verification Agent interprets evidence and proposes updates;
- Orchestrator Agent coordinates investigation;
- Workflow Controller enforces permitted transitions;
- Decision Engine owns recommendation logic and fields;
- Explanation Agent owns the analyst-facing explanation;
- Escalation Agent coordinates controlled handoff;
- human analyst retains authority when human review is required.

## 13. Open Business and Design Questions

The following remain subject to later approval:

- final CreditState design approval;
- synthetic decision and workflow thresholds;
- verification providers;
- human-review interface;
- challenger model choice;
- concrete evaluation metrics and acceptance thresholds.

No implementation should resolve these silently.

## 14. Approval Gate

Before these requirements are treated as approved:

- confirm the V1 user, purpose, and business objectives;
- confirm functional and non-functional requirements;
- confirm V1 scope and non-goals;
- confirm the Golden Demo outcomes;
- confirm role and human-authority boundaries;
- confirm that open questions remain explicit;
- record human approval.
