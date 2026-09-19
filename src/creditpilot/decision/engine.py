"""Explicit deterministic rules for synthetic decision-support outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creditpilot.state import (
    CreditState,
    DecisionEligibility,
    ProtectedStateController,
    WorkflowController,
)
from creditpilot.state.schemas import RecommendationState, utc_now

ALLOWED_RECOMMENDATIONS = frozenset(
    {
        "APPROVAL_RECOMMENDATION",
        "MANUAL_REVIEW",
        "REQUEST_MORE_INFORMATION",
        "HIGH_RISK_REVIEW",
    }
)


class DecisionEngineError(ValueError):
    """Raised when eligibility, evidence, or explicit rules are invalid."""


@dataclass(frozen=True, slots=True)
class DecisionEngineConfig:
    rule_version: str
    synthetic_policy_notice: str
    approval_max_pd: float
    high_risk_min_pd: float

    def validate(self) -> None:
        if not self.rule_version:
            raise DecisionEngineError("decision rule version is required")
        if "synthetic" not in self.synthetic_policy_notice.lower():
            raise DecisionEngineError(
                "decision thresholds must be identified as synthetic"
            )
        if not 0 <= self.approval_max_pd < self.high_risk_min_pd <= 1:
            raise DecisionEngineError("synthetic PD thresholds are invalid")


@dataclass(frozen=True, slots=True)
class DecisionAuditRecord:
    audit_reference: str
    application_id: str
    input_state_version: int
    rule_version: str
    recommendation: str
    decision_rule: str
    pd_score: float
    approval_max_pd: float
    high_risk_min_pd: float
    synthetic_policy_notice: str
    decided_at: datetime
    resulting_state_version: int


@dataclass(frozen=True, slots=True)
class DecisionStepResult:
    state: CreditState
    status: str
    eligibility: DecisionEligibility
    recommendation: RecommendationState | None
    audit: DecisionAuditRecord | None


def make_recommendation(
    state: CreditState,
    eligibility: DecisionEligibility,
    config: DecisionEngineConfig,
) -> RecommendationState:
    """Apply caller-approved synthetic thresholds without agent reasoning."""

    config.validate()
    if eligibility.input_state_version != state.state_metadata.state_version:
        raise DecisionEngineError("decision eligibility result is stale")
    if not eligibility.eligible:
        raise DecisionEngineError("ineligible evidence cannot enter Decision Engine")
    pd_score = state.quantitative_model_state.pd_score
    if pd_score is None or not 0 <= pd_score <= 1:
        raise DecisionEngineError("a valid committed PD is required")
    if pd_score <= config.approval_max_pd:
        recommendation = "APPROVAL_RECOMMENDATION"
        rule = "pd_at_or_below_synthetic_approval_max"
        reason = "Committed PD is within the configured synthetic low-risk range."
    elif pd_score >= config.high_risk_min_pd:
        recommendation = "HIGH_RISK_REVIEW"
        rule = "pd_at_or_above_synthetic_high_risk_min"
        reason = "Committed PD is within the configured synthetic high-risk range."
    else:
        recommendation = "MANUAL_REVIEW"
        rule = "pd_between_synthetic_review_thresholds"
        reason = "Committed PD falls between the configured synthetic thresholds."
    if recommendation not in ALLOWED_RECOMMENDATIONS:
        raise DecisionEngineError("decision outcome is not architecture-approved")
    return RecommendationState(
        recommendation=recommendation,
        decision_rule=f"{config.rule_version}:{rule}",
        decision_reason=reason,
        input_state_version=state.state_metadata.state_version,
        decided_at=utc_now(),
    )


def record_decision_audit(
    state: CreditState,
    result: RecommendationState,
    config: DecisionEngineConfig,
    controller: ProtectedStateController,
) -> tuple[CreditState, DecisionAuditRecord]:
    """Link a committed recommendation to a reference-only audit record."""

    if state.recommendation_state != result:
        raise DecisionEngineError("decision audit requires the committed result")
    if result.recommendation is None or result.decision_rule is None or (
        result.decided_at is None
    ):
        raise DecisionEngineError("decision audit provenance is incomplete")
    reference = (
        f"decision://{state.identity_references.application_id}/"
        f"{result.input_state_version}/{config.rule_version}"
    )
    committed = controller.append_audit_reference(
        state,
        category="decision_references",
        reference=reference,
        written_by="audit_persistence",
        expected_state_version=state.state_metadata.state_version,
    )
    record = DecisionAuditRecord(
        audit_reference=reference,
        application_id=state.identity_references.application_id,
        input_state_version=result.input_state_version or 0,
        rule_version=config.rule_version,
        recommendation=result.recommendation,
        decision_rule=result.decision_rule,
        pd_score=float(state.quantitative_model_state.pd_score),
        approval_max_pd=config.approval_max_pd,
        high_risk_min_pd=config.high_risk_min_pd,
        synthetic_policy_notice=config.synthetic_policy_notice,
        decided_at=result.decided_at,
        resulting_state_version=committed.state_metadata.state_version,
    )
    return committed, record


def run_decision_step(
    state: CreditState,
    *,
    config: DecisionEngineConfig,
    review_recommendations: frozenset[str],
    state_controller: ProtectedStateController,
    workflow_controller: WorkflowController,
) -> DecisionStepResult:
    """Enforce eligibility, decision ownership, audit, and review ordering."""

    eligibility = workflow_controller.check_decision_eligibility(state)
    if not eligibility.eligible:
        reason = "decision ineligible: " + "; ".join(eligibility.reasons)
        state = workflow_controller.require_human_review(
            state,
            reason=reason,
            written_by="workflow_controller",
            expected_state_version=state.state_metadata.state_version,
        )
        return DecisionStepResult(
            state=state,
            status="ineligible",
            eligibility=eligibility,
            recommendation=None,
            audit=None,
        )
    recommendation = make_recommendation(state, eligibility, config)
    state = state_controller.commit_recommendation(
        state,
        recommendation,
        written_by="decision_engine",
        expected_state_version=state.state_metadata.state_version,
    )
    state, audit = record_decision_audit(
        state, recommendation, config, state_controller
    )
    state = workflow_controller.enforce_post_decision_review(
        state,
        review_recommendations=review_recommendations,
        written_by="workflow_controller",
        expected_state_version=state.state_metadata.state_version,
    )
    return DecisionStepResult(
        state=state,
        status="complete",
        eligibility=eligibility,
        recommendation=recommendation,
        audit=audit,
    )
