"""Permission-controlled retrieval from the synthetic policy corpus."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from creditpilot.policy import PolicyIndex
from creditpilot.state.schemas import CreditState, utc_now, validate_no_identity_pii
from creditpilot.tools.contracts import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)
from creditpilot.tools.internal import _validate_invocation

SEARCH_POLICY_TOOL_VERSION = "search-credit-policy-v1"
ALLOWED_CONTEXT_FIELDS = frozenset(
    {"evidence_status", "verification_status", "model_status", "policy_status"}
)


def _non_success(
    invocation: ToolInvocation,
    *,
    status: str,
    code: str,
    message: str,
    started_at,
) -> ToolResult:
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status=status,
        result={},
        evidence_references=(),
        failure=ToolFailure(code=code, message=message),
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=SEARCH_POLICY_TOOL_VERSION,
    )


def search_credit_policy(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    index: PolicyIndex,
) -> ToolResult:
    """Return raw ranked policy evidence without interpretation or state mutation."""

    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool="search_credit_policy",
        state=state,
        permissions=permissions,
        required_scope="policy:search",
    )
    allowed_arguments = {
        "policy_question",
        "requested_evidence",
        "sanitized_context",
        "top_k",
        "required_policy_versions",
    }
    if set(invocation.arguments) - allowed_arguments:
        return _non_success(
            invocation,
            status="failure",
            code="unsupported_arguments",
            message="policy search contains unsupported arguments",
            started_at=started_at,
        )
    question = invocation.arguments.get("policy_question")
    requested_evidence = invocation.arguments.get("requested_evidence")
    context = invocation.arguments.get("sanitized_context", {})
    top_k = invocation.arguments.get("top_k")
    versions = invocation.arguments.get("required_policy_versions", ())
    if not isinstance(question, str) or not isinstance(requested_evidence, str):
        return _non_success(
            invocation,
            status="failure",
            code="invalid_arguments",
            message="policy question and requested evidence must be text",
            started_at=started_at,
        )
    if not isinstance(context, Mapping):
        return _non_success(
            invocation,
            status="failure",
            code="invalid_arguments",
            message="sanitized context must be a mapping",
            started_at=started_at,
        )
    try:
        validate_no_identity_pii(context, "policy_search.sanitized_context")
    except ValueError:
        return _non_success(
            invocation,
            status="failure",
            code="prohibited_context_data",
            message="policy search context contains prohibited identity data",
            started_at=started_at,
        )
    if set(context) - ALLOWED_CONTEXT_FIELDS:
        return _non_success(
            invocation,
            status="failure",
            code="unsupported_context",
            message="policy search context contains fields outside the allowlist",
            started_at=started_at,
        )
    if any(
        not isinstance(value, (str, bool)) and value is not None
        for value in context.values()
    ):
        return _non_success(
            invocation,
            status="failure",
            code="invalid_context",
            message="policy search context values must be bounded status values",
            started_at=started_at,
        )
    valid_versions = isinstance(versions, tuple) and all(
        isinstance(version, str) and version for version in versions
    )
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not valid_versions:
        return _non_success(
            invocation,
            status="failure",
            code="invalid_arguments",
            message="top_k or policy version requirements are invalid",
            started_at=started_at,
        )
    query = f"{question.strip()} {requested_evidence.strip()}".strip()
    try:
        matches = index.search(
            query,
            top_k=top_k,
            required_policy_versions=versions,
        )
    except ValueError:
        return _non_success(
            invocation,
            status="failure",
            code="invalid_search_request",
            message="policy search request is invalid",
            started_at=started_at,
        )
    except LookupError:
        return _non_success(
            invocation,
            status="unavailable",
            code="policy_evidence_unavailable",
            message="no searchable synthetic policy evidence is available",
            started_at=started_at,
        )
    evidence = tuple(asdict(match) for match in matches)
    references = tuple(
        (
            f"policy://{match.source_document}/"
            f"{match.section_or_chunk_reference}@{match.policy_version}"
        )
        for match in matches
    )
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result={
            "evidence": evidence,
            "result_count": len(evidence),
            "input_state_version": state.state_metadata.state_version,
        },
        evidence_references=references,
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=SEARCH_POLICY_TOOL_VERSION,
    )
