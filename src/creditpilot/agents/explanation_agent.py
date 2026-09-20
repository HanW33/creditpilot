"""Read-only Explanation Agent with deterministic evidence validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol

from creditpilot.agents.contracts import AgentFailure, AgentInvocation
from creditpilot.state.schemas import StateUpdateProposal, utc_now

EXPLANATION_OUTPUT_FIELDS = frozenset(
    {
        "status",
        "explanation",
        "evidence_references",
        "input_state_version",
        "limitations",
        "unresolved_items",
    }
)
REQUIRED_SECTIONS = ("Model:", "Policy:", "Verification:", "Decision:")
AUTONOMOUS_CLAIM = re.compile(
    r"\b(?:we|system|agent)\s+(?:approved|declined|rejected)\b", re.IGNORECASE
)
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


class ExplanationAgentValidationError(ValueError):
    """Raised when an explanation is ungrounded or exceeds authority."""


@dataclass(frozen=True, slots=True)
class ExplanationContext:
    state_version: int
    authorized_state: Mapping[str, Any]
    known_evidence_references: tuple[str, ...]


class ExplanationReasoningBackend(Protocol):
    def generate_explanation(
        self, context: ExplanationContext
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ExplanationAgentOutput:
    invocation_id: str
    agent_role: str
    status: str
    explanation: str | None
    evidence_references: tuple[str, ...]
    input_state_version: int
    limitations: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    proposed_actions: tuple[str, ...]
    created_at: datetime
    failure: AgentFailure | None = None


def _texts(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ExplanationAgentValidationError(
            f"{field} must be a sequence of non-empty text"
        )
    return tuple(item.strip() for item in value)


def _known_references(view: Mapping[str, Any]) -> tuple[str, ...]:
    references = {str(view["application_data"]["source_reference"])}
    model = view["quantitative_model_state"]
    if model.model_version and model.input_state_version is not None:
        references.add(
            f"model://{model.model_version}/state/{model.input_state_version}"
        )
    policy = view["policy_state"]
    references.update(
        f"policy://{item.source_document}/"
        f"{item.section_or_chunk_reference}@{item.policy_version}"
        for item in policy.retrieved_evidence
    )
    verification = view["verification_state"]
    references.update(
        str(item["raw_evidence_reference"])
        for item in verification.get("tool_result_statuses", ())
    )
    return tuple(sorted(references))


def _validate_draft(
    draft: Mapping[str, Any], context: ExplanationContext
) -> ExplanationAgentOutput:
    if set(draft) != EXPLANATION_OUTPUT_FIELDS:
        raise ExplanationAgentValidationError("Explanation output fields are invalid")
    if draft["status"] != "complete":
        raise ExplanationAgentValidationError("Explanation status must be complete")
    if draft["input_state_version"] != context.state_version:
        raise ExplanationAgentValidationError("Explanation input state is stale")
    explanation = draft["explanation"]
    if not isinstance(explanation, str) or not explanation.strip():
        raise ExplanationAgentValidationError("Explanation text is required")
    if any(section not in explanation for section in REQUIRED_SECTIONS):
        raise ExplanationAgentValidationError(
            "Explanation must distinguish all evidence categories"
        )
    if AUTONOMOUS_CLAIM.search(explanation):
        raise ExplanationAgentValidationError(
            "Explanation claims autonomous lending authority"
        )
    if EMAIL_PATTERN.search(explanation):
        raise ExplanationAgentValidationError("Explanation contains identity PII")
    references = _texts(draft["evidence_references"], "evidence_references")
    limitations = _texts(draft["limitations"], "limitations")
    unresolved = _texts(draft["unresolved_items"], "unresolved_items")
    if not references or not set(references).issubset(
        context.known_evidence_references
    ):
        raise ExplanationAgentValidationError(
            "Explanation must cite only committed evidence"
        )
    view = context.authorized_state
    model = view["quantitative_model_state"]
    if model.pd_score is not None and str(model.pd_score) not in explanation:
        raise ExplanationAgentValidationError("Explanation omits committed PD")
    recommendation = view["recommendation_state"]
    if recommendation.recommendation is None:
        raise ExplanationAgentValidationError(
            "committed recommendation is required for explanation"
        )
    if (
        recommendation.recommendation not in explanation
        or str(recommendation.decision_rule) not in explanation
    ):
        raise ExplanationAgentValidationError(
            "Explanation omits committed recommendation evidence"
        )
    verification = view["verification_state"]
    for key, value in verification.get("verified_values", {}).items():
        if str(key) not in explanation or str(value) not in explanation:
            raise ExplanationAgentValidationError(
                "Explanation omits committed verification evidence"
            )
    policy = view["policy_state"]
    if str(policy.status) not in explanation or any(
        finding not in explanation for finding in policy.findings
    ):
        raise ExplanationAgentValidationError(
            "Explanation omits committed policy evidence"
        )
    required_unresolved = {
        *policy.conflicts,
        *verification.get("conflicts", ()),
    }
    if not required_unresolved.issubset(unresolved):
        raise ExplanationAgentValidationError(
            "Explanation conceals unresolved conflicts"
        )
    workflow = view["workflow_state"]
    if not set(workflow.mandatory_review_reasons).issubset(limitations):
        raise ExplanationAgentValidationError(
            "Explanation omits mandatory-review reasons"
        )
    if any(item not in explanation for item in (*limitations, *unresolved)):
        raise ExplanationAgentValidationError(
            "Explanation text must communicate limitations and unresolved items"
        )
    return ExplanationAgentOutput(
        invocation_id="",
        agent_role="explanation_agent",
        status="complete",
        explanation=explanation.strip(),
        evidence_references=references,
        input_state_version=context.state_version,
        limitations=limitations,
        unresolved_items=unresolved,
        proposed_actions=(),
        created_at=utc_now(),
    )


def run_explanation_agent(
    invocation: AgentInvocation, backend: ExplanationReasoningBackend
) -> ExplanationAgentOutput:
    if invocation.agent_role != "explanation_agent":
        raise ExplanationAgentValidationError(
            "invocation is not for the Explanation Agent"
        )
    if invocation.permitted_tools:
        raise ExplanationAgentValidationError(
            "Explanation Agent must not receive side-effect tools"
        )
    context = ExplanationContext(
        state_version=invocation.input_state_version,
        authorized_state=invocation.authorized_state_view.data,
        known_evidence_references=_known_references(
            invocation.authorized_state_view.data
        ),
    )
    try:
        draft = backend.generate_explanation(context)
        if not isinstance(draft, Mapping):
            raise ExplanationAgentValidationError(
                "Explanation backend output must be a mapping"
            )
        output = _validate_draft(draft, context)
    except ExplanationAgentValidationError:
        raise
    except Exception as error:
        return ExplanationAgentOutput(
            invocation_id=invocation.invocation_id,
            agent_role="explanation_agent",
            status="failure",
            explanation=None,
            evidence_references=(),
            input_state_version=invocation.input_state_version,
            limitations=("Explanation backend failed",),
            unresolved_items=(),
            proposed_actions=(),
            created_at=utc_now(),
            failure=AgentFailure(
                "explanation_backend_failed", type(error).__name__
            ),
        )
    return replace(output, invocation_id=invocation.invocation_id)


def explanation_output_to_state_proposal(
    output: ExplanationAgentOutput, *, expected_state_version: int
) -> StateUpdateProposal:
    if output.failure is not None or output.explanation is None:
        raise ExplanationAgentValidationError("failed explanation cannot be proposed")
    return StateUpdateProposal(
        proposal_id=f"explanation-{output.invocation_id}",
        target_domain="explanation_state",
        proposed_changes={"explanation": output.explanation},
        basis_references=output.evidence_references,
        proposed_by="explanation_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )
