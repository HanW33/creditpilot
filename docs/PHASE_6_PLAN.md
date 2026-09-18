# Phase 6 Plan - Verification Tools and Verification Agent

Status: Complete

## Objective

Implement the approved verification boundary with synthetic, deterministic,
offline evidence only. This phase does not select or connect a real
verification provider.

## Scope

- provide injected synthetic evidence for income, employment, and credit report
  verification;
- require an active, approved, committed verification request before a tool can
  run;
- enforce tool permissions, evidence-type matching, state version, and
  provenance;
- allow the Verification Agent to select the approved HOW, interpret returned
  facts, structure evidence, and propose a protected-state update;
- require deterministic controls to record tool provenance and commit verified
  values;
- preserve reported and verified values as separate state domains;
- fail explicitly when evidence is missing or invalid.

## Responsibility Boundary

- Policy Agent: WHAT evidence is required.
- Orchestrator Agent: WHETHER verification is needed and proposes the request.
- Deterministic controls: validate and commit the request.
- Verification Agent: HOW the approved evidence is obtained and interpreted.
- Approved verification tools: obtain and return raw evidence.
- Deterministic controls: validate and commit protected verification state.

## Approval Assumption

The instruction to proceed approves only repository-owned deterministic mock
providers for Phase 6. Real providers, APIs, credentials, and production data
remain outside scope and unresolved.

## Completion Evidence

- all three approved verification capabilities are implemented;
- negative tests cover missing approval, tool mismatch, unavailable evidence,
  and unpermitted tools;
- the Golden Demo preserves reported income of 150,000 while separately
  committing verified income of 98,000;
- repository lint and test checks pass.
