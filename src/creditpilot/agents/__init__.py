"""Provider-independent boundaries for the five approved agents."""

from creditpilot.agents.audit import (
    record_policy_agent_audit,
    record_verification_agent_audit,
)
from creditpilot.agents.contracts import (
    AgentAuditRecord,
    AgentFailure,
    AgentInvocation,
)
from creditpilot.agents.policy_agent import (
    PolicyAgentContext,
    PolicyAgentOutput,
    PolicyAgentValidationError,
    PolicyReasoningBackend,
    policy_output_to_state_proposal,
    run_policy_agent,
)
from creditpilot.agents.verification_agent import (
    VerificationAgentOutput,
    VerificationAgentValidationError,
    run_verification_agent,
    verification_output_to_state_proposal,
)

__all__ = [
    "AgentAuditRecord",
    "AgentFailure",
    "AgentInvocation",
    "PolicyAgentContext",
    "PolicyAgentOutput",
    "PolicyAgentValidationError",
    "PolicyReasoningBackend",
    "policy_output_to_state_proposal",
    "record_policy_agent_audit",
    "record_verification_agent_audit",
    "run_policy_agent",
    "VerificationAgentOutput",
    "VerificationAgentValidationError",
    "run_verification_agent",
    "verification_output_to_state_proposal",
]
