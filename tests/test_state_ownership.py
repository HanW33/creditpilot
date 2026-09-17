from datetime import UTC, datetime

import pytest

from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    StateUpdateRejected,
    create_credit_state,
)
from creditpilot.state.schemas import (
    FailureRecord,
    PolicyEvidence,
    QuantitativeModelState,
    RecommendationState,
    ValidationState,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000002",
        customer_token="customer-token-002",
        reported_values={"annual_income": 90_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-2",
        now=NOW,
    )


def test_validation_state_accepts_only_deterministic_validator() -> None:
    result = ValidationState(
        status="success",
        findings=(),
        validated_at=NOW,
        validator_version="application-validator-v1",
    )

    with pytest.raises(StateUpdateRejected, match="deterministic_validation"):
        ProtectedStateController().commit_validation_result(
            _state(),
            result,
            written_by="orchestrator_agent",
            expected_state_version=1,
        )


def test_quantitative_model_commits_traceable_pd_and_shap() -> None:
    state = _state()
    result = QuantitativeModelState(
        status="success",
        pd_score=0.23,
        shap_risk_factors={"dti": 0.31},
        model_version="logistic-regression-v1",
        model_timestamp=NOW,
        input_state_version=state.state_metadata.state_version,
    )

    committed = ProtectedStateController().commit_quantitative_model_result(
        state,
        result,
        written_by="quantitative_model",
        expected_state_version=state.state_metadata.state_version,
    )

    assert committed.quantitative_model_state.pd_score == 0.23
    assert committed.quantitative_model_state.shap_risk_factors["dti"] == 0.31
    assert committed.state_metadata.state_version == 2


def test_failed_model_cannot_contain_invented_pd() -> None:
    state = _state()
    result = QuantitativeModelState(
        status="failure",
        pd_score=0.23,
        input_state_version=state.state_metadata.state_version,
        failure=FailureRecord("model_error", "synthetic failure", NOW),
    )

    with pytest.raises(StateUpdateRejected, match="cannot invent PD or SHAP"):
        ProtectedStateController().commit_quantitative_model_result(
            state,
            result,
            written_by="quantitative_model",
            expected_state_version=state.state_metadata.state_version,
        )


def test_policy_findings_must_cite_committed_retrieval_evidence() -> None:
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="policy-proposal-1",
        target_domain="policy_state.findings",
        proposed_changes={"findings": ("Income verification required",)},
        basis_references=("income-section",),
        proposed_by="policy_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="lack committed evidence"):
        ProtectedStateController().commit_policy_findings(state, proposal)


def test_policy_evidence_then_grounded_finding_commits() -> None:
    controller = ProtectedStateController()
    state = _state()
    state = controller.record_policy_evidence(
        state,
        PolicyEvidence(
            source_document="synthetic-policy.md",
            section_or_chunk_reference="income-section",
            policy_version="synthetic-policy-v1",
        ),
        written_by="policy_retrieval",
        expected_state_version=state.state_metadata.state_version,
    )
    proposal = StateUpdateProposal(
        proposal_id="policy-proposal-1",
        target_domain="policy_state.findings",
        proposed_changes={
            "status": "complete",
            "findings": ("Income verification required",),
            "required_evidence": ("verified_income",),
        },
        basis_references=("income-section",),
        proposed_by="policy_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    committed = controller.commit_policy_findings(state, proposal)

    assert committed.policy_state.required_evidence == ("verified_income",)
    assert committed.policy_state.retrieved_evidence[0].policy_version == (
        "synthetic-policy-v1"
    )


def test_only_decision_engine_can_commit_recommendation() -> None:
    state = _state()
    result = RecommendationState(
        recommendation="MANUAL_REVIEW",
        decision_rule="synthetic-rule-1",
        decision_reason="Synthetic demonstration reason",
        input_state_version=state.state_metadata.state_version,
        decided_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="decision_engine"):
        ProtectedStateController().commit_recommendation(
            state,
            result,
            written_by="orchestrator_agent",
            expected_state_version=state.state_metadata.state_version,
        )


def test_decision_engine_recommendation_preserves_input_version() -> None:
    state = _state()
    result = RecommendationState(
        recommendation="MANUAL_REVIEW",
        decision_rule="synthetic-rule-1",
        decision_reason="Synthetic demonstration reason",
        input_state_version=state.state_metadata.state_version,
        decided_at=NOW,
    )

    committed = ProtectedStateController().commit_recommendation(
        state,
        result,
        written_by="decision_engine",
        expected_state_version=state.state_metadata.state_version,
    )

    assert committed.recommendation_state.recommendation == "MANUAL_REVIEW"
    assert committed.recommendation_state.input_state_version == 1
    assert committed.state_metadata.state_version == 2
