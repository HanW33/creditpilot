"""Deterministic workflow controls over the protected WorkflowState domain."""

from __future__ import annotations

from dataclasses import dataclass, replace

from creditpilot.state.control import StateUpdateRejected
from creditpilot.state.schemas import (
    CreditState,
    StateMetadata,
    StateUpdateProposal,
    WorkflowTransition,
    utc_now,
)


@dataclass(frozen=True, slots=True)
class WorkflowControlConfig:
    """Explicit workflow configuration supplied by an approved later design."""

    allowed_transitions: frozenset[tuple[str | None, str]]
    max_investigation_iterations: int
    max_tool_calls: int
    max_retries: int

    def validate(self) -> None:
        if not self.allowed_transitions:
            raise ValueError("at least one allowed transition is required")
        if min(
            self.max_investigation_iterations,
            self.max_tool_calls,
            self.max_retries,
        ) < 1:
            raise ValueError("workflow limits must be positive")


class WorkflowController:
    """Enforce transitions and counters; never decide what should happen next."""

    def __init__(self, config: WorkflowControlConfig) -> None:
        config.validate()
        self._config = config

    @staticmethod
    def _next_metadata(state: CreditState) -> StateMetadata:
        return replace(
            state.state_metadata,
            state_version=state.state_metadata.state_version + 1,
            updated_at=utc_now(),
        )

    @staticmethod
    def _require_current_version(state: CreditState, expected: int) -> None:
        if expected != state.state_metadata.state_version:
            raise StateUpdateRejected("stale workflow update")

    def commit_orchestrator_action(
        self, state: CreditState, proposal: StateUpdateProposal
    ) -> CreditState:
        """Commit only the Orchestrator-owned next-action proposal field."""

        self._require_current_version(state, proposal.expected_state_version)
        if proposal.target_domain != "workflow_state.proposed_next_action":
            raise StateUpdateRejected("proposal targets the wrong state domain")
        if proposal.proposed_by != "orchestrator_agent":
            raise StateUpdateRejected(
                "only the Orchestrator may propose the next action"
            )
        if set(proposal.proposed_changes) != {"proposed_next_action"}:
            raise StateUpdateRejected("Orchestrator proposal contains protected fields")
        action = proposal.proposed_changes["proposed_next_action"]
        if not isinstance(action, str) or not action.strip():
            raise StateUpdateRejected("proposed next action must be non-empty")
        workflow = replace(state.workflow_state, proposed_next_action=action)
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            workflow_state=workflow,
        )

    def transition(
        self,
        state: CreditState,
        *,
        to_stage: str,
        reason: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Apply only an explicitly configured stage transition."""

        self._require_current_version(state, expected_state_version)
        if written_by != "workflow_controller":
            raise StateUpdateRejected("only the Workflow Controller may transition")
        transition_key = (state.workflow_state.current_stage, to_stage)
        if transition_key not in self._config.allowed_transitions:
            raise StateUpdateRejected("workflow transition is not permitted")
        if not reason:
            raise StateUpdateRejected("workflow transition requires a reason")
        transition = WorkflowTransition(
            from_stage=state.workflow_state.current_stage or "uninitialized",
            to_stage=to_stage,
            permitted=True,
            reason=reason,
            timestamp=utc_now(),
        )
        workflow = replace(
            state.workflow_state,
            current_stage=to_stage,
            proposed_next_action=None,
            last_transition=transition,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            workflow_state=workflow,
        )

    def increment_counter(
        self,
        state: CreditState,
        *,
        counter: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Increment an approved bounded counter and enforce its configured limit."""

        self._require_current_version(state, expected_state_version)
        if written_by != "workflow_controller":
            raise StateUpdateRejected("only the Workflow Controller may set counters")
        limits = {
            "investigation_iteration_count": self._config.max_investigation_iterations,
            "tool_call_count": self._config.max_tool_calls,
            "retry_count": self._config.max_retries,
        }
        if counter not in limits:
            raise StateUpdateRejected("counter is not controlled by the workflow")
        current_count = getattr(state.workflow_state, counter)
        if current_count >= limits[counter]:
            raise StateUpdateRejected("workflow counter limit already reached")
        new_count = current_count + 1
        limit_reached = new_count >= limits[counter]
        reasons = state.workflow_state.mandatory_review_reasons
        limit_reason = f"{counter} limit reached"
        if limit_reached and limit_reason not in reasons:
            reasons = (*reasons, limit_reason)
        workflow = replace(
            state.workflow_state,
            **{counter: new_count},
            mandatory_human_review=(
                state.workflow_state.mandatory_human_review or limit_reached
            ),
            mandatory_review_reasons=reasons,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            workflow_state=workflow,
        )

    def require_human_review(
        self,
        state: CreditState,
        *,
        reason: str,
        written_by: str,
        expected_state_version: int,
    ) -> CreditState:
        """Set, but never clear, a deterministic mandatory-review condition."""

        self._require_current_version(state, expected_state_version)
        if written_by != "workflow_controller":
            raise StateUpdateRejected(
                "only the Workflow Controller may require human review"
            )
        if not reason:
            raise StateUpdateRejected("mandatory review requires a reason")
        reasons = state.workflow_state.mandatory_review_reasons
        if reason not in reasons:
            reasons = (*reasons, reason)
        workflow = replace(
            state.workflow_state,
            mandatory_human_review=True,
            mandatory_review_reasons=reasons,
        )
        return replace(
            state,
            state_metadata=self._next_metadata(state),
            workflow_state=workflow,
        )
