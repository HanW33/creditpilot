"""Permission-controlled offline ACTION tools for human-review escalation."""

from __future__ import annotations

import re
from typing import Protocol

from creditpilot.state.schemas import CreditState, utc_now, validate_no_identity_pii
from creditpilot.tools.contracts import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)
from creditpilot.tools.internal import _validate_invocation

ACTION_TOOL_VERSION = "synthetic-action-tools-v1"
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


class ActionProvider(Protocol):
    provider_name: str

    def create_review_case(self, idempotency_key: str) -> tuple[str, bool]: ...

    def send_notification(self, idempotency_key: str) -> tuple[str, bool]: ...


def _validate_action(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    expected_tool: str,
    required_scope: str,
) -> str | ToolResult:
    _validate_invocation(
        invocation,
        expected_tool=expected_tool,
        state=state,
        permissions=permissions,
        required_scope=required_scope,
    )
    if not state.workflow_state.mandatory_human_review:
        return _failure(invocation, "human_review_not_required")
    escalation = state.escalation_state
    if escalation.status != "prepared" or not escalation.review_package_reference:
        return _failure(invocation, "escalation_not_prepared")
    if expected_tool not in escalation.requested_actions:
        return _failure(invocation, "action_not_requested")
    if invocation.arguments.get("review_package_reference") != (
        escalation.review_package_reference
    ):
        return _failure(invocation, "package_reference_mismatch")
    if not invocation.idempotency_key:
        return _failure(invocation, "idempotency_key_required")
    return invocation.idempotency_key


def _failure(invocation: ToolInvocation, code: str) -> ToolResult:
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="failure",
        result={},
        evidence_references=(),
        failure=ToolFailure(code, "Controlled action precondition failed."),
        started_at=invocation.requested_at,
        completed_at=utc_now(),
        tool_version=ACTION_TOOL_VERSION,
    )


def _success(
    invocation: ToolInvocation,
    provider: ActionProvider,
    reference: str,
    replayed: bool,
) -> ToolResult:
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result={
            "action_reference": reference,
            "provider_reference": provider.provider_name,
            "idempotency_outcome": "replayed" if replayed else "created",
            "input_state_version": invocation.input_state_version,
        },
        evidence_references=(reference,),
        failure=None,
        started_at=invocation.requested_at,
        completed_at=utc_now(),
        tool_version=ACTION_TOOL_VERSION,
    )


def create_review_case(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    provider: ActionProvider,
) -> ToolResult:
    key = _validate_action(
        invocation,
        state,
        permissions,
        expected_tool="create_review_case",
        required_scope="action:create_review_case",
    )
    if isinstance(key, ToolResult):
        return key
    reasons = invocation.arguments.get("escalation_reasons")
    if not isinstance(reasons, tuple) or not reasons:
        return _failure(invocation, "invalid_review_case_arguments")
    validate_no_identity_pii(reasons, "review_case_arguments")
    if EMAIL_PATTERN.search(repr(reasons)):
        return _failure(invocation, "review_case_not_sanitized")
    reference, replayed = provider.create_review_case(key)
    return _success(invocation, provider, reference, replayed)


def send_notification(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    provider: ActionProvider,
) -> ToolResult:
    key = _validate_action(
        invocation,
        state,
        permissions,
        expected_tool="send_notification",
        required_scope="action:send_notification",
    )
    if isinstance(key, ToolResult):
        return key
    destination = invocation.arguments.get("destination_reference")
    message = invocation.arguments.get("sanitized_message")
    if not isinstance(destination, str) or not destination.startswith(
        "destination://approved/"
    ):
        return _failure(invocation, "destination_not_approved")
    if (
        not isinstance(message, str)
        or not message.strip()
        or EMAIL_PATTERN.search(message)
    ):
        return _failure(invocation, "notification_not_sanitized")
    reference, replayed = provider.send_notification(key)
    return _success(invocation, provider, reference, replayed)
