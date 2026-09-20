# Phase 14 — Deployment and Monitoring

## Status

Complete.

## Scope

Phase 14 packages the synthetic V1 demo for repeatable local execution and adds
operational visibility without claiming production-lending readiness.

Delivered controls:

- a non-root container image and local Compose configuration;
- read-only container filesystem, temporary `/tmp`, and no-new-privileges;
- environment-driven host, port, and log-level configuration;
- a hard deployment-mode guard that permits `synthetic_demo` only;
- liveness (`/health`) and artifact-aware readiness (`/ready`) endpoints;
- in-process request/status/human-review counters at `/metrics`;
- structured JSON request logs containing method, route, status, and duration,
  but no request bodies, case evidence, identity data, or review rationale;
- a response header that identifies the synthetic-only data scope;
- automated tests for configuration, readiness, metrics, and log minimization.

## Local Process

```bash
python -m creditpilot.interface.run
```

Supported variables:

- `CREDITPILOT_DEPLOYMENT_MODE=synthetic_demo`;
- `CREDITPILOT_HOST=127.0.0.1` or `0.0.0.0` for a container binding;
- `CREDITPILOT_PORT=8000`;
- `CREDITPILOT_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`.

## Container

```bash
docker compose up --build
```

The Compose port is bound to `127.0.0.1` and is not exposed remotely by
default. The in-memory repository is intentionally ephemeral.

The container contract is covered by repository tests. Docker was not installed
on the completion host, so an actual image build remains an environment-level
verification step when Docker is available.

## Explicit Non-Production Boundary

This deployment is not production-ready and does not select production
authentication, durable storage, secret management, TLS termination,
distributed tracing, alert routing, availability targets, or infrastructure.
It must not process real customer PII or proprietary underwriting policy.

Moving beyond this synthetic local demo requires a separately approved
security, privacy, operations, and architecture review.
