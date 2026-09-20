"""Replaceable in-memory persistence for the synthetic V1 interface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creditpilot.state import CreditState


class CaseNotFoundError(KeyError):
    """Raised when a synthetic case does not exist."""


@dataclass(frozen=True, slots=True)
class HumanReviewRecord:
    reference: str
    application_id: str
    outcome: str
    rationale: str
    reviewer_token: str
    reviewed_state_version: int
    recorded_at: datetime
    idempotency_key: str


class InMemoryCaseRepository:
    """Store demo state locally without selecting a production database."""

    def __init__(self) -> None:
        self._cases: dict[str, CreditState] = {}
        self._reviews: dict[str, HumanReviewRecord] = {}
        self._idempotency: dict[str, str] = {}

    def add(self, state: CreditState) -> None:
        application_id = state.identity_references.application_id
        if application_id in self._cases:
            raise ValueError("application_id already exists")
        self._cases[application_id] = state

    def get(self, application_id: str) -> CreditState:
        try:
            return self._cases[application_id]
        except KeyError as error:
            raise CaseNotFoundError(application_id) from error

    def save(self, state: CreditState) -> None:
        application_id = state.identity_references.application_id
        if application_id not in self._cases:
            raise CaseNotFoundError(application_id)
        self._cases[application_id] = state

    def list(self) -> tuple[CreditState, ...]:
        return tuple(self._cases[key] for key in sorted(self._cases))

    def review_for_key(self, idempotency_key: str) -> HumanReviewRecord | None:
        reference = self._idempotency.get(idempotency_key)
        return self._reviews.get(reference) if reference else None

    def add_review(self, record: HumanReviewRecord) -> None:
        self._reviews[record.reference] = record
        self._idempotency[record.idempotency_key] = record.reference

    def get_review(self, reference: str) -> HumanReviewRecord | None:
        return self._reviews.get(reference)
