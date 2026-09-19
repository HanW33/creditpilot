from datetime import UTC, datetime

import pytest

from creditpilot.agents import (
    AgentInvocation,
    OrchestratorValidationError,
    orchestrator_output_to_verification_request,
    orchestrator_output_to_workflow_proposal,
    record_orchestrator_agent_audit,
    run_orchestrator_agent,
)
from creditpilot.state import (
    ProtectedStateController,
    WorkflowControlConfig,
    WorkflowController,
    build_role_state_view,
    create_credit_state,
)
from creditpilot.state.schemas import PolicyEvidence, StateUpdateProposal

NOW = datetime(2026, 9, 20, tzinfo=UTC)
POLICY_REFERENCE = "policy://synthetic-policy.md/income-evidence@v1"


class DraftBackend:
    def __init__(self, draft):
        self.draft = draft
        self.last_context = None

    def propose_next_action(self, context):
        self.last_context = context
        return self.draft


def _policy_state():
    controller = ProtectedStateController()
    state = create_credit_state(
        application_id="SYN-0000010",
        customer_token="customer-token-010",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-10",
        now=NOW,
    )
    state = controller.record_policy_evidence(
        state,
        PolicyEvidence(
            source_document="synthetic-policy.md",
            section_or_chunk_reference="income-evidence",
            policy_version="v1",
        ),
        written_by="policy_retrieval",
        expected_state_version=state.state_metadata.state_version,
    )
    proposal = StateUpdateProposal(
        proposal_id="policy-finding-1",
        target_domain="policy_state.findings",
        proposed_changes={
            "status": "complete",
            "findings": ("Verified income is required.",),
            "required_evidence": ("verified_income",),
        },
        basis_references=(POLICY_REFERENCE,),
        proposed_by="policy_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )
    return controller.commit_policy_findings(state, proposal)


def _invocation(state, permitted_tools=frozenset()):
    return AgentInvocation(
        invocation_id="orchestrator-agent-1",
        agent_role="orchestrator_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Propose the next bounded investigation step",
        authorized_state_view=build_role_state_view(state, "orchestrator_agent"),
        permitted_tools=permitted_tools,
        workflow_constraints={"limits_are_enforced_externally": True},
        invoked_at=NOW,
    )


def _draft(action="create_verification_request"):
    return {
        "proposed_next_action": action,
        "reason": "Required verified income is not committed.",
        "evidence_references": [POLICY_REFERENCE],
        "prerequisites": ["workflow authorization"],
        "unresolved_items": ["verified_income"],
        "status": "proposed",
    }


def test_orchestrator_proposes_request_but_deterministic_control_commits_it() -> None:
    state = _policy_state()
    output = run_orchestrator_agent(_invocation(state), DraftBackend(_draft()))
    request = orchestrator_output_to_verification_request(
        output,
        request_id="verification-request-7",
        evidence_required="verified_income",
        expected_state_version=state.state_metadata.state_version,
    )

    committed = ProtectedStateController().commit_verification_request(state, request)

    assert output.proposed_next_action == "create_verification_request"
    assert committed.verification_state.requests[0].status == "approved"
    assert committed.workflow_state.active_request_ids == ("verification-request-7",)


def test_workflow_controller_commits_only_the_proposed_action_field() -> None:
    state = _policy_state()
    output = run_orchestrator_agent(_invocation(state), DraftBackend(_draft()))
    proposal = orchestrator_output_to_workflow_proposal(
        output, expected_state_version=state.state_metadata.state_version
    )
    workflow = WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "verification_requested")}),
            max_investigation_iterations=2,
            max_tool_calls=2,
            max_retries=1,
        )
    )

    committed = workflow.commit_orchestrator_action(state, proposal)

    assert committed.workflow_state.proposed_next_action == (
        "create_verification_request"
    )
    assert committed.workflow_state.current_stage is None


def test_existing_approved_request_causes_wait_instead_of_duplicate_request() -> None:
    controller = ProtectedStateController()
    state = _policy_state()
    existing = StateUpdateProposal(
        proposal_id="existing-request-proposal",
        target_domain="verification_state.requests",
        proposed_changes={
            "request_id": "verification-request-existing",
            "evidence_required": "verified_income",
        },
        basis_references=(POLICY_REFERENCE,),
        proposed_by="orchestrator_agent",
        expected_state_version=state.state_metadata.state_version,
        proposed_at=NOW,
    )
    state = controller.commit_verification_request(state, existing)
    output = run_orchestrator_agent(
        _invocation(state), DraftBackend(_draft("await_verification"))
    )

    assert output.proposed_next_action == "await_verification"
    with pytest.raises(OrchestratorValidationError, match="does not authorize"):
        orchestrator_output_to_verification_request(
            output,
            request_id="verification-request-duplicate",
            evidence_required="verified_income",
            expected_state_version=state.state_metadata.state_version,
        )


def test_orchestrator_cannot_receive_verification_tools() -> None:
    state = _policy_state()

    with pytest.raises(OrchestratorValidationError, match="execution tools"):
        run_orchestrator_agent(
            _invocation(state, frozenset({"verify_income"})),
            DraftBackend(_draft()),
        )


def test_orchestrator_rejects_action_inconsistent_with_missing_evidence() -> None:
    state = _policy_state()
    draft = _draft("evaluate_decision_eligibility")

    with pytest.raises(OrchestratorValidationError, match="inconsistent"):
        run_orchestrator_agent(_invocation(state), DraftBackend(draft))


def test_orchestrator_rejects_recommendation_or_extra_fields() -> None:
    state = _policy_state()
    draft = {**_draft(), "recommendation": "APPROVE"}

    with pytest.raises(OrchestratorValidationError, match="fields are invalid"):
        run_orchestrator_agent(_invocation(state), DraftBackend(draft))


def test_orchestrator_reason_cannot_claim_final_decision_authority() -> None:
    state = _policy_state()
    draft = {**_draft(), "reason": "Approve the application now."}

    with pytest.raises(OrchestratorValidationError, match="recommendation authority"):
        run_orchestrator_agent(_invocation(state), DraftBackend(draft))


def test_orchestrator_audit_is_reference_only_in_credit_state() -> None:
    state = _policy_state()
    invocation = _invocation(state)
    output = run_orchestrator_agent(invocation, DraftBackend(_draft()))

    committed, record = record_orchestrator_agent_audit(
        state,
        invocation,
        ProtectedStateController(),
        output=output,
    )

    assert record.proposed_actions == ("create_verification_request",)
    assert committed.governance_audit_references.agent_output_references == (
        "agent-output://orchestrator-agent-1",
    )
