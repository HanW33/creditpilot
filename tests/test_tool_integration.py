from datetime import UTC, datetime

import pytest

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import generate_synthetic_applications
from creditpilot.ml.evaluation import stratified_split
from creditpilot.ml.model import train_baseline
from creditpilot.state import ProtectedStateController, create_credit_state
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    calculate_dti,
    commit_quantitative_tool_results,
    explain_model,
    record_tool_audit,
    run_credit_risk_model,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def _state(application_id: str = "SYN-0000007"):
    return create_credit_state(
        application_id=application_id,
        customer_token="customer-token-007",
        reported_values={"annual_income": 100_000},
        sanitized_attributes={},
        source_reference="synthetic-application-7",
        now=NOW,
    )


def test_tool_audit_records_metadata_not_argument_payload() -> None:
    state = _state()
    permissions = ToolPermissionPolicy(
        callers_by_tool={
            "calculate_dti": frozenset({"deterministic_feature_component"})
        }
    )
    invocation = ToolInvocation(
        invocation_id="audit-dti-1",
        tool_name="calculate_dti",
        application_id="SYN-0000007",
        case_id=None,
        requested_by="deterministic_feature_component",
        purpose="Calculate traceable synthetic DTI",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"feature:calculate_dti"}),
        arguments={
            "monthly_debt_payment": 2_000,
            "annual_income": 100_000,
            "feature_logic_version": "dti-v1",
            "source_references": ("synthetic-application-7",),
        },
        requested_at=NOW,
    )
    result = calculate_dti(invocation, state, permissions)

    committed, audit = record_tool_audit(
        state, invocation, result, ProtectedStateController()
    )

    assert committed.governance_audit_references.tool_call_references == (
        "tool-audit://audit-dti-1",
    )
    assert audit.argument_keys == (
        "annual_income",
        "feature_logic_version",
        "monthly_debt_payment",
        "source_references",
    )
    assert not hasattr(audit, "arguments")


def test_matching_model_and_shap_results_commit_atomically() -> None:
    config = Phase1Config(sample_count=400, random_seed=53)
    splits = stratified_split(generate_synthetic_applications(config), config)
    model = train_baseline(splits.train, config)
    features = splits.test.head(1).drop(columns="defaulted")
    application_id = str(features.iloc[0]["application_id"])
    state = _state(application_id)
    permissions = ToolPermissionPolicy(
        callers_by_tool={
            "run_credit_risk_model": frozenset({"quantitative_model"}),
            "explain_model": frozenset({"quantitative_shap"}),
        }
    )
    model_invocation = ToolInvocation(
        invocation_id="integrated-model-1",
        tool_name="run_credit_risk_model",
        application_id=application_id,
        case_id=None,
        requested_by="quantitative_model",
        purpose="Run approved synthetic model",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:predict"}),
        arguments={
            "model_version": model.model_version,
            "feature_references": ("synthetic-features://7",),
        },
        requested_at=NOW,
    )
    model_run = run_credit_risk_model(
        model_invocation,
        state,
        permissions,
        model=model,
        features=features,
    )
    explain_invocation = ToolInvocation(
        invocation_id="integrated-explain-1",
        tool_name="explain_model",
        application_id=application_id,
        case_id=None,
        requested_by="quantitative_shap",
        purpose="Explain approved synthetic model run",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"model:explain"}),
        arguments={"model_run_reference": "model-run://integrated-model-1"},
        requested_at=NOW,
    )
    explanation = explain_model(
        explain_invocation,
        state,
        permissions,
        model=model,
        features=features,
        model_run=model_run,
    )

    committed = commit_quantitative_tool_results(
        state, model_run, explanation, ProtectedStateController()
    )

    assert committed.quantitative_model_state.status == "success"
    assert committed.quantitative_model_state.pd_score == pytest.approx(
        model_run.result["pd_score"]
    )
    assert committed.quantitative_model_state.shap_risk_factors
    assert committed.state_metadata.state_version == 2
