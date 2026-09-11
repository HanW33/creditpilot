# CreditPilot — Tool Design

## Status

Phase 0 — Proposed Tool Design

Pending human approval.

## Authority

This document defines the proposed tool boundaries and logical contracts for
CreditPilot V1.

`docs/ARCHITECTURE_SPEC_V1.md` remains the canonical architecture source of
truth. `docs/STATE_DESIGN.md` defines the proposed CreditState structure and
protected update path. If this document conflicts with either, the architecture
specification takes precedence.

This design does not select a programming language, tool framework, API
provider, verification provider, model, database, threshold, or human-review
interface.

## 1. Tool Principles

Every CreditPilot tool must be:

- a typed, bounded capability;
- granted only to authorized callers;
- validated before execution;
- restricted to minimum-necessary, sanitized inputs;
- explicit about side effects;
- auditable;
- deterministic when explicit rules or calculations are sufficient;
- explicit about success, failure, and unavailable results;
- subject to retries and limits enforced by deterministic controls.

Agents must not receive unrestricted access to application code, databases,
identity stores, arbitrary APIs, external systems, or arbitrary actions.

A tool result is not permission to mutate protected CreditState. Tools return
bounded results. The designated owner proposes or writes the applicable field,
and deterministic workflow or state controls validate protected updates before
commit.

## 2. Tool Categories

CreditPilot V1 uses these conceptual tool categories:

| Category | Tools | Purpose |
| --- | --- | --- |
| Data | `get_application()`, `get_customer_profile()` | Retrieve authorized, sanitized case data. |
| Model | `calculate_dti()`, `run_credit_risk_model()`, `explain_model()` | Perform deterministic calculations, quantitative prediction, and SHAP computation. |
| Policy | `search_credit_policy()` | Retrieve traceable synthetic policy evidence. |
| Verification | `verify_income()`, `verify_employment()`, `get_credit_report()` | Obtain raw external verification evidence. |
| Action | `create_review_case()`, `send_notification()` | Perform controlled external escalation actions. |

These tools are approved conceptual capabilities, not approval of a specific
vendor, provider, API, library, or implementation.

## 3. Common Invocation Contract

Every invocation should receive a control envelope:

```text
ToolInvocation
├── invocation_id
├── tool_name
├── application_id
├── case_id
├── requested_by
├── purpose
├── input_state_version
├── authorized_scope
├── arguments
├── idempotency_key
└── requested_at
```

Rules:

- `invocation_id` uniquely identifies the attempt;
- `requested_by` identifies the authorized component or agent;
- `purpose` states why the capability is required;
- `input_state_version` links the call to the state used to authorize it;
- `authorized_scope` records the approved data and action boundary;
- `arguments` must conform to the tool-specific schema;
- `idempotency_key` is required where repeated execution could duplicate an
  external side effect;
- raw identity PII must not be added merely for convenience.

The deterministic Workflow Controller or applicable permission control must
verify the caller, tool permission, arguments, workflow preconditions, current
state, retry and call limits, and side-effect conditions before execution.

## 4. Common Result Contract

Every tool returns a structured result:

```text
ToolResult
├── invocation_id
├── tool_name
├── status
├── result
├── evidence_references[]
├── failure
├── started_at
├── completed_at
└── tool_version
```

Rules:

- `status` distinguishes success, failure, unavailable, and other explicit
  outcomes defined by the implementation;
- `result` contains only the bounded output of the capability;
- `evidence_references` links relevant source evidence without copying
  unnecessary raw payloads or PII into CreditState;
- `failure` contains a sanitized structured failure when execution does not
  succeed;
- timestamps and `tool_version` support auditability and reproducibility;
- missing, failed, and unavailable results must not be represented as
  successful empty values;
- tools must never fabricate evidence, PD, SHAP output, policy, or action
  outcomes.

## 5. Data Tool Contracts

### 5.1 `get_application()`

Purpose:

Retrieve the authorized application data needed by the current workflow step.

Logical input:

- `application_id`;
- requested field scope;
- authorization context.

Logical output:

- application reference;
- reported values within the approved scope;
- sanitized application attributes;
- source reference;
- retrieval status.

Constraints:

