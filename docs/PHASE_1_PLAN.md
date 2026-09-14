# CreditPilot Phase 1 Plan

## Status

Phase 1 — In Progress

Started on 2026-09-15.

## Authority and Scope

Phase 0 architecture was approved and frozen on 2026-09-15.
`docs/ARCHITECTURE_SPEC_V1.md` and `AGENTS.md` govern this work.

Phase 1 is limited to:

- deterministic synthetic credit-risk dataset generation;
- deterministic feature preparation;
- an interpretable Logistic Regression baseline;
- probability-of-default output;
- calibration evaluation;
- SHAP quantitative attribution;
- ML evaluation and tests.

Phase 1 does not implement agents, RAG, verification providers, CreditState,
Workflow Controller, Decision Engine, API, UI, database, or deployment.

## Approved Technical Direction

- Language: Python.
- Data processing: pandas and NumPy.
- Baseline model: scikit-learn Logistic Regression.
- Quantitative attribution: SHAP.
- Tests: pytest.

A challenger model is deferred until the baseline is implemented and evaluated.

## Dataset Design

Use a deterministic synthetic generator with a fixed random seed. The dataset
must contain no real PII and no proprietary bank data.

The initial dataset should contain credit-risk-style numeric and categorical
features suitable for demonstrating:

- income and debt relationships;
- DTI;
- credit history;
- recent inquiries;
- utilization or existing debt;
- employment-related attributes;
- a binary default target.

All fields and distributions are synthetic demonstration assumptions and must
be documented. No generated threshold may be represented as real underwriting
policy.

Split data into stratified training, validation, and test partitions with a
fixed seed. Exact proportions are implementation configuration, not lending
policy.

## Baseline Model

Build an sklearn pipeline that:

- validates the expected feature schema;
- imputes missing values deterministically;
- encodes categorical features;
- scales numeric features where required;
- trains Logistic Regression;
- returns probability of default;
- preserves model and feature metadata;
- supports reproducible evaluation.

Risk bands are not assigned in Phase 1 because synthetic decision thresholds
remain an open architecture question.

## Evaluation

Report, without inventing pass thresholds:

- ROC-AUC;
- PR-AUC;
- Precision;
- Recall;
- F1;
- KS statistic;
- calibration curve or calibration summary;
- confusion matrix at a clearly identified evaluation cutoff;
- dataset size and target rate;
- split and random-seed configuration.

The evaluation cutoff is for model diagnostics only and must not be presented
as a lending or recommendation threshold.

## SHAP

Generate SHAP attribution from the trained quantitative model and transformed
features. Preserve feature names, model version, and evaluation context.

SHAP must not be produced or modified by an LLM.

## Deliverables

- dataset generation module;
- feature and model pipeline;
- evaluation module;
- SHAP module;
- configuration for reproducibility;
- unit tests;
- an evaluation report generated from a successful run;
- README instructions limited to implemented Phase 1 functionality.

## Definition of Done

Phase 1 initial baseline is complete when:

- synthetic data generation is deterministic;
- no real PII or proprietary policy is present;
- the model pipeline trains and predicts PD;
- all approved metrics are computed;
- SHAP attribution runs successfully;
- failure paths and schema validation are tested;
- unit tests pass;
- lint and type checks pass where configured;
- generated results record relevant seed, data, feature, and model versions;
- the diff is reviewed;
- unresolved risks and assumptions are reported.
