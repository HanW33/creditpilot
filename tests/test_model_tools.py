from datetime import UTC, datetime

import numpy as np
import pytest

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import generate_synthetic_applications
from creditpilot.ml.evaluation import stratified_split
from creditpilot.ml.model import train_baseline
from creditpilot.state import create_credit_state
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    explain_model,
    run_credit_risk_model,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


@pytest.fixture(scope="module")
def model_case():
    config = Phase1Config(sample_count=500, random_seed=47)
    splits = stratified_split(generate_synthetic_applications(config), config)
    model = train_baseline(splits.train, config)
    features = splits.test.head(1).drop(columns="defaulted")
    application_id = str(features.iloc[0]["application_id"])
    state = create_credit_state(
        application_id=application_id,
        customer_token="synthetic-model-case-token",
        reported_values={"annual_income": float(features.iloc[0]["annual_income"])},
        sanitized_attributes={},
        source_reference="synthetic-model-case",
        now=NOW,
    )
    permissions = ToolPermissionPolicy(
        callers_by_tool={
            "run_credit_risk_model": frozenset({"quantitative_model"}),
            "explain_model": frozenset({"quantitative_shap"}),
        }
    )
    return model, features, state, permissions


def _model_invocation(state, model) -> ToolInvocation:
    return ToolInvocation(
        invocation_id="model-run-1",
        tool_name="run_credit_risk_model",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="quantitative_model",
        purpose="Generate synthetic probability of default",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:predict"}),
        arguments={
            "model_version": model.model_version,
            "feature_references": ("synthetic-features://case-1",),
        },
        requested_at=NOW,
    )


def test_model_tool_returns_pd_but_never_recommendation(model_case) -> None:
    model, features, state, permissions = model_case

    result = run_credit_risk_model(
        _model_invocation(state, model),
        state,
        permissions,
        model=model,
        features=features,
    )

    assert result.status == "success"
    assert 0 <= result.result["pd_score"] <= 1
    assert result.result["model_version"] == model.model_version
    assert "recommendation" not in result.result
    assert state.quantitative_model_state.status == "not_run"


def test_model_tool_rejects_version_mismatch(model_case) -> None:
    model, features, state, permissions = model_case
    invocation = _model_invocation(state, model)
    invocation = ToolInvocation(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        application_id=invocation.application_id,
        case_id=invocation.case_id,
        requested_by=invocation.requested_by,
        purpose=invocation.purpose,
        input_state_version=invocation.input_state_version,
        authorized_scope=invocation.authorized_scope,
        arguments={
            "model_version": "unapproved-model",
            "feature_references": ("synthetic-features://case-1",),
        },
        requested_at=invocation.requested_at,
    )

    result = run_credit_risk_model(
        invocation, state, permissions, model=model, features=features
    )

    assert result.status == "failure"
    assert result.result == {}
    assert result.failure is not None
    assert result.failure.code == "model_version_mismatch"


def test_explain_model_returns_model_derived_shap(model_case) -> None:
    model, features, state, permissions = model_case
    model_run = run_credit_risk_model(
        _model_invocation(state, model),
        state,
        permissions,
        model=model,
        features=features,
    )
    invocation = ToolInvocation(
        invocation_id="explain-run-1",
        tool_name="explain_model",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="quantitative_shap",
        purpose="Explain approved synthetic model run",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:explain"}),
        arguments={"model_run_reference": "model-run://1"},
        requested_at=NOW,
    )

    result = explain_model(
        invocation,
        state,
        permissions,
        model=model,
        features=features,
        model_run=model_run,
    )

    values = np.asarray(result.result["shap_values"])
    assert result.status == "success"
    assert values.shape[0] == 1
    assert np.isfinite(values).all()
    assert result.evidence_references == ("model-run://1",)


def test_explain_model_rejects_failed_or_unrelated_run(model_case) -> None:
    model, features, state, permissions = model_case
    failed_run = run_credit_risk_model(
        ToolInvocation(
            invocation_id="model-run-failed",
            tool_name="run_credit_risk_model",
            application_id=state.identity_references.application_id,
            case_id=None,
            requested_by="quantitative_model",
            purpose="Demonstrate explicit model failure",
            input_state_version=state.state_metadata.state_version,
            authorized_scope=frozenset({"model:predict"}),
            arguments={
                "model_version": "wrong-version",
                "feature_references": ("synthetic-features://case-1",),
            },
            requested_at=NOW,
        ),
        state,
        permissions,
        model=model,
        features=features,
    )
    invocation = ToolInvocation(
        invocation_id="explain-run-2",
        tool_name="explain_model",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="quantitative_shap",
        purpose="Reject failed model run",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:explain"}),
        arguments={"model_run_reference": "model-run://failed"},
        requested_at=NOW,
    )

    result = explain_model(
        invocation,
        state,
        permissions,
        model=model,
        features=features,
        model_run=failed_run,
    )

    assert result.status == "failure"
    assert result.failure is not None
    assert result.failure.code == "invalid_model_run"


def test_explain_model_rejects_different_application_features(model_case) -> None:
    model, features, state, permissions = model_case
    model_run = run_credit_risk_model(
        _model_invocation(state, model),
        state,
        permissions,
        model=model,
        features=features,
    )
    mismatched = features.copy()
    mismatched.loc[mismatched.index[0], "application_id"] = "SYN-OTHER"
    invocation = ToolInvocation(
        invocation_id="explain-run-3",
        tool_name="explain_model",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="quantitative_shap",
        purpose="Reject mismatched feature row",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:explain"}),
        arguments={"model_run_reference": "model-run://1"},
        requested_at=NOW,
    )

    result = explain_model(
        invocation,
        state,
        permissions,
        model=model,
        features=mismatched,
        model_run=model_run,
    )

    assert result.status == "failure"
    assert result.failure is not None
    assert result.failure.code == "invalid_model_input"
