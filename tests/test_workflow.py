from datetime import UTC, datetime

import pytest

from creditpilot.state import (
    StateUpdateProposal,
    StateUpdateRejected,
    WorkflowControlConfig,
    WorkflowController,
    create_credit_state,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state():
    return create_credit_state(
        application_id="SYN-0000003",
        customer_token="customer-token-003",
        reported_values={"annual_income": 120_000},
        sanitized_attributes={},
        source_reference="synthetic-application-3",
        now=NOW,
    )


def _controller() -> WorkflowController:
    # Test-only values demonstrate configuration; they are not lending policy.
    return WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset(
                {(None, "validated"), ("validated", "modelled")}
            ),
            max_investigation_iterations=2,
            max_tool_calls=3,
            max_retries=2,
        )
    )


def test_orchestrator_can_propose_but_not_change_protected_workflow_fields() -> None:
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="next-action-1",
        target_domain="workflow_state.proposed_next_action",
        proposed_changes={
            "proposed_next_action": "run_model",
            "current_stage": "modelled",
        },
        basis_references=("validation-result-1",),
        proposed_by="orchestrator_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )

    with pytest.raises(StateUpdateRejected, match="protected fields"):
        _controller().commit_orchestrator_action(state, proposal)


def test_workflow_controller_enforces_configured_transition() -> None:
    controller = _controller()
    state = _state()
    proposal = StateUpdateProposal(
        proposal_id="next-action-1",
        target_domain="workflow_state.proposed_next_action",
        proposed_changes={"proposed_next_action": "validate"},
        basis_references=(),
        proposed_by="orchestrator_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )
    state = controller.commit_orchestrator_action(state, proposal)
    state = controller.transition(
        state,
        to_stage="validated",
        reason="Synthetic validation completed",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )

    assert state.workflow_state.current_stage == "validated"
    assert state.workflow_state.proposed_next_action is None
    assert state.workflow_state.last_transition is not None
    assert state.workflow_state.last_transition.permitted is True


def test_unconfigured_transition_and_unauthorized_writer_are_rejected() -> None:
    state = _state()

    with pytest.raises(StateUpdateRejected, match="not permitted"):
        _controller().transition(
            state,
            to_stage="decision",
            reason="Not configured",
            written_by="workflow_controller",
            expected_state_version=state.state_metadata.state_version,
        )
    with pytest.raises(StateUpdateRejected, match="only the Workflow Controller"):
        _controller().transition(
            state,
            to_stage="validated",
            reason="Agent cannot enforce this",
            written_by="orchestrator_agent",
            expected_state_version=state.state_metadata.state_version,
        )


def test_reaching_configured_limit_requires_human_review() -> None:
    controller = _controller()
    state = _state()
    state = controller.increment_counter(
        state,
        counter="investigation_iteration_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    assert state.workflow_state.mandatory_human_review is False

    state = controller.increment_counter(
        state,
        counter="investigation_iteration_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )

    assert state.workflow_state.mandatory_human_review is True
    assert state.workflow_state.mandatory_review_reasons == (
        "investigation_iteration_count limit reached",
    )
    with pytest.raises(StateUpdateRejected, match="limit already reached"):
        controller.increment_counter(
            state,
            counter="investigation_iteration_count",
            written_by="workflow_controller",
            expected_state_version=state.state_metadata.state_version,
        )


def test_mandatory_review_cannot_be_set_by_agent() -> None:
    state = _state()

    with pytest.raises(StateUpdateRejected, match="only the Workflow Controller"):
        _controller().require_human_review(
            state,
            reason="Synthetic unresolved evidence",
            written_by="orchestrator_agent",
            expected_state_version=state.state_metadata.state_version,
        )
