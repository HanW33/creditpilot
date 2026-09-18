from datetime import UTC, datetime

import pytest

from creditpilot.state import create_credit_state
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    calculate_dti,
    get_application,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000006",
        customer_token="customer-token-006",
        reported_values={
            "annual_income": 120_000,
            "monthly_debt_payment": 2_500,
        },
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-6",
        now=NOW,
    )


def _permissions() -> ToolPermissionPolicy:
    return ToolPermissionPolicy(
        callers_by_tool={
            "get_application": frozenset({"authorized_data_component"}),
            "calculate_dti": frozenset({"deterministic_feature_component"}),
        }
    )


def test_get_application_returns_only_requested_fields() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="read-1",
        tool_name="get_application",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="authorized_data_component",
        purpose="Read minimum synthetic application scope",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"application:read"}),
        arguments={
            "reported_fields": ("annual_income",),
            "sanitized_fields": (),
        },
        requested_at=NOW,
    )

    result = get_application(invocation, state, _permissions())

    assert result.status == "success"
    assert result.result["reported_values"] == {"annual_income": 120_000}
    assert "monthly_debt_payment" not in result.result["reported_values"]
    assert "customer_token" not in result.result


def test_tool_rejects_unauthorized_caller_and_scope() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="read-2",
        tool_name="get_application",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="unapproved_agent",
        purpose="Unauthorized read",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"application:read"}),
        arguments={"reported_fields": (), "sanitized_fields": ()},
        requested_at=NOW,
    )

    with pytest.raises(PermissionError, match="not authorized"):
        get_application(invocation, state, _permissions())


def test_calculate_dti_is_deterministic_and_traceable() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="dti-1",
        tool_name="calculate_dti",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="deterministic_feature_component",
        purpose="Calculate approved synthetic DTI feature",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"feature:calculate_dti"}),
        arguments={
            "monthly_debt_payment": 2_500,
            "annual_income": 120_000,
            "feature_logic_version": "dti-v1",
            "source_references": ("synthetic-application-6",),
        },
        requested_at=NOW,
    )

    first = calculate_dti(invocation, state, _permissions())
    second = calculate_dti(invocation, state, _permissions())

    assert first.result["dti"] == pytest.approx(0.25)
    assert second.result["dti"] == first.result["dti"]
    assert first.evidence_references == ("synthetic-application-6",)


def test_calculate_dti_fails_without_inventing_missing_inputs() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="dti-2",
        tool_name="calculate_dti",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="deterministic_feature_component",
        purpose="Calculate approved synthetic DTI feature",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"feature:calculate_dti"}),
        arguments={"annual_income": 120_000},
        requested_at=NOW,
    )

    result = calculate_dti(invocation, state, _permissions())

    assert result.status == "failure"
    assert result.result == {}
    assert result.failure is not None
    assert result.failure.code == "invalid_arguments"


def test_calculate_dti_rejects_non_finite_input() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="dti-3",
        tool_name="calculate_dti",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="deterministic_feature_component",
        purpose="Reject invalid synthetic DTI input",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"feature:calculate_dti"}),
        arguments={
            "monthly_debt_payment": float("nan"),
            "annual_income": 120_000,
            "feature_logic_version": "dti-v1",
            "source_references": ("synthetic-application-6",),
        },
        requested_at=NOW,
    )

    result = calculate_dti(invocation, state, _permissions())

    assert result.status == "failure"
    assert result.failure is not None


def test_tool_rejects_stale_state_version() -> None:
    state = _state()
    invocation = ToolInvocation(
        invocation_id="read-3",
        tool_name="get_application",
        application_id="SYN-0000006",
        case_id=None,
        requested_by="authorized_data_component",
        purpose="Stale read",
        input_state_version=2,
        authorized_scope=frozenset({"application:read"}),
        arguments={"reported_fields": (), "sanitized_fields": ()},
        requested_at=NOW,
    )

    with pytest.raises(ValueError, match="stale"):
        get_application(invocation, state, _permissions())
