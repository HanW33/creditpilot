"""READ-only verification tools backed by an injected evidence provider."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from creditpilot.state.schemas import CreditState, utc_now, validate_no_identity_pii
from creditpilot.tools.contracts import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)
from creditpilot.tools.internal import _validate_invocation

VERIFICATION_TOOL_VERSION = "synthetic-verification-tools-v1"
TOOL_EVIDENCE_TYPES = {
    "verify_income": "verified_income",
    "verify_employment": "verified_employment",
    "get_credit_report": "credit_report",
}


class VerificationEvidenceProvider(Protocol):
    provider_name: str

    def obtain(
        self, application_id: str, evidence_type: str
    ) -> Mapping[str, Any] | None: ...


def _run_verification_tool(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    provider: VerificationEvidenceProvider,
    *,
    expected_tool: str,
) -> ToolResult:
    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool=expected_tool,
        state=state,
        permissions=permissions,
        required_scope="verification:read",
    )
    request_id = invocation.arguments.get("request_id")
    request = next(
        (
            item
            for item in state.verification_state.requests
            if item.request_id == request_id
            and item.status == "approved"
            and item.request_id in state.workflow_state.active_request_ids
        ),
        None,
    )
    evidence_type = TOOL_EVIDENCE_TYPES[expected_tool]
    if request is None:
        return _failure(invocation, "request_not_approved", started_at)
    if request.evidence_required != evidence_type:
        return _failure(invocation, "request_tool_mismatch", started_at)
    evidence = provider.obtain(invocation.application_id, evidence_type)
    if evidence is None:
        return _failure(invocation, "evidence_unavailable", started_at)
    try:
        validate_no_identity_pii(evidence, "raw_verification_evidence")
    except ValueError:
        return _failure(invocation, "prohibited_evidence_data", started_at)
    if set(evidence) != {evidence_type}:
        return _failure(invocation, "invalid_provider_evidence", started_at)

    reference = (
        f"verification://{provider.provider_name}/"
        f"{invocation.application_id}/{request_id}/{evidence_type}"
    )
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=expected_tool,
        status="success",
        result={
            "request_id": request_id,
            "evidence_type": evidence_type,
            "raw_evidence": evidence,
            "raw_evidence_reference": reference,
            "provider_reference": provider.provider_name,
            "input_state_version": state.state_metadata.state_version,
        },
        evidence_references=(reference,),
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=VERIFICATION_TOOL_VERSION,
    )


def _failure(
    invocation: ToolInvocation, code: str, started_at: Any
) -> ToolResult:
    messages = {
        "request_not_approved": "An active approved verification request is required.",
        "request_tool_mismatch": "The tool does not match the requested evidence.",
        "evidence_unavailable": "Synthetic verification evidence is unavailable.",
        "prohibited_evidence_data": (
            "Verification evidence contains prohibited identity data."
        ),
        "invalid_provider_evidence": "Verification provider evidence is malformed.",
    }
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="failure",
        result={},
        evidence_references=(),
        failure=ToolFailure(code=code, message=messages[code]),
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=VERIFICATION_TOOL_VERSION,
    )


def verify_income(invocation, state, permissions, *, provider):
    return _run_verification_tool(
        invocation, state, permissions, provider, expected_tool="verify_income"
    )


def verify_employment(invocation, state, permissions, *, provider):
    return _run_verification_tool(
        invocation, state, permissions, provider, expected_tool="verify_employment"
    )


def get_credit_report(invocation, state, permissions, *, provider):
    return _run_verification_tool(
        invocation, state, permissions, provider, expected_tool="get_credit_report"
    )
