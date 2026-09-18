"""Deterministic ownership and commit controls for protected CreditState."""

from __future__ import annotations

from dataclasses import replace

from creditpilot.state.schemas import (
    CreditState,
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
