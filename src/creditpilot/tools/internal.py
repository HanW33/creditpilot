"""Phase 3 internal READ and deterministic COMPUTE tools."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any

from creditpilot.state.schemas import CreditState, utc_now
from creditpilot.tools.contracts import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)

GET_APPLICATION_VERSION = "get-application-v1"
CALCULATE_DTI_VERSION = "calculate-dti-v1"


def _validate_invocation(
    invocation: ToolInvocation,
    *,
    expected_tool: str,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    required_scope: str,
) -> None:
    if invocation.tool_name != expected_tool:
        raise ValueError("invocation tool_name does not match capability")
    if invocation.application_id != state.identity_references.application_id:
        raise ValueError("invocation application_id does not match state")
    if invocation.input_state_version != state.state_metadata.state_version:
        raise ValueError("invocation uses a stale state version")
    permissions.authorize(invocation, required_scope)


def _failure_result(
    invocation: ToolInvocation,
    *,
    code: str,
    message: str,
    started_at: datetime,
    tool_version: str,
) -> ToolResult:
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="failure",
        result={},
        evidence_references=(),
        failure=ToolFailure(code=code, message=message),
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=tool_version,
    )


def get_application(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
) -> ToolResult:
    """Return only explicitly requested committed application fields."""

    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool="get_application",
        state=state,
        permissions=permissions,
        required_scope="application:read",
    )
    reported_fields = invocation.arguments.get("reported_fields", ())
    sanitized_fields = invocation.arguments.get("sanitized_fields", ())
    if not isinstance(reported_fields, tuple) or not isinstance(
        sanitized_fields, tuple
    ):
        return _failure_result(
            invocation,
            code="invalid_arguments",
            message="requested field lists must be sequences",
            started_at=started_at,
            tool_version=GET_APPLICATION_VERSION,
        )
    missing = tuple(
        field
        for field in reported_fields
        if field not in state.application_data.reported_values
    ) + tuple(
        field
        for field in sanitized_fields
        if field not in state.application_data.sanitized_attributes
    )
    if missing:
        return _failure_result(
            invocation,
            code="requested_field_unavailable",
            message="one or more requested fields are unavailable",
            started_at=started_at,
            tool_version=GET_APPLICATION_VERSION,
        )
    result: dict[str, Any] = {
        "application_id": state.identity_references.application_id,
        "reported_values": {
            field: state.application_data.reported_values[field]
            for field in reported_fields
        },
        "sanitized_attributes": {
            field: state.application_data.sanitized_attributes[field]
            for field in sanitized_fields
        },
        "source_reference": state.application_data.source_reference,
        "input_state_version": state.state_metadata.state_version,
    }
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result=result,
        evidence_references=(state.application_data.source_reference,),
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=GET_APPLICATION_VERSION,
    )


def calculate_dti(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
) -> ToolResult:
    """Calculate monthly debt payment divided by gross monthly income."""

    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool="calculate_dti",
        state=state,
        permissions=permissions,
        required_scope="feature:calculate_dti",
    )
    try:
        monthly_payment = float(invocation.arguments["monthly_debt_payment"])
        annual_income = float(invocation.arguments["annual_income"])
        feature_version = str(invocation.arguments["feature_logic_version"])
        supplied_references = invocation.arguments["source_references"]
    except (KeyError, TypeError, ValueError):
        return _failure_result(
            invocation,
            code="invalid_arguments",
            message="required numeric inputs or provenance are missing",
            started_at=started_at,
            tool_version=CALCULATE_DTI_VERSION,
        )
    valid_references = isinstance(supplied_references, tuple) and all(
        isinstance(reference, str) and reference
        for reference in supplied_references
    )
    if (
        not isfinite(annual_income)
        or not isfinite(monthly_payment)
        or annual_income <= 0
        or monthly_payment < 0
        or not feature_version
        or not valid_references
    ):
        return _failure_result(
            invocation,
            code="invalid_arguments",
            message="inputs and source references must be valid",
            started_at=started_at,
            tool_version=CALCULATE_DTI_VERSION,
        )
    source_references = tuple(supplied_references)
    dti = monthly_payment / (annual_income / 12)
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result={
            "dti": dti,
            "feature_logic_version": feature_version,
            "input_state_version": state.state_metadata.state_version,
        },
        evidence_references=source_references,
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=CALCULATE_DTI_VERSION,
    )
