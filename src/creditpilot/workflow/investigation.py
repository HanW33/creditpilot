"""Bounded integration of policy, orchestration, and verification components."""

from __future__ import annotations

from dataclasses import dataclass

from creditpilot.agents import (
    AgentInvocation,
    OrchestratorOutput,
    OrchestratorReasoningBackend,
    PolicyReasoningBackend,
    orchestrator_output_to_verification_request,
    orchestrator_output_to_workflow_proposal,
    policy_output_to_state_proposal,
    record_orchestrator_agent_audit,
    record_policy_agent_audit,
    record_verification_agent_audit,
    run_orchestrator_agent,
    run_policy_agent,
    run_verification_agent,
    verification_output_to_state_proposal,
)
from creditpilot.policy import PolicyIndex
from creditpilot.state import (
    CreditState,
    ProtectedStateController,
    WorkflowController,
    build_role_state_view,
)
from creditpilot.state.schemas import utc_now
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    commit_policy_retrieval_result,
    get_credit_report,
    record_tool_audit,
    record_verification_tool_result,
    search_credit_policy,
    verify_employment,
    verify_income,
)
from creditpilot.tools.verification_tools import VerificationEvidenceProvider

VERIFICATION_TOOLS = {
    "verified_income": ("verify_income", verify_income),
    "verified_employment": ("verify_employment", verify_employment),
    "credit_report": ("get_credit_report", get_credit_report),
}


@dataclass(frozen=True, slots=True)
class InvestigationCycleIds:
    policy_tool_invocation_id: str
    policy_agent_invocation_id: str
    orchestrator_invocation_id: str
    verification_request_id: str
    verification_tool_invocation_id: str
    verification_agent_invocation_id: str
    follow_up_orchestrator_invocation_id: str


@dataclass(frozen=True, slots=True)
class InvestigationCycleResult:
    state: CreditState
    status: str
    completed_steps: tuple[str, ...]
    next_action: str
    audit_references: tuple[str, ...]


def _audit_references(state: CreditState) -> tuple[str, ...]:
    audit = state.governance_audit_references
    return (*audit.agent_output_references, *audit.tool_call_references)


def _record_tool_failure(
    state: CreditState,
    invocation: ToolInvocation,
    result,
    *,
    state_controller: ProtectedStateController,
    workflow_controller: WorkflowController,
) -> CreditState:
    state, _ = record_tool_audit(
        state, invocation, result, state_controller
    )
    return workflow_controller.increment_counter(
        state,
        counter="retry_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )


def _agent_invocation(
    state: CreditState,
    *,
    invocation_id: str,
    role: str,
    purpose: str,
    permitted_tools: frozenset[str],
) -> AgentInvocation:
    return AgentInvocation(
        invocation_id=invocation_id,
        agent_role=role,
        application_id=state.identity_references.application_id,
        case_id=state.identity_references.case_id,
        input_state_version=state.state_metadata.state_version,
        purpose=purpose,
        authorized_state_view=build_role_state_view(state, role),
        permitted_tools=permitted_tools,
        workflow_constraints={"enforced_by": "workflow_controller"},
        invoked_at=utc_now(),
    )


def _run_orchestrator_step(
    state: CreditState,
    *,
    invocation_id: str,
    backend: OrchestratorReasoningBackend,
    state_controller: ProtectedStateController,
    workflow_controller: WorkflowController,
) -> tuple[CreditState, OrchestratorOutput]:
    invocation = _agent_invocation(
        state,
        invocation_id=invocation_id,
        role="orchestrator_agent",
        purpose="Propose the next bounded investigation step",
        permitted_tools=frozenset(),
    )
    output = run_orchestrator_agent(invocation, backend)
    proposal = orchestrator_output_to_workflow_proposal(
        output, expected_state_version=state.state_metadata.state_version
    )
    state = workflow_controller.commit_orchestrator_action(state, proposal)
    state, _ = record_orchestrator_agent_audit(
        state, invocation, state_controller, output=output
    )
    return state, output


def run_policy_verification_cycle(
    state: CreditState,
    *,
    ids: InvestigationCycleIds,
    policy_index: PolicyIndex,
    policy_backend: PolicyReasoningBackend,
    orchestrator_backend: OrchestratorReasoningBackend,
    verification_provider: VerificationEvidenceProvider,
    tool_permissions: ToolPermissionPolicy,
    state_controller: ProtectedStateController,
    workflow_controller: WorkflowController,
    policy_question: str,
    requested_evidence: str,
    supported_evidence_types: frozenset[str],
) -> InvestigationCycleResult:
    """Run one explicit policy-to-verification cycle and stop before model rerun."""

    completed: list[str] = []
    state = workflow_controller.increment_counter(
        state,
        counter="tool_call_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    policy_tool = ToolInvocation(
        invocation_id=ids.policy_tool_invocation_id,
        tool_name="search_credit_policy",
        application_id=state.identity_references.application_id,
        case_id=state.identity_references.case_id,
        requested_by="policy_retrieval",
        purpose="Retrieve synthetic policy for the current evidence question",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"policy:search"}),
        arguments={
            "policy_question": policy_question,
            "requested_evidence": requested_evidence,
            "sanitized_context": {"evidence_status": "missing"},
            "top_k": 2,
            "required_policy_versions": (),
        },
        requested_at=utc_now(),
    )
    retrieval = search_credit_policy(
        policy_tool, state, tool_permissions, index=policy_index
    )
    if retrieval.status != "success":
        state = _record_tool_failure(
            state,
            policy_tool,
            retrieval,
            state_controller=state_controller,
            workflow_controller=workflow_controller,
        )
        return InvestigationCycleResult(
            state=state,
            status="failure",
            completed_steps=tuple(completed),
            next_action=(
                "prepare_escalation"
                if state.workflow_state.mandatory_human_review
                else "retry"
            ),
            audit_references=_audit_references(state),
        )
    state = commit_policy_retrieval_result(state, retrieval, state_controller)
    state, _ = record_tool_audit(
        state, policy_tool, retrieval, state_controller
    )
    completed.append("policy_retrieval")

    policy_invocation = _agent_invocation(
        state,
        invocation_id=ids.policy_agent_invocation_id,
        role="policy_agent",
        purpose="Interpret retrieved synthetic policy evidence",
        permitted_tools=frozenset({"search_credit_policy"}),
    )
    policy_output = run_policy_agent(
        policy_invocation,
        retrieval,
        policy_backend,
        supported_evidence_types=supported_evidence_types,
    )
    policy_proposal = policy_output_to_state_proposal(
        policy_output, expected_state_version=state.state_metadata.state_version
    )
    state = state_controller.commit_policy_findings(state, policy_proposal)
    state, _ = record_policy_agent_audit(
        state, policy_invocation, state_controller, output=policy_output
    )
    completed.append("policy_interpretation")

    state = workflow_controller.increment_counter(
        state,
        counter="investigation_iteration_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    state, orchestrator_output = _run_orchestrator_step(
        state,
        invocation_id=ids.orchestrator_invocation_id,
        backend=orchestrator_backend,
        state_controller=state_controller,
        workflow_controller=workflow_controller,
    )
    next_action = orchestrator_output.proposed_next_action or ""
    completed.append("orchestrator_evaluation")
    if next_action != "create_verification_request":
        return InvestigationCycleResult(
            state=state,
            status="stopped",
            completed_steps=tuple(completed),
            next_action=next_action,
            audit_references=_audit_references(state),
        )

    missing = tuple(
        item
        for item in state.policy_state.required_evidence
        if item not in state.verification_state.verified_values
    )
    if not missing or missing[0] not in VERIFICATION_TOOLS:
        return InvestigationCycleResult(
            state=state,
            status="stopped",
            completed_steps=tuple(completed),
            next_action=next_action,
            audit_references=_audit_references(state),
        )
    evidence_required = missing[0]
    request = orchestrator_output_to_verification_request(
        orchestrator_output,
        request_id=ids.verification_request_id,
        evidence_required=evidence_required,
        expected_state_version=state.state_metadata.state_version,
    )
    state = state_controller.commit_verification_request(state, request)
    completed.append("verification_request_commit")

    tool_name, tool = VERIFICATION_TOOLS[evidence_required]
    state = workflow_controller.increment_counter(
        state,
        counter="tool_call_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    verification_tool = ToolInvocation(
        invocation_id=ids.verification_tool_invocation_id,
        tool_name=tool_name,
        application_id=state.identity_references.application_id,
        case_id=state.identity_references.case_id,
        requested_by="verification_agent",
        purpose="Obtain evidence for the approved verification request",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"verification:read"}),
        arguments={"request_id": ids.verification_request_id},
        requested_at=utc_now(),
    )
    tool_result = tool(
        verification_tool,
        state,
        tool_permissions,
        provider=verification_provider,
    )
    if tool_result.status != "success":
        state = _record_tool_failure(
            state,
            verification_tool,
            tool_result,
            state_controller=state_controller,
            workflow_controller=workflow_controller,
        )
        return InvestigationCycleResult(
            state=state,
            status="failure",
            completed_steps=tuple(completed),
            next_action=(
                "prepare_escalation"
                if state.workflow_state.mandatory_human_review
                else "retry"
            ),
            audit_references=_audit_references(state),
        )
    state = record_verification_tool_result(state, tool_result, state_controller)
    state, _ = record_tool_audit(
        state, verification_tool, tool_result, state_controller
    )
    completed.append("verification_tool")

    verification_invocation = _agent_invocation(
        state,
        invocation_id=ids.verification_agent_invocation_id,
        role="verification_agent",
        purpose="Interpret evidence for the approved verification request",
        permitted_tools=frozenset({tool_name}),
    )
    verification_output = run_verification_agent(
        verification_invocation,
        tool_result,
        request_id=ids.verification_request_id,
    )
    verified_proposal = verification_output_to_state_proposal(
        verification_output,
        expected_state_version=state.state_metadata.state_version,
    )
    state = state_controller.commit_verified_values(
        state, verified_proposal, verification_output.interpretation
    )
    state, _ = record_verification_agent_audit(
        state,
        verification_invocation,
        state_controller,
        output=verification_output,
    )
    completed.append("verified_evidence_commit")

    state = workflow_controller.increment_counter(
        state,
        counter="investigation_iteration_count",
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    state, follow_up_output = _run_orchestrator_step(
        state,
        invocation_id=ids.follow_up_orchestrator_invocation_id,
        backend=orchestrator_backend,
        state_controller=state_controller,
        workflow_controller=workflow_controller,
    )
    next_action = follow_up_output.proposed_next_action or ""
    completed.append("follow_up_orchestrator_evaluation")
    return InvestigationCycleResult(
        state=state,
        status="complete",
        completed_steps=tuple(completed),
        next_action=next_action,
        audit_references=_audit_references(state),
    )
