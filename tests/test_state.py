from datetime import UTC, datetime

import pytest

from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    StateUpdateRejected,
    create_credit_state,
)
from creditpilot.state.schemas import (
    VerificationInterpretation,
    VerificationToolResult,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000001",
        customer_token="customer-token-001",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-1",
        now=NOW,
    )


def _request_proposal(version: int = 1, proposer: str = "orchestrator_agent"):
    return StateUpdateProposal(
        proposal_id="proposal-request-1",
        target_domain="verification_state.requests",
        proposed_changes={
            "request_id": "verify-income-1",
            "evidence_required": "verified_income",
        },
        basis_references=("policy-finding-1",),
        proposed_by=proposer,
        expected_state_version=version,
        proposed_at=NOW,
    )


def test_credit_state_rejects_raw_identity_pii() -> None:
    with pytest.raises(ValueError, match="raw identity PII"):
        create_credit_state(
            application_id="SYN-1",
            customer_token="token-1",
            reported_values={"annual_income": 100_000, "email": "not-allowed"},
            sanitized_attributes={},
            source_reference="synthetic-1",
            now=NOW,
        )


def test_credit_state_mappings_cannot_be_mutated_directly() -> None:
    state = _state()

    with pytest.raises(TypeError):
        state.application_data.reported_values["annual_income"] = 98_000


def test_only_orchestrator_can_propose_verification_request() -> None:
    with pytest.raises(StateUpdateRejected, match="only the Orchestrator"):
        ProtectedStateController().commit_verification_request(
            _state(), _request_proposal(proposer="verification_agent")
        )


def test_stale_proposal_is_rejected() -> None:
    controller = ProtectedStateController()
    committed = controller.commit_verification_request(_state(), _request_proposal())

    with pytest.raises(StateUpdateRejected, match="stale"):
        controller.commit_verification_request(committed, _request_proposal())


def test_verified_income_is_traceable_and_does_not_overwrite_reported_income() -> None:
    controller = ProtectedStateController()
    state = controller.commit_verification_request(_state(), _request_proposal())
    state = controller.record_verification_tool_result(
        state,
        VerificationToolResult(
            result_id="income-result-1",
            request_id="verify-income-1",
            tool_name="mock_verify_income",
            raw_evidence_reference="evidence://income-result-1",
            status="success",
            returned_at=NOW,
        ),
    )
    interpretation = VerificationInterpretation(
        interpretation_id="interpretation-1",
        result_id="income-result-1",
        structured_evidence={"verified_income": 98_000},
        proposed_state_update={"annual_income": 98_000},
        created_at=NOW,
    )
    proposal = StateUpdateProposal(
        proposal_id="proposal-verified-income-1",
        target_domain="verification_state.verified_values",
        proposed_changes={"annual_income": 98_000},
        basis_references=("income-result-1",),
        proposed_by="verification_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    committed = controller.commit_verified_values(state, proposal, interpretation)

    assert committed.application_data.reported_values["annual_income"] == 150_000
    assert committed.verification_state.verified_values["annual_income"] == 98_000
    assert committed.state_metadata.state_version == 4


def test_verified_value_requires_successful_tool_evidence() -> None:
    controller = ProtectedStateController()
    state = controller.commit_verification_request(_state(), _request_proposal())
    interpretation = VerificationInterpretation(
        interpretation_id="interpretation-1",
        result_id="missing-result",
        structured_evidence={"verified_income": 98_000},
        proposed_state_update={"annual_income": 98_000},
        created_at=NOW,
    )
    proposal = StateUpdateProposal(
        proposal_id="proposal-verified-income-1",
        target_domain="verification_state.verified_values",
        proposed_changes={"annual_income": 98_000},
        basis_references=("missing-result",),
        proposed_by="verification_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="successful tool evidence"):
        controller.commit_verified_values(state, proposal, interpretation)
