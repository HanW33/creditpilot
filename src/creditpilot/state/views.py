"""Allowlisted, read-only, minimum-context views for the five approved agents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from creditpilot.state.schemas import CreditState, _freeze_mapping

APPROVED_AGENT_ROLES = frozenset(
    {
        "policy_agent",
        "orchestrator_agent",
        "verification_agent",
        "explanation_agent",
        "escalation_agent",
    }
)


@dataclass(frozen=True, slots=True)
class RoleStateView:
    role: str
    state_version: int
    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze_mapping(self.data))


def _case_reference(state: CreditState) -> Mapping[str, str | None]:
    return {
        "application_id": state.identity_references.application_id,
        "case_id": state.identity_references.case_id,
    }


def _application_context(state: CreditState) -> Mapping[str, Any]:
    return {
        "reported_values": state.application_data.reported_values,
        "sanitized_attributes": state.application_data.sanitized_attributes,
        "source_reference": state.application_data.source_reference,
    }


def _verification_summary(state: CreditState) -> Mapping[str, Any]:
    return {
        "requests": state.verification_state.requests,
        "tool_result_statuses": tuple(
            {
                "result_id": result.result_id,
                "request_id": result.request_id,
                "status": result.status,
                "failure": result.failure,
            }
            for result in state.verification_state.tool_results
        ),
        "verified_values": state.verification_state.verified_values,
        "conflicts": state.verification_state.conflicts,
    }


def build_role_state_view(state: CreditState, role: str) -> RoleStateView:
    """Build a deny-by-default view for one of the five approved agent roles."""

    if role not in APPROVED_AGENT_ROLES:
        raise ValueError(f"unsupported agent role: {role}")

    case_reference = _case_reference(state)
    application = _application_context(state)
    verification = _verification_summary(state)
    views: dict[str, Mapping[str, Any]] = {
        "policy_agent": {
            "case_reference": case_reference,
            "application_data": application,
            "validation_state": state.validation_state,
            "verified_values": state.verification_state.verified_values,
            "policy_state": state.policy_state,
        },
        "orchestrator_agent": {
            "case_reference": case_reference,
            "validation_state": state.validation_state,
            "quantitative_model_state": state.quantitative_model_state,
            "policy_state": state.policy_state,
            "verification_state": verification,
            "workflow_state": state.workflow_state,
        },
        "verification_agent": {
            "case_reference": case_reference,
            "application_data": application,
            "required_evidence": state.policy_state.required_evidence,
            "active_request_ids": state.workflow_state.active_request_ids,
            "verification_state": {
                "requests": state.verification_state.requests,
                "tool_results": state.verification_state.tool_results,
                "interpretations": state.verification_state.interpretations,
                "conflicts": state.verification_state.conflicts,
            },
        },
        "explanation_agent": {
            "case_reference": case_reference,
            "application_data": application,
            "quantitative_model_state": state.quantitative_model_state,
            "policy_state": state.policy_state,
            "verification_state": verification,
            "recommendation_state": state.recommendation_state,
            "workflow_state": state.workflow_state,
        },
        "escalation_agent": {
            "case_reference": case_reference,
            "application_data": application,
            "quantitative_model_state": state.quantitative_model_state,
            "policy_state": state.policy_state,
            "verification_state": verification,
            "recommendation_state": state.recommendation_state,
            "explanation_state": state.explanation_state,
            "workflow_state": state.workflow_state,
            "escalation_state": state.escalation_state,
        },
    }
    return RoleStateView(
        role=role,
        state_version=state.state_metadata.state_version,
        data=views[role],
    )
