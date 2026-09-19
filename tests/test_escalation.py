from datetime import UTC, datetime

import pytest

from creditpilot.actions import MockActionProvider
from creditpilot.agents import (
    AgentInvocation,
    EscalationAgentValidationError,
    escalation_output_to_state_proposal,
    record_escalation_agent_audit,
    run_escalation_agent,
)
from creditpilot.state import (
    ProtectedStateController,
    WorkflowControlConfig,
    WorkflowController,
    build_role_state_view,
    create_credit_state,
)
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    create_review_case,
    record_action_tool_result,
    record_tool_audit,
    send_notification,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)


class DraftBackend:
    def __init__(self, draft):
        self.draft = draft

    def prepare_handoff(self, context):
        return self.draft


def _workflow():
    return WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "unused")}),
            max_investigation_iterations=2,
            max_tool_calls=4,
            max_retries=2,
        )
    )


def _state(mandatory=True):
    state = create_credit_state(
        application_id="SYN-0000013",
        customer_token="customer-token-013",
        reported_values={"annual_income": 98_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-13",
        now=NOW,
    )
    if mandatory:
        state = _workflow().require_human_review(
            state,
            reason="Synthetic manual review outcome",
            written_by="workflow_controller",
            expected_state_version=state.state_metadata.state_version,
        )
    return state


def _draft():
    return {
        "status": "prepared",
        "escalation_reason": "Mandatory human review requires analyst handoff.",
        "review_package": {
            "application_reference": "SYN-0000013",
            "summary": "Synthetic case requires authorized analyst review.",
        },
        "requested_actions": ["create_review_case", "send_notification"],
        "evidence_references": [],
        "unresolved_items": ["Authorized human outcome pending"],
        "action_result_references": [],
    }


def _agent_invocation(state):
    return AgentInvocation(
        invocation_id="escalation-agent-1",
        agent_role="escalation_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Prepare a sanitized mandatory-review handoff",
        authorized_state_view=build_role_state_view(state, "escalation_agent"),
        permitted_tools=frozenset(
            {"create_review_case", "send_notification"}
        ),
        workflow_constraints={"human_decision_remains_external": True},
        invoked_at=NOW,
    )


def _permissions():
    return ToolPermissionPolicy(
        callers_by_tool={
            "create_review_case": frozenset({"escalation_agent"}),
            "send_notification": frozenset({"escalation_agent"}),
        }
    )


def test_escalation_requires_committed_mandatory_human_review() -> None:
    state = _state(mandatory=False)

    with pytest.raises(EscalationAgentValidationError, match="mandatory human review"):
        run_escalation_agent(_agent_invocation(state), DraftBackend(_draft()))


def test_escalation_rejects_pii_and_premature_action_success_claims() -> None:
    state = _state()
    pii = _draft()
    pii["review_package"] = {"summary": "Contact analyst@example.com"}
    with pytest.raises(EscalationAgentValidationError, match="identity PII"):
        run_escalation_agent(_agent_invocation(state), DraftBackend(pii))

    claimed = _draft()
    claimed["action_result_references"] = ["review-case://invented/1"]
    with pytest.raises(EscalationAgentValidationError, match="cannot claim"):
        run_escalation_agent(_agent_invocation(state), DraftBackend(claimed))


def test_controlled_actions_are_preconditioned_audited_and_idempotent() -> None:
    controller = ProtectedStateController()
    provider = MockActionProvider()
    state = _state()
    agent_invocation = _agent_invocation(state)
    output = run_escalation_agent(agent_invocation, DraftBackend(_draft()))
    proposal = escalation_output_to_state_proposal(
        output, expected_state_version=state.state_metadata.state_version
    )
    state = controller.commit_escalation_package(state, proposal)
    state, agent_audit = record_escalation_agent_audit(
        state, agent_invocation, controller, output=output
    )

    case_invocation = ToolInvocation(
        invocation_id="create-review-case-1",
        tool_name="create_review_case",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="escalation_agent",
        purpose="Create the approved synthetic review case",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"action:create_review_case"}),
        arguments={
            "review_package_reference": output.review_package_reference,
            "escalation_reasons": (output.escalation_reason,),
        },
        requested_at=NOW,
        idempotency_key="review-case-key-1",
    )
    first = create_review_case(
        case_invocation, state, _permissions(), provider=provider
    )
    replay = create_review_case(
        case_invocation, state, _permissions(), provider=provider
    )
    assert first.result["action_reference"] == replay.result["action_reference"]
    assert replay.result["idempotency_outcome"] == "replayed"
    state = record_action_tool_result(state, first, controller)
    state, case_audit = record_tool_audit(
        state, case_invocation, first, controller
    )

    notification_invocation = ToolInvocation(
        invocation_id="send-notification-1",
        tool_name="send_notification",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="escalation_agent",
        purpose="Notify an approved synthetic analyst destination",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"action:send_notification"}),
        arguments={
            "review_package_reference": output.review_package_reference,
            "destination_reference": "destination://approved/credit-review-queue",
            "sanitized_message": "Synthetic review case is ready.",
        },
        requested_at=NOW,
        idempotency_key="notification-key-1",
    )
    notification = send_notification(
        notification_invocation, state, _permissions(), provider=provider
    )
    state = record_action_tool_result(state, notification, controller)
    state, notification_audit = record_tool_audit(
        state, notification_invocation, notification, controller
    )

    assert agent_audit.proposed_actions == (
        "create_review_case",
        "send_notification",
    )
    assert case_audit.status == "success"
    assert notification_audit.status == "success"
    assert len(state.escalation_state.action_results) == 2
    assert state.escalation_state.human_review_outcome_reference is None


def test_action_tool_rejects_missing_idempotency_key() -> None:
    controller = ProtectedStateController()
    state = _state()
    output = run_escalation_agent(_agent_invocation(state), DraftBackend(_draft()))
    state = controller.commit_escalation_package(
        state,
        escalation_output_to_state_proposal(
            output, expected_state_version=state.state_metadata.state_version
        ),
    )
    invocation = ToolInvocation(
        invocation_id="create-review-case-no-key",
        tool_name="create_review_case",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="escalation_agent",
        purpose="Attempt controlled review creation",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"action:create_review_case"}),
        arguments={
            "review_package_reference": output.review_package_reference,
            "escalation_reasons": (output.escalation_reason,),
        },
        requested_at=NOW,
    )

    result = create_review_case(
        invocation, state, _permissions(), provider=MockActionProvider()
    )

    assert result.status == "failure"
    assert result.failure.code == "idempotency_key_required"
