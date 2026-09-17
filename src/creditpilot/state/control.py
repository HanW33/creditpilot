"""Deterministic ownership and commit controls for protected CreditState."""

from __future__ import annotations

from dataclasses import replace

from creditpilot.state.schemas import (
    CreditState,
    StateMetadata,
    StateUpdateProposal,
    VerificationInterpretation,
    VerificationRequest,
    VerificationToolResult,
    utc_now,
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
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            verification_state=verification,
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
