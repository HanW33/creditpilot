# CreditPilot — Architecture Specification V1

## Status

Phase 0 — Architecture Definition

## Architecture Authority

This document is the canonical architecture source of truth for CreditPilot.

If implementation, derived documentation, prompts, agent behaviour,
or coding-agent output conflicts with this specification,
this specification takes precedence.

Material architectural changes require explicit human approval.

## 1. Project Definition

### Project Name

CreditPilot — Agentic AI Credit Risk Decision Support System

### Purpose

CreditPilot demonstrates how agentic AI can assist a Credit Risk Analyst
or Underwriter by combining:

- quantitative credit-risk modelling;
- explainable AI;
- policy retrieval and reasoning;
- adaptive investigation workflows;
- external evidence verification;
- human-in-the-loop review;
- controlled enterprise actions;
- auditability;
- AI and data governance.

CreditPilot is a decision-support system.

It is not an autonomous real-world lending system.

### Primary User

The primary user is a Credit Risk Analyst or Underwriter.

CreditPilot assists the analyst with:

- investigating credit applications;
- identifying missing or conflicting information;
- retrieving relevant synthetic credit policy;
- obtaining verification evidence;
- generating structured recommendations;
- explaining model, policy, and verification evidence;
- escalating unresolved cases for human review.

### Data Scope

CreditPilot V1 uses synthetic, mock, simulated, or suitable public demo data only.

It does not use real customer PII or proprietary bank underwriting policies.
