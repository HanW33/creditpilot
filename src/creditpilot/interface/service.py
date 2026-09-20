"""Deterministic application service for analyst-facing operations."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from creditpilot.interface.repository import (
    HumanReviewRecord,
    InMemoryCaseRepository,
)
from creditpilot.state import ProtectedStateController, create_credit_state
from creditpilot.state.schemas import CreditState, validate_no_identity_pii
from creditpilot.state.workflow import WorkflowControlConfig, WorkflowController

HUMAN_REVIEW_OUTCOMES = frozenset(
    {"ACKNOWLEDGED", "RETURN_FOR_INFORMATION", "CLOSED_AFTER_REVIEW"}
)
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


class InterfaceValidationError(ValueError):
    """Raised when an analyst-interface operation violates its contract."""


class AnalystInterfaceService:
    def __init__(self, repository: InMemoryCaseRepository) -> None:
        self.repository = repository
        self.state_controller = ProtectedStateController()
        self.workflow_controller = WorkflowController(
            WorkflowControlConfig(
                allowed_transitions=frozenset({(None, "intake")}),
                max_investigation_iterations=2,
                max_tool_calls=4,
                max_retries=2,
            )
        )

    def create_case(
        self,
        *,
        application_id: str,
        customer_token: str,
        reported_values: dict[str, Any],
        sanitized_attributes: dict[str, Any],
        source_reference: str,
    ) -> CreditState:
        state = create_credit_state(
            application_id=application_id,
            customer_token=customer_token,
            reported_values=reported_values,
            sanitized_attributes=sanitized_attributes,
            source_reference=source_reference,
        )
        self.repository.add(state)
        return state

    def require_demo_review(self, application_id: str, reason: str) -> CreditState:
        if not reason.strip() or EMAIL_PATTERN.search(reason):
            raise InterfaceValidationError("review reason must be sanitized")
        state = self.repository.get(application_id)
        state = self.workflow_controller.require_human_review(
            state,
            reason=reason,
            written_by="workflow_controller",
            expected_state_version=state.state_metadata.state_version,
        )
        self.repository.save(state)
        return state

    def record_human_review(
        self,
        application_id: str,
        *,
        outcome: str,
        rationale: str,
        reviewer_token: str,
        expected_state_version: int,
        idempotency_key: str,
        actor_role: str,
        now: datetime | None = None,
    ) -> tuple[CreditState, HumanReviewRecord, bool]:
        if actor_role != "authorized_human_analyst":
            raise PermissionError("authorized human analyst role is required")
        if outcome not in HUMAN_REVIEW_OUTCOMES:
            raise InterfaceValidationError("unsupported human review outcome")
        if not rationale.strip() or EMAIL_PATTERN.search(rationale):
            raise InterfaceValidationError("rationale must be non-empty and sanitized")
        validate_no_identity_pii({"rationale": rationale})
        if not reviewer_token or not reviewer_token.startswith("analyst-token-"):
            raise InterfaceValidationError("opaque reviewer token is required")
        if not idempotency_key:
            raise InterfaceValidationError("idempotency key is required")
        replay = self.repository.review_for_key(idempotency_key)
        if replay is not None:
            if (
                replay.application_id != application_id
                or replay.outcome != outcome
                or replay.rationale != rationale
                or replay.reviewer_token != reviewer_token
                or replay.reviewed_state_version != expected_state_version
            ):
                raise InterfaceValidationError("idempotency key payload conflict")
            return self.repository.get(application_id), replay, True
        state = self.repository.get(application_id)
        recorded_at = now or datetime.now(UTC)
        digest = sha256(f"{application_id}:{idempotency_key}".encode()).hexdigest()[:16]
        reference = f"human-review://synthetic/{digest}"
        state = self.state_controller.commit_human_review_outcome(
            state,
            outcome_reference=reference,
            written_by=actor_role,
            expected_state_version=expected_state_version,
        )
        state = self.state_controller.append_audit_reference(
            state,
            category="human_review_references",
            reference=reference,
            written_by="audit_persistence",
            expected_state_version=state.state_metadata.state_version,
        )
        record = HumanReviewRecord(
            reference=reference,
            application_id=application_id,
            outcome=outcome,
            rationale=rationale,
            reviewer_token=reviewer_token,
            reviewed_state_version=expected_state_version,
            recorded_at=recorded_at,
            idempotency_key=idempotency_key,
        )
        self.repository.save(state)
        self.repository.add_review(record)
        return state, record, False


def case_summary(state: CreditState) -> dict[str, Any]:
    """Expose only the approved, sanitized analyst view."""

    model = state.quantitative_model_state
    policy = state.policy_state
    verification = state.verification_state
    recommendation = state.recommendation_state
    escalation = state.escalation_state
    return {
        "application_id": state.identity_references.application_id,
        "case_id": state.identity_references.case_id,
        "state_version": state.state_metadata.state_version,
        "schema_version": state.state_metadata.schema_version,
        "updated_at": state.state_metadata.updated_at,
        "reported_values": dict(state.application_data.reported_values),
        "sanitized_attributes": dict(state.application_data.sanitized_attributes),
        "model": {
            "status": model.status,
            "pd_score": model.pd_score,
            "risk_band": model.risk_band,
            "shap_risk_factors": dict(model.shap_risk_factors),
            "model_version": model.model_version,
        },
        "policy": {
            "status": policy.status,
            "findings": policy.findings,
            "required_evidence": policy.required_evidence,
            "conflicts": policy.conflicts,
            "citations": [
                {
                    "source_document": item.source_document,
                    "section": item.section_or_chunk_reference,
                    "policy_version": item.policy_version,
                }
                for item in policy.retrieved_evidence
            ],
        },
        "verification": {
            "verified_values": dict(verification.verified_values),
            "conflicts": verification.conflicts,
            "raw_evidence_references": tuple(
                item.raw_evidence_reference for item in verification.tool_results
            ),
        },
        "workflow": {
            "current_stage": state.workflow_state.current_stage,
            "mandatory_human_review": state.workflow_state.mandatory_human_review,
            "mandatory_review_reasons": state.workflow_state.mandatory_review_reasons,
        },
        "recommendation": asdict(recommendation),
        "explanation": state.explanation_state.explanation,
        "escalation": {
            "status": escalation.status,
            "reasons": escalation.reasons,
            "review_package_reference": escalation.review_package_reference,
            "human_review_outcome_reference": (
                escalation.human_review_outcome_reference
            ),
        },
        "audit": asdict(state.governance_audit_references),
        "synthetic_notice": "Synthetic decision-support data only.",
    }
