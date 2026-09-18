import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from creditpilot.policy import PolicyIndex, load_policy_documents
from creditpilot.policy.schemas import section_chunks
from creditpilot.state import ProtectedStateController, create_credit_state
from creditpilot.tools import (
    ToolInvocation,
    ToolPermissionPolicy,
    commit_policy_retrieval_result,
    search_credit_policy,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)
POLICY_DIRECTORY = Path(__file__).parents[1] / "policies"


@pytest.fixture(scope="module")
def policy_index() -> PolicyIndex:
    return PolicyIndex(section_chunks(load_policy_documents(POLICY_DIRECTORY)))


def _state():
    return create_credit_state(
        application_id="SYN-0000008",
        customer_token="customer-token-008",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={},
        source_reference="synthetic-application-8",
        now=NOW,
    )


def _permissions() -> ToolPermissionPolicy:
    return ToolPermissionPolicy(
        callers_by_tool={"search_credit_policy": frozenset({"policy_retrieval"})}
    )


def _invocation(**argument_overrides) -> ToolInvocation:
    arguments = {
        "policy_question": "What income evidence is required?",
        "requested_evidence": "verified income",
        "sanitized_context": {"evidence_status": "missing"},
        "top_k": 2,
        "required_policy_versions": (),
        **argument_overrides,
    }
    return ToolInvocation(
        invocation_id="policy-search-1",
        tool_name="search_credit_policy",
        application_id="SYN-0000008",
        case_id=None,
        requested_by="policy_retrieval",
        purpose="Retrieve synthetic income evidence policy",
        input_state_version=1,
        authorized_scope=frozenset({"policy:search"}),
        arguments=arguments,
        requested_at=NOW,
    )


def test_policy_sources_are_synthetic_versioned_and_stably_chunked() -> None:
    documents = load_policy_documents(POLICY_DIRECTORY)
    chunks = section_chunks(documents)

    assert len(documents) == 2
    assert len(chunks) == 6
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(
        "Fictional demonstration policy only" in chunk.synthetic_policy_notice
        for chunk in chunks
    )
    assert all(chunk.policy_version.startswith("synthetic-") for chunk in chunks)
    assert all("%" not in chunk.text and "$" not in chunk.text for chunk in chunks)


def test_policy_loader_rejects_unknown_schema_fields(tmp_path: Path) -> None:
    invalid = {
        "policy_document_id": "synthetic-invalid-policy",
        "title": "Invalid synthetic policy",
        "policy_version": "synthetic-invalid-v1",
        "effective_date": "2026-01-01",
        "synthetic_policy_notice": (
            "Fictional demonstration policy only. Not for lending decisions."
        ),
        "provenance": "Synthetic test",
        "sections": [
            {"section_id": "test", "title": "Test", "text": "Synthetic text"}
        ],
        "unexpected": "not allowed",
    }
    (tmp_path / "invalid.json").write_text(json.dumps(invalid), encoding="utf-8")

    with pytest.raises(ValueError, match="approved schema"):
        load_policy_documents(tmp_path)


def test_search_returns_ranked_raw_evidence_with_citations(policy_index) -> None:
    result = search_credit_policy(
        _invocation(), _state(), _permissions(), index=policy_index
    )

    assert result.status == "success"
    assert result.result["result_count"] == 2
    first = result.result["evidence"][0]
    assert first["section_or_chunk_reference"] == "income-evidence"
    assert first["policy_version"] == "synthetic-evidence-v1"
    assert 0 <= first["retrieval_score"] <= 1
    assert "interpretation" not in first
    assert "recommendation" not in first


def test_search_rejects_pii_bearing_context(policy_index) -> None:
    result = search_credit_policy(
        _invocation(sanitized_context={"email": "prohibited@example.invalid"}),
        _state(),
        _permissions(),
        index=policy_index,
    )

    assert result.status == "failure"
    assert result.failure is not None
    assert result.failure.code == "prohibited_context_data"


def test_search_rejects_context_outside_allowlist(policy_index) -> None:
    result = search_credit_policy(
        _invocation(sanitized_context={"notes": "unbounded context"}),
        _state(),
        _permissions(),
        index=policy_index,
    )

    assert result.status == "failure"
    assert result.failure is not None
    assert result.failure.code == "unsupported_context"


def test_search_rejects_unauthorized_caller(policy_index) -> None:
    invocation = _invocation()
    unauthorized = ToolInvocation(
        invocation_id=invocation.invocation_id,
        tool_name=invocation.tool_name,
        application_id=invocation.application_id,
        case_id=None,
        requested_by="policy_agent",
        purpose=invocation.purpose,
        input_state_version=invocation.input_state_version,
        authorized_scope=invocation.authorized_scope,
        arguments=invocation.arguments,
        requested_at=NOW,
    )

    with pytest.raises(PermissionError, match="not authorized"):
        search_credit_policy(
            unauthorized, _state(), _permissions(), index=policy_index
        )


def test_search_unknown_terms_is_explicitly_unavailable(policy_index) -> None:
    result = search_credit_policy(
        _invocation(
            policy_question="zyxwv qqqjj",
            requested_evidence="xxxyyy",
        ),
        _state(),
        _permissions(),
        index=policy_index,
    )

    assert result.status == "unavailable"
    assert result.result == {}
    assert result.failure is not None


def test_search_does_not_silently_select_missing_version(policy_index) -> None:
    result = search_credit_policy(
        _invocation(required_policy_versions=("missing-policy-version",)),
        _state(),
        _permissions(),
        index=policy_index,
    )

    assert result.status == "unavailable"


def test_raw_policy_evidence_commits_without_interpretation(policy_index) -> None:
    state = _state()
    result = search_credit_policy(
        _invocation(), state, _permissions(), index=policy_index
    )

    committed = commit_policy_retrieval_result(
        state, result, ProtectedStateController()
    )

    assert len(committed.policy_state.retrieved_evidence) == 2
    assert committed.policy_state.findings == ()
    assert committed.policy_state.required_evidence == ()
    assert committed.state_metadata.state_version == 3
