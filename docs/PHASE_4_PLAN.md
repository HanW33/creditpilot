# CreditPilot Phase 4 Plan

## Status

Phase 4 — Proposed, Human Approval Required

Prepared on 2026-09-18 after completion of Phase 3.

## Authority and Approval Boundary

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/CREDIT_POLICY_DESIGN.md`,
`docs/TOOL_DESIGN.md`, and `AGENTS.md` govern this phase.

The frozen policy design explicitly leaves the synthetic policy rules,
physical policy schema, chunking implementation, embedding model, vector
store, and retrieval ranking threshold unselected. This plan proposes a
minimal implementation profile; it does not approve or implement those
choices. Human approval is required before code or policy content is added.

## Proposed Phase 4 Scope

Phase 4 would provide:

- versioned synthetic policy documents with an explicit demonstration notice;
- stable section and chunk references;
- deterministic document loading and validation;
- local vectorization and retrieval;
- a permission-controlled `search_credit_policy()` READ tool;
- source, chunk, version, effective-date, score, invocation, and audit
  traceability;
- explicit empty, unavailable, invalid-source, and retrieval-failure results;
- tests for citations, versions, PII rejection, permissions, and failure paths.

Phase 4 would not implement the Policy Agent, verification providers, external
actions, decision thresholds, recommendations, real bank policy, or an
internet-connected policy source.

## Proposed Implementation Decisions

### 1. Physical policy schema

Use frozen Python records for:

- `SyntheticPolicyDocument`;
- `SyntheticPolicySection`;
- `PolicyChunk`;
- `PolicySearchRequest`;
- `PolicyEvidenceMatch`.

Every document would require a document ID, title, policy version, effective
date, synthetic-policy notice, provenance, and stable section identifiers.

### 2. Synthetic policy content

Use repository-owned demonstration documents only. Initial content would
describe evidence and safe-routing requirements already present in the frozen
architecture, such as:

- request verified income when a synthetic policy condition explicitly
  requires income evidence;
- preserve reported and verified values separately;
- expose conflicting or missing evidence;
- route unresolved conflicts, verification failure, and model failure to
  human review.

The documents would contain no approval, decline, PD, income, DTI, pricing, or
credit-score thresholds. They would be labelled fictional and unsuitable for
real lending decisions.

### 3. Chunking

Use one stable chunk per authored policy section. Do not split a section by
token count in V1. Chunk IDs would derive from document and section IDs, which
keeps citations stable and avoids silently changing evidence boundaries.

### 4. Vectorization

Use local scikit-learn TF-IDF vectors. This introduces no new external model,
network call, hosted embedding service, or additional runtime dependency.
Vocabulary and fitted vectorizer exist only for the supplied synthetic policy
corpus.

### 5. Vector store

Use an in-memory read-only index built from the validated synthetic corpus.
Database-backed persistence and remote vector stores remain out of scope.

### 6. Retrieval ranking

Use cosine similarity and a caller-supplied bounded `top_k`. Return scores and
source metadata for every result. Do not introduce a minimum similarity or
acceptance threshold in Phase 4. An empty corpus or query with no searchable
terms returns an explicit non-success result; it never becomes policy
approval.

### 7. Version handling

Return every retrieved item's policy version and effective date. Do not select
between multiple versions, infer precedence, or apply effective-date migration
logic. Multiple versions remain visible as a conflict for later interpretation.

### 8. State ownership

The retrieval tool returns raw `PolicyEvidence` only. It does not interpret
policy and does not write `policy_state`. Existing deterministic state controls
remain responsible for committing retrieved evidence. The future Policy Agent
will interpret evidence in Phase 5.

## Proposed Definition of Done

Phase 4 would be complete when:

- all approved implementation decisions above are represented in code and
  documentation;
- the corpus is entirely synthetic and versioned;
- retrieval returns stable citations and scores;
- raw evidence remains separate from interpretation;
- unauthorized, stale, PII-bearing, missing, and failed requests are rejected
  or returned explicitly;
- tool calls are auditable by reference;
- no synthetic threshold is represented as real policy;
- all tests, lint checks, and diff review pass.

## Approval Requested

Human approval is requested for the eight proposed implementation decisions
above. Implementation must not begin until that approval is explicit.
