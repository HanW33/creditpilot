"""Provider-independent Policy Agent with deterministic grounding validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol

from creditpilot.agents.contracts import AgentFailure, AgentInvocation
from creditpilot.state.schemas import StateUpdateProposal, _freeze_mapping, utc_now
from creditpilot.tools.contracts import ToolResult

POLICY_OUTPUT_FIELDS = frozenset(
    {
        "finding_id",
        "status",
        "applicable_policy_evidence",
        "interpretation",
        "required_evidence",
        "policy_constraints",
        "conflicts",
        "unresolved_items",
        "source_references",
        "policy_versions",
    }
)
ALLOWED_POLICY_STATUSES = frozenset({"complete", "conflict", "unresolved"})
THRESHOLD_PATTERN = re.compile(r"(?:[$£€]\s*\d|\d+(?:\.\d+)?\s*%|[<>]=?\s*\d)")
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
AUTHORITY_PATTERN = re.compile(
    r"\b(?:approve|decline|reject)\s+(?:the\s+)?application\b",
    re.IGNORECASE,
)


class PolicyAgentValidationError(ValueError):
    """Raised when untrusted Policy Agent output violates its contract."""


@dataclass(frozen=True, slots=True)
class PolicyAgentContext:
    state_version: int
    authorized_state: Mapping[str, Any]
    retrieved_evidence: tuple[Mapping[str, Any], ...]
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "authorized_state", _freeze_mapping(self.authorized_state)
        )
        object.__setattr__(
            self,
            "retrieved_evidence",
            tuple(_freeze_mapping(item) for item in self.retrieved_evidence),
        )


class PolicyReasoningBackend(Protocol):
    def generate_policy_finding(
        self, context: PolicyAgentContext
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PolicyAgentOutput:
    invocation_id: str
    agent_role: str
    status: str
    reasoning_summary: str
    finding_id: str | None
    applicable_policy_evidence: tuple[str, ...]
    interpretation: str | None
    required_evidence: tuple[str, ...]
    policy_constraints: tuple[str, ...]
    conflicts: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    source_references: tuple[str, ...]
    policy_versions: tuple[str, ...]
    proposed_actions: tuple[str, ...]
    created_at: datetime
    failure: AgentFailure | None = None


def _as_text_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise PolicyAgentValidationError(f"{field} must be a tuple of non-empty text")
    return tuple(item.strip() for item in value)


def _validate_text_authority(texts: tuple[str, ...]) -> None:
    for text in texts:
        if THRESHOLD_PATTERN.search(text):
            raise PolicyAgentValidationError("Policy Agent output invents a threshold")
        if AUTHORITY_PATTERN.search(text):
            raise PolicyAgentValidationError(
                "Policy Agent output exceeds recommendation authority"
            )
        if EMAIL_PATTERN.search(text):
            raise PolicyAgentValidationError(
                "Policy Agent output contains identity PII"
            )


def _canonical_reference(item: Mapping[str, Any]) -> str:
    return (
        f"policy://{item['source_document']}/"
        f"{item['section_or_chunk_reference']}@{item['policy_version']}"
    )


def _validate_draft(
    draft: Mapping[str, Any],
    context: PolicyAgentContext,
    supported_evidence_types: frozenset[str],
) -> PolicyAgentOutput:
    if set(draft) != POLICY_OUTPUT_FIELDS:
        raise PolicyAgentValidationError("Policy Agent output fields are invalid")
    status = draft["status"]
    if status not in ALLOWED_POLICY_STATUSES:
        raise PolicyAgentValidationError("Policy Agent status is invalid")
    finding_id = draft["finding_id"]
    interpretation = draft["interpretation"]
    if not isinstance(finding_id, str) or not finding_id.strip():
        raise PolicyAgentValidationError("finding_id must be non-empty")
    if not isinstance(interpretation, str) or not interpretation.strip():
        raise PolicyAgentValidationError("interpretation must be non-empty")

    applicable = _as_text_tuple(
        draft["applicable_policy_evidence"], "applicable_policy_evidence"
    )
    required = _as_text_tuple(draft["required_evidence"], "required_evidence")
    constraints = _as_text_tuple(draft["policy_constraints"], "policy_constraints")
    conflicts = _as_text_tuple(draft["conflicts"], "conflicts")
    unresolved = _as_text_tuple(draft["unresolved_items"], "unresolved_items")
    sources = _as_text_tuple(draft["source_references"], "source_references")
    versions = _as_text_tuple(draft["policy_versions"], "policy_versions")

    known_references = set(context.evidence_references)
    if not applicable or not sources:
        raise PolicyAgentValidationError("material findings require citations")
    if not set(applicable).issubset(known_references) or not set(sources).issubset(
        known_references
    ):
        raise PolicyAgentValidationError("Policy Agent cites unknown evidence")
    if not set(applicable).issubset(sources):
        raise PolicyAgentValidationError(
            "applicable policy evidence must be included in source references"
        )
    evidence_by_reference = {
        _canonical_reference(item): item for item in context.retrieved_evidence
    }
    cited_versions = {
        str(evidence_by_reference[reference]["policy_version"])
        for reference in sources
        if reference in evidence_by_reference
    }
    if set(versions) != cited_versions:
        raise PolicyAgentValidationError("policy versions do not match cited evidence")
    if not set(required).issubset(supported_evidence_types):
        raise PolicyAgentValidationError("Policy Agent requests unsupported evidence")
    if status == "conflict" and not conflicts:
        raise PolicyAgentValidationError(
            "conflict status requires an explicit conflict"
        )
    if status == "unresolved" and not unresolved:
        raise PolicyAgentValidationError(
            "unresolved status requires an explicit unresolved item"
        )
    _validate_text_authority(
        (interpretation.strip(), *constraints, *conflicts, *unresolved)
    )
    return PolicyAgentOutput(
        invocation_id="",
        agent_role="policy_agent",
        status=status,
        reasoning_summary="Policy interpretation grounded in cited synthetic evidence.",
        finding_id=finding_id.strip(),
        applicable_policy_evidence=applicable,
        interpretation=interpretation.strip(),
        required_evidence=required,
        policy_constraints=constraints,
        conflicts=conflicts,
        unresolved_items=unresolved,
        source_references=sources,
        policy_versions=versions,
        proposed_actions=(),
        created_at=utc_now(),
    )


def _failure_output(
    invocation: AgentInvocation, code: str, message: str
) -> PolicyAgentOutput:
    return PolicyAgentOutput(
        invocation_id=invocation.invocation_id,
        agent_role="policy_agent",
        status="failure",
        reasoning_summary="Policy analysis did not produce a valid finding.",
        finding_id=None,
        applicable_policy_evidence=(),
        interpretation=None,
        required_evidence=(),
        policy_constraints=(),
        conflicts=(),
        unresolved_items=(message,),
        source_references=(),
        policy_versions=(),
        proposed_actions=(),
        created_at=utc_now(),
        failure=AgentFailure(code=code, message=message),
    )


def run_policy_agent(
    invocation: AgentInvocation,
    retrieval_result: ToolResult,
    backend: PolicyReasoningBackend,
    *,
    supported_evidence_types: frozenset[str],
) -> PolicyAgentOutput:
    """Run an injected backend and deterministically validate its untrusted output."""

    if invocation.agent_role != "policy_agent":
        raise PolicyAgentValidationError("invocation is not for the Policy Agent")
    if invocation.permitted_tools - {"search_credit_policy"}:
        raise PolicyAgentValidationError("Policy Agent has an unapproved tool")
    case_reference = invocation.authorized_state_view.data.get("case_reference", {})
    if case_reference.get("application_id") != invocation.application_id:
        raise PolicyAgentValidationError("agent application reference is inconsistent")
    if retrieval_result.tool_name != "search_credit_policy":
        raise PolicyAgentValidationError("Policy Agent received the wrong tool result")
    if retrieval_result.status != "success":
        return _failure_output(
            invocation,
            "policy_retrieval_failed",
            "Synthetic policy retrieval did not return usable evidence.",
        )
    retrieval_state_version = retrieval_result.result.get("input_state_version")
    if not isinstance(retrieval_state_version, int) or (
        retrieval_state_version > invocation.input_state_version
    ):
        raise PolicyAgentValidationError(
            "policy retrieval state version is inconsistent"
        )
    evidence = retrieval_result.result.get("evidence")
    if not isinstance(evidence, tuple) or not evidence:
        return _failure_output(
            invocation,
            "policy_evidence_missing",
            "Synthetic policy evidence is missing.",
        )
    context = PolicyAgentContext(
        state_version=invocation.input_state_version,
        authorized_state=invocation.authorized_state_view.data,
        retrieved_evidence=evidence,
        evidence_references=retrieval_result.evidence_references,
    )
    try:
        draft = backend.generate_policy_finding(context)
        if not isinstance(draft, Mapping):
            raise PolicyAgentValidationError("Policy backend output must be a mapping")
        output = _validate_draft(draft, context, supported_evidence_types)
    except PolicyAgentValidationError:
        raise
    except Exception as error:
        return _failure_output(
            invocation,
            "policy_backend_failed",
            f"Policy reasoning backend failed: {type(error).__name__}",
        )
    return replace(
        output,
        invocation_id=invocation.invocation_id,
        created_at=utc_now(),
    )


def policy_output_to_state_proposal(
    output: PolicyAgentOutput, *, expected_state_version: int
) -> StateUpdateProposal:
    """Convert only a valid non-failure output into a controlled state proposal."""

    if output.failure is not None or output.finding_id is None or (
        output.interpretation is None
    ):
        raise PolicyAgentValidationError(
            "failed Policy Agent output cannot be proposed"
        )
    return StateUpdateProposal(
        proposal_id=output.finding_id,
        target_domain="policy_state.findings",
        proposed_changes={
            "status": output.status,
            "findings": (output.interpretation, *output.policy_constraints),
            "required_evidence": output.required_evidence,
            "conflicts": (*output.conflicts, *output.unresolved_items),
        },
        basis_references=output.source_references,
        proposed_by="policy_agent",
        expected_state_version=expected_state_version,
        proposed_at=output.created_at,
    )
