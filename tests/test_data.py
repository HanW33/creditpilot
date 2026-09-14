import pandas as pd
import pytest

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import (
    MODEL_FEATURES,
    TARGET_COLUMN,
    generate_synthetic_applications,
    validate_dataset,
)


def test_synthetic_generation_is_deterministic() -> None:
    config = Phase1Config(sample_count=300, random_seed=7)
    first = generate_synthetic_applications(config)
    second = generate_synthetic_applications(config)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 300
    assert set(MODEL_FEATURES).issubset(first.columns)
    assert set(first[TARGET_COLUMN].unique()) == {0, 1}


def test_validation_rejects_identity_pii() -> None:
    frame = generate_synthetic_applications(Phase1Config(sample_count=300))
    frame["email"] = "synthetic@example.invalid"
    with pytest.raises(ValueError, match="identity PII"):
        validate_dataset(frame)


def test_validation_rejects_missing_feature() -> None:
    frame = generate_synthetic_applications(Phase1Config(sample_count=300))
    with pytest.raises(ValueError, match="annual_income"):
        validate_dataset(frame.drop(columns="annual_income"))
