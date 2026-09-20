from datetime import UTC, datetime

import pytest

from creditpilot.agents import (
    AgentInvocation,
    ExplanationAgentValidationError,
    explanation_output_to_state_proposal,
    record_explanation_agent_audit,
    run_explanation_agent,
)
from creditpilot.decision import DecisionEngineConfig, run_decision_step
from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    WorkflowControlConfig,
    WorkflowController,
    build_role_state_view,
    create_credit_state,
)
from creditpilot.state.schemas import QuantitativeModelState, ValidationState

NOW = datetime(2026, 9, 20, tzinfo=UTC)


class DraftBackend:
    def __init__(self, draft_factory):
        self.draft_factory = draft_factory

    def generate_explanation(self, context):
        return self.draft_factory(context)


def _workflow():
    return WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "unused")}),
            max_investigation_iterations=3,
            max_tool_calls=3,
            max_retries=2,
        )
    )


def _state(pd_score=0.10):
    controller = ProtectedStateController()
    state = create_credit_state(
        application_id="SYN-0000014",
        customer_token="customer-token-014",
        reported_values={"annual_income": 98_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-14",
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
            shap_risk_factors={"dti": 0.2},
            model_version="logistic-regression-v1",
            model_timestamp=NOW,
            input_state_version=state.state_metadata.state_version,
        ),
        written_by="quantitative_model",
        expected_state_version=state.state_metadata.state_version,
    )
    state = controller.commit_policy_findings(
        state,
        StateUpdateProposal(
            proposal_id="explanation-policy-ready",
            target_domain="policy_state.findings",
            proposed_changes={
                "status": "complete",
                "findings": (),
                "required_evidence": (),
                "conflicts": (),
            },
            basis_references=(),
            proposed_by="policy_agent",
            expected_state_version=state.state_metadata.state_version,
            proposed_at=NOW,
        ),
    )
    decision = run_decision_step(
        state,
        config=DecisionEngineConfig(
            rule_version="synthetic-explanation-rules-v1",
            synthetic_policy_notice="Synthetic demonstration only.",
            approval_max_pd=0.20,
            high_risk_min_pd=0.60,
        ),
        review_recommendations=frozenset(
            {"MANUAL_REVIEW", "HIGH_RISK_REVIEW"}
        ),
        state_controller=controller,
        workflow_controller=_workflow(),
    )
    return decision.state


def _invocation(state, tools=frozenset()):
    return AgentInvocation(
        invocation_id="explanation-agent-1",
        agent_role="explanation_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Explain committed decision-support evidence",
        authorized_state_view=build_role_state_view(state, "explanation_agent"),
        permitted_tools=tools,
        workflow_constraints={"read_only": True},
        invoked_at=NOW,
    )


def _valid_draft(context):
    view = context.authorized_state
    model = view["quantitative_model_state"]
    recommendation = view["recommendation_state"]
    workflow = view["workflow_state"]
    return {
        "status": "complete",
        "explanation": (
            f"Model: committed PD is {model.pd_score}. "
            "Policy: policy evaluation is complete with no conflict. "
            "Verification: no additional verified value was required. "
            f"Decision: {recommendation.recommendation} under "
            f"{recommendation.decision_rule}."
        ),
        "evidence_references": list(context.known_evidence_references),
        "input_state_version": context.state_version,
        "limitations": list(workflow.mandatory_review_reasons),
        "unresolved_items": [],
    }


def test_grounded_explanation_commits_without_changing_decision_evidence() -> None:
    controller = ProtectedStateController()
    state = _state()
    invocation = _invocation(state)
    output = run_explanation_agent(invocation, DraftBackend(_valid_draft))
    original_recommendation = state.recommendation_state
    original_model = state.quantitative_model_state
    state = controller.commit_explanation(
        state,
        explanation_output_to_state_proposal(
            output, expected_state_version=state.state_metadata.state_version
        ),
    )
    state, audit = record_explanation_agent_audit(
        state, invocation, controller, output=output
    )

    assert state.explanation_state.explanation == output.explanation
    assert state.recommendation_state == original_recommendation
    assert state.quantitative_model_state == original_model
    assert audit.validation_result == "accepted"


def test_explanation_agent_has_no_tools() -> None:
    state = _state()
    with pytest.raises(ExplanationAgentValidationError, match="must not receive"):
        run_explanation_agent(
            _invocation(state, frozenset({"send_notification"})),
            DraftBackend(_valid_draft),
        )


def test_explanation_cannot_omit_committed_recommendation() -> None:
    state = _state()

    def invalid(context):
        draft = _valid_draft(context)
        draft["explanation"] = draft["explanation"].replace(
            "APPROVAL_RECOMMENDATION", "an unspecified outcome"
        )
        return draft

    with pytest.raises(ExplanationAgentValidationError, match="recommendation"):
        run_explanation_agent(_invocation(state), DraftBackend(invalid))


def test_explanation_must_disclose_mandatory_review_reason() -> None:
    state = _state(pd_score=0.40)

    def concealed(context):
        draft = _valid_draft(context)
        draft["limitations"] = []
        return draft

    with pytest.raises(ExplanationAgentValidationError, match="mandatory-review"):
        run_explanation_agent(_invocation(state), DraftBackend(concealed))


def test_explanation_rejects_unknown_evidence_reference() -> None:
    state = _state()

    def invented(context):
        draft = _valid_draft(context)
        draft["evidence_references"] = ["evidence://invented"]
        return draft

    with pytest.raises(ExplanationAgentValidationError, match="committed evidence"):
        run_explanation_agent(_invocation(state), DraftBackend(invented))
