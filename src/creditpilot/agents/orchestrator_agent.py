"""Provider-independent Orchestrator Agent with deterministic boundary checks."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol

from creditpilot.agents.contracts import AgentFailure, AgentInvocation
from creditpilot.state.schemas import StateUpdateProposal, utc_now

ORCHESTRATOR_OUTPUT_FIELDS = frozenset(
    {
        "proposed_next_action",
        "reason",
        "evidence_references",
        "prerequisites",
        "unresolved_items",
        "status",
    }
)
APPROVED_ORCHESTRATOR_ACTIONS = frozenset(
    {
        "create_verification_request",
        "await_verification",
        "reevaluate_case",
        "evaluate_decision_eligibility",
        "generate_explanation",
        "prepare_escalation",
    }
)
AUTHORITY_PATTERN = re.compile(
    r"\b(?:approve|decline|reject)\s+(?:the\s+)?application\b", re.IGNORECASE
)
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


class OrchestratorValidationError(ValueError):
    """Raised when untrusted output violates Orchestrator authority."""


@dataclass(frozen=True, slots=True)
class OrchestratorContext:
    state_version: int
    authorized_state: Mapping[str, Any]
    required_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    active_request_evidence: tuple[str, ...]
    known_evidence_references: tuple[str, ...]


class OrchestratorReasoningBackend(Protocol):
    def propose_next_action(
        self, context: OrchestratorContext
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OrchestratorOutput:
    invocation_id: str
    agent_role: str
    proposed_next_action: str | None
    reason: str
    evidence_references: tuple[str, ...]
    prerequisites: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    status: str
    created_at: datetime
    failure: AgentFailure | None = None

    @property
    def proposed_actions(self) -> tuple[str, ...]:
        if self.proposed_next_action is None:
            return ()
        return (self.proposed_next_action,)


def _text_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise OrchestratorValidationError(
            f"{field} must be a sequence of non-empty text"
        )
    return tuple(item.strip() for item in value)


def _build_context(invocation: AgentInvocation) -> OrchestratorContext:
    view = invocation.authorized_state_view.data
    policy = view.get("policy_state")
    verification = view.get("verification_state")
    if policy is None or not isinstance(verification, Mapping):
        raise OrchestratorValidationError("Orchestrator context is incomplete")
    required = tuple(policy.required_evidence)
    verified = set(verification.get("verified_values", {}))
    missing = tuple(item for item in required if item not in verified)
    requests = verification.get("requests", ())
    active_ids = set(view.get("workflow_state").active_request_ids)
    active_evidence = tuple(
        item.evidence_required
        for item in requests
        if item.status == "approved" and item.request_id in active_ids
    )
    references = {item.section_or_chunk_reference for item in policy.retrieved_evidence}
    references.update(
        f"policy://{item.source_document}/"
        f"{item.section_or_chunk_reference}@{item.policy_version}"
        for item in policy.retrieved_evidence
    )
    references.update(
        str(item["result_id"])
        for item in verification.get("tool_result_statuses", ())
    )
    return OrchestratorContext(
        state_version=invocation.input_state_version,
        authorized_state=view,
        required_evidence=required,
        missing_evidence=missing,
        active_request_evidence=active_evidence,
        known_evidence_references=tuple(sorted(references)),
    )


def _expected_actions(context: OrchestratorContext) -> frozenset[str]:
    workflow = context.authorized_state["workflow_state"]
    policy = context.authorized_state["policy_state"]
    if workflow.mandatory_human_review:
        return frozenset({"prepare_escalation"})
    if policy.conflicts or policy.failure is not None:
        return frozenset({"prepare_escalation"})
    if context.missing_evidence:
        if set(context.missing_evidence) & set(context.active_request_evidence):
            return frozenset({"await_verification"})
        return frozenset({"create_verification_request"})
    recommendation = context.authorized_state.get("recommendation_state")
    if recommendation is not None and recommendation.recommendation:
        return frozenset({"generate_explanation"})
    model = context.authorized_state["quantitative_model_state"]
    verification = context.authorized_state["verification_state"]
    if verification.get("verified_values") and (
        model.input_state_version is None
        or model.input_state_version < context.state_version
    ):
        return frozenset({"reevaluate_case"})
    return frozenset({"evaluate_decision_eligibility"})


def _validate_draft(
    draft: Mapping[str, Any], context: OrchestratorContext
) -> OrchestratorOutput:
    if set(draft) != ORCHESTRATOR_OUTPUT_FIELDS:
        raise OrchestratorValidationError("Orchestrator output fields are invalid")
    action = draft["proposed_next_action"]
    reason = draft["reason"]
    status = draft["status"]
    if action not in APPROVED_ORCHESTRATOR_ACTIONS:
        raise OrchestratorValidationError("Orchestrator action is not approved")
    if action not in _expected_actions(context):
        raise OrchestratorValidationError(
            "Orchestrator action is inconsistent with committed state"
        )
    if not isinstance(reason, str) or not reason.strip():
        raise OrchestratorValidationError("Orchestrator reason is required")
    if status != "proposed":
        raise OrchestratorValidationError("Orchestrator status must be proposed")
    references = _text_tuple(draft["evidence_references"], "evidence_references")
    prerequisites = _text_tuple(draft["prerequisites"], "prerequisites")
    unresolved = _text_tuple(draft["unresolved_items"], "unresolved_items")
    narrative = (reason, *prerequisites, *unresolved)
    if any(AUTHORITY_PATTERN.search(item) for item in narrative):
        raise OrchestratorValidationError(
            "Orchestrator output exceeds recommendation authority"
        )
    if any(EMAIL_PATTERN.search(item) for item in narrative):
        raise OrchestratorValidationError("Orchestrator output contains identity PII")
    if references and not set(references).issubset(context.known_evidence_references):
        raise OrchestratorValidationError("Orchestrator cites unknown evidence")
    if context.known_evidence_references and not references:
        raise OrchestratorValidationError("Orchestrator action requires evidence")
    if action in {"create_verification_request", "await_verification"} and not set(
        context.missing_evidence
    ).issubset(unresolved):
        raise OrchestratorValidationError("missing evidence must remain unresolved")
    return OrchestratorOutput(
        invocation_id="",
        agent_role="orchestrator_agent",
        proposed_next_action=action,
        reason=reason.strip(),
        evidence_references=references,
        prerequisites=prerequisites,
        unresolved_items=unresolved,
        status=status,
        created_at=utc_now(),
    )


def run_orchestrator_agent(
    invocation: AgentInvocation, backend: OrchestratorReasoningBackend
) -> OrchestratorOutput:
    """Generate and deterministically validate one bounded next-step proposal."""

    if invocation.agent_role != "orchestrator_agent":
        raise OrchestratorValidationError("invocation is not for the Orchestrator")
    if invocation.permitted_tools:
        raise OrchestratorValidationError(
            "Orchestrator must not receive execution tools"
        )
    context = _build_context(invocation)
    try:
        draft = backend.propose_next_action(context)
        if not isinstance(draft, Mapping):
            raise OrchestratorValidationError(
                "Orchestrator backend output must be a mapping"
            )
        output = _validate_draft(draft, context)
    except OrchestratorValidationError:
        raise
    except Exception as error:
        return OrchestratorOutput(
            invocation_id=invocation.invocation_id,
            agent_role="orchestrator_agent",
            proposed_next_action=None,
            reason="Orchestrator reasoning did not produce a valid proposal.",
            evidence_references=(),
            prerequisites=(),
            unresolved_items=("Orchestrator backend failure",),
            status="failure",
            created_at=utc_now(),
            failure=AgentFailure(
                code="orchestrator_backend_failed",
                message=f"Orchestrator backend failed: {type(error).__name__}",
            ),
        )
    return replace(output, invocation_id=invocation.invocation_id)


def orchestrator_output_to_workflow_proposal(
    output: OrchestratorOutput, *, expected_state_version: int
) -> StateUpdateProposal:
    if output.failure is not None or output.proposed_next_action is None:
        raise OrchestratorValidationError("failed output cannot be proposed")
    return StateUpdateProposal(
        proposal_id=f"workflow-{output.invocation_id}",
        target_domain="workflow_state.proposed_next_action",
        proposed_changes={"proposed_next_action": output.proposed_next_action},
        basis_references=output.evidence_references,
        proposed_by="orchestrator_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )


def orchestrator_output_to_verification_request(
    output: OrchestratorOutput,
    *,
    request_id: str,
    evidence_required: str,
    expected_state_version: int,
) -> StateUpdateProposal:
    if output.failure is not None or (
        output.proposed_next_action != "create_verification_request"
    ):
        raise OrchestratorValidationError(
            "output does not authorize a verification request proposal"
        )
    if not request_id or evidence_required not in output.unresolved_items:
        raise OrchestratorValidationError(
            "request must target unresolved policy-required evidence"
        )
    return StateUpdateProposal(
        proposal_id=f"request-{output.invocation_id}",
        target_domain="verification_state.requests",
        proposed_changes={
            "request_id": request_id,
            "evidence_required": evidence_required,
        },
        basis_references=output.evidence_references,
        proposed_by="orchestrator_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )
