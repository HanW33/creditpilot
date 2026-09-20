"""Deterministic ownership and commit controls for protected CreditState."""

from __future__ import annotations

from dataclasses import replace

from creditpilot.state.schemas import (
    CreditState,
    ExplanationState,
    GovernanceAuditReferences,
    PolicyEvidence,
    QuantitativeModelState,
    RecommendationState,
    StateMetadata,
    StateUpdateProposal,
    ValidationState,
    VerificationInterpretation,
    VerificationRequest,
    VerificationToolResult,
    utc_now,
    validate_no_identity_pii,
)


class StateUpdateRejected(ValueError):
    """Raised when a proposed protected update fails deterministic controls."""


class ProtectedStateController:
    """Validate and commit protected updates without transferring ownership."""

    @staticmethod
    def _validate_version(state: CreditState, proposal: StateUpdateProposal) -> None:
        if proposal.expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update proposal")

    @staticmethod
    def _next_metadata(state: CreditState) -> StateMetadata:
        return replace(
            state.state_metadata,
            state_version=state.state_metadata.state_version + 1,
            updated_at=utc_now(),
        )

    @staticmethod
    def _require_writer(actual: str, expected: str, domain: str) -> None:
        if actual != expected:
            raise StateUpdateRejected(f"only {expected} may write {domain}")

    def commit_validation_result(
        self,
        state: CreditState,
        result: ValidationState,
        *,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Commit output owned by the deterministic validation component."""

        self._require_writer(written_by, "deterministic_validation", "validation_state")
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update")
        if result.status == "success" and result.failure is not None:
            raise StateUpdateRejected("successful validation cannot contain a failure")
        if result.status == "failure" and result.failure is None:
            raise StateUpdateRejected("failed validation requires a failure record")
        if result.validated_at is None or not result.validator_version:
            raise StateUpdateRejected("validation provenance is incomplete")
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            validation_state=result,
        )

    def commit_quantitative_model_result(
        self,
        state: CreditState,
        result: QuantitativeModelState,
        *,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Commit PD and SHAP output owned by an approved quantitative component."""

        self._require_writer(
            written_by, "quantitative_model", "quantitative_model_state"
        )
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update")
        if result.input_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected(
                "model output was not produced from current state"
            )
        if result.status == "success":
            if result.failure is not None:
                raise StateUpdateRejected(
                    "successful model output cannot contain failure"
                )
            if result.pd_score is None or not 0 <= result.pd_score <= 1:
                raise StateUpdateRejected("successful model output requires valid PD")
            if not result.model_version or result.model_timestamp is None:
                raise StateUpdateRejected("model provenance is incomplete")
        elif result.status == "failure":
            if result.failure is None:
                raise StateUpdateRejected("failed model output requires failure record")
            if result.pd_score is not None or result.shap_risk_factors:
                raise StateUpdateRejected(
                    "failed model output cannot invent PD or SHAP"
                )
        else:
            raise StateUpdateRejected("model status must be success or failure")
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            quantitative_model_state=result,
        )

    def record_policy_evidence(
        self,
        state: CreditState,
        evidence: PolicyEvidence,
        *,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Record traceable raw evidence from the approved retrieval capability."""

        self._require_writer(
            written_by, "policy_retrieval", "policy_state.retrieved_evidence"
        )
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update")
        if not (
            evidence.source_document
            and evidence.section_or_chunk_reference
            and evidence.policy_version
        ):
            raise StateUpdateRejected("policy evidence provenance is incomplete")
        policy = replace(
            state.policy_state,
            retrieved_evidence=(*state.policy_state.retrieved_evidence, evidence),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            policy_state=policy,
        )

    def commit_policy_findings(
        self, state: CreditState, proposal: StateUpdateProposal
    ) -> CreditState:
        """Commit Policy Agent findings only when grounded in retrieved evidence."""

        self._validate_version(state, proposal)
        if proposal.target_domain != "policy_state.findings":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "policy_agent":
            raise StateUpdateRejected("only the Policy Agent may propose findings")
        allowed = {"status", "findings", "required_evidence", "conflicts"}
        if set(proposal.proposed_changes) - allowed:
            raise StateUpdateRejected("policy proposal contains unsupported fields")
        evidence_references = {
            item.section_or_chunk_reference
            for item in state.policy_state.retrieved_evidence
        }
        evidence_references.update(
            f"policy://{item.source_document}/"
            f"{item.section_or_chunk_reference}@{item.policy_version}"
            for item in state.policy_state.retrieved_evidence
        )
        if proposal.proposed_changes.get("findings") and not set(
            proposal.basis_references
        ).issubset(evidence_references):
            raise StateUpdateRejected("policy findings lack committed evidence")
        if proposal.proposed_changes.get("findings") and not proposal.basis_references:
            raise StateUpdateRejected("policy findings must cite committed evidence")
        policy = replace(
            state.policy_state,
            status=str(proposal.proposed_changes.get("status", "complete")),
            findings=tuple(proposal.proposed_changes.get("findings", ())),
            required_evidence=tuple(
                proposal.proposed_changes.get("required_evidence", ())
            ),
            conflicts=tuple(proposal.proposed_changes.get("conflicts", ())),
            evaluated_at=proposal.proposed_at,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            policy_state=policy,
        )

    def commit_recommendation(
        self,
        state: CreditState,
        result: RecommendationState,
        *,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Commit fields exclusively owned by the deterministic Decision Engine."""

        self._require_writer(written_by, "decision_engine", "recommendation_state")
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update")
        if state.workflow_state.mandatory_human_review:
            raise StateUpdateRejected("mandatory human review blocks recommendation")
        if result.input_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected(
                "recommendation was not produced from current committed state"
            )
        if not (
            result.recommendation
            and result.decision_rule
            and result.decision_reason
            and result.decided_at
        ):
            raise StateUpdateRejected("recommendation provenance is incomplete")
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            recommendation_state=result,
        )

    def commit_explanation(
        self, state: CreditState, proposal: StateUpdateProposal
    ) -> CreditState:
        """Commit an analyst explanation without permitting evidence mutation."""

        self._validate_version(state, proposal)
        if proposal.target_domain != "explanation_state":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "explanation_agent":
            raise StateUpdateRejected(
                "only the Explanation Agent may write explanation"
            )
        if set(proposal.proposed_changes) != {"explanation"}:
            raise StateUpdateRejected("explanation proposal contains protected fields")
        explanation = proposal.proposed_changes["explanation"]
        if not isinstance(explanation, str) or not explanation.strip():
            raise StateUpdateRejected("explanation must be non-empty")
        if not proposal.basis_references:
            raise StateUpdateRejected("explanation must cite committed evidence")
        committed_references = {state.application_data.source_reference}
        model = state.quantitative_model_state
        if model.model_version and model.input_state_version is not None:
            committed_references.add(
                f"model://{model.model_version}/state/{model.input_state_version}"
            )
        committed_references.update(
            f"policy://{item.source_document}/"
            f"{item.section_or_chunk_reference}@{item.policy_version}"
            for item in state.policy_state.retrieved_evidence
        )
        committed_references.update(
            item.raw_evidence_reference
            for item in state.verification_state.tool_results
        )
        audit = state.governance_audit_references
        for field in audit.__dataclass_fields__:
            committed_references.update(getattr(audit, field))
        unresolved_references = set(proposal.basis_references) - committed_references
        legacy_external_prefixes = ("model-run-", "policy-finding-")
        if any(
            not reference.startswith(legacy_external_prefixes)
            for reference in unresolved_references
        ):
            raise StateUpdateRejected("explanation cites uncommitted evidence")
        result = ExplanationState(
            explanation=explanation,
            input_state_version=state.state_metadata.state_version,
            created_at=proposal.proposed_at,
            created_by=proposal.proposed_by,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            explanation_state=result,
        )

    def commit_escalation_package(
        self, state: CreditState, proposal: StateUpdateProposal
    ) -> CreditState:
        """Commit a human-review package prepared by the Escalation Agent."""

        self._validate_version(state, proposal)
        if proposal.target_domain != "escalation_state":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "escalation_agent":
            raise StateUpdateRejected("only the Escalation Agent may prepare handoff")
        if not state.workflow_state.mandatory_human_review:
            raise StateUpdateRejected("escalation requires mandatory human review")
        allowed = {
            "status",
            "reasons",
            "review_package_reference",
            "requested_actions",
        }
        if set(proposal.proposed_changes) - allowed:
            raise StateUpdateRejected("escalation proposal contains protected fields")
        reasons = tuple(proposal.proposed_changes.get("reasons", ()))
        package_reference = proposal.proposed_changes.get(
            "review_package_reference"
        )
        if not reasons or not package_reference:
            raise StateUpdateRejected("escalation package provenance is incomplete")
        requested_actions = tuple(
            proposal.proposed_changes.get("requested_actions", ())
        )
        if set(requested_actions) - {
            "create_review_case",
            "send_notification",
        }:
            raise StateUpdateRejected("escalation requests an unsupported action")
        escalation = replace(
            state.escalation_state,
            status=str(proposal.proposed_changes.get("status", "prepared")),
            reasons=reasons,
            review_package_reference=str(package_reference),
            requested_actions=requested_actions,
            timestamps=(*state.escalation_state.timestamps, proposal.proposed_at),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            escalation_state=escalation,
        )

    def append_audit_reference(
        self,
        state: CreditState,
        *,
        category: str,
        reference: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Append a reference through controlled audit persistence."""

        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale state update")
        categories = GovernanceAuditReferences.__dataclass_fields__
        if category not in categories:
            raise StateUpdateRejected("unknown audit reference category")
        expected_writer = (
            "pii_audit" if category == "pii_audit_references" else "audit_persistence"
        )
        self._require_writer(written_by, expected_writer, category)
        if not reference:
            raise StateUpdateRejected("audit reference must be non-empty")
        current = getattr(state.governance_audit_references, category)
        audit = replace(
            state.governance_audit_references,
            **{category: (*current, reference)},
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            governance_audit_references=audit,
        )

    def record_escalation_action_result(
        self,
        state: CreditState,
        *,
        action_result_reference: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Record an approved action result without granting decision authority."""

        self._require_writer(
            written_by, "action_tool", "escalation_state.action_results"
        )
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale action result")
        if not state.workflow_state.mandatory_human_review or (
            state.escalation_state.status != "prepared"
        ):
            raise StateUpdateRejected("action result requires prepared escalation")
        if not action_result_reference:
            raise StateUpdateRejected("action result reference is required")
        if action_result_reference in state.escalation_state.action_results:
            return state
        escalation = replace(
            state.escalation_state,
            action_results=(
                *state.escalation_state.action_results,
                action_result_reference,
            ),
            timestamps=(*state.escalation_state.timestamps, utc_now()),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            escalation_state=escalation,
        )

    def commit_human_review_outcome(
        self,
        state: CreditState,
        *,
        outcome_reference: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Attach an authorized human outcome without changing decision evidence."""

        self._require_writer(
            written_by,
            "authorized_human_analyst",
            "escalation_state.human_review_outcome_reference",
        )
        if expected_state_version != state.state_metadata.state_version:
            raise StateUpdateRejected("stale human review outcome")
        if not state.workflow_state.mandatory_human_review:
            raise StateUpdateRejected("human outcome requires mandatory review")
        if not outcome_reference.startswith("human-review://synthetic/"):
            raise StateUpdateRejected("invalid human review outcome reference")
        existing = state.escalation_state.human_review_outcome_reference
        if existing is not None:
            if existing == outcome_reference:
                return state
            raise StateUpdateRejected("human review outcome already recorded")
        escalation = replace(
            state.escalation_state,
            human_review_outcome_reference=outcome_reference,
            timestamps=(*state.escalation_state.timestamps, utc_now()),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            escalation_state=escalation,
        )

    def commit_verification_request(
        self, state: CreditState, proposal: StateUpdateProposal
    ) -> CreditState:
        """Commit a request proposed by the Orchestrator through state controls."""

        self._validate_version(state, proposal)
        if proposal.target_domain != "verification_state.requests":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "orchestrator_agent":
            raise StateUpdateRejected("only the Orchestrator may propose a request")

        required = {"request_id", "evidence_required"}
        if not required.issubset(proposal.proposed_changes):
            raise StateUpdateRejected("verification request fields are incomplete")
        request_id = str(proposal.proposed_changes["request_id"])
        if any(
            item.request_id == request_id
            for item in state.verification_state.requests
        ):
            raise StateUpdateRejected("verification request_id already exists")

        request = VerificationRequest(
            request_id=request_id,
            evidence_required=str(proposal.proposed_changes["evidence_required"]),
            requested_by=proposal.proposed_by,
            requested_at=proposal.proposed_at,
            status="approved",
        )
        verification = replace(
            state.verification_state,
            requests=(*state.verification_state.requests, request),
        )
        workflow = replace(
            state.workflow_state,
            active_request_ids=(*state.workflow_state.active_request_ids, request_id),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            verification_state=verification,
            workflow_state=workflow,
        )

    def record_verification_tool_result(
        self, state: CreditState, result: VerificationToolResult
    ) -> CreditState:
        """Record raw evidence returned by an approved verification tool path."""

        approved_request_ids = {
            item.request_id
            for item in state.verification_state.requests
            if item.status == "approved"
        }
        if result.request_id not in approved_request_ids:
            raise StateUpdateRejected("tool result has no approved committed request")
        if not result.raw_evidence_reference:
            raise StateUpdateRejected("raw evidence must remain traceable by reference")
        if any(
            item.result_id == result.result_id
            for item in state.verification_state.tool_results
        ):
            raise StateUpdateRejected("verification result_id already exists")

        verification = replace(
            state.verification_state,
            tool_results=(*state.verification_state.tool_results, result),
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            verification_state=verification,
        )

    def commit_verified_values(
        self,
        state: CreditState,
        proposal: StateUpdateProposal,
        interpretation: VerificationInterpretation,
    ) -> CreditState:
        """Commit traceable verified values proposed by the Verification Agent."""

        self._validate_version(state, proposal)
        if proposal.target_domain != "verification_state.verified_values":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "verification_agent":
            raise StateUpdateRejected(
                "only the Verification Agent may propose verified values"
            )
        matching_results = {
            item.result_id: item for item in state.verification_state.tool_results
        }
        result = matching_results.get(interpretation.result_id)
        if result is None or result.status != "success":
            raise StateUpdateRejected(
                "verified values require successful tool evidence"
            )
        if interpretation.result_id not in proposal.basis_references:
            raise StateUpdateRejected("proposal must cite its tool evidence result")
        if proposal.proposed_changes != interpretation.proposed_state_update:
            raise StateUpdateRejected(
                "proposal and interpretation updates do not match"
            )
        if not proposal.proposed_changes:
            raise StateUpdateRejected("verified update must not be empty")
        try:
            validate_no_identity_pii(
                proposal.proposed_changes, "verification_state.verified_values"
            )
        except ValueError as error:
            raise StateUpdateRejected(str(error)) from error

        # Verified values are a separate domain and never replace reported values.
        verified_values = {
            **state.verification_state.verified_values,
            **proposal.proposed_changes,
        }
        verification = replace(
            state.verification_state,
            interpretations=(*state.verification_state.interpretations, interpretation),
            verified_values=verified_values,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            verification_state=verification,
        )
