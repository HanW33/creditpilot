"""Generate the versioned synthetic Phase 12 Golden Demo evaluation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from creditpilot.evaluation.harness import (
    EvaluationConfig,
    ScenarioObservation,
    evaluate_golden_scenarios,
)
from creditpilot.state.schemas import SCHEMA_VERSION


def reference_observations() -> tuple[ScenarioObservation, ...]:
    """Return approved synthetic trace fixtures, not production case outcomes."""

    return (
        ScenarioObservation(
            scenario_id="golden-1-low-risk",
            policy_citations=("policy://synthetic/v1/eligibility",),
            recommendation="APPROVAL_RECOMMENDATION",
            recommendation_writer="decision_engine",
            audit_references=("audit://golden-1",),
        ),
        ScenarioObservation(
            scenario_id="golden-2-income-verification",
            reported_income=150000,
            verified_income=98000,
            model_run_count=2,
            policy_run_count=2,
            policy_citations=("policy://synthetic/v1/income-verification",),
            verification_requested=True,
            raw_verification_evidence=True,
            deterministic_verification_commit=True,
            recommendation="MANUAL_REVIEW",
            recommendation_writer="decision_engine",
            mandatory_human_review=True,
            escalation_performed=True,
            audit_references=("audit://golden-2", "verification://golden-2"),
        ),
        ScenarioObservation(
            scenario_id="golden-3-policy-conflict",
            policy_citations=("policy://synthetic/v1/conflict-a",),
            policy_conflicts=("unresolved synthetic evidence conflict",),
            mandatory_human_review=True,
            escalation_performed=True,
            audit_references=("audit://golden-3", "escalation://golden-3"),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--baseline-report",
        type=Path,
        default=Path("reports/phase1_baseline_metrics.json"),
    )
    args = parser.parse_args()
    baseline = json.loads(args.baseline_report.read_text())
    metrics = {
        key: float(value)
        for key, value in baseline["metrics"].items()
        if isinstance(value, (int, float))
    }
    report = evaluate_golden_scenarios(
        EvaluationConfig(
            evaluation_id="phase12-golden-demo-v1",
            data_version="synthetic-golden-demo-v1",
            model_version=str(baseline["model_version"]),
            policy_version="synthetic-policy-v1",
            workflow_version="phase12-workflow-v1",
            schema_version=SCHEMA_VERSION,
            synthetic_notice="Synthetic evaluation fixtures only; not lending policy.",
        ),
        reference_observations(),
        quantitative_metrics=metrics,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.to_dict(), indent=2) + "\n")


if __name__ == "__main__":
    main()
