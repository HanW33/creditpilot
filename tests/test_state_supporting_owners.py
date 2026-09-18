from datetime import UTC, datetime

import pytest

from creditpilot.state import (
    ProtectedStateController,
    StateUpdateProposal,
    StateUpdateRejected,
    WorkflowControlConfig,
    WorkflowController,
    create_credit_state,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000005",
        customer_token="customer-token-005",
        reported_values={"annual_income": 75_000},
        sanitized_attributes={},
        source_reference="synthetic-application-5",
        now=NOW,
    )


def test_explanation_agent_cannot_modify_decision_evidence() -> None:
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="explanation-1",
        target_domain="explanation_state",
        proposed_changes={
            "explanation": "Synthetic explanation",
            "recommendation": "APPROVE",
        },
        basis_references=("model-run-1",),
        proposed_by="explanation_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="protected fields"):
        ProtectedStateController().commit_explanation(state, proposal)


def test_traceable_explanation_commits_against_current_state() -> None:
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="explanation-1",
        target_domain="explanation_state",
        proposed_changes={"explanation": "Synthetic evidence-based explanation"},
        basis_references=("model-run-1", "policy-finding-1"),
        proposed_by="explanation_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    committed = ProtectedStateController().commit_explanation(state, proposal)

    assert committed.explanation_state.input_state_version == 1
    assert committed.explanation_state.created_by == "explanation_agent"


def test_escalation_requires_mandatory_human_review() -> None:
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="escalation-1",
        target_domain="escalation_state",
        proposed_changes={
            "reasons": ("Synthetic unresolved evidence",),
            "review_package_reference": "review-package://case-5",
        },
        basis_references=("workflow-event-1",),
        proposed_by="escalation_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="mandatory human review"):
        ProtectedStateController().commit_escalation_package(state, proposal)


def test_escalation_agent_prepares_but_does_not_decide_human_outcome() -> None:
    state = _state()
    workflow = WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "synthetic-stage")}),
            max_investigation_iterations=2,
            max_tool_calls=2,
            max_retries=2,
        )
    )
    state = workflow.require_human_review(
        state,
        reason="Synthetic unresolved evidence",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    proposal = StateUpdateProposal(
        proposal_id="escalation-1",
        target_domain="escalation_state",
        proposed_changes={
            "status": "prepared",
            "reasons": ("Synthetic unresolved evidence",),
            "review_package_reference": "review-package://case-5",
        },
        basis_references=("workflow-event-1",),
        proposed_by="escalation_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    committed = ProtectedStateController().commit_escalation_package(state, proposal)

    assert committed.escalation_state.review_package_reference == (
        "review-package://case-5"
    )
    assert committed.escalation_state.human_review_outcome_reference is None


def test_pii_audit_reference_requires_separate_writer() -> None:
    state = _state()

    with pytest.raises(StateUpdateRejected, match="pii_audit"):
        ProtectedStateController().append_audit_reference(
            state,
            category="pii_audit_references",
            reference="pii-audit://event-1",
            written_by="audit_persistence",
            expected_state_version=state.state_metadata.state_version,
        )


def test_controlled_audit_reference_is_append_only() -> None:
    state = _state()
    controller = ProtectedStateController()
    state = controller.append_audit_reference(
        state,
        category="model_run_references",
        reference="model-run://1",
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    state = controller.append_audit_reference(
        state,
        category="model_run_references",
        reference="model-run://2",
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )

    assert state.governance_audit_references.model_run_references == (
        "model-run://1",
        "model-run://2",
    )
