from datetime import UTC, datetime

import pytest

from creditpilot.state import build_role_state_view, create_credit_state

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000004",
        customer_token="opaque-customer-token-004",
        reported_values={"annual_income": 85_000},
        sanitized_attributes={"employment_type": "contract"},
        source_reference="synthetic-application-4",
        now=NOW,
    )


@pytest.mark.parametrize(
    "role",
    [
        "policy_agent",
        "orchestrator_agent",
        "verification_agent",
        "explanation_agent",
        "escalation_agent",
    ],
)
def test_agent_views_exclude_customer_token_and_governance_audit(role: str) -> None:
    view = build_role_state_view(_state(), role)

    assert "customer_token" not in repr(view.data)
    assert "governance_audit_references" not in view.data
    assert view.data["case_reference"]["application_id"] == "SYN-0000004"


def test_policy_agent_does_not_receive_recommendation_or_workflow_state() -> None:
    view = build_role_state_view(_state(), "policy_agent")

    assert "recommendation_state" not in view.data
    assert "workflow_state" not in view.data


def test_orchestrator_does_not_receive_raw_application_or_recommendation() -> None:
    view = build_role_state_view(_state(), "orchestrator_agent")

    assert "application_data" not in view.data
    assert "recommendation_state" not in view.data


def test_role_view_is_read_only() -> None:
    view = build_role_state_view(_state(), "verification_agent")

    with pytest.raises(TypeError):
        view.data["active_request_ids"] = ("request-1",)
    with pytest.raises(TypeError):
        view.data["application_data"]["reported_values"]["annual_income"] = 1


def test_unknown_role_is_rejected_by_default() -> None:
    with pytest.raises(ValueError, match="unsupported agent role"):
        build_role_state_view(_state(), "new_unapproved_agent")
