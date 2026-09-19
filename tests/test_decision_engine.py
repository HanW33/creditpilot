from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from creditpilot.decision import (
    DecisionEngineConfig,
    DecisionEngineError,
    make_recommendation,
    record_decision_audit,
    run_decision_step,
)
from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    WorkflowControlConfig,
    WorkflowController,
    create_credit_state,
)
from creditpilot.state.schemas import (
    QuantitativeModelState,
    ValidationState,
    VerificationInterpretation,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def _workflow():
    return WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "unused")}),
            max_investigation_iterations=3,
            max_tool_calls=3,
            max_retries=2,
        )
    )


def _config():
    return DecisionEngineConfig(
        rule_version="synthetic-decision-rules-v1",
        synthetic_policy_notice="Synthetic demonstration thresholds only.",
        approval_max_pd=0.20,
        high_risk_min_pd=0.60,
    )


def _eligible_state(pd_score=0.40, required_evidence=()):
    controller = ProtectedStateController()
    state = create_credit_state(
        application_id="SYN-0000012",
        customer_token="customer-token-012",
        reported_values={"annual_income": 98_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-12",
        now=NOW,
    )
    state = controller.commit_validation_result(
        state,
        ValidationState(
            status="success",
            validated_at=NOW,
            validator_version="synthetic-validator-v1",
        ),
        written_by="deterministic_validation",
        expected_state_version=state.state_metadata.state_version,
    )
    state = controller.commit_quantitative_model_result(
        state,
        QuantitativeModelState(
            status="success",
            pd_score=pd_score,
            risk_band="synthetic-test-band",
            shap_risk_factors={"dti": 0.2},
            model_version="logistic-regression-v1",
            model_timestamp=NOW,
            input_state_version=state.state_metadata.state_version,
        ),
        written_by="quantitative_model",
        expected_state_version=state.state_metadata.state_version,
    )
    proposal = StateUpdateProposal(
        proposal_id="policy-ready-1",
        target_domain="policy_state.findings",
        proposed_changes={
            "status": "complete",
            "findings": (),
            "required_evidence": required_evidence,
            "conflicts": (),
        },
        basis_references=(),
        proposed_by="policy_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )
    return controller.commit_policy_findings(state, proposal)


@pytest.mark.parametrize(
    ("pd_score", "expected"),
    [
        (0.10, "APPROVAL_RECOMMENDATION"),
        (0.40, "MANUAL_REVIEW"),
        (0.80, "HIGH_RISK_REVIEW"),
    ],
)
def test_explicit_synthetic_thresholds_produce_deterministic_outcomes(
    pd_score, expected
) -> None:
    state = _eligible_state(pd_score)
    eligibility = _workflow().check_decision_eligibility(state)

    result = make_recommendation(state, eligibility, _config())

    assert result.recommendation == expected
    assert result.decision_rule.startswith("synthetic-decision-rules-v1:")
    assert result.input_state_version == state.state_metadata.state_version


def test_missing_required_evidence_blocks_decision_engine() -> None:
    state = _eligible_state(required_evidence=("verified_income",))
    eligibility = _workflow().check_decision_eligibility(state)

    assert eligibility.eligible is False
    assert "policy-required evidence is missing" in eligibility.reasons
    with pytest.raises(DecisionEngineError, match="ineligible evidence"):
        make_recommendation(state, eligibility, _config())


def test_model_must_be_rerun_after_committed_verified_evidence() -> None:
    state = _eligible_state(required_evidence=("verified_income",))
    interpretation = VerificationInterpretation(
        interpretation_id="late-evidence-1",
        result_id="verification-result-1",
        structured_evidence={"verified_income": 98_000},
        proposed_state_update={"verified_income": 98_000},
        created_at=NOW + timedelta(minutes=1),
    )
    state = replace(
        state,
        verification_state=replace(
            state.verification_state,
            interpretations=(interpretation,),
            verified_values={"verified_income": 98_000},
        ),
    )

    eligibility = _workflow().check_decision_eligibility(state)

    assert eligibility.eligible is False
    assert "quantitative model predates committed verified evidence" in (
        eligibility.reasons
    )


def test_thresholds_require_explicit_synthetic_notice_and_valid_order() -> None:
    state = _eligible_state()
    eligibility = _workflow().check_decision_eligibility(state)
    no_notice = DecisionEngineConfig("v1", "production bank rule", 0.2, 0.6)
    invalid_order = DecisionEngineConfig("v1", "synthetic demo", 0.7, 0.6)

    with pytest.raises(DecisionEngineError, match="identified as synthetic"):
        make_recommendation(state, eligibility, no_notice)
    with pytest.raises(DecisionEngineError, match="thresholds are invalid"):
        make_recommendation(state, eligibility, invalid_order)


def test_decision_commit_audit_and_review_routing_preserve_ownership() -> None:
    controller = ProtectedStateController()
    workflow = _workflow()
    state = _eligible_state(pd_score=0.40)
    eligibility = workflow.check_decision_eligibility(state)
    result = make_recommendation(state, eligibility, _config())
    state = controller.commit_recommendation(
        state,
        result,
        written_by="decision_engine",
        expected_state_version=state.state_metadata.state_version,
    )
    state, audit = record_decision_audit(state, result, _config(), controller)
    state = workflow.enforce_post_decision_review(
        state,
        review_recommendations=frozenset(
            {"MANUAL_REVIEW", "HIGH_RISK_REVIEW"}
        ),
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )

    assert state.recommendation_state.recommendation == "MANUAL_REVIEW"
    assert state.workflow_state.mandatory_human_review is True
    assert audit.recommendation == "MANUAL_REVIEW"
    assert state.governance_audit_references.decision_references == (
        audit.audit_reference,
    )


def test_mandatory_review_blocks_normal_decision_entry() -> None:
    workflow = _workflow()
    state = _eligible_state(pd_score=0.10)
    state = workflow.require_human_review(
        state,
        reason="Synthetic unresolved conflict",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    eligibility = workflow.check_decision_eligibility(state)

    assert eligibility.eligible is False
    assert "mandatory human review is already required" in eligibility.reasons


def test_ineligible_decision_step_routes_without_writing_recommendation() -> None:
    state = _eligible_state(required_evidence=("verified_income",))

    step = run_decision_step(
        state,
        config=_config(),
        review_recommendations=frozenset(
            {"MANUAL_REVIEW", "HIGH_RISK_REVIEW"}
        ),
        state_controller=ProtectedStateController(),
        workflow_controller=_workflow(),
    )

    assert step.status == "ineligible"
    assert step.recommendation is None
    assert step.audit is None
    assert step.state.recommendation_state.recommendation is None
    assert step.state.workflow_state.mandatory_human_review is True
