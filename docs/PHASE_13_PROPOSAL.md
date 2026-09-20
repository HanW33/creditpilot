# Phase 13 Proposal — API and Analyst Interface

## Status

Proposed — human approval required before implementation.

## Authority

This proposal is governed by `docs/ARCHITECTURE_SPEC_V1.md` and `AGENTS.md`.
It proposes a resolution for OQ-5, the V1 human-review interface. It does not
change agent roles, protected-state ownership, recommendation authority, or
mandatory-review ordering.

## Recommended V1 Shape

Implement a local, synthetic-demo web application with:

- a typed HTTP API for case submission, case-state retrieval, evaluation trace
  retrieval, and authorized human-review outcome recording;
- a small analyst dashboard that displays sanitized application evidence,
  model and SHAP output, policy citations, verification evidence, conflicts,
  deterministic recommendation, explanation, escalation status, and audit
  references;
- an explicit human-review form available only when mandatory review is
  committed;
- an in-memory repository for V1 demo cases, with interfaces that keep storage
  replaceable and no production database selection;
- offline synthetic providers only, with no live identity, verification,
  notification, or lending-system integration.

## Proposed Human-Review Contract

An authorized synthetic-demo analyst may record:

- application or case reference;
- a controlled review outcome from a small explicit enum;
- a sanitized rationale;
- reviewer token or role reference, never raw identity PII;
- reviewed state version and timestamp;
- an idempotency key and audit reference.

The write must be rejected when:

- mandatory human review is not committed;
- the case or state version is stale;
- the outcome is outside the approved enum;
- the payload includes prohibited identity fields;
- authorization or idempotency requirements are absent;
- an outcome would overwrite an existing result inconsistently.

The human-review outcome must not rewrite PD, SHAP, policy findings,
verification evidence, recommendation, decision rule, or decision reason.

## Proposed API Boundary

The API should expose only minimum-necessary synthetic demo data:

1. create a synthetic case;
2. list and retrieve sanitized case summaries;
3. retrieve the structured evidence and audit trace for one case;
4. run an explicitly supported demo workflow;
5. record an authorized human-review outcome;
6. retrieve the Phase 12 evaluation report and health status.

All request and response schemas should be typed. Mutation endpoints should
require explicit authorization context, expected state version, and
idempotency where applicable. Raw PII and unrestricted CreditState mutation
must not be exposed.

## Analyst Dashboard

The dashboard should be evidence-first and show:

- current workflow and mandatory-review status;
- reported and verified values separately;
- PD, model version, and SHAP factors;
- policy findings with source references and versions;
- verification source, interpretation, and conflicts;
- deterministic recommendation and rule;
- grounded explanation;
- escalation and human-review status;
- versioned audit timeline.

It must label all data and policy as synthetic and CreditPilot as decision
support. It must not present the recommendation as a final real-world lending
decision.

## Technology Choice Requiring Approval

Recommended implementation: FastAPI for the typed local API and server-rendered
HTML with minimal JavaScript for the analyst dashboard. This keeps the V1
interface small, inspectable, and easy to test without introducing a separate
frontend application.

Alternative: API-only Phase 13, leaving the visible dashboard for a later
phase. This reduces work but does not fully satisfy the planned analyst-interface
scope.

## Delivery Slices

1. approve OQ-5 and this Phase 13 scope;
2. implement typed API schemas and in-memory case repository;
3. implement sanitized read endpoints and demo workflow entry point;
4. implement protected human-review recording and audit;
5. implement the analyst dashboard;
6. add authorization, PII, stale-version, idempotency, and ownership tests;
7. run Phase 12 evaluation and the full test suite;
8. review, document, commit, and push.

## Non-Goals

- production authentication or identity management;
- a production database;
- real customer data or proprietary policy;
- live external providers;
- autonomous approval or denial;
- changing the five-agent architecture;
- selecting deployment infrastructure, which belongs to Phase 14.

## Approval Requested

Approve the recommended local web application: FastAPI, server-rendered analyst
dashboard, in-memory synthetic case repository, and protected/idempotent human
review recording under the controls above.
