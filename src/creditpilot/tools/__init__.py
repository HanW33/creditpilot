"""Typed, bounded CreditPilot tool capabilities."""

from creditpilot.tools.contracts import (
    ToolAuditRecord,
    ToolFailure,
    ToolInvocation,
    ToolPermissionPolicy,
    ToolResult,
)
from creditpilot.tools.integration import (
    commit_policy_retrieval_result,
    commit_quantitative_tool_results,
    record_tool_audit,
    record_verification_tool_result,
)
from creditpilot.tools.internal import (
    calculate_dti,
    get_application,
    get_customer_profile,
)
from creditpilot.tools.model_tools import explain_model, run_credit_risk_model
from creditpilot.tools.policy_tools import search_credit_policy
from creditpilot.tools.verification_tools import (
    get_credit_report,
    verify_employment,
    verify_income,
)

__all__ = [
    "ToolAuditRecord",
    "ToolFailure",
    "ToolInvocation",
    "ToolPermissionPolicy",
    "ToolResult",
    "calculate_dti",
    "commit_policy_retrieval_result",
    "commit_quantitative_tool_results",
    "explain_model",
    "get_application",
    "get_customer_profile",
    "get_credit_report",
    "record_tool_audit",
    "record_verification_tool_result",
    "run_credit_risk_model",
    "search_credit_policy",
    "verify_employment",
    "verify_income",
]
