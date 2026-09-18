"""Deterministic bridges from bounded tool results to protected state controls."""

from __future__ import annotations

from datetime import datetime

from creditpilot.state import ProtectedStateController, StateUpdateRejected
from creditpilot.state.schemas import (
    CreditState,
    PolicyEvidence,
    QuantitativeModelState,
)
from creditpilot.tools.contracts import ToolAuditRecord, ToolInvocation, ToolResult


def commit_quantitative_tool_results(
    state: CreditState,
    model_run: ToolResult,
    explanation_run: ToolResult,
    controller: ProtectedStateController,
) -> CreditState:
    """Validate matching PD and SHAP results and commit them atomically."""

    if model_run.tool_name != "run_credit_risk_model" or model_run.status != "success":
        raise StateUpdateRejected("successful quantitative model result is required")
    if explanation_run.tool_name != "explain_model" or (
        explanation_run.status != "success"
    ):
        raise StateUpdateRejected("successful SHAP result is required")
    model_version = model_run.result.get("model_version")
    if not model_version or (
        explanation_run.result.get("model_version") != model_version
    ):
        raise StateUpdateRejected("model and SHAP versions do not match")
    expected_version = state.state_metadata.state_version
    if model_run.result.get("input_state_version") != expected_version or (
        explanation_run.result.get("input_state_version") != expected_version
    ):
        raise StateUpdateRejected("quantitative results are stale")
    feature_names = explanation_run.result.get("feature_names")
    shap_rows = explanation_run.result.get("shap_values")
    if not isinstance(feature_names, tuple) or not isinstance(shap_rows, tuple) or (
        len(shap_rows) != 1
    ):
        raise StateUpdateRejected("SHAP result shape is invalid")
    shap_values = shap_rows[0]
    if not isinstance(shap_values, tuple) or len(shap_values) != len(feature_names):
        raise StateUpdateRejected("SHAP features and values do not align")
    factors = {
        str(name): float(value)
        for name, value in zip(feature_names, shap_values, strict=True)
    }
    model_timestamp = model_run.result.get("model_timestamp")
    if not isinstance(model_timestamp, datetime):
        raise StateUpdateRejected("model timestamp is invalid")
    result = QuantitativeModelState(
        status="success",
        pd_score=float(model_run.result["pd_score"]),
        shap_risk_factors=factors,
        model_version=str(model_version),
        model_timestamp=model_timestamp,
        input_state_version=expected_version,
    )
    return controller.commit_quantitative_model_result(
        state,
        result,
        written_by="quantitative_model",
        expected_state_version=expected_version,
    )


def record_tool_audit(
    state: CreditState,
    invocation: ToolInvocation,
    result: ToolResult,
    controller: ProtectedStateController,
) -> tuple[CreditState, ToolAuditRecord]:
    """Append an audit reference while keeping tool payloads outside CreditState."""

    if result.invocation_id != invocation.invocation_id or (
        result.tool_name != invocation.tool_name
    ):
        raise StateUpdateRejected("tool result does not match its invocation")
    audit_reference = f"tool-audit://{invocation.invocation_id}"
    committed = controller.append_audit_reference(
        state,
        category="tool_call_references",
        reference=audit_reference,
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    record = ToolAuditRecord(
        audit_reference=audit_reference,
        application_id=invocation.application_id,
        case_id=invocation.case_id,
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        requested_by=invocation.requested_by,
        purpose=invocation.purpose,
        authorized_scope=invocation.authorized_scope,
        argument_keys=tuple(sorted(invocation.arguments)),
        input_state_version=invocation.input_state_version,
        tool_version=result.tool_version,
        started_at=result.started_at,
        completed_at=result.completed_at,
        status=result.status,
        evidence_references=result.evidence_references,
        failure=result.failure,
        resulting_state_version=committed.state_metadata.state_version,
    )
    return committed, record


def commit_policy_retrieval_result(
    state: CreditState,
    result: ToolResult,
    controller: ProtectedStateController,
) -> CreditState:
    """Commit raw retrieval evidence without adding Policy Agent interpretation."""

    if result.tool_name != "search_credit_policy" or result.status != "success":
        raise StateUpdateRejected("successful policy retrieval result is required")
    if result.result.get("input_state_version") != state.state_metadata.state_version:
        raise StateUpdateRejected("policy retrieval result is stale")
    evidence_items = result.result.get("evidence")
    if not isinstance(evidence_items, tuple) or not evidence_items:
        raise StateUpdateRejected("policy retrieval contains no evidence")
    committed = state
    for item in evidence_items:
        required = {
            "source_document",
            "section_or_chunk_reference",
            "policy_version",
            "retrieval_score",
            "effective_date",
        }
        if not required.issubset(item):
            raise StateUpdateRejected("policy evidence provenance is incomplete")
        evidence = PolicyEvidence(
            source_document=str(item["source_document"]),
            section_or_chunk_reference=str(item["section_or_chunk_reference"]),
            policy_version=str(item["policy_version"]),
            retrieval_score=float(item["retrieval_score"]),
            effective_date=str(item["effective_date"]),
        )
        committed = controller.record_policy_evidence(
            committed,
            evidence,
            written_by="policy_retrieval",
            expected_state_version=committed.state_metadata.state_version,
        )
    return committed
