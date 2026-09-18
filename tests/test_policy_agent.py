from datetime import UTC, datetime
from pathlib import Path

import pytest

from creditpilot.agents import (
    AgentInvocation,
    PolicyAgentValidationError,
    policy_output_to_state_proposal,
    record_policy_agent_audit,
    run_policy_agent,
)
from creditpilot.policy import PolicyIndex, load_policy_documents
from creditpilot.policy.schemas import section_chunks
from creditpilot.state import (
    ProtectedStateController,
    build_role_state_view,
    create_credit_state,
)
from creditpilot.tools import (
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
    commit_policy_retrieval_result,
    search_credit_policy,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)
POLICY_DIRECTORY = Path(__file__).parents[1] / "policies"


class DraftBackend:
    def __init__(self, draft):
        self.draft = draft
        self.calls = 0
        self.last_context = None

    def generate_policy_finding(self, context):
        self.calls += 1
        self.last_context = context
        return self.draft


def _state():
    return create_credit_state(
        application_id="SYN-0000009",
        customer_token="customer-token-009",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-9",
        now=NOW,
    )


def _retrieval(state):
    index = PolicyIndex(section_chunks(load_policy_documents(POLICY_DIRECTORY)))
    invocation = ToolInvocation(
        invocation_id="policy-search-agent-1",
        tool_name="search_credit_policy",
        application_id=state.identity_references.application_id,
        case_id=None,
        requested_by="policy_retrieval",
        purpose="Retrieve synthetic income evidence policy",
        input_state_version=state.state_metadata.state_version,
        authorized_scope=frozenset({"policy:search"}),
        arguments={
            "policy_question": "What income evidence is required?",
            "requested_evidence": "verified income",
            "sanitized_context": {"evidence_status": "missing"},
            "top_k": 2,
            "required_policy_versions": (),
        },
        requested_at=NOW,
    )
    permissions = ToolPermissionPolicy(
        callers_by_tool={"search_credit_policy": frozenset({"policy_retrieval"})}
    )
    return search_credit_policy(invocation, state, permissions, index=index)


def _agent_invocation(state) -> AgentInvocation:
    return AgentInvocation(
        invocation_id="policy-agent-1",
        agent_role="policy_agent",
        application_id=state.identity_references.application_id,
        case_id=None,
        input_state_version=state.state_metadata.state_version,
        purpose="Interpret retrieved synthetic income policy",
        authorized_state_view=build_role_state_view(state, "policy_agent"),
        permitted_tools=frozenset({"search_credit_policy"}),
        workflow_constraints={"max_tool_calls": 1},
        invoked_at=NOW,
    )


def _valid_draft(reference: str):
    return {
        "finding_id": "policy-finding-1",
        "status": "complete",
        "applicable_policy_evidence": [reference],
        "interpretation": "The synthetic policy requires verified income evidence.",
        "required_evidence": ["verified_income"],
        "policy_constraints": [
            "Reported and verified income must remain separate and traceable."
        ],
        "conflicts": [],
        "unresolved_items": [],
        "source_references": [reference],
        "policy_versions": ["synthetic-evidence-v1"],
    }


def test_grounded_policy_output_can_commit_through_state_controls() -> None:
    original = _state()
    retrieval = _retrieval(original)
    state = commit_policy_retrieval_result(
        original, retrieval, ProtectedStateController()
    )
    income_reference = next(
        reference
        for reference in retrieval.evidence_references
        if "/income-evidence@" in reference
    )
    backend = DraftBackend(_valid_draft(income_reference))

    output = run_policy_agent(
        _agent_invocation(state),
        retrieval,
        backend,
        supported_evidence_types=frozenset(
            {"verified_income", "verified_employment", "credit_report"}
        ),
    )
    proposal = policy_output_to_state_proposal(
        output, expected_state_version=state.state_metadata.state_version
    )
    committed = ProtectedStateController().commit_policy_findings(state, proposal)

    assert output.required_evidence == ("verified_income",)
    assert committed.policy_state.required_evidence == ("verified_income",)
    assert committed.policy_state.retrieved_evidence
    assert backend.last_context is not None
    assert "recommendation_state" not in backend.last_context.authorized_state


def test_policy_agent_rejects_unknown_citation() -> None:
    state = _state()
    retrieval = _retrieval(state)
    backend = DraftBackend(_valid_draft("policy://invented/section@version"))

    with pytest.raises(PolicyAgentValidationError, match="unknown evidence"):
        run_policy_agent(
            _agent_invocation(state),
            retrieval,
            backend,
            supported_evidence_types=frozenset({"verified_income"}),
        )


