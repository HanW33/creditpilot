"""Reproducible Phase 1 configuration."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Phase1Config:
    """Configuration for synthetic data and the approved baseline model."""

    random_seed: int = 33
    sample_count: int = 5_000
    test_fraction: float = 0.20
    validation_fraction: float = 0.20
    diagnostic_cutoff: float = 0.50
    data_version: str = "synthetic-credit-v1"
    feature_version: str = "credit-features-v1"
    model_version: str = "logistic-regression-v1"

    def validate(self) -> None:
        if self.sample_count < 200:
            raise ValueError("sample_count must be at least 200")
        if not 0 < self.test_fraction < 1:
            raise ValueError("test_fraction must be between 0 and 1")
        if not 0 < self.validation_fraction < 1:
            raise ValueError("validation_fraction must be between 0 and 1")
        if self.test_fraction + self.validation_fraction >= 1:
            raise ValueError("test and validation fractions must sum to less than 1")
        if not 0 < self.diagnostic_cutoff < 1:
            raise ValueError("diagnostic_cutoff must be between 0 and 1")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return asdict(self)
