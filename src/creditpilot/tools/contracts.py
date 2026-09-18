"""Common contracts and deterministic permission checks for tools."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creditpilot.state.schemas import _freeze_mapping


@dataclass(frozen=True, slots=True)
class ToolFailure:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    invocation_id: str
    tool_name: str
    application_id: str
    case_id: str | None
    requested_by: str
    purpose: str
    input_state_version: int
    authorized_scope: frozenset[str]
    arguments: Mapping[str, Any]
    requested_at: datetime
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not (
            self.invocation_id
            and self.tool_name
            and self.application_id
            and self.requested_by
            and self.purpose
        ):
            raise ValueError("tool invocation identity and purpose are required")
        if self.input_state_version < 1:
            raise ValueError("input_state_version must be positive")
        object.__setattr__(self, "arguments", _freeze_mapping(self.arguments))


@dataclass(frozen=True, slots=True)
class ToolResult:
    invocation_id: str
    tool_name: str
    status: str
    result: Mapping[str, Any]
    evidence_references: tuple[str, ...]
    failure: ToolFailure | None
    started_at: datetime
    completed_at: datetime
    tool_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", _freeze_mapping(self.result))
        if self.status == "success" and self.failure is not None:
            raise ValueError("successful tool result cannot contain failure")
        if self.status != "success" and self.failure is None:
            raise ValueError("non-success tool result requires failure")


@dataclass(frozen=True, slots=True)
class ToolAuditRecord:
    audit_reference: str
    application_id: str
    case_id: str | None
    invocation_id: str
    tool_name: str
    requested_by: str
    purpose: str
    authorized_scope: frozenset[str]
    argument_keys: tuple[str, ...]
    input_state_version: int
    tool_version: str
    started_at: datetime
    completed_at: datetime
    status: str
    evidence_references: tuple[str, ...]
    failure: ToolFailure | None
    resulting_state_version: int


@dataclass(frozen=True, slots=True)
class ToolPermissionPolicy:
    """Caller allowlists remain explicit configuration, not hard-coded roles."""

    callers_by_tool: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "callers_by_tool", _freeze_mapping(self.callers_by_tool)
        )

    def authorize(self, invocation: ToolInvocation, required_scope: str) -> None:
        allowed = self.callers_by_tool.get(invocation.tool_name, frozenset())
        if invocation.requested_by not in allowed:
            raise PermissionError("caller is not authorized for this tool")
        if required_scope not in invocation.authorized_scope:
            raise PermissionError("invocation lacks required authorized scope")
