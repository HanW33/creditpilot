# CreditPilot Phase 7 Plan

## Status

Phase 7 — Complete

Started and completed on 2026-09-20 after Phase 6 verification boundaries were
committed.

## Authority and Scope

`docs/ARCHITECTURE_SPEC_V1.md`, `docs/AGENT_DESIGN.md`, `docs/WORKFLOW.md`, and
`AGENTS.md` govern this phase.

Phase 7 implements a provider-independent Orchestrator boundary:

- typed minimum-context input and structured output records;
- an injectable reasoning-backend protocol without selecting a model provider;
- deterministic validation of role, state consistency, evidence references,
  approved next actions, missing evidence, active requests, PII, and authority;
- protected proposal conversion for the next workflow action;
- protected proposal conversion for one policy-required verification request;
- reference-only Orchestrator audit records;
- deterministic mock-backend tests.

## Responsibility Boundary

- Policy Agent determines WHAT evidence is required.
- Orchestrator determines WHETHER verification or another investigation step is
  needed and proposes that next step.
- Workflow and state controls validate and commit protected changes.
- Verification Agent determines HOW an approved request is executed.
- Decision Engine alone owns recommendation fields.

The Orchestrator receives no execution tools in this phase. It cannot invoke
verification, enforce transitions, commit state, calculate credit risk, write
recommendations, bypass workflow limits, or bypass mandatory human review.

## Completion Evidence

- missing committed evidence produces a bounded verification-request proposal;
- only deterministic controls approve and commit the protected request;
- inconsistent actions, extra recommendation fields, decision-authority claims,
  and verification-tool access are rejected;
- material output is represented by a reference-only audit link in CreditState;
- repository lint and test checks pass.
