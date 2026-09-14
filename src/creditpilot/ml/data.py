"""Deterministic synthetic credit-risk data generation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from creditpilot.ml.config import Phase1Config

TARGET_COLUMN = "defaulted"
REFERENCE_COLUMNS = ("application_id",)
NUMERIC_FEATURES = (
    "annual_income",
    "existing_debt",
    "monthly_debt_payment",
    "dti",
    "credit_utilization",
    "credit_history_years",
    "recent_inquiries",
    "delinquency_count",
    "employment_years",
    "requested_amount",
    "loan_term_months",
)
CATEGORICAL_FEATURES = ("home_ownership", "employment_type")
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
IDENTITY_PII_COLUMNS = frozenset(
    {
        "name",
        "full_name",
        "email",
        "address",
        "phone",
        "ssn",
        "tax_id",
        "identity_number",
    }
)


def generate_synthetic_applications(config: Phase1Config) -> pd.DataFrame:
    """Generate reproducible demo data with no real PII or proprietary policy."""

    config.validate()
    rng = np.random.default_rng(config.random_seed)
    n = config.sample_count

    annual_income = np.clip(rng.lognormal(np.log(78_000), 0.52, n), 18_000, 350_000)
    existing_debt = np.clip(rng.lognormal(np.log(24_000), 0.85, n), 0, 280_000)
    monthly_debt_payment = np.clip(
        existing_debt / rng.uniform(30, 95, n) + rng.normal(220, 95, n), 0, 8_000
    )
    dti = np.clip(monthly_debt_payment / (annual_income / 12), 0, 1.5)
    utilization = np.clip(rng.beta(2.0, 3.3, n), 0, 1)
    credit_history = np.clip(rng.gamma(3.0, 3.2, n), 0.25, 40)
    inquiries = np.clip(rng.poisson(1.8, n), 0, 12)
    delinquencies = np.clip(rng.poisson(0.35, n), 0, 8)
    employment_years = np.minimum(
        np.clip(rng.gamma(2.2, 2.8, n), 0, 35), credit_history
    )
    requested_amount = np.clip(rng.lognormal(np.log(18_000), 0.62, n), 2_000, 100_000)
    loan_term = rng.choice([24, 36, 48, 60], n, p=[0.08, 0.48, 0.14, 0.30])
    home_ownership = rng.choice(
        ["rent", "mortgage", "own", "other"], n, p=[0.38, 0.43, 0.16, 0.03]
    )
    employment_type = rng.choice(
        ["salaried", "self_employed", "contract", "other"],
        n,
        p=[0.66, 0.16, 0.14, 0.04],
    )

    # These coefficients create synthetic labels for model development only.
    # They are not underwriting rules or real lending thresholds.
    latent_risk = (
        -3.15
        + 2.05 * dti
        + 1.65 * utilization
        + 0.19 * inquiries
        + 0.48 * delinquencies
        - 0.055 * credit_history
        - 0.035 * employment_years
        + 0.000010 * requested_amount
        - 0.000004 * annual_income
        + 0.34 * (employment_type == "self_employed")
        + 0.24 * (employment_type == "contract")
        + 0.20 * (home_ownership == "rent")
        + rng.normal(0, 0.45, n)
    )
    probability = 1 / (1 + np.exp(-latent_risk))
    defaulted = rng.binomial(1, probability, n)

    return pd.DataFrame(
        {
            "application_id": [f"SYN-{i:07d}" for i in range(1, n + 1)],
            "annual_income": annual_income.round(2),
            "existing_debt": existing_debt.round(2),
            "monthly_debt_payment": monthly_debt_payment.round(2),
            "dti": dti.round(6),
            "credit_utilization": utilization.round(6),
            "credit_history_years": credit_history.round(3),
            "recent_inquiries": inquiries.astype(int),
            "delinquency_count": delinquencies.astype(int),
            "employment_years": employment_years.round(3),
            "requested_amount": requested_amount.round(2),
            "loan_term_months": loan_term.astype(int),
            "home_ownership": home_ownership,
            "employment_type": employment_type,
            TARGET_COLUMN: defaulted.astype(int),
        }
    )


def validate_dataset(frame: pd.DataFrame, *, require_target: bool = True) -> None:
    """Reject missing schema fields, identity PII, and invalid targets."""

    pii = sorted(set(frame.columns).intersection(IDENTITY_PII_COLUMNS))
    if pii:
        raise ValueError(f"identity PII columns are prohibited: {pii}")

    required = set(MODEL_FEATURES)
    if require_target:
        required.add(TARGET_COLUMN)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    if require_target:
        values = set(frame[TARGET_COLUMN].dropna().unique())
        if values != {0, 1}:
            raise ValueError("defaulted must contain both binary classes 0 and 1")