def test_policy_agent_rejects_threshold_and_recommendation_authority() -> None:
    state = _state()
    retrieval = _retrieval(state)
    reference = retrieval.evidence_references[0]
    threshold = _valid_draft(reference)
    threshold["interpretation"] = "Require income above $100000."
    with pytest.raises(PolicyAgentValidationError, match="threshold"):
        run_policy_agent(
            _agent_invocation(state),
            retrieval,
            DraftBackend(threshold),
            supported_evidence_types=frozenset({"verified_income"}),
        )

    recommendation = _valid_draft(reference)
    recommendation["interpretation"] = "Approve the application."
    with pytest.raises(PolicyAgentValidationError, match="authority"):
        run_policy_agent(
            _agent_invocation(state),
            retrieval,
            DraftBackend(recommendation),
            supported_evidence_types=frozenset({"verified_income"}),
        )


def test_policy_agent_rejects_unsupported_evidence_type() -> None:
    state = _state()
    retrieval = _retrieval(state)
    reference = retrieval.evidence_references[0]
    draft = _valid_draft(reference)
    draft["required_evidence"] = ["invented_evidence"]

    with pytest.raises(PolicyAgentValidationError, match="unsupported evidence"):
        run_policy_agent(
            _agent_invocation(state),
            retrieval,
            DraftBackend(draft),
            supported_evidence_types=frozenset({"verified_income"}),
        )


def test_policy_agent_requires_explicit_conflict_for_conflict_status() -> None:
    state = _state()
    retrieval = _retrieval(state)
    reference = retrieval.evidence_references[0]
    draft = _valid_draft(reference)
    draft["status"] = "conflict"

    with pytest.raises(PolicyAgentValidationError, match="explicit conflict"):
        run_policy_agent(
            _agent_invocation(state),
            retrieval,
            DraftBackend(draft),
            supported_evidence_types=frozenset({"verified_income"}),
        )


def test_retrieval_failure_does_not_call_backend_or_become_approval() -> None:
    state = _state()
    failed_retrieval = ToolResult(
        invocation_id="failed-search",
        tool_name="search_credit_policy",
        status="unavailable",
        result={},
        evidence_references=(),
        failure=ToolFailure("unavailable", "Synthetic retrieval unavailable"),
        started_at=NOW,
        completed_at=NOW,
        tool_version="search-credit-policy-v1",
    )
    backend = DraftBackend({})

    output = run_policy_agent(
        _agent_invocation(state),
        failed_retrieval,
        backend,
        supported_evidence_types=frozenset({"verified_income"}),
    )

    assert output.status == "failure"
    assert output.failure is not None
    assert output.interpretation is None
    assert backend.calls == 0
    with pytest.raises(PolicyAgentValidationError, match="cannot be proposed"):
        policy_output_to_state_proposal(output, expected_state_version=1)


def test_agent_audit_links_validated_output_by_reference() -> None:
    original = _state()
    retrieval = _retrieval(original)
    state = commit_policy_retrieval_result(
        original, retrieval, ProtectedStateController()
    )
    reference = next(
        item
        for item in retrieval.evidence_references
        if "/income-evidence@" in item
    )
    invocation = _agent_invocation(state)
    output = run_policy_agent(
        invocation,
        retrieval,
        DraftBackend(_valid_draft(reference)),
        supported_evidence_types=frozenset({"verified_income"}),
    )

    committed, audit = record_policy_agent_audit(
        state,
        invocation,
        ProtectedStateController(),
        output=output,
    )

    assert committed.governance_audit_references.agent_output_references == (
        "agent-output://policy-agent-1",
    )
    assert audit.validation_result == "accepted"
    assert audit.structured_output["finding_id"] == "policy-finding-1"
    assert "customer_token" not in repr(audit.structured_output)


def test_rejected_agent_draft_audit_does_not_store_untrusted_payload() -> None:
    state = _state()
    invocation = _agent_invocation(state)

    committed, audit = record_policy_agent_audit(
        state,
        invocation,
        ProtectedStateController(),
        validation_error="Policy Agent output fields are invalid",
    )

    assert committed.state_metadata.state_version == 2
    assert audit.validation_result == "rejected"
    assert audit.structured_output == {}
    assert audit.failure is not None
