# Phase 13 — API and Analyst Interface

## Status

Complete.

Approved on 2026-09-20 through `docs/PHASE_13_PROPOSAL.md`.

## Delivered Scope

- typed FastAPI endpoints for synthetic case intake, listing, detail, demo
  mandatory-review routing, human-review recording, evaluation, and health;
- a replaceable in-memory V1 repository with no production database choice;
- one-click UI execution of all three versioned Golden Demo architecture
  contracts, with per-check trace and explicit fixture/provider distinction;
- an evidence-first server-rendered analyst dashboard and case view;
- separate reported and verified evidence presentation;
- protected, versioned, authorized, and idempotent human-review recording;
- append-only human-review audit references;
- deterministic rejection of raw identity PII, stale state, unsupported
  outcomes, missing authorization, and conflicting idempotency replays;
- synthetic-data and decision-support notices in API metadata and pages.

The interface does not alter PD, SHAP, policy findings, verification evidence,
recommendation fields, or agent responsibilities. Human-review outcomes use
non-lending workflow outcomes and remain distinct from the Decision Engine's
recommendation.

## Run Locally

```bash
python -m creditpilot.interface.run
```

Open `http://127.0.0.1:8000`. Interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

The repository is intentionally in-memory: restarting the process clears demo
cases. Production authentication, storage, networking, secrets, and deployment
remain outside Phase 13.

## Next Phase

Phase 14 covers deployment packaging, operational configuration, health and
readiness behaviour, structured logging, and monitoring for the synthetic V1
demo. It must not turn CreditPilot into a production lending system.
