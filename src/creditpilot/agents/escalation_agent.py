"""Provider-independent Escalation Agent with sanitized handoff validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from creditpilot.agents.contracts import AgentFailure, AgentInvocation
from creditpilot.state.schemas import (
    StateUpdateProposal,
    _freeze_mapping,
    utc_now,
    validate_no_identity_pii,
)

ESCALATION_OUTPUT_FIELDS = frozenset(
    {
        "status",
        "escalation_reason",
        "review_package",
        "requested_actions",
        "evidence_references",
        "unresolved_items",
        "action_result_references",
    }
)
APPROVED_ACTIONS = frozenset({"create_review_case", "send_notification"})
DECISION_CLAIM = re.compile(
    r"\b(?:approve|decline|reject)\s+(?:the\s+)?application\b", re.IGNORECASE
)
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


class EscalationAgentValidationError(ValueError):
    """Raised when escalation output crosses its authority boundary."""


@dataclass(frozen=True, slots=True)
class EscalationContext:
    state_version: int
    authorized_state: Mapping[str, Any]
    known_evidence_references: tuple[str, ...]


class EscalationReasoningBackend(Protocol):
    def prepare_handoff(self, context: EscalationContext) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class EscalationAgentOutput:
    invocation_id: str
    agent_role: str
    status: str
    escalation_reason: str
    review_package: Mapping[str, Any]
    review_package_reference: str
    requested_actions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    action_result_references: tuple[str, ...]
    proposed_actions: tuple[str, ...]
    created_at: datetime
    failure: AgentFailure | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_package", _freeze_mapping(self.review_package))


def _texts(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise EscalationAgentValidationError(
            f"{field} must be a sequence of non-empty text"
        )
    return tuple(item.strip() for item in value)


def _known_references(view: Mapping[str, Any]) -> tuple[str, ...]:
    refs: set[str] = set()
    audit = view.get("governance_audit_references")
    if audit is not None:
        for field in audit.__dataclass_fields__:
            refs.update(getattr(audit, field))
    policy = view.get("policy_state")
    if policy is not None:
        refs.update(
            f"policy://{item.source_document}/"
            f"{item.section_or_chunk_reference}@{item.policy_version}"
            for item in policy.retrieved_evidence
        )
    verification = view.get("verification_state", {})
    refs.update(
        str(item["result_id"])
        for item in verification.get("tool_result_statuses", ())
    )
    return tuple(sorted(refs))


def run_escalation_agent(
    invocation: AgentInvocation, backend: EscalationReasoningBackend
) -> EscalationAgentOutput:
    if invocation.agent_role != "escalation_agent":
        raise EscalationAgentValidationError(
            "invocation is not for the Escalation Agent"
        )
    if invocation.permitted_tools - APPROVED_ACTIONS:
        raise EscalationAgentValidationError("Escalation Agent has an unapproved tool")
    view = invocation.authorized_state_view.data
    workflow = view.get("workflow_state")
    if workflow is None or not workflow.mandatory_human_review:
        raise EscalationAgentValidationError(
            "mandatory human review is required before escalation"
        )
    context = EscalationContext(
        state_version=invocation.input_state_version,
        authorized_state=view,
        known_evidence_references=_known_references(view),
    )
    try:
        draft = backend.prepare_handoff(context)
    except Exception as error:
        return EscalationAgentOutput(
            invocation_id=invocation.invocation_id,
            agent_role="escalation_agent",
            status="failure",
            escalation_reason="Escalation handoff preparation failed.",
            review_package={},
            review_package_reference="",
            requested_actions=(),
            evidence_references=(),
            unresolved_items=("Escalation backend failure",),
            action_result_references=(),
            proposed_actions=(),
            created_at=utc_now(),
            failure=AgentFailure(
                "escalation_backend_failed", type(error).__name__
            ),
        )
    if not isinstance(draft, Mapping) or set(draft) != ESCALATION_OUTPUT_FIELDS:
        raise EscalationAgentValidationError("Escalation output fields are invalid")
    if draft["status"] != "prepared":
        raise EscalationAgentValidationError("Escalation status must be prepared")
    reason = draft["escalation_reason"]
    package = draft["review_package"]
    if not isinstance(reason, str) or not reason.strip():
        raise EscalationAgentValidationError("escalation reason is required")
    if not isinstance(package, Mapping) or not package:
        raise EscalationAgentValidationError("sanitized review package is required")
    validate_no_identity_pii(package, "escalation_review_package")
    if EMAIL_PATTERN.search(reason) or EMAIL_PATTERN.search(repr(package)):
        raise EscalationAgentValidationError(
            "review package contains raw identity PII"
        )
    if DECISION_CLAIM.search(reason) or DECISION_CLAIM.search(repr(package)):
        raise EscalationAgentValidationError(
            "Escalation Agent cannot make the human decision"
        )
    actions = _texts(draft["requested_actions"], "requested_actions")
    references = _texts(draft["evidence_references"], "evidence_references")
    unresolved = _texts(draft["unresolved_items"], "unresolved_items")
    action_results = _texts(
        draft["action_result_references"], "action_result_references"
    )
    if set(actions) - invocation.permitted_tools:
        raise EscalationAgentValidationError("requested action is not permitted")
    if references and not set(references).issubset(context.known_evidence_references):
        raise EscalationAgentValidationError("Escalation Agent cites unknown evidence")
    if action_results:
        raise EscalationAgentValidationError(
            "Agent cannot claim action results before tool execution"
        )
    package_reference = f"review-package://{invocation.invocation_id}"
    return EscalationAgentOutput(
        invocation_id=invocation.invocation_id,
        agent_role="escalation_agent",
        status="prepared",
        escalation_reason=reason.strip(),
        review_package=package,
        review_package_reference=package_reference,
        requested_actions=actions,
        evidence_references=references,
        unresolved_items=unresolved,
        action_result_references=(),
        proposed_actions=actions,
        created_at=utc_now(),
    )


def escalation_output_to_state_proposal(
    output: EscalationAgentOutput, *, expected_state_version: int
) -> StateUpdateProposal:
    if output.failure is not None or output.status != "prepared":
        raise EscalationAgentValidationError("failed escalation cannot be proposed")
    return StateUpdateProposal(
        proposal_id=f"escalation-{output.invocation_id}",
        target_domain="escalation_state",
        proposed_changes={
            "status": "prepared",
            "reasons": (output.escalation_reason, *output.unresolved_items),
            "review_package_reference": output.review_package_reference,
            "requested_actions": output.requested_actions,
        },
        basis_references=output.evidence_references,
        proposed_by="escalation_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )
