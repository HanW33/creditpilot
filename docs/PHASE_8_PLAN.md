# CreditPilot Phase 8 Plan

## Status

Phase 8 — Complete

Started and completed on 2026-09-20 after the Orchestrator boundary was
committed.

## Authority and Scope

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/WORKFLOW.md`, `docs/AGENT_DESIGN.md`, and
`AGENTS.md` govern this phase.

Phase 8 integrates one explicit, bounded investigation cycle:

1. retrieve traceable synthetic policy evidence;
2. commit raw retrieval evidence separately;
3. run and audit the Policy Agent;
4. run and audit the Orchestrator;
5. validate and commit one protected verification request;
6. run and audit the matching approved verification tool;
7. run and audit the Verification Agent;
8. validate and commit verified evidence separately from reported evidence;
9. run the Orchestrator again and stop at the model-reevaluation boundary.

## Deterministic Controls

- tool-call and investigation counters are enforced by the Workflow Controller;
- tool-call capacity is checked before each tool executes;
- retry limits remain configuration supplied by the caller;
- reaching a configured limit sets mandatory human review;
- failed verification is audited, does not fabricate verified evidence, and
  routes to retry or escalation according to deterministic limit state;
- every protected update is committed by its existing state or workflow owner;
- the cycle is explicit and finite, with no recursive autonomous loop.

## Out of Scope

This phase does not implement the Phase 9 Decision Engine, recommendation
rules, lending thresholds, a real model or LLM provider, production data,
external verification, or a human-review interface. After verified evidence is
committed, the integrated cycle stops at `reevaluate_case` so approved feature,
model, and policy reevaluation can occur without crossing ownership boundaries.

## Completion Evidence

- the Golden Demo retains reported income of 150,000 and separately commits
  verified income of 98,000;
- policy, agent, tool, verification, and workflow boundaries are exercised in a
  single integration test;
- an investigation limit routes before verification execution;
- unavailable verification evidence is audited and routes safely without a
  fabricated value;
- repository lint and test checks pass.