- return minimum-necessary data only;
- do not expose raw identity PII to ordinary agent reasoning;
- do not modify application data or CreditState;
- preserve the distinction between reported values and verified evidence.

### 5.2 `get_customer_profile()`

Purpose:

Retrieve an authorized, sanitized customer profile for the current workflow
step.

Logical input:

- opaque `customer_token`;
- requested field scope;
- authorization context.

Logical output:

- `customer_token`;
- approved sanitized profile attributes;
- source reference;
- retrieval status.

Constraints:

- `customer_token` must remain opaque;
- ordinary agents must not use this tool to access the PII Vault directly;
- raw identity data and token-to-identity mappings must not be returned to
  ordinary agent reasoning;
- any separately authorized PII Vault access remains least-privilege and
  independently audited;
- this tool is read-only relative to CreditState.

## 6. Model Tool Contracts

### 6.1 `calculate_dti()`

Purpose:

Calculate debt-to-income or another explicitly approved deterministic feature.

Logical input:

- approved numeric inputs;
- input source references;
- feature-logic version;
- input state version.

Logical output:

- calculated value;
- calculation status;
- feature-logic version;
- input state version;
- failure, if any.

Constraints:

- calculation logic must be deterministic;
- the tool must not infer or invent missing inputs;
- reported and verified inputs remain traceable;
- which input is applicable must be defined by explicit feature logic;
- no LLM performs or overrides the calculation.

### 6.2 `run_credit_risk_model()`

Purpose:

Run the approved quantitative credit-risk model.

Logical input:

- validated model features;
- feature provenance;
- model version;
- input state version.

Logical output:

- `pd_score`;
- `risk_band`, when produced by the approved quantitative component;
- model version;
- model timestamp;
- input state version;
- execution status or explicit failure.

Constraints:

- only the approved quantitative model produces PD and model outputs;
- agents and LLMs must not generate, replace, or modify these outputs;
- model failure must not produce invented PD;
- the tool does not produce recommendation fields;
- this design does not select a model or threshold.

### 6.3 `explain_model()`

Purpose:

Compute quantitative feature attribution using SHAP for an approved model run.

Logical input:

- model-run reference;
- approved model inputs;
- model version;
- input state version.

Logical output:

- SHAP risk factors;
- model-run reference;
- model version;
- computation timestamp;
- status or explicit failure.

Constraints:

- SHAP output must derive from the quantitative model;
- agents and LLMs must not invent or modify SHAP results;
- failure must not produce fabricated explanation values;
- this quantitative explanation remains distinct from the analyst-facing
  narrative owned by the Explanation Agent.

## 7. Policy Tool Contract

### 7.1 `search_credit_policy()`

Purpose:

Retrieve relevant evidence from synthetic credit-policy documents.

Logical input:

- structured search request;
- authorized sanitized case context;
- requested evidence or policy question.

Logical output:

- matching policy evidence;
- source document;
- section or chunk reference;
- policy version;
- retrieval score, where available;
- effective date, where applicable;
- retrieval status or explicit failure.

Constraints:

- retrieval results remain distinct from Policy Agent interpretation;
- preserve citations and provenance;
- do not invent policy or thresholds;
- do not represent synthetic policy as real bank policy;
- retrieval failure must not silently become policy approval;
- the tool is read-only relative to policy documents and CreditState.

## 8. Verification Tool Contracts

The verification responsibility boundary is:

- Policy Agent = WHAT evidence is required;
- Orchestrator Agent = WHETHER verification is needed now;
- Verification Agent = HOW evidence is obtained;
- approved verification tools = obtain and return raw evidence;
- deterministic workflow and state controls = validate and commit protected
  verification-state updates.

Verification providers remain unresolved under OQ-4. These contracts do not
approve a real, public, sandbox, or mock provider.

### 8.1 `verify_income()`

Purpose:

Obtain raw evidence relevant to an income-verification request.

Logical input:

- verification request ID;
- application or case reference;
- opaque customer reference;
- minimum authorized verification attributes;
- authorization and purpose context.

Logical output:

- verification request ID;
- raw evidence reference;
- returned income evidence, when available and authorized;
- source or provider reference;
- evidence timestamp;
- status or explicit failure.

Constraints:

