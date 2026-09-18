from datetime import UTC, datetime

import pytest

from creditpilot.agents import (
    AgentInvocation,
    VerificationAgentValidationError,
    run_verification_agent,
    verification_output_to_state_proposal,
)
from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    build_role_state_view,
    create_credit_state,
)
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    get_credit_report,
    record_verification_tool_result,
    verify_employment,
    verify_income,
)
from creditpilot.verification import MockVerificationProvider

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000009",
        customer_token="customer-token-009",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-9",
        now=NOW,
    )


def _approved_state(evidence_required="verified_income"):
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="request-proposal-1",
        target_domain="verification_state.requests",
        proposed_changes={
            "request_id": "verification-request-1",
            "evidence_required": evidence_required,
        },
        basis_references=("policy-finding-1",),
        proposed_by="orchestrator_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )
    return ProtectedStateController().commit_verification_request(state, proposal)


def _invocation(state, tool="verify_income"):
    return ToolInvocation(
        invocation_id=f"{tool}-result-1",
        tool_name=tool,
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="verification_agent",
        purpose="Obtain evidence for an approved synthetic request",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"verification:read"}),
        arguments={"request_id": "verification-request-1"},
        requested_at=NOW,
    )


def _permissions(*tools):
    return ToolPermissionPolicy(
        callers_by_tool={tool: frozenset({"verification_agent"}) for tool in tools}
    )


def _provider(records=None):
    return MockVerificationProvider(
        records=records
        or {"SYN-0000009": {"verified_income": {"verified_income": 98_000}}}
    )


def test_verification_tool_requires_approved_committed_request() -> None:
    state = _state()
    result = verify_income(
        _invocation(state),
        state,
        _permissions("verify_income"),
        provider=_provider(),
    )

    assert result.status == "failure"
    assert result.failure.code == "request_not_approved"
    assert result.result == {}


def test_verification_tool_must_match_requested_evidence() -> None:
    state = _approved_state("verified_income")
    result = verify_employment(
        _invocation(state, "verify_employment"),
        state,
        _permissions("verify_employment"),
        provider=_provider(),
    )

    assert result.status == "failure"
    assert result.failure.code == "request_tool_mismatch"


def test_unavailable_evidence_is_explicit_and_not_fabricated() -> None:
    state = _approved_state()
    provider = MockVerificationProvider(records={"OTHER": {}})
    result = verify_income(
        _invocation(state),
        state,
        _permissions("verify_income"),
        provider=provider,
    )

    assert result.status == "failure"
    assert result.failure.code == "evidence_unavailable"
    assert result.evidence_references == ()


@pytest.mark.parametrize(
    ("evidence_type", "tool_name", "tool", "value"),
    [
        ("verified_employment", "verify_employment", verify_employment, "active"),
        (
            "credit_report",
            "get_credit_report",
            get_credit_report,
            {"delinquencies": 0, "open_accounts": 4},
        ),
    ],
)
def test_other_approved_verification_capabilities_return_synthetic_evidence(
    evidence_type, tool_name, tool, value
) -> None:
    state = _approved_state(evidence_type)
    provider = _provider(
        {"SYN-0000009": {evidence_type: {evidence_type: value}}}
    )

    result = tool(
        _invocation(state, tool_name),
        state,
        _permissions(tool_name),
        provider=provider,
    )

    assert result.status == "success"
    assert result.result["raw_evidence"][evidence_type] == value


def test_golden_income_flow_keeps_reported_and_verified_values_separate() -> None:
    controller = ProtectedStateController()
    state = _approved_state()
    tool_result = verify_income(
        _invocation(state),
        state,
        _permissions("verify_income"),
        provider=_provider(),
    )
    assert tool_result.evidence_references[0].startswith("verification://")
    state = record_verification_tool_result(state, tool_result, controller)
    invocation = AgentInvocation(
        invocation_id="verification-agent-1",
        agent_role="verification_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Interpret income evidence for the approved request",
        authorized_state_view=build_role_state_view(state, "verification_agent"),
        permitted_tools=frozenset({"verify_income"}),
        workflow_constraints={"max_tool_calls": 1},
        invoked_at=NOW,
    )
    output = run_verification_agent(
        invocation, tool_result, request_id="verification-request-1"
    )
    proposal = verification_output_to_state_proposal(
        output, expected_state_version=state.state_metadata.state_version
    )
    committed = controller.commit_verified_values(
        state, proposal, output.interpretation
    )

    assert committed.application_data.reported_values["annual_income"] == 150_000
    assert committed.verification_state.verified_values["verified_income"] == 98_000
    assert committed.verification_state.tool_results[0].raw_evidence_reference


def test_verification_agent_cannot_use_unpermitted_capability() -> None:
    state = _approved_state()
    tool_result = verify_income(
        _invocation(state),
        state,
        _permissions("verify_income"),
        provider=_provider(),
    )
    invocation = AgentInvocation(
        invocation_id="verification-agent-2",
        agent_role="verification_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Interpret approved verification evidence",
        authorized_state_view=build_role_state_view(state, "verification_agent"),
        permitted_tools=frozenset({"verify_employment"}),
        workflow_constraints={},
        invoked_at=NOW,
    )

    with pytest.raises(VerificationAgentValidationError, match="no permitted tool"):
        run_verification_agent(
            invocation, tool_result, request_id="verification-request-1"
        )
