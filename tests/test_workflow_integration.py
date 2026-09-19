from datetime import UTC, datetime
from pathlib import Path

from creditpilot.policy import PolicyIndex, load_policy_documents
from creditpilot.policy.schemas import section_chunks
from creditpilot.state import (
    ProtectedStateController,
    WorkflowControlConfig,
    WorkflowController,
    create_credit_state,
)
from creditpilot.tools import ToolPermissionPolicy
from creditpilot.verification import MockVerificationProvider
from creditpilot.workflow import InvestigationCycleIds, run_policy_verification_cycle

NOW = datetime(2026, 9, 20, tzinfo=UTC)
POLICY_DIRECTORY = Path(__file__).parents[1] / "policies"


class GroundedPolicyBackend:
    def generate_policy_finding(self, context):
        evidence = next(
            item
            for item in context.retrieved_evidence
            if item["section_or_chunk_reference"] == "income-evidence"
        )
        reference = next(
            item
            for item in context.evidence_references
            if "/income-evidence@" in item
        )
        return {
            "finding_id": "integrated-policy-finding",
            "status": "complete",
            "applicable_policy_evidence": [reference],
            "interpretation": (
                "The synthetic policy requires verified income evidence."
            ),
            "required_evidence": ["verified_income"],
            "policy_constraints": [
                "Reported and verified income remain separate and traceable."
            ],
            "conflicts": [],
            "unresolved_items": [],
            "source_references": [reference],
            "policy_versions": [evidence["policy_version"]],
        }


class StateAwareOrchestratorBackend:
    def propose_next_action(self, context):
        workflow = context.authorized_state["workflow_state"]
        if workflow.mandatory_human_review:
            action = "prepare_escalation"
            unresolved = list(context.missing_evidence)
        elif context.missing_evidence:
            action = "create_verification_request"
            unresolved = list(context.missing_evidence)
        else:
            action = "reevaluate_case"
            unresolved = []
        return {
            "proposed_next_action": action,
            "reason": "The next action follows the current committed evidence state.",
            "evidence_references": list(context.known_evidence_references[:1]),
            "prerequisites": ["deterministic workflow authorization"],
            "unresolved_items": unresolved,
            "status": "proposed",
        }


def _state():
    return create_credit_state(
        application_id="SYN-0000011",
        customer_token="customer-token-011",
        reported_values={"annual_income": 150_000},
        sanitized_attributes={"employment_type": "salaried"},
        source_reference="synthetic-application-11",
        now=NOW,
    )


def _ids():
    return InvestigationCycleIds(
        policy_tool_invocation_id="integrated-policy-tool-1",
        policy_agent_invocation_id="integrated-policy-agent-1",
        orchestrator_invocation_id="integrated-orchestrator-1",
        verification_request_id="integrated-request-1",
        verification_tool_invocation_id="integrated-verification-tool-1",
        verification_agent_invocation_id="integrated-verification-agent-1",
        follow_up_orchestrator_invocation_id="integrated-orchestrator-2",
    )


def _permissions():
    return ToolPermissionPolicy(
        callers_by_tool={
            "search_credit_policy": frozenset({"policy_retrieval"}),
            "verify_income": frozenset({"verification_agent"}),
        }
    )


def _workflow(max_iterations=3):
    return WorkflowController(
        WorkflowControlConfig(
            allowed_transitions=frozenset({(None, "unused")}),
            max_investigation_iterations=max_iterations,
            max_tool_calls=3,
            max_retries=1,
        )
    )


def _run(state, workflow, provider_records=None):
    index = PolicyIndex(section_chunks(load_policy_documents(POLICY_DIRECTORY)))
    provider = MockVerificationProvider(
        records=provider_records
        or {
            "SYN-0000011": {
                "verified_income": {"verified_income": 98_000},
            }
        }
    )
    return run_policy_verification_cycle(
        state,
        ids=_ids(),
        policy_index=index,
        policy_backend=GroundedPolicyBackend(),
        orchestrator_backend=StateAwareOrchestratorBackend(),
        verification_provider=provider,
        tool_permissions=_permissions(),
        state_controller=ProtectedStateController(),
        workflow_controller=workflow,
        policy_question="What income evidence is required?",
        requested_evidence="verified income",
        supported_evidence_types=frozenset(
            {"verified_income", "verified_employment", "credit_report"}
        ),
    )


def test_integrated_golden_cycle_stops_at_model_reevaluation_boundary() -> None:
    result = _run(_state(), _workflow())

    assert result.status == "complete"
    assert result.next_action == "reevaluate_case"
    assert result.state.application_data.reported_values["annual_income"] == 150_000
    assert result.state.verification_state.verified_values["verified_income"] == 98_000
    assert result.state.workflow_state.tool_call_count == 2
    assert result.state.workflow_state.investigation_iteration_count == 2
    assert result.state.recommendation_state.recommendation is None
    assert result.completed_steps == (
        "policy_retrieval",
        "policy_interpretation",
        "orchestrator_evaluation",
        "verification_request_commit",
        "verification_tool",
        "verified_evidence_commit",
        "follow_up_orchestrator_evaluation",
    )
    assert len(result.audit_references) == 6


def test_investigation_limit_routes_before_verification_execution() -> None:
    result = _run(_state(), _workflow(max_iterations=1))

    assert result.status == "stopped"
    assert result.next_action == "prepare_escalation"
    assert result.state.workflow_state.mandatory_human_review is True
    assert result.state.verification_state.requests == ()
    assert result.state.verification_state.verified_values == {}
    assert result.state.workflow_state.tool_call_count == 1


def test_verification_failure_is_audited_and_routes_without_fabrication() -> None:
    result = _run(
        _state(),
        _workflow(),
        provider_records={"SYN-NO-EVIDENCE": {}},
    )

    assert result.status == "failure"
    assert result.next_action == "prepare_escalation"
    assert result.state.workflow_state.retry_count == 1
    assert result.state.workflow_state.mandatory_human_review is True
    assert result.state.verification_state.verified_values == {}
    assert result.state.application_data.reported_values["annual_income"] == 150_000
    assert len(result.state.governance_audit_references.tool_call_references) == 2
