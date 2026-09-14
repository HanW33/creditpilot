# CreditPilot — Credit Policy Design

## Status

Phase 0 — Proposed Credit Policy Design

Pending human review.

## Authority

This document derives from `docs/ARCHITECTURE_SPEC_V1.md`. The architecture
specification remains authoritative if any conflict exists.

This design covers synthetic policy documents, retrieval, evidence, and Policy
Agent outputs. It does not define real bank policy or select decision
thresholds.

## 1. Purpose

Credit policy support must:

- retrieve relevant synthetic policy evidence;
- keep retrieved text distinct from agent interpretation;
- identify required evidence and policy constraints;
- preserve citations and versions;
- expose uncertainty, conflicts, and retrieval failures;
- provide structured findings to the workflow and deterministic Decision
  Engine.

The Policy Agent interprets applicable policy. It does not invent policy,
perform external verification, enforce workflow transitions, or make final
credit recommendations.

## 2. Policy Scope

CreditPilot V1 uses synthetic credit-policy documents only.

Every policy artefact must be clearly identified as synthetic demonstration
content and must preserve:

- source document;
- section or chunk reference;
- policy version;
- effective date where applicable;
- retrieval score where available.

No synthetic policy may be presented as proprietary or real bank underwriting
policy.

## 3. Policy Source Structure

A policy source should contain:

- `policy_document_id`;
- `title`;
- `policy_version`;
- `effective_date`, where applicable;
- `synthetic_policy_notice`;
- sections with stable references;
- policy text;
- provenance metadata.

Policy text and metadata are source evidence. They must remain separate from
the Policy Agent's interpretation.

## 4. Retrieval Flow

The approved flow is:

```text
Synthetic Policy Documents
→ Chunking
→ Embeddings
→ Vector Store
→ Retrieval
→ Policy Agent
→ Structured Policy Finding
```

The retrieval capability must return grounded results with traceable source
references. Retrieval must not silently add policy content or thresholds.

## 5. Retrieval Request

A logical policy retrieval request contains:

- case or application reference;
- sanitized, minimum-necessary case context;
- policy question;
- requested evidence or constraint;
- current policy version requirements, where applicable;
- invocation and audit reference.

Raw identity PII must not be included. Context must be allowlisted and
deterministically sanitized before any LLM use.

## 6. Retrieval Result

A logical retrieval result contains:

- retrieval status;
- matching evidence items;
- source document;
- section or chunk reference;
- policy version;
- retrieval score where available;
- effective date where applicable;
- tool and timestamp references;
- explicit failure information when retrieval fails.

A missing result, unavailable source, or retrieval failure is not policy
approval.

## 7. Policy Agent Output

The Policy Agent should produce a structured finding:

```text
PolicyFinding
├── finding_id
├── status
├── applicable_policy_evidence[]
├── interpretation
├── required_evidence[]
├── policy_constraints[]
├── conflicts[]
├── unresolved_questions[]
├── source_references[]
├── policy_versions[]
├── created_at
└── failure
```

Rules:

- every material interpretation must cite retrieved synthetic policy evidence;
- required evidence must be traceable to applicable policy;
- conflicts and missing evidence must remain explicit;
- retrieved evidence and interpretation must remain distinguishable;
- the Policy Agent must not invent policy, thresholds, or recommendations;
- invalid structured output must be rejected and routed safely.

## 8. Verification Boundary

The responsibility split is:

- Policy Agent = WHAT evidence is required;
- Orchestrator Agent = WHETHER verification is needed now;
- Verification Agent = HOW evidence is obtained.

The Policy Agent may identify `verified_income`, employment evidence, credit
report evidence, or another supported item as required when grounded in
retrieved policy. It must not call verification a success, fabricate evidence,
or perform the verification itself.

## 9. State and Ownership

Approved retrieval capabilities return raw policy evidence. The Policy Agent
owns structured policy findings. Deterministic controls validate protected
updates before they are committed to `policy_state`.

The Policy Agent does not write:

- quantitative model outputs;
- verification facts;
- workflow transitions;
- `recommendation`;
- `decision_rule`;
- `decision_reason`.

Policy findings consumed downstream must preserve the input state version,
policy version, and source references used.

## 10. Policy Versioning

Every policy document and material retrieval result must preserve a
`policy_version`. Effective date should also be retained where applicable.

A policy finding must identify the policy version or versions used. Rerunning
policy analysis must create a traceable new finding rather than erase the
evidence and interpretation used previously.

If multiple versions are retrieved, or the applicable version is unclear, the
Policy Agent must record the conflict or unresolved question. It must not
silently select a version or infer an effective-date rule.

This document does not define policy migration, precedence, or version-selection
logic. Those rules require explicit approval.

## 11. Policy Change and Reevaluation

When relevant committed evidence changes, policy evaluation must rerun where
required.

The new finding must:

- use the relevant current evidence;
- preserve its policy sources and versions;
- replace no historical audit evidence;
- make changed requirements or conflicts traceable;
- remain subject to deterministic state controls.

This document does not define policy effective-date selection rules or policy
migration behaviour beyond the traceability requirements in the architecture.

## 12. Failure Handling

If retrieval fails:

- record the failure;
- do not fabricate policy;
- do not treat failure as approval;
- retry only within configured limits;
- route unresolved cases to human review.

If Policy Agent output is invalid:

- reject the output;
- preserve the error;
- retry only within configured limits;
- route to safe fallback or human review.

Policy conflicts and unresolved interpretations must remain explicit and may
trigger human review under configured workflow rules.

## 13. Evaluation Requirements

Policy evaluation should verify:

- citation coverage for material findings;
- consistency between evidence and interpretation;
- correct identification of required evidence;
- explicit handling of conflicts and missing sources;
- refusal to invent policy or thresholds;
- safe handling of retrieval and structured-output failures;
- preservation of policy versions and references;
- separation of policy findings from recommendation authority.

No acceptance threshold is selected in this document.

## 14. Security and Audit

Policy retrieval and interpretation must:

- use synthetic policy only;
- receive sanitized, minimum-necessary context;
- enforce least-privilege tool access;
- log retrieval calls and outcomes;
- record Policy Agent outputs;
- avoid unnecessary raw PII in prompts, logs, and traces;
- preserve source and version provenance.

## 15. Decisions Not Made Here

This document does not select:

- synthetic policy rules or thresholds;
- embedding model;
- vector store;
- chunking implementation;
- retrieval ranking threshold;
- physical policy schema;
- sensitive-attribute classification;
- quantitative credit model;
- human-review interface.

These require separate approved design decisions.

## 16. Review Gate

Before approval:

- confirm the source and finding structures;
- confirm retrieval traceability;
- confirm the Policy Agent boundary;
- confirm failure and conflict routing;
- confirm PII and minimum-context controls;
- confirm that no real policy or threshold is implied;
- record human approval.