- do not overwrite reported income;
- do not fabricate a verified value;
- return raw evidence to the controlled verification flow;
- the Verification Agent may interpret, structure, and propose an update;
- deterministic controls validate and commit any protected verified value;
- raw identity PII must not be copied into CreditState.

### 8.2 `verify_employment()`

Purpose:

Obtain raw evidence relevant to an employment-verification request.

Logical input:

- verification request ID;
- application or case reference;
- opaque customer reference;
- minimum authorized verification attributes;
- authorization and purpose context.

Logical output:

- verification request ID;
- raw evidence reference;
- returned employment evidence, when available and authorized;
- source or provider reference;
- evidence timestamp;
- status or explicit failure.

Constraints:

- keep reported and verified employment information separate;
- do not fabricate verified facts;
- use the same interpretation, proposal, deterministic validation, and commit
  boundary as other verification tools;
- raw identity PII must not be copied into CreditState.

### 8.3 `get_credit_report()`

Purpose:

Obtain raw evidence relevant to an authorized credit-report request.

Logical input:

- verification request ID;
- application or case reference;
- opaque customer reference;
- minimum authorized request scope;
- authorization and purpose context.

Logical output:

- verification request ID;
- raw evidence reference;
- authorized credit-report evidence;
- source or provider reference;
- evidence timestamp;
- status or explicit failure.

Constraints:

- enforce least privilege and minimum-necessary scope;
- do not fabricate or reinterpret raw evidence inside the tool;
- the Verification Agent may interpret and structure the result but may not
  bypass protected state controls;
- deterministic controls validate and commit protected verification updates;
- this design does not classify bureau data under OQ-1 or select a provider
  under OQ-4.

## 9. Action Tool Contracts

Action tools create external side effects. They require explicit preconditions,
permission checks, audit logging, sanitized inputs, deterministic workflow
approval, and idempotency where appropriate.

### 9.1 `create_review_case()`

Purpose:

Create one controlled human-review case after the workflow authorizes
escalation.

Logical input:

- application or case reference;
- sanitized review-package reference;
- escalation reasons;
- authorization context;
- idempotency key.

Logical output:

- external review-case reference;
- action status;
- idempotency outcome;
- timestamp;
- explicit failure, if any.

Preconditions:

- human review is required or otherwise permitted by deterministic workflow
  rules;
- the review package contains sufficient sanitized evidence;
- the caller and action are authorized;
- the idempotency key has been checked.

Constraints:

- do not include unnecessary raw PII;
- repeated execution with the same idempotency key must not create duplicate
  review cases;
- the tool records the external action result but does not make the human
  decision;
- this design does not choose the human-review interface.

### 9.2 `send_notification()`

Purpose:

Send a controlled notification for an authorized workflow or escalation event.

Logical input:

- approved destination reference;
- sanitized message payload;
- application or case reference;
- purpose;
- authorization context;
- idempotency key, where duplicate delivery must be prevented.

Logical output:

- delivery reference;
- delivery status;
- idempotency outcome, where applicable;
- timestamp;
- explicit failure, if any.

Preconditions:

- the workflow permits the notification;
- destination and payload are authorized;
- the payload has passed deterministic sanitization;
- idempotency has been checked where appropriate.

Constraints:

- notifications must not contain unnecessary raw PII;
- normally reference `application_id`, `case_id`, or `customer_token`;
- the tool must not send arbitrary agent-generated content without the required
  controls;
- delivery failure remains explicit and auditable.

## 10. Agent Tool Permissions

Apply least privilege. The architecture explicitly provides these examples:

| Agent | Permitted tool capability |
| --- | --- |
| Policy Agent | `search_credit_policy()` |
| Verification Agent | `verify_income()`, `verify_employment()`, `get_credit_report()` |
| Explanation Agent | Read-only access to approved state; no external side-effect tools |
| Escalation Agent | `create_review_case()`, `send_notification()` |

The Orchestrator coordinates investigation and proposes the next action. It
must not receive verification or action capabilities merely to perform those
operations itself.

Data and model tool access must be granted only to the authorized component or
workflow step that requires the capability. This document does not broaden any
agent's role or grant unrestricted tool access.

## 11. Execution and State-Commit Flow

The standard tool path is:

