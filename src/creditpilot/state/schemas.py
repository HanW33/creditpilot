"""Physical Phase 2 schemas derived from the approved logical State Design."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

SCHEMA_VERSION = "credit-state-v1"
IDENTITY_PII_KEYS = frozenset(
    {
        "name",
        "full_name",
        "email",
        "address",
        "phone",
        "ssn",
        "tax_id",
        "identity_number",
    }
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_value(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    return value


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return _freeze_value(value)


@dataclass(frozen=True, slots=True)
class FailureRecord:
    code: str
    message: str
    occurred_at: datetime
    source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class StateMetadata:
    schema_version: str
    state_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IdentityReferences:
    application_id: str
    customer_token: str
    case_id: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationData:
    reported_values: Mapping[str, Any]
    sanitized_attributes: Mapping[str, Any]
    source_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reported_values", _freeze_mapping(self.reported_values)
        )
        object.__setattr__(
            self, "sanitized_attributes", _freeze_mapping(self.sanitized_attributes)
        )


@dataclass(frozen=True, slots=True)
class ValidationState:
    status: str = "not_run"
    findings: tuple[str, ...] = ()
    failure: FailureRecord | None = None
    validated_at: datetime | None = None
    validator_version: str | None = None


@dataclass(frozen=True, slots=True)
class QuantitativeModelState:
    status: str = "not_run"
    pd_score: float | None = None
    risk_band: str | None = None
    shap_risk_factors: Mapping[str, float] = field(default_factory=dict)
    model_version: str | None = None
    model_timestamp: datetime | None = None
    input_state_version: int | None = None
    failure: FailureRecord | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "shap_risk_factors", _freeze_mapping(self.shap_risk_factors)
        )


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    source_document: str
    section_or_chunk_reference: str
    policy_version: str
    retrieval_score: float | None = None
    effective_date: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyState:
    status: str = "not_run"
    retrieved_evidence: tuple[PolicyEvidence, ...] = ()
    findings: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    evaluated_at: datetime | None = None
    failure: FailureRecord | None = None


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    request_id: str
    evidence_required: str
    requested_by: str
    requested_at: datetime
    status: str


@dataclass(frozen=True, slots=True)
class VerificationToolResult:
    result_id: str
    request_id: str
    tool_name: str
    raw_evidence_reference: str
    status: str
    returned_at: datetime
    failure: FailureRecord | None = None


@dataclass(frozen=True, slots=True)
class VerificationInterpretation:
    interpretation_id: str
    result_id: str
    structured_evidence: Mapping[str, Any]
    proposed_state_update: Mapping[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "structured_evidence", _freeze_mapping(self.structured_evidence)
        )
        object.__setattr__(
            self, "proposed_state_update", _freeze_mapping(self.proposed_state_update)
        )


@dataclass(frozen=True, slots=True)
class VerificationState:
    requests: tuple[VerificationRequest, ...] = ()
    tool_results: tuple[VerificationToolResult, ...] = ()
    interpretations: tuple[VerificationInterpretation, ...] = ()
    verified_values: Mapping[str, Any] = field(default_factory=dict)
    conflicts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "verified_values", _freeze_mapping(self.verified_values)
        )


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    from_stage: str
    to_stage: str
    permitted: bool
    reason: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class WorkflowState:
    current_stage: str | None = None
    proposed_next_action: str | None = None
    mandatory_human_review: bool = False
    mandatory_review_reasons: tuple[str, ...] = ()
    investigation_iteration_count: int = 0
    tool_call_count: int = 0
    retry_count: int = 0
    active_request_ids: tuple[str, ...] = ()
    last_transition: WorkflowTransition | None = None
    failure: FailureRecord | None = None


@dataclass(frozen=True, slots=True)
class RecommendationState:
    recommendation: str | None = None
    decision_rule: str | None = None
    decision_reason: str | None = None
    input_state_version: int | None = None
    decided_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExplanationState:
    explanation: str | None = None
    input_state_version: int | None = None
    created_at: datetime | None = None
    created_by: str | None = None


@dataclass(frozen=True, slots=True)
class EscalationState:
    status: str = "not_started"
    reasons: tuple[str, ...] = ()
    review_package_reference: str | None = None
    requested_actions: tuple[str, ...] = ()
    action_results: tuple[str, ...] = ()
    human_review_outcome_reference: str | None = None
    timestamps: tuple[datetime, ...] = ()


@dataclass(frozen=True, slots=True)
class GovernanceAuditReferences:
    workflow_event_references: tuple[str, ...] = ()
    agent_output_references: tuple[str, ...] = ()
    tool_call_references: tuple[str, ...] = ()
    model_run_references: tuple[str, ...] = ()
    policy_evidence_references: tuple[str, ...] = ()
    verification_evidence_references: tuple[str, ...] = ()
    decision_references: tuple[str, ...] = ()
    escalation_references: tuple[str, ...] = ()
    human_review_references: tuple[str, ...] = ()
    pii_audit_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreditState:
    state_metadata: StateMetadata
    identity_references: IdentityReferences
    application_data: ApplicationData
    validation_state: ValidationState = field(default_factory=ValidationState)
    quantitative_model_state: QuantitativeModelState = field(
        default_factory=QuantitativeModelState
    )
    policy_state: PolicyState = field(default_factory=PolicyState)
    verification_state: VerificationState = field(default_factory=VerificationState)
    workflow_state: WorkflowState = field(default_factory=WorkflowState)
    recommendation_state: RecommendationState = field(
        default_factory=RecommendationState
    )
    explanation_state: ExplanationState = field(default_factory=ExplanationState)
    escalation_state: EscalationState = field(default_factory=EscalationState)
    governance_audit_references: GovernanceAuditReferences = field(
        default_factory=GovernanceAuditReferences
    )


@dataclass(frozen=True, slots=True)
class StateUpdateProposal:
    proposal_id: str
    target_domain: str
    proposed_changes: Mapping[str, Any]
    basis_references: tuple[str, ...]
    proposed_by: str
    expected_state_version: int
    proposed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "proposed_changes", _freeze_mapping(self.proposed_changes)
        )


def _reject_identity_pii(value: Any, path: str = "CreditState") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key.lower() in IDENTITY_PII_KEYS:
                raise ValueError(f"raw identity PII is prohibited at {path}.{key}")
            _reject_identity_pii(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_identity_pii(child, f"{path}[{index}]")


def create_credit_state(
    *,
    application_id: str,
    customer_token: str,
    reported_values: dict[str, Any],
    sanitized_attributes: dict[str, Any],
    source_reference: str,
    case_id: str | None = None,
    now: datetime | None = None,
) -> CreditState:
    """Create the initial protected state after deterministic PII separation."""

    if not application_id or not customer_token or not source_reference:
        raise ValueError(
            "application_id, customer_token, and source_reference are required"
        )
    _reject_identity_pii(reported_values, "application_data.reported_values")
    _reject_identity_pii(
        sanitized_attributes, "application_data.sanitized_attributes"
    )
    timestamp = now or utc_now()
    return CreditState(
        state_metadata=StateMetadata(
            schema_version=SCHEMA_VERSION,
            state_version=1,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        identity_references=IdentityReferences(
            application_id=application_id,
            customer_token=customer_token,
            case_id=case_id,
        ),
        application_data=ApplicationData(
            reported_values=dict(reported_values),
            sanitized_attributes=dict(sanitized_attributes),
            source_reference=source_reference,
        ),
    )
