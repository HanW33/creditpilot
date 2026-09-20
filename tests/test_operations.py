import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from creditpilot.interface import create_app
from creditpilot.interface.operations import (
    JsonFormatter,
    RuntimeConfig,
    route_template,
)
from creditpilot.interface.repository import InMemoryCaseRepository


def test_runtime_config_is_synthetic_only(monkeypatch) -> None:
    monkeypatch.setenv("CREDITPILOT_DEPLOYMENT_MODE", "synthetic_demo")
    monkeypatch.setenv("CREDITPILOT_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("CREDITPILOT_HOST", "0.0.0.0")
    monkeypatch.setenv("CREDITPILOT_PORT", "8080")

    config = RuntimeConfig.from_environment()

    assert config.deployment_mode == "synthetic_demo"
    assert config.log_level == "WARNING"
    assert config.host == "0.0.0.0"
    assert config.port == 8080

    monkeypatch.setenv("CREDITPILOT_DEPLOYMENT_MODE", "production")
    with pytest.raises(ValueError, match="synthetic_demo"):
        RuntimeConfig.from_environment()


def test_structured_logging_excludes_request_payload() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        "creditpilot.interface",
        logging.INFO,
        "",
        0,
        "request_complete",
        (),
        None,
    )
    record.method = "POST"
    record.path = "/api/cases/{id}/human-review"
    record.status_code = 200
    record.duration_ms = 1.25

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "request_complete"
    assert payload["path"] == "/api/cases/{id}/human-review"
    assert "body" not in payload
    assert "rationale" not in payload
    assert route_template("/api/cases/SYN-SECRET/human-review") == (
        "/api/cases/{id}/human-review"
    )


def test_readiness_metrics_and_scope_header(tmp_path: Path) -> None:
    report = tmp_path / "evaluation.json"
    report.write_text('{"status":"pass"}')
    app = create_app(
        InMemoryCaseRepository(),
        evaluation_report_path=report,
        runtime_config=RuntimeConfig(log_level="ERROR"),
    )
    test_client = TestClient(app)

    ready = test_client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "deployment_mode": "synthetic_demo",
        "persistence": "in_memory",
        "data_scope": "synthetic_only",
    }
    assert ready.headers["X-CreditPilot-Data-Scope"] == "synthetic-only"
    test_client.get("/health")
    metrics = test_client.get("/metrics").json()
    assert metrics["requests"]["GET /ready"] == 1
    assert metrics["requests"]["GET /health"] == 1
    assert metrics["status_codes"]["200"] >= 2
    assert metrics["persistence"] == "in_memory"


def test_readiness_fails_when_evaluation_artifact_is_missing(tmp_path: Path) -> None:
    app = create_app(
        InMemoryCaseRepository(),
        evaluation_report_path=tmp_path / "missing.json",
        runtime_config=RuntimeConfig(log_level="ERROR"),
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "required artifacts unavailable"


def test_container_configuration_preserves_local_synthetic_boundary() -> None:
    root = Path(__file__).parents[1]
    dockerfile = (root / "Dockerfile").read_text()
    compose = (root / "compose.yaml").read_text()

    assert "USER creditpilot" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "CREDITPILOT_DEPLOYMENT_MODE=synthetic_demo" in dockerfile
    assert '"127.0.0.1:8000:8000"' in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
