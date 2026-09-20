from datetime import UTC, datetime

import pytest

from creditpilot.evaluation import (
    EvaluationConfig,
    ScenarioObservation,
    evaluate_golden_scenarios,
)
from creditpilot.evaluation.cli import reference_observations


def config() -> EvaluationConfig:
    return EvaluationConfig(
        evaluation_id="test-eval-v1",
        data_version="synthetic-v1",
        model_version="model-v1",
        policy_version="synthetic-policy-v1",
        workflow_version="workflow-v1",
        schema_version="credit-state-v1",
        synthetic_notice="Synthetic test data only.",
    )


def test_all_golden_demo_contracts_pass() -> None:
    timestamp = datetime(2026, 9, 20, tzinfo=UTC)
    report = evaluate_golden_scenarios(
        config(), reference_observations(), evaluated_at=timestamp
    )

    assert report.status == "pass"
    assert len(report.scenarios) == 3
    assert all(item.status == "pass" for item in report.scenarios)
    assert report.to_dict()["evaluated_at"] == timestamp.isoformat()
    assert report.quantitative_acceptance_thresholds == "not_approved"


def test_hard_invariant_failure_cannot_be_masked() -> None:
    observations = list(reference_observations())
    original = observations[0]
    observations[0] = ScenarioObservation(
        scenario_id=original.scenario_id,
        policy_citations=original.policy_citations,
        recommendation=original.recommendation,
        recommendation_writer=original.recommendation_writer,
        audit_references=original.audit_references,
        raw_identity_pii_present=True,
    )

    report = evaluate_golden_scenarios(config(), tuple(observations))

    assert report.status == "fail"
    failure = report.scenarios[0].checks[0]
    assert failure.check_id == "security.no_raw_identity_pii"
    assert failure.hard_invariant is True
    assert failure.status == "fail"


def test_missing_or_duplicate_scenarios_are_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        evaluate_golden_scenarios(config(), reference_observations()[:2])


def test_income_scenario_requires_reruns_and_separate_values() -> None:
    observations = list(reference_observations())
    observations[1] = ScenarioObservation(
        scenario_id="golden-2-income-verification",
        reported_income=98000,
        verified_income=98000,
        policy_citations=("policy://synthetic/v1/income",),
        raw_verification_evidence=True,
        deterministic_verification_commit=True,
        recommendation="MANUAL_REVIEW",
        recommendation_writer="decision_engine",
        mandatory_human_review=True,
        escalation_performed=True,
        audit_references=("audit://bad-income",),
    )

    report = evaluate_golden_scenarios(config(), tuple(observations))
    checks = {item.check_id: item.status for item in report.scenarios[1].checks}

    assert checks["verification.reported_preserved"] == "fail"
    assert checks["verification.verified_separate"] == "fail"
    assert checks["rerun.model_and_policy"] == "fail"
