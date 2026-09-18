"""Permission-controlled wrappers around the approved quantitative components."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from math import isfinite
from typing import Any

import pandas as pd

from creditpilot.ml.explain import explain_with_shap
from creditpilot.ml.model import BaselineModel
from creditpilot.state.schemas import CreditState, utc_now
from creditpilot.tools.contracts import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)
from creditpilot.tools.internal import _validate_invocation

RUN_MODEL_TOOL_VERSION = "run-credit-risk-model-v1"
EXPLAIN_MODEL_TOOL_VERSION = "explain-model-v1"


def _failed(
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


def _feature_references(arguments: Mapping[str, Any]) -> tuple[str, ...] | None:
    references = arguments.get("feature_references")
    if not isinstance(references, tuple) or not references:
        return None
    if not all(isinstance(reference, str) and reference for reference in references):
        return None
    return references


def _features_match_application(
    features: pd.DataFrame, application_id: str
) -> bool:
    return "application_id" not in features or (
        len(features) == 1
        and str(features.iloc[0]["application_id"]) == application_id
    )


def run_credit_risk_model(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    model: BaselineModel,
    features: pd.DataFrame,
) -> ToolResult:
    """Run the approved model for one case without committing protected state."""

    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool="run_credit_risk_model",
        state=state,
        permissions=permissions,
        required_scope="model:predict",
    )
    references = _feature_references(invocation.arguments)
    if invocation.arguments.get("model_version") != model.model_version:
        return _failed(
            invocation,
            code="model_version_mismatch",
            message="requested model version is not the loaded approved model",
            started_at=started_at,
            tool_version=RUN_MODEL_TOOL_VERSION,
        )
    if references is None or len(features) != 1:
        return _failed(
            invocation,
            code="invalid_model_input",
            message="one feature row and feature provenance are required",
            started_at=started_at,
            tool_version=RUN_MODEL_TOOL_VERSION,
        )
    if not _features_match_application(features, invocation.application_id):
        return _failed(
            invocation,
            code="application_mismatch",
            message="feature row does not match the authorized application",
            started_at=started_at,
            tool_version=RUN_MODEL_TOOL_VERSION,
        )
    try:
        pd_score = float(model.predict_pd(features)[0])
    except (KeyError, TypeError, ValueError):
        return _failed(
            invocation,
            code="model_execution_failed",
            message="approved quantitative model could not score the provided features",
            started_at=started_at,
            tool_version=RUN_MODEL_TOOL_VERSION,
        )
    if not isfinite(pd_score) or not 0 <= pd_score <= 1:
        return _failed(
            invocation,
            code="invalid_model_output",
            message="approved quantitative model returned an invalid PD",
            started_at=started_at,
            tool_version=RUN_MODEL_TOOL_VERSION,
        )
    model_timestamp = utc_now()
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result={
            "pd_score": pd_score,
            "model_version": model.model_version,
            "feature_version": model.feature_version,
            "data_version": model.data_version,
            "model_timestamp": model_timestamp,
            "input_state_version": state.state_metadata.state_version,
        },
        evidence_references=references,
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=RUN_MODEL_TOOL_VERSION,
    )


def explain_model(
    invocation: ToolInvocation,
    state: CreditState,
    permissions: ToolPermissionPolicy,
    *,
    model: BaselineModel,
    features: pd.DataFrame,
    model_run: ToolResult,
) -> ToolResult:
    """Compute SHAP only for a successful, matching quantitative model run."""

    started_at = utc_now()
    _validate_invocation(
        invocation,
        expected_tool="explain_model",
        state=state,
        permissions=permissions,
        required_scope="model:explain",
    )
    model_run_reference = invocation.arguments.get("model_run_reference")
    valid_run = (
        model_run.tool_name == "run_credit_risk_model"
        and model_run.status == "success"
        and model_run.result.get("model_version") == model.model_version
        and model_run.result.get("input_state_version")
        == state.state_metadata.state_version
    )
    if not valid_run or not isinstance(model_run_reference, str) or not (
        model_run_reference
    ):
        return _failed(
            invocation,
            code="invalid_model_run",
            message="a matching successful model run reference is required",
            started_at=started_at,
            tool_version=EXPLAIN_MODEL_TOOL_VERSION,
        )
    if len(features) != 1 or not _features_match_application(
        features, invocation.application_id
    ):
        return _failed(
            invocation,
            code="invalid_model_input",
            message="exactly one feature row is required for case explanation",
            started_at=started_at,
            tool_version=EXPLAIN_MODEL_TOOL_VERSION,
        )
    try:
        explanation = explain_with_shap(model, features, max_rows=1)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return _failed(
            invocation,
            code="explanation_failed",
            message="SHAP could not explain the approved model run",
            started_at=started_at,
            tool_version=EXPLAIN_MODEL_TOOL_VERSION,
        )
    return ToolResult(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        status="success",
        result={
            **explanation,
            "model_run_reference": model_run_reference,
            "computation_timestamp": utc_now(),
            "input_state_version": state.state_metadata.state_version,
        },
        evidence_references=(model_run_reference,),
        failure=None,
        started_at=started_at,
        completed_at=utc_now(),
        tool_version=EXPLAIN_MODEL_TOOL_VERSION,
    )
