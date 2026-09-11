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

## 2. Data Privacy and PII Architecture

### 2.1 Core Principle

Raw identity PII must be separated from the main AI and agent workflow.

Agents and LLMs should operate primarily on:

- application_id;
- opaque customer_token;
- non-PII application attributes;
- sanitized evidence;
- model outputs;
- policy findings;
- workflow state.

Raw identity PII must not be unnecessarily exposed to agents or LLMs.

### 2.2 PII Governance Layer

All incoming application data must pass through a deterministic PII Governance Layer before entering the main CreditPilot AI workflow.

The PII Governance Layer is responsible for:

- schema-based PII classification;
- deterministic PII identification;
- tokenization;
- identity separation;
- context sanitization;
- access-control enforcement;
- PII access auditing.

PII handling must not depend primarily on an LLM.

### 2.3 Identity Tokenization

Customer identity must be represented inside the AI workflow using an opaque customer_token.

For example:

Raw identity data may contain:

- name;
- email;
- address;
- synthetic identity identifiers.

The main workflow instead uses:

customer_token = opaque identifier

The customer_token must not itself contain meaningful identity information.

### 2.4 PII Vault

Identity information and token-to-identity mappings must be stored separately from the main CreditState in a protected PII Vault.

Agents must not directly access the PII Vault.

PII Vault access must:

- use explicitly authorized capabilities;
- follow least-privilege access;
- be independently audited;
- be unavailable to ordinary agent reasoning.

### 2.5 LLM Security Boundary

Before any context is sent to an LLM:

1. context must be constructed using an allowlist;
2. unnecessary PII must be removed;
3. deterministic PII redaction must be applied;
4. only the minimum necessary information may be provided.

The LLM must not be treated as the primary PII detection or protection mechanism.

### 2.6 Notification Boundary

Slack, email, or other external notifications must not contain unnecessary raw PII.

Notifications should normally reference controlled identifiers such as:

- application_id;
- case_id;
- customer_token.

Authorized users may retrieve identity information separately through controlled systems when required.

### 2.7 PII Auditability

PII access must be auditable separately from normal model, agent, and workflow activity.

PII access audit events should record:

- actor;
- timestamp;
- purpose;
- resource accessed;
- access outcome;
- related application or case reference.

## 3. Fundamental Architecture Principle

CreditPilot separates responsibilities across deterministic software,
quantitative machine learning, LLM-enabled agents, and human decision-making.

### 3.1 Deterministic Software

Use deterministic software when explicit rules or calculations are sufficient.

Deterministic components are responsible for:

- application validation;
- deterministic feature calculations;
- explicit policy gates;
- workflow safety rules;
- state-transition enforcement;
- decision rules;
- permission enforcement;
- retry limits;
- investigation loop limits.

### 3.2 Quantitative Machine Learning

Quantitative ML is responsible for credit-risk prediction.

This includes:

- Probability of Default (PD) prediction;
- risk scoring;
- model calibration;
- quantitative feature attribution using SHAP.

LLMs and agents must never generate, replace, or modify quantitative model outputs.

### 3.3 LLM-Enabled Agents

Agents are used only where adaptive reasoning or workflow adaptation is required.

Agents may perform activities such as:

- identifying unresolved evidence;
- planning investigation steps;
- selecting authorized tools;
- retrieving and interpreting policy;
- requesting verification;
- synthesizing evidence;
- generating explanations;
- preparing escalation.

Agents must not replace deterministic logic or quantitative models when those mechanisms are sufficient.

### 3.4 Human Authority

CreditPilot is a decision-support system.

Human review remains mandatory when required by policy, workflow rules,
model failure, unresolved ambiguity, verification failure, or other
configured review conditions.

Agents must not bypass mandatory human review.

### 3.5 Guiding Principle

Use deterministic software when explicit logic is sufficient.

Use quantitative ML for credit-risk prediction.

Use LLM-enabled agents only where adaptive reasoning, investigation,
tool selection, evidence gathering, or workflow adaptation is required.

Use human review where final authority or unresolved risk requires
human judgment.
