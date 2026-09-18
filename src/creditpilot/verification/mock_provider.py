"""Deterministic synthetic verification provider for local demonstrations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from creditpilot.state.schemas import _freeze_mapping, validate_no_identity_pii


@dataclass(frozen=True, slots=True)
class MockVerificationProvider:
    """Look up injected synthetic evidence without network or identity PII."""

    records: Mapping[str, Mapping[str, Mapping[str, Any]]]
    provider_name: str = "creditpilot-synthetic-verification-v1"

    def __post_init__(self) -> None:
        validate_no_identity_pii(self.records, "mock_verification_records")
        object.__setattr__(self, "records", _freeze_mapping(self.records))

    def obtain(
        self, application_id: str, evidence_type: str
    ) -> Mapping[str, Any] | None:
        application = self.records.get(application_id)
        if application is None:
            return None
        return application.get(evidence_type)
