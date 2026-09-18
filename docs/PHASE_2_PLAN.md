# CreditPilot Phase 2 Plan

## Status

Phase 2 — Complete

Started on 2026-09-18 after completion of the Phase 1 synthetic quantitative
baseline.
Completed on 2026-09-18.

The typed state container, protected update paths, workflow-state controls,
role-specific read views, and ownership tests satisfy the Phase 2 definition
of done. The implementation provides in-memory immutable records and does not
select a database, production identity system, deployment authorization
mechanism, verification provider, external action provider, or human-review
interface. Those remain governed by their later approved phases.

## Authority and Scope

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/STATE_DESIGN.md`, and `AGENTS.md` govern
this work. Phase 2 implements the approved logical CreditState design as typed
Python schemas and deterministic protected-state controls.

Phase 2 includes:

- typed schemas for every approved CreditState domain;
- explicit separation of reported and verified values;
- rejection of raw identity PII from CreditState;
- versioned state and stale-update protection;
- structured state-update proposals;
- deterministic ownership and commit validation;
- tests for schema invariants and unauthorized or stale updates.

Phase 2 does not select risk thresholds, workflow stages or numeric limits,
verification providers, a human-review interface, or a challenger model. It
does not implement agents, external tools, policy RAG, the Decision Engine,
API, UI, database, or deployment.

## Initial Increment

The initial implementation establishes the full typed state container and the
protected verification update path needed by the approved Golden Demo. It
allows an Orchestrator proposal to become a committed verification request
only through deterministic controls, and allows verified values to be
committed only from an approved tool result through a Verification Agent
proposal and deterministic validation.

The next protected paths cover deterministic validation results, quantitative
model outputs, grounded Policy Agent findings, and Decision Engine-owned
recommendations. These controls enforce ownership and provenance only; they do
not introduce policy thresholds or replace the later Workflow Controller
eligibility design.

The workflow-control increment adds configured transition enforcement, bounded
counters, mandatory-review enforcement, and the Orchestrator-owned next-action
proposal field. The implementation accepts explicit transition and limit
configuration; it does not select stages or numeric limits as architecture.

Role-specific read views use explicit allowlists for the five approved agents.
They are immutable, deny unknown roles by default, exclude opaque customer
tokens and PII-audit references, and omit unrelated state domains.

Supporting ownership paths keep the Explanation Agent read-only relative to
decision evidence, permit the Escalation Agent to prepare a handoff only after
mandatory review is committed, and append ordinary and PII audit references
through separately authorized deterministic writers.

## Definition of Done

Phase 2 is complete when:

- all logical CreditState domains have typed representations;
- ownership rules are enforced for implemented update paths;
- every protected commit increments `state_version`;
- stale proposals are rejected;
- reported values cannot be overwritten by verification;
- verified values require traceable tool evidence;
- raw identity PII is rejected from CreditState;
- relevant tests and lint checks pass;
- remaining physical persistence and access-control assumptions are recorded
  without silently resolving later-phase decisions.
