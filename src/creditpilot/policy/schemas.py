"""Typed physical schema for approved synthetic policy sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SYNTHETIC_NOTICE_MARKER = "Fictional demonstration policy only."
STABLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class SyntheticPolicySection:
    section_id: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class SyntheticPolicyDocument:
    policy_document_id: str
    title: str
    policy_version: str
    effective_date: str
    synthetic_policy_notice: str
    provenance: str
    sections: tuple[SyntheticPolicySection, ...]


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    chunk_id: str
    source_document: str
    document_title: str
    section_or_chunk_reference: str
    section_title: str
    policy_version: str
    effective_date: str
    synthetic_policy_notice: str
    text: str


@dataclass(frozen=True, slots=True)
class PolicyEvidenceMatch:
    source_document: str
    document_title: str
    section_or_chunk_reference: str
    section_title: str
    policy_version: str
    effective_date: str
    synthetic_policy_notice: str
    text: str
    retrieval_score: float


def _required_text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"policy field {field} must be non-empty text")
    return value.strip()


def _parse_document(path: Path) -> SyntheticPolicyDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy document must be a JSON object")
    allowed_document_fields = {
        "policy_document_id",
        "title",
        "policy_version",
        "effective_date",
        "synthetic_policy_notice",
        "provenance",
        "sections",
    }
    if set(payload) != allowed_document_fields:
        raise ValueError("policy document fields do not match the approved schema")
    document_id = _required_text(payload, "policy_document_id")
    policy_version = _required_text(payload, "policy_version")
    if not STABLE_ID_PATTERN.fullmatch(document_id):
        raise ValueError("policy_document_id must be a stable lowercase identifier")
    notice = _required_text(payload, "synthetic_policy_notice")
    if SYNTHETIC_NOTICE_MARKER not in notice:
        raise ValueError("policy document lacks the required synthetic notice")
    effective_date = _required_text(payload, "effective_date")
    date.fromisoformat(effective_date)
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("policy document must contain sections")
    sections: list[SyntheticPolicySection] = []
    seen: set[str] = set()
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            raise ValueError("policy section must be an object")
        if set(raw_section) != {"section_id", "title", "text"}:
            raise ValueError("policy section fields do not match the approved schema")
        section_id = _required_text(raw_section, "section_id")
        if not STABLE_ID_PATTERN.fullmatch(section_id) or section_id in seen:
            raise ValueError("policy section IDs must be unique stable identifiers")
        seen.add(section_id)
        sections.append(
            SyntheticPolicySection(
                section_id=section_id,
                title=_required_text(raw_section, "title"),
                text=_required_text(raw_section, "text"),
            )
        )
    return SyntheticPolicyDocument(
        policy_document_id=document_id,
        title=_required_text(payload, "title"),
        policy_version=policy_version,
        effective_date=effective_date,
        synthetic_policy_notice=notice,
        provenance=_required_text(payload, "provenance"),
        sections=tuple(sections),
    )


def load_policy_documents(directory: Path) -> tuple[SyntheticPolicyDocument, ...]:
    """Load and validate every synthetic JSON policy document deterministically."""

    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("synthetic policy corpus is empty")
    documents = tuple(_parse_document(path) for path in paths)
    document_ids = [document.policy_document_id for document in documents]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("policy document IDs must be unique")
    return documents


def section_chunks(
    documents: tuple[SyntheticPolicyDocument, ...],
) -> tuple[PolicyChunk, ...]:
    """Create exactly one stable retrieval chunk for each authored section."""

    return tuple(
        PolicyChunk(
            chunk_id=f"{document.policy_document_id}::{section.section_id}",
            source_document=document.policy_document_id,
            document_title=document.title,
            section_or_chunk_reference=section.section_id,
            section_title=section.title,
            policy_version=document.policy_version,
            effective_date=document.effective_date,
            synthetic_policy_notice=document.synthetic_policy_notice,
            text=section.text,
        )
        for document in documents
        for section in document.sections
    )