1. An authorized component or agent proposes a tool invocation.
2. Deterministic controls validate the caller, permission, arguments, workflow
   transition, current state version, retry limits, tool-call limits, and
   side-effect preconditions.
3. The approved tool performs its bounded capability.
4. The tool returns a structured result or explicit failure.
5. The authorized owner interprets the result or proposes the applicable state
   update.
6. Deterministic workflow and state controls validate the protected update.
7. The designated component owner writes protected fields.
8. Persistence commits a new state version.
9. The invocation, result, transition, and commit outcome are linked to audit
   records.

No tool invocation gives an agent unrestricted authority to mutate CreditState.

## 12. Failure, Retry, and Timeout Rules

Tool failures must preserve:

- invocation and tool reference;
- explicit failure status;
- sanitized failure reason;
- attempt number;
- timestamps;
- retry eligibility;
- safe routing outcome.

Retries, maximum tool calls, investigation iterations, and timeouts are
enforced deterministically. An agent must not create an uncontrolled retry
loop. When limits are reached, the workflow stops safely and routes according
to configured rules.

Verification failure preserves reported data separately and must not create
verified evidence. Model failure must not create PD or SHAP output. Policy
retrieval failure must not become approval. Action failure must not be reported
as successful completion.

This design does not define numeric retry, call, iteration, or timeout limits.

## 13. Audit Requirements

For each material invocation, preserve:

- application or case reference;
- invocation ID and tool name;
- caller and purpose;
- authorized scope;
- sanitized arguments or argument references;
- input state version;
- tool version;
- start and completion timestamps;
- result status and evidence references;
- failure and retry information;
- side-effect and idempotency outcome;
- resulting workflow transition and state-version reference.

PII-access auditing remains separately identifiable from ordinary tool and
workflow auditing. Logs and traces must avoid unnecessary raw PII.

## 14. Security Requirements

Tool implementations must:

- validate inputs against an allowlisted schema;
- reject unauthorized fields and capabilities;
- enforce least privilege and least context;
- sanitize LLM-bound and externally bound content;
- prevent direct ordinary-agent access to the PII Vault;
- avoid placing secrets, credentials, or unnecessary raw payloads in
  CreditState, prompts, logs, or notifications;
- expose only bounded results;
- preserve explicit provenance;
- reject unauthorized or stale protected-state updates.

LLMs must not be the primary enforcement mechanism for permissions, PII
protection, state transitions, retries, limits, or side-effect preconditions.

## 15. Design Invariants

1. Tools are typed, bounded, permission-controlled capabilities.
2. Tool results do not bypass protected CreditState controls.
3. Deterministic logic remains deterministic.
4. Only quantitative components produce PD and SHAP outputs.
5. Policy retrieval remains grounded, cited, and distinct from interpretation.
6. Verification tools obtain raw evidence; the Verification Agent interprets
   and proposes; deterministic controls validate and commit.
7. Reported and verified information remain separate.
8. Action tools require deterministic approval and audit.
9. Mandatory human review cannot be bypassed.
10. Failures and exhausted limits route safely and explicitly.
11. Raw identity PII is excluded from ordinary agent context and CreditState.
12. Every material tool call and outcome remains traceable.
13. No new agent or unrestricted capability is introduced.

## 16. Decisions Explicitly Not Made Here

This document does not resolve:

- OQ-1: classification of sensitive credit attributes;
- OQ-3: synthetic PD and workflow thresholds;
- OQ-4: verification providers;
- OQ-5: human-review interface;
- OQ-6: baseline or challenger model choice.

It does not select concrete APIs, vendors, network protocols, credentials,
schemas, libraries, deployment topology, or physical storage.

## 17. Approval Gate

Before this tool design becomes authoritative:

- confirm every V1 tool is necessary and sufficiently bounded;
- confirm all caller permissions and side-effect preconditions;
- confirm tool inputs use minimum-necessary sanitized context;
- confirm output ownership and protected-state commit paths;
- confirm verification tools cannot overwrite reported information;
- confirm external actions are auditable and idempotent where appropriate;
- confirm failures and limits route safely;
- confirm no open architecture question was resolved implicitly;
- record explicit human approval.

Until approval is recorded, this document is a proposal and implementation
must not treat its unresolved choices as frozen architecture.
