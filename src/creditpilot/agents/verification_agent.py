"""Bounded Verification Agent interpretation and proposal boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creditpilot.agents.contracts import AgentFailure, AgentInvocation
from creditpilot.state.schemas import (
    StateUpdateProposal,
    VerificationInterpretation,
    utc_now,
    validate_no_identity_pii,
)
from creditpilot.tools.contracts import ToolResult
from creditpilot.tools.verification_tools import TOOL_EVIDENCE_TYPES


class VerificationAgentValidationError(ValueError):
    """Raised when inputs cross the Verification Agent authority boundary."""


@dataclass(frozen=True, slots=True)
class VerificationAgentOutput:
    invocation_id: str
    agent_role: str
    status: str
    selected_tool: str
    selection_reason: str
    tool_result_references: tuple[str, ...]
    interpretation: VerificationInterpretation | None
    proposed_actions: tuple[str, ...]
    created_at: datetime
    failure: AgentFailure | None = None


def run_verification_agent(
    invocation: AgentInvocation,
    tool_result: ToolResult,
    *,
    request_id: str,
) -> VerificationAgentOutput:
    """Interpret tool facts for one already-approved committed request."""

    if invocation.agent_role != "verification_agent":
        raise VerificationAgentValidationError(
            "invocation is not for the Verification Agent"
        )
    if invocation.permitted_tools - set(TOOL_EVIDENCE_TYPES):
        raise VerificationAgentValidationError(
            "Verification Agent has an unapproved tool"
        )
    view = invocation.authorized_state_view.data
    requests = view.get("verification_state", {}).get("requests", ())
    request = next(
        (
            item
            for item in requests
            if item.request_id == request_id and item.status == "approved"
        ),
        None,
    )
    if request is None or request_id not in view.get("active_request_ids", ()):
        raise VerificationAgentValidationError(
            "Verification Agent requires an active approved request"
        )
    expected_tool = next(
        (
            tool
            for tool, evidence in TOOL_EVIDENCE_TYPES.items()
            if evidence == request.evidence_required
        ),
        None,
    )
    if expected_tool is None or expected_tool not in invocation.permitted_tools:
        raise VerificationAgentValidationError(
            "no permitted tool supports the requested evidence"
        )
    if tool_result.tool_name != expected_tool:
        raise VerificationAgentValidationError("tool result does not match the request")
    if tool_result.status != "success":
        return VerificationAgentOutput(
            invocation_id=invocation.invocation_id,
            agent_role="verification_agent",
            status="failure",
            selected_tool=expected_tool,
            selection_reason=(
                "The approved request maps to this verification capability."
            ),
            tool_result_references=(),
            interpretation=None,
            proposed_actions=(),
            created_at=utc_now(),
            failure=AgentFailure(
                code="verification_tool_failed",
                message="Approved verification evidence was not returned.",
            ),
        )
    if tool_result.result.get("request_id") != request_id:
        raise VerificationAgentValidationError("tool result request is inconsistent")
    if tool_result.result.get("evidence_type") != request.evidence_required:
        raise VerificationAgentValidationError("tool evidence type is inconsistent")
    raw_evidence = tool_result.result.get("raw_evidence")
    if not isinstance(raw_evidence, dict) and not hasattr(raw_evidence, "items"):
        raise VerificationAgentValidationError("tool evidence is malformed")
    if set(raw_evidence) != {request.evidence_required}:
        raise VerificationAgentValidationError("tool evidence fields are invalid")
    proposed_update = {
        request.evidence_required: raw_evidence[request.evidence_required]
    }
    validate_no_identity_pii(proposed_update, "verification_agent_proposal")
    result_reference = tool_result.result.get("raw_evidence_reference")
    if not isinstance(result_reference, str) or (
        result_reference not in tool_result.evidence_references
    ):
        raise VerificationAgentValidationError("tool evidence lacks provenance")
    interpretation = VerificationInterpretation(
        interpretation_id=f"interpretation-{invocation.invocation_id}",
        result_id=tool_result.invocation_id,
        structured_evidence=proposed_update,
        proposed_state_update=proposed_update,
        created_at=utc_now(),
    )
    return VerificationAgentOutput(
        invocation_id=invocation.invocation_id,
        agent_role="verification_agent",
        status="complete",
        selected_tool=expected_tool,
        selection_reason="The approved request maps to this verification capability.",
        tool_result_references=(tool_result.invocation_id, result_reference),
        interpretation=interpretation,
        proposed_actions=(),
        created_at=utc_now(),
    )


def verification_output_to_state_proposal(
    output: VerificationAgentOutput, *, expected_state_version: int
) -> StateUpdateProposal:
    if output.failure is not None or output.interpretation is None:
        raise VerificationAgentValidationError(
            "failed Verification Agent output cannot be proposed"
        )
    return StateUpdateProposal(
        proposal_id=f"proposal-{output.interpretation.interpretation_id}",
        target_domain="verification_state.verified_values",
        proposed_changes=output.interpretation.proposed_state_update,
        basis_references=(output.interpretation.result_id,),
        proposed_by="verification_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )
