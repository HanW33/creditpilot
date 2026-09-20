from pathlib import Path

from fastapi.testclient import TestClient

from creditpilot.interface import create_app
from creditpilot.interface.repository import InMemoryCaseRepository


def client(tmp_path: Path) -> TestClient:
    report = tmp_path / "evaluation.json"
    report.write_text('{"status":"pass","data_scope":"synthetic"}')
    return TestClient(
        create_app(InMemoryCaseRepository(), evaluation_report_path=report)
    )


def synthetic_case(application_id: str = "SYN-API-001") -> dict:
    return {
        "application_id": application_id,
        "customer_token": "customer-token-api-001",
        "reported_values": {"annual_income": 150000, "dti": 0.31},
        "sanitized_attributes": {"employment_type": "salaried"},
        "source_reference": "synthetic-api-fixture-1",
    }


def create_review_case(test_client: TestClient) -> dict:
    created = test_client.post("/api/cases", json=synthetic_case())
    assert created.status_code == 201
    reviewed = test_client.post(
        "/api/cases/SYN-API-001/demo-review",
        json={"reason": "Synthetic policy requires authorized analyst review."},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def test_health_case_api_and_dashboard_use_synthetic_sanitized_view(
    tmp_path: Path,
) -> None:
    test_client = client(tmp_path)

    assert test_client.get("/health").json() == {
        "status": "ok",
        "data_scope": "synthetic_only",
    }
    created = test_client.post("/api/cases", json=synthetic_case())
    assert created.status_code == 201
    body = created.json()
    assert body["synthetic_notice"]
    assert body["reported_values"]["annual_income"] == 150000
    assert "customer_token" not in body

    listing = test_client.get("/api/cases")
    assert [item["application_id"] for item in listing.json()] == ["SYN-API-001"]
    dashboard = test_client.get("/")
    assert dashboard.status_code == 200
    assert "Synthetic decision support only" in dashboard.text
    assert "Create a synthetic case" in dashboard.text
    assert 'id="annual-income"' in dashboard.text
    assert "Math.random()" in dashboard.text
    assert "browser request failed" in dashboard.text
    assert "SYN-API-001" in dashboard.text
    detail = test_client.get("/cases/SYN-API-001")
    assert "Reported evidence" in detail.text
    assert "Human authority is retained" in detail.text


def test_case_intake_rejects_raw_identity_pii(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    payload = synthetic_case()
    payload["reported_values"]["email"] = "person@example.com"

    response = test_client.post("/api/cases", json=payload)

    assert response.status_code == 422
    assert "raw identity PII is prohibited" in response.json()["detail"]
    assert test_client.get("/api/cases").json() == []


def test_human_review_requires_authorized_role_and_mandatory_review(
    tmp_path: Path,
) -> None:
    test_client = client(tmp_path)
    created = test_client.post("/api/cases", json=synthetic_case()).json()
    payload = {
        "outcome": "ACKNOWLEDGED",
        "rationale": "Reviewed synthetic evidence and retained human authority.",
        "reviewer_token": "analyst-token-001",
        "expected_state_version": created["state_version"],
        "idempotency_key": "review-key-001",
    }

    forbidden = test_client.post("/api/cases/SYN-API-001/human-review", json=payload)
    assert forbidden.status_code == 403

    headers = {"X-Analyst-Role": "authorized_human_analyst"}
    not_required = test_client.post(
        "/api/cases/SYN-API-001/human-review", json=payload, headers=headers
    )
    assert not_required.status_code == 409
    assert "requires mandatory review" in not_required.json()["detail"]


def test_human_review_is_versioned_audited_and_idempotent(tmp_path: Path) -> None:
    test_client = client(tmp_path)
    state = create_review_case(test_client)
    review_page = test_client.get("/cases/SYN-API-001")
    assert "Record authorized human review" in review_page.text
    assert "expected_state_version" in review_page.text
    payload = {
        "outcome": "RETURN_FOR_INFORMATION",
        "rationale": "Additional synthetic evidence is required.",
        "reviewer_token": "analyst-token-002",
        "expected_state_version": state["state_version"],
        "idempotency_key": "review-key-002",
    }
    headers = {"X-Analyst-Role": "authorized_human_analyst"}

    first = test_client.post(
        "/api/cases/SYN-API-001/human-review", json=payload, headers=headers
    )
    replay = test_client.post(
        "/api/cases/SYN-API-001/human-review", json=payload, headers=headers
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["replayed"] is False
    assert replay.json()["replayed"] is True
    reference = first.json()["review_reference"]
    case = replay.json()["case"]
    assert case["escalation"]["human_review_outcome_reference"] == reference
    assert case["audit"]["human_review_references"] == [reference]
    assert case["recommendation"]["recommendation"] is None
    completed_page = test_client.get("/cases/SYN-API-001")
    assert "Record authorized human review" not in completed_page.text


def test_review_rejects_stale_state_pii_and_idempotency_conflict(
    tmp_path: Path,
) -> None:
    test_client = client(tmp_path)
    state = create_review_case(test_client)
    headers = {"X-Analyst-Role": "authorized_human_analyst"}
    base = {
        "outcome": "ACKNOWLEDGED",
        "rationale": "Synthetic evidence reviewed.",
        "reviewer_token": "analyst-token-003",
        "expected_state_version": state["state_version"],
        "idempotency_key": "review-key-003",
    }
    stale = {**base, "expected_state_version": state["state_version"] - 1}
    assert (
        test_client.post(
            "/api/cases/SYN-API-001/human-review", json=stale, headers=headers
        ).status_code
        == 409
    )
    pii = {**base, "rationale": "Contact person@example.com for the decision."}
    assert (
        test_client.post(
            "/api/cases/SYN-API-001/human-review", json=pii, headers=headers
        ).status_code
        == 422
    )
    assert (
        test_client.post(
            "/api/cases/SYN-API-001/human-review", json=base, headers=headers
        ).status_code
        == 200
    )
    conflict = {**base, "outcome": "CLOSED_AFTER_REVIEW"}
    response = test_client.post(
        "/api/cases/SYN-API-001/human-review", json=conflict, headers=headers
    )
    assert response.status_code == 422
    assert "idempotency key payload conflict" in response.json()["detail"]


def test_evaluation_endpoint_and_not_found(tmp_path: Path) -> None:
    test_client = client(tmp_path)

    assert test_client.get("/api/evaluation").json()["status"] == "pass"
    assert test_client.get("/api/cases/missing").status_code == 404


def test_one_click_golden_demo_runs_live_contract_trace(tmp_path: Path) -> None:
    test_client = client(tmp_path)

    catalog = test_client.get("/api/demos")
    assert catalog.status_code == 200
    assert len(catalog.json()) == 3
    response = test_client.post("/api/demos/golden-2-income-verification/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pass"
    assert body["execution_kind"] == "synthetic_architecture_contract"
    assert "not a live provider call" in body["execution_notice"]
    checks = {item["check_id"]: item for item in body["trace"]}
    assert checks["verification.reported_preserved"]["status"] == "pass"
    assert checks["rerun.model_and_policy"]["actual"] == "model=2,policy=2"
    saved = test_client.get(f"/api/demo-runs/{body['run_id']}")
    assert saved.json() == body
    assert test_client.post("/api/demos/missing/run").status_code == 404

    dashboard = test_client.get("/")
    assert "Golden Demo validation" in dashboard.text
    assert "Run validation" in dashboard.text
