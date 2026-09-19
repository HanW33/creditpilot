"""Reference-only CreditState linkage for sanitized agent audit records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any

from creditpilot.agents.contracts import AgentAuditRecord, AgentFailure, AgentInvocation
from creditpilot.agents.orchestrator_agent import OrchestratorOutput
from creditpilot.agents.policy_agent import PolicyAgentOutput
from creditpilot.agents.verification_agent import VerificationAgentOutput
from creditpilot.state import ProtectedStateController
from creditpilot.state.schemas import CreditState, utc_now


def _to_audit_value(value: Any) -> Any:
    """Convert frozen dataclass values without deepcopying mapping proxies."""

    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _to_audit_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {key: _to_audit_value(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return tuple(_to_audit_value(child) for child in value)
    return value


def record_orchestrator_agent_audit(
    state: CreditState,
    invocation: AgentInvocation,
    controller: ProtectedStateController,
    *,
    output: OrchestratorOutput | None = None,
    validation_error: str | None = None,
) -> tuple[CreditState, AgentAuditRecord]:
    """Persist a sanitized reference-only Orchestrator audit record."""

    if invocation.agent_role != "orchestrator_agent":
        raise ValueError("audit invocation is not for the Orchestrator")
    if (output is None) == (validation_error is None):
        raise ValueError("provide exactly one output or validation_error")
    if output is not None and output.invocation_id != invocation.invocation_id:
        raise ValueError("agent output does not match invocation")
    audit_reference = f"agent-output://{invocation.invocation_id}"
    committed = controller.append_audit_reference(
        state,
        category="agent_output_references",
        reference=audit_reference,
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    if output is not None:
        structured_output = _to_audit_value(output)
        evidence_references = output.evidence_references
        status = output.status
        actions = output.proposed_actions
        failure = output.failure
        validation_result = "accepted"
    else:
        structured_output = {}
        evidence_references = ()
        status = "rejected"
        actions = ()
        failure = AgentFailure(
            code="invalid_structured_output",
            message=validation_error or "Orchestrator output rejected",
        )
        validation_result = "rejected"
    record = AgentAuditRecord(
        audit_reference=audit_reference,
        invocation_id=invocation.invocation_id,
        agent_role=invocation.agent_role,
        application_id=invocation.application_id,
        case_id=invocation.case_id,
        purpose=invocation.purpose,
        input_state_version=invocation.input_state_version,
        authorized_context_reference=(
            f"agent-context://{invocation.invocation_id}/"
            f"state/{invocation.input_state_version}"
        ),
        authorized_context_keys=tuple(
            sorted(invocation.authorized_state_view.data)
        ),
        permitted_tools=invocation.permitted_tools,
        status=status,
        evidence_references=evidence_references,
        structured_output=structured_output,
        proposed_actions=actions,
        validation_result=validation_result,
        failure=failure,
        created_at=utc_now(),
        resulting_state_version=committed.state_metadata.state_version,
    )
    return committed, record


def record_policy_agent_audit(
    state: CreditState,
    invocation: AgentInvocation,
    controller: ProtectedStateController,
    *,
    output: PolicyAgentOutput | None = None,
    validation_error: str | None = None,
) -> tuple[CreditState, AgentAuditRecord]:
    """Record accepted/failure output or a sanitized validation rejection."""

    if invocation.agent_role != "policy_agent":
        raise ValueError("audit invocation is not for the Policy Agent")
    if (output is None) == (validation_error is None):
        raise ValueError("provide exactly one output or validation_error")
    if output is not None and output.invocation_id != invocation.invocation_id:
        raise ValueError("agent output does not match invocation")

    audit_reference = f"agent-output://{invocation.invocation_id}"
    committed = controller.append_audit_reference(
        state,
        category="agent_output_references",
        reference=audit_reference,
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    if output is not None:
        structured_output = _to_audit_value(output)
        evidence_references = output.source_references
        status = output.status
        actions = output.proposed_actions
        failure = output.failure
        validation_result = "accepted"
    else:
        structured_output = {}
        evidence_references = ()
        status = "rejected"
        actions = ()
        failure = AgentFailure(
            code="invalid_structured_output",
            message=validation_error or "Policy Agent output rejected",
        )
        validation_result = "rejected"
    record = AgentAuditRecord(
        audit_reference=audit_reference,
        invocation_id=invocation.invocation_id,
        agent_role=invocation.agent_role,
        application_id=invocation.application_id,
        case_id=invocation.case_id,
        purpose=invocation.purpose,
        input_state_version=invocation.input_state_version,
        authorized_context_reference=(
            f"agent-context://{invocation.invocation_id}/"
            f"state/{invocation.input_state_version}"
        ),
        authorized_context_keys=tuple(
            sorted(invocation.authorized_state_view.data)
        ),
        permitted_tools=invocation.permitted_tools,
        status=status,
        evidence_references=evidence_references,
        structured_output=structured_output,
        proposed_actions=actions,
        validation_result=validation_result,
        failure=failure,
        created_at=utc_now(),
        resulting_state_version=committed.state_metadata.state_version,
    )
    return committed, record


def record_verification_agent_audit(
    state: CreditState,
    invocation: AgentInvocation,
    controller: ProtectedStateController,
    *,
    output: VerificationAgentOutput | None = None,
    validation_error: str | None = None,
) -> tuple[CreditState, AgentAuditRecord]:
    """Persist a sanitized audit record for Verification Agent output."""

    if invocation.agent_role != "verification_agent":
        raise ValueError("audit invocation is not for the Verification Agent")
    if (output is None) == (validation_error is None):
        raise ValueError("provide exactly one output or validation_error")
    if output is not None and output.invocation_id != invocation.invocation_id:
        raise ValueError("agent output does not match invocation")

    audit_reference = f"agent-output://{invocation.invocation_id}"
    committed = controller.append_audit_reference(
        state,
        category="agent_output_references",
        reference=audit_reference,
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    if output is not None:
        structured_output = _to_audit_value(output)
        evidence_references = output.tool_result_references
        status = output.status
        actions = output.proposed_actions
        failure = output.failure
        validation_result = "accepted"
    else:
        structured_output = {}
        evidence_references = ()
        status = "rejected"
        actions = ()
        failure = AgentFailure(
            code="invalid_structured_output",
            message=validation_error or "Verification Agent output rejected",
        )
        validation_result = "rejected"
    record = AgentAuditRecord(
        audit_reference=audit_reference,
        invocation_id=invocation.invocation_id,
        agent_role=invocation.agent_role,
        application_id=invocation.application_id,
        case_id=invocation.case_id,
        purpose=invocation.purpose,
        input_state_version=invocation.input_state_version,
        authorized_context_reference=(
            f"agent-context://{invocation.invocation_id}/"
            f"state/{invocation.input_state_version}"
        ),
        authorized_context_keys=tuple(
            sorted(invocation.authorized_state_view.data)
        ),
        permitted_tools=invocation.permitted_tools,
        status=status,
        evidence_references=evidence_references,
        structured_output=structured_output,
        proposed_actions=actions,
        validation_result=validation_result,
        failure=failure,
        created_at=utc_now(),
        resulting_state_version=committed.state_metadata.state_version,
    )
    return committed, record
