"""Common typed invocation and failure records for approved agents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creditpilot.state.schemas import _freeze_mapping
from creditpilot.state.views import APPROVED_AGENT_ROLES, RoleStateView


@dataclass(frozen=True, slots=True)
class AgentFailure:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AgentAuditRecord:
    audit_reference: str
    invocation_id: str
    agent_role: str
    application_id: str
    case_id: str | None
    purpose: str
    input_state_version: int
    authorized_context_reference: str
    authorized_context_keys: tuple[str, ...]
    permitted_tools: frozenset[str]
    status: str
    evidence_references: tuple[str, ...]
    structured_output: Mapping[str, Any]
    proposed_actions: tuple[str, ...]
    validation_result: str
    failure: AgentFailure | None
    created_at: datetime
    resulting_state_version: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "structured_output", _freeze_mapping(self.structured_output)
        )


@dataclass(frozen=True, slots=True)
class AgentInvocation:
    invocation_id: str
    agent_role: str
    application_id: str
    case_id: str | None
    input_state_version: int
    purpose: str
    authorized_state_view: RoleStateView
    permitted_tools: frozenset[str]
    workflow_constraints: Mapping[str, Any]
    invoked_at: datetime

    def __post_init__(self) -> None:
        if self.agent_role not in APPROVED_AGENT_ROLES:
            raise ValueError("agent role is not approved")
        if self.authorized_state_view.role != self.agent_role:
            raise ValueError("authorized state view does not match agent role")
        if self.authorized_state_view.state_version != self.input_state_version:
            raise ValueError("authorized state view is stale")
        if not self.invocation_id or not self.application_id or not self.purpose:
            raise ValueError("agent invocation identity and purpose are required")
        object.__setattr__(
            self,
            "workflow_constraints",
            _freeze_mapping(self.workflow_constraints),
        )
