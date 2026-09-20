"""Deterministic, threshold-neutral evaluation of the approved demo contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    evaluation_id: str
    data_version: str
    model_version: str
    policy_version: str
    workflow_version: str
    schema_version: str
    synthetic_notice: str

    def validate(self) -> None:
        values = asdict(self)
        if any(not value for value in values.values()):
            raise ValueError("all evaluation version fields are required")
        if "synthetic" not in self.synthetic_notice.lower():
            raise ValueError(
                "evaluation data must be explicitly identified as synthetic"
            )


@dataclass(frozen=True, slots=True)
class ScenarioObservation:
    scenario_id: str
    reported_income: float | None = None
    verified_income: float | None = None
    model_run_count: int = 1
    policy_run_count: int = 1
    policy_citations: tuple[str, ...] = ()
    policy_conflicts: tuple[str, ...] = ()
    verification_requested: bool = False
    raw_verification_evidence: bool = False
    deterministic_verification_commit: bool = False
    recommendation: str | None = None
    recommendation_writer: str | None = None
    mandatory_human_review: bool = False
    escalation_performed: bool = False
    explanation_grounded: bool = True
    audit_references: tuple[str, ...] = ()
    raw_identity_pii_present: bool = False
    unauthorized_state_mutation: bool = False
    fabricated_evidence: bool = False
    limits_respected: bool = True


@dataclass(frozen=True, slots=True)
class EvaluationCheck:
    check_id: str
    layer: str
    status: str
    hard_invariant: bool
    expected: str
    actual: str
    evidence_references: tuple[str, ...] = ()
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioEvaluation:
    scenario_id: str
    status: str
    checks: tuple[EvaluationCheck, ...]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    config: EvaluationConfig
    status: str
    evaluated_at: datetime
    scenarios: tuple[ScenarioEvaluation, ...]
    quantitative_metrics: dict[str, float]
    quantitative_acceptance_thresholds: str = "not_approved"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evaluated_at"] = self.evaluated_at.isoformat()
        return result


def _check(
    check_id: str,
    layer: str,
    passed: bool,
    expected: str,
    actual: str,
    *,
    evidence: tuple[str, ...] = (),
    hard: bool = True,
) -> EvaluationCheck:
    return EvaluationCheck(
        check_id=check_id,
        layer=layer,
        status="pass" if passed else "fail",
        hard_invariant=hard,
        expected=expected,
        actual=actual,
        evidence_references=evidence,
        failure=None if passed else f"expected {expected}; observed {actual}",
    )


def _common_checks(observation: ScenarioObservation) -> list[EvaluationCheck]:
    return [
        _check(
            "security.no_raw_identity_pii",
            "security",
            not observation.raw_identity_pii_present,
            "no raw identity PII",
            "present" if observation.raw_identity_pii_present else "absent",
        ),
        _check(
            "state.protected_ownership",
            "deterministic_controls",
            not observation.unauthorized_state_mutation,
            "protected writes use approved owners",
            "violation" if observation.unauthorized_state_mutation else "enforced",
        ),
        _check(
            "evidence.not_fabricated",
            "tools_and_evidence",
            not observation.fabricated_evidence,
            "no fabricated evidence",
            "fabricated" if observation.fabricated_evidence else "grounded",
        ),
        _check(
            "workflow.bounded",
            "workflow",
            observation.limits_respected,
            "configured limits respected",
            "respected" if observation.limits_respected else "exceeded",
        ),
        _check(
            "audit.present",
            "end_to_end",
            bool(observation.audit_references),
            "traceable audit references",
            str(len(observation.audit_references)),
            evidence=observation.audit_references,
        ),
    ]


def evaluate_scenario(observation: ScenarioObservation) -> ScenarioEvaluation:
    checks = _common_checks(observation)
    if observation.scenario_id == "golden-1-low-risk":
        checks.extend(
            [
                _check(
                    "policy.grounded",
                    "policy_rag",
                    bool(observation.policy_citations),
                    "policy citations",
                    str(len(observation.policy_citations)),
                ),
                _check(
                    "verification.not_unnecessary",
                    "agents",
                    not observation.verification_requested,
                    "no verification request",
                    str(observation.verification_requested),
                ),
                _check(
                    "decision.owner",
                    "decision",
                    observation.recommendation is not None
                    and observation.recommendation_writer == "decision_engine",
                    "Decision Engine recommendation",
                    f"{observation.recommendation_writer}:{observation.recommendation}",
                ),
                _check(
                    "review.not_required",
                    "workflow",
                    not observation.mandatory_human_review,
                    "no mandatory review",
                    str(observation.mandatory_human_review),
                ),
                _check(
                    "explanation.grounded",
                    "agents",
                    observation.explanation_grounded,
                    "grounded explanation",
                    str(observation.explanation_grounded),
                ),
            ]
        )
    elif observation.scenario_id == "golden-2-income-verification":
        checks.extend(
            [
                _check(
                    "verification.reported_preserved",
                    "state",
                    observation.reported_income == 150000,
                    "reported_income=150000",
                    str(observation.reported_income),
                ),
                _check(
                    "verification.verified_separate",
                    "state",
                    observation.verified_income == 98000
                    and observation.reported_income != observation.verified_income,
                    "separate verified_income=98000",
                    str(observation.verified_income),
                ),
                _check(
                    "verification.raw_evidence",
                    "tools_and_evidence",
                    observation.raw_verification_evidence,
                    "tool-returned raw evidence",
                    str(observation.raw_verification_evidence),
                ),
                _check(
                    "verification.controlled_commit",
                    "deterministic_controls",
                    observation.deterministic_verification_commit,
                    "deterministic protected commit",
                    str(observation.deterministic_verification_commit),
                ),
                _check(
                    "rerun.model_and_policy",
                    "end_to_end",
                    observation.model_run_count >= 2
                    and observation.policy_run_count >= 2,
                    "model and policy rerun",
                    f"model={observation.model_run_count},policy={observation.policy_run_count}",
                ),
                _check(
                    "decision.manual_review",
                    "decision",
                    observation.recommendation == "MANUAL_REVIEW"
                    and observation.recommendation_writer == "decision_engine",
                    "Decision Engine MANUAL_REVIEW",
                    f"{observation.recommendation_writer}:{observation.recommendation}",
                ),
                _check(
                    "review.enforced",
                    "workflow",
                    observation.mandatory_human_review
                    and observation.escalation_performed,
                    "mandatory review and controlled escalation",
                    f"review={observation.mandatory_human_review},escalation={observation.escalation_performed}",
                ),
            ]
        )
    elif observation.scenario_id == "golden-3-policy-conflict":
        safe_route = observation.mandatory_human_review and (
            observation.recommendation in {None, "MANUAL_REVIEW"}
        )
        checks.extend(
            [
                _check(
                    "policy.conflict_preserved",
                    "policy_rag",
                    bool(observation.policy_conflicts),
                    "explicit unresolved conflict",
                    str(len(observation.policy_conflicts)),
                ),
                _check(
                    "policy.cited",
                    "policy_rag",
                    bool(observation.policy_citations),
                    "versioned policy citations",
                    str(len(observation.policy_citations)),
                ),
                _check(
                    "conflict.safe_route",
                    "workflow",
                    safe_route,
                    "mandatory human review without approval",
                    f"review={observation.mandatory_human_review},recommendation={observation.recommendation}",
                ),
                _check(
                    "escalation.controlled",
                    "agents",
                    observation.escalation_performed,
                    "controlled escalation",
                    str(observation.escalation_performed),
                ),
            ]
        )
    else:
        raise ValueError(f"unknown Golden Demo scenario: {observation.scenario_id}")
    status = "pass" if all(item.status == "pass" for item in checks) else "fail"
    return ScenarioEvaluation(observation.scenario_id, status, tuple(checks))


def evaluate_golden_scenarios(
    config: EvaluationConfig,
    observations: tuple[ScenarioObservation, ...],
    *,
    quantitative_metrics: dict[str, float] | None = None,
    evaluated_at: datetime | None = None,
) -> EvaluationReport:
    """Evaluate all three contracts; no average can mask a failed invariant."""

    config.validate()
    expected = {
        "golden-1-low-risk",
        "golden-2-income-verification",
        "golden-3-policy-conflict",
    }
    actual = {item.scenario_id for item in observations}
    if actual != expected or len(observations) != len(expected):
        raise ValueError("exactly one observation for each Golden Demo is required")
    scenarios = tuple(evaluate_scenario(item) for item in observations)
    status = "pass" if all(item.status == "pass" for item in scenarios) else "fail"
    return EvaluationReport(
        config=config,
        status=status,
        evaluated_at=evaluated_at or datetime.now(UTC),
        scenarios=scenarios,
        quantitative_metrics=dict(quantitative_metrics or {}),
    )
