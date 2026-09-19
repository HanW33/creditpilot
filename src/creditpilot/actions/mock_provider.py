"""Stateful in-memory action provider with deterministic idempotency."""

from __future__ import annotations


class MockActionProvider:
    """Simulate side effects locally without selecting an external service."""

    provider_name = "creditpilot-synthetic-actions-v1"

    def __init__(self) -> None:
        self._review_cases: dict[str, str] = {}
        self._notifications: dict[str, str] = {}

    def create_review_case(self, idempotency_key: str) -> tuple[str, bool]:
        existing = self._review_cases.get(idempotency_key)
        if existing is not None:
            return existing, True
        reference = f"review-case://synthetic/{len(self._review_cases) + 1}"
        self._review_cases[idempotency_key] = reference
        return reference, False

    def send_notification(self, idempotency_key: str) -> tuple[str, bool]:
        existing = self._notifications.get(idempotency_key)
        if existing is not None:
            return existing, True
        reference = f"notification://synthetic/{len(self._notifications) + 1}"
        self._notifications[idempotency_key] = reference
        return reference, False
