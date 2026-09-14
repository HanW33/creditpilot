# AGENTS.md

## Authority and Scope

This file provides implementation instructions derived from
`docs/ARCHITECTURE_SPEC_V1.md`.

`docs/ARCHITECTURE_SPEC_V1.md` is the canonical architecture source of truth.
If this file, implementation, derived documentation, prompts, agent behaviour,
or coding-agent output conflicts with that specification, follow the
architecture specification.

Do not make material architecture changes without explicit human approval.
Do not introduce new architecture decisions while implementing existing ones.

CreditPilot V1 is a decision-support, portfolio, and learning system. It is not
an autonomous lending system, a production lending platform, or a substitute
for legal or regulatory advice. Use only synthetic, mock, simulated, or
suitable public demo data. Do not use real customer PII or proprietary bank
underwriting policies.

Implementation must not begin before the Phase 0 documentation and review
requirements in the architecture specification are complete.

## Preserve the Responsibility Boundaries

Keep deterministic software, quantitative ML, LLM-enabled agents, and human
decision-making separate.

Use deterministic software for:

- application validation;
- deterministic feature calculations;
- explicit policy gates;
- workflow safety rules and state-transition enforcement;
- decision rules;
- permission enforcement;
- retry and investigation-loop limits.

Use quantitative ML only for credit-risk prediction, including PD, risk
scoring, model calibration, and SHAP-based quantitative feature attribution.
LLMs and agents must never generate, replace, or modify quantitative model
outputs.

Use LLM-enabled agents only where adaptive reasoning, investigation, tool
selection, evidence gathering, explanation, or workflow adaptation is
required. Do not convert deterministic components into agents.

CreditPilot V1 has exactly five specialized LLM-enabled agents:

1. Orchestrator Agent: determine and propose the next investigation step.
2. Policy Agent: retrieve and interpret applicable synthetic policy.
3. Verification Agent: determine how to obtain requested evidence with
   approved verification tools.
4. Explanation Agent: produce analyst-facing explanations from existing
   evidence and remain read-only relative to decision evidence.
5. Escalation Agent: prepare and coordinate controlled handoff to a human
   analyst.

Do not add another agent without an approved architecture change.

The following remain non-agent components:

- application validation;
- PII classification and tokenization;
- feature engineering and deterministic calculations;
- credit-risk model and SHAP computation;
- Workflow Controller and workflow-state enforcement;
- deterministic Decision Engine;
- persistence and audit logging;
- permission, retry, and loop-limit enforcement.

## Verification Boundary

Preserve the verification responsibility chain:

- Policy Agent = WHAT evidence is required.
- Orchestrator Agent = WHETHER verification is needed now.
- Verification Agent = HOW the evidence is obtained.

The Policy Agent must not perform external verification. The Orchestrator must
not perform verification or enforce workflow transitions. The Verification
Agent must use only approved verification tools.

Approved verification tools obtain and return raw verification evidence. The
Verification Agent may interpret and structure that evidence and propose
evidence or verification-state updates. It must not fabricate verified facts
or bypass protected state controls.

Deterministic workflow and state controls must validate and commit protected
verification-state updates to CreditState. Keep reported applicant information
and verified evidence separate and traceable; verification must never overwrite
the reported value.

## CreditState and Protected Ownership

Treat CreditState as protected by deterministic workflow controls. Agents may
read authorized fields and propose permitted actions or updates, but they must
not have unrestricted mutation authority.

Preserve these ownership rules:

- quantitative model components own PD and model outputs;
- Policy Agent owns policy findings;
- approved verification tools obtain and return raw verification evidence;
- Verification Agent interprets and structures evidence and proposes
  verification-state updates;
- deterministic workflow and state controls validate and commit protected
  verification-state updates;
- Orchestrator Agent owns the proposed next workflow action;
- Decision Engine exclusively owns `recommendation`, `decision_rule`, and
  `decision_reason`;
- Explanation Agent owns the analyst-facing explanation;
- Escalation Agent and controlled action tools own escalation fields;
- Workflow Controller owns protected workflow transitions and counters.

Only approved quantitative components may write `pd_score`, `risk_band`,
SHAP risk factors, `model_version`, or `model_timestamp`. No LLM-enabled
agent may directly produce or modify protected recommendation fields.

The Orchestrator determines what should happen next. The deterministic Workflow
Controller determines whether the transition is permitted and enforces valid
transitions, permissions, mandatory-review conditions, retries, loop limits,
and protection against unauthorized state mutation.

The deterministic Decision Engine applies explicit recommendation logic using
approved evidence. It must not use unrestricted LLM reasoning for the final
recommendation.

## PII and LLM Security Boundary

Separate raw identity PII from the main AI workflow and CreditState. Represent
identity in the workflow with controlled references such as `application_id`
and opaque `customer_token`. Store identity information and token mappings in
a separate protected PII Vault.

Agents must not directly access the PII Vault. Any PII Vault access must use
explicitly authorized capabilities, least privilege, and independent auditing.

Before sending context to an LLM:

1. construct context with an allowlist;
2. remove unnecessary PII;
3. apply deterministic PII redaction;
4. provide only the minimum necessary information.

Do not use an LLM as the primary PII detection or protection mechanism.
Notifications and logs must avoid unnecessary raw PII. Keep PII-access auditing
separately identifiable from ordinary workflow auditing.

## Approved Credit Data Classification

CreditPilot V1 uses three information classes:

- Identity PII includes raw name, email, address, identity identifiers, and
  token mappings and remains in the protected PII Vault.
- Sensitive Credit Data includes income, employment information, credit bureau
  information, and verified financial evidence. It may enter CreditState only
  in structured, minimum-necessary, access-controlled form.
- Derived Risk Features include DTI, approved derived features, PD, risk band,
  and SHAP. They may enter protected CreditState under explicit ownership and
  minimum-context controls.

Raw identity documents and unnecessary identity PII must not enter CreditState
or ordinary agent and LLM context.

When verification is required, the Orchestrator proposes request creation.
Deterministic workflow and state controls validate, create, and commit the
protected verification request. The Verification Agent may act only on an
approved committed request.

Before Decision Engine entry, the Workflow Controller checks evidence
eligibility and routes ineligible mandatory-review cases safely. For eligible
cases, the Decision Engine writes the recommendation. The Workflow Controller
then enforces every mandatory-review condition without rewriting it.

## Tools, External Actions, and Policy Retrieval

Treat tools as typed, bounded capabilities with explicit permissions. Give each
agent only the minimum tools required for its role. Do not give agents
unrestricted access to application code, databases, identity stores, external
systems, arbitrary APIs, or arbitrary external actions.

External side effects must use approved tools and require explicit
preconditions, permission checks, audit logging, sanitized inputs, deterministic
workflow approval, and idempotency controls where appropriate.

Ground policy findings in retrieved synthetic policy. Preserve source,
section or chunk reference, policy version, retrieval score where available,
and effective date where applicable. Distinguish retrieved policy from
interpretation. Do not invent policy or thresholds, and do not treat policy
retrieval failure as policy approval.

## Failure, Human Review, and Audit Rules

Make failures explicit and route them safely. Never invent PD, SHAP output,
policy, or verified evidence after a failure. Preserve failure results and
errors. Retry only within configured limits.

Enforce maximum investigation iterations, tool calls, retries, and timeout
handling. Do not allow uncontrolled recursive agent execution. When configured
limits are reached, stop safely and route according to configured rules.

Mandatory human review must not be bypassed. Human review takes precedence when
required by policy, workflow rules, model failure, unresolved ambiguity,
verification failure, investigation limits, or other configured review
conditions. The Escalation Agent may prepare the handoff but must not make the
human decision.

Keep every material decision-support step traceable, including relevant case
references, model and policy versions, model outputs, SHAP evidence, policy
evidence, agent outputs, tool calls and outcomes, workflow transitions,
verification evidence, Decision Engine rule and recommendation, escalation
reason, human-review outcome where captured, and timestamps.

## Do Not Resolve Open Questions Implicitly

The architecture specification intentionally leaves these matters open:

- physical CreditState schema;
- synthetic PD and workflow thresholds;
- verification providers;
- human-review interface;
- challenger model choice.

Do not silently decide or encode answers to these questions. Any resolution
requires the later design approval identified in the architecture specification.

## Architecture Change Process

After Phase 0 human approval, the architecture is frozen. Do not silently
change agent responsibilities, state ownership, tool contracts, decision
authority, human-review rules, safety boundaries, or major workflow semantics.

If implementation requires a material change, report:

- the current architecture rule;
- the implementation problem;
- the proposed change and reason;
- affected components;
- risks;
- whether human approval is required.

Do not implement the material change before explicit human approval.

## Future Task Workflow

Future Codex tasks should normally:

1. read this file and the relevant architecture documents;
2. propose an implementation plan;
3. identify assumptions, conflicts, and unresolved risks;
4. implement only approved scope;
5. run relevant tests and evaluations;
6. review the diff;
7. report results and remaining risks.

Follow this development sequence:

```text
Canonical Architecture
→ AGENTS.md
→ Relevant Module Specification
→ Task Plan
→ Implement
→ Test
→ Evaluate
→ Self Review
→ Report
```

## Testing Expectations

For implemented modules:

- add relevant unit tests;
- add integration tests where applicable;
- test failure paths and permission rejection;
- verify that protected state cannot be mutated by unauthorized agents or
  components;
- run applicable lint and type checks;
- exercise relevant Golden Demo and evaluation paths when their dependencies
  exist.

Testing must not use real customer PII or proprietary bank policy.

## Definition of Done

A future module is complete only when:

- implementation matches the canonical architecture and relevant design;
- typed interfaces and ownership boundaries are respected;
- relevant unit tests pass;
- integration tests pass where applicable;
- failure and unauthorized-action paths are tested;
- unauthorized protected-state mutation is absent;
- applicable lint and type checks pass;
- the diff has been reviewed;
- architectural assumptions and unresolved risks are reported.
