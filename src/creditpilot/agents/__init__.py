"""Provider-independent boundaries for the five approved agents."""

from creditpilot.agents.audit import (
    record_escalation_agent_audit,
    record_explanation_agent_audit,
    record_orchestrator_agent_audit,
    record_policy_agent_audit,
    record_verification_agent_audit,
)
from creditpilot.agents.contracts import (
    AgentAuditRecord,
    AgentFailure,
    AgentInvocation,
)
from creditpilot.agents.escalation_agent import (
    EscalationAgentOutput,
    EscalationAgentValidationError,
    EscalationContext,
    EscalationReasoningBackend,
    escalation_output_to_state_proposal,
    run_escalation_agent,
)
from creditpilot.agents.explanation_agent import (
    ExplanationAgentOutput,
    ExplanationAgentValidationError,
    ExplanationContext,
    ExplanationReasoningBackend,
    explanation_output_to_state_proposal,
    run_explanation_agent,
)
from creditpilot.agents.orchestrator_agent import (
    OrchestratorContext,
    OrchestratorOutput,
    OrchestratorReasoningBackend,
    OrchestratorValidationError,
    orchestrator_output_to_verification_request,
    orchestrator_output_to_workflow_proposal,
    run_orchestrator_agent,
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
    "EscalationAgentOutput",
    "EscalationAgentValidationError",
    "EscalationContext",
    "EscalationReasoningBackend",
    "ExplanationAgentOutput",
    "ExplanationAgentValidationError",
    "ExplanationContext",
    "ExplanationReasoningBackend",
    "OrchestratorContext",
    "OrchestratorOutput",
    "OrchestratorReasoningBackend",
    "OrchestratorValidationError",
    "PolicyAgentContext",
    "PolicyAgentOutput",
    "PolicyAgentValidationError",
    "PolicyReasoningBackend",
    "policy_output_to_state_proposal",
    "escalation_output_to_state_proposal",
    "explanation_output_to_state_proposal",
    "record_escalation_agent_audit",
    "record_explanation_agent_audit",
    "orchestrator_output_to_verification_request",
    "orchestrator_output_to_workflow_proposal",
    "record_orchestrator_agent_audit",
    "record_policy_agent_audit",
    "record_verification_agent_audit",
    "run_policy_agent",
    "run_escalation_agent",
    "run_explanation_agent",
    "run_orchestrator_agent",
    "VerificationAgentOutput",
    "VerificationAgentValidationError",
    "run_verification_agent",
    "verification_output_to_state_proposal",
]
