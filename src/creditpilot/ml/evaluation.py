"""Phase 1 quantitative model evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import TARGET_COLUMN, validate_dataset
from creditpilot.ml.model import BaselineModel


@dataclass(frozen=True, slots=True)
class DatasetSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def stratified_split(frame: pd.DataFrame, config: Phase1Config) -> DatasetSplits:
    validate_dataset(frame)
    config.validate()
    train_validation, test = train_test_split(
        frame,
        test_size=config.test_fraction,
        stratify=frame[TARGET_COLUMN],
        random_state=config.random_seed,
    )
    validation_share = config.validation_fraction / (1 - config.test_fraction)
    train, validation = train_test_split(
        train_validation,
        test_size=validation_share,
        stratify=train_validation[TARGET_COLUMN],
        random_state=config.random_seed,
    )
    return DatasetSplits(
        train=train.reset_index(drop=True),
        validation=validation.reset_index(drop=True),
        test=test.reset_index(drop=True),
    )


def ks_statistic(y_true: pd.Series | np.ndarray, probability: np.ndarray) -> float:
    false_positive_rate, true_positive_rate, _ = roc_curve(y_true, probability)
    return float(np.max(true_positive_rate - false_positive_rate))


def evaluate_model(
    model: BaselineModel,
    frame: pd.DataFrame,
    config: Phase1Config,
) -> dict[str, object]:
    """Evaluate PD estimates without defining a lending threshold."""

    validate_dataset(frame)
    probability = model.predict_pd(frame)
    prediction = (probability >= config.diagnostic_cutoff).astype(int)
    observed, predicted = calibration_curve(
        frame[TARGET_COLUMN], probability, n_bins=10, strategy="quantile"
    )
    matrix = confusion_matrix(frame[TARGET_COLUMN], prediction, labels=[0, 1])
    metrics = {
        "roc_auc": float(roc_auc_score(frame[TARGET_COLUMN], probability)),
        "pr_auc": float(average_precision_score(frame[TARGET_COLUMN], probability)),
        "precision": float(
            precision_score(frame[TARGET_COLUMN], prediction, zero_division=0)
        ),
        "recall": float(
            recall_score(frame[TARGET_COLUMN], prediction, zero_division=0)
        ),
        "f1": float(f1_score(frame[TARGET_COLUMN], prediction, zero_division=0)),
        "ks": ks_statistic(frame[TARGET_COLUMN], probability),
        "brier_score": float(brier_score_loss(frame[TARGET_COLUMN], probability)),
        "confusion_matrix": matrix.tolist(),
        "calibration": [
            {"predicted": float(p), "observed": float(o)}
            for p, o in zip(predicted, observed, strict=True)
        ],
    }
    return {
        "model_version": model.model_version,
        "feature_version": model.feature_version,
        "data_version": model.data_version,
        "random_seed": model.random_seed,
        "sample_count": int(len(frame)),
        "target_rate": float(frame[TARGET_COLUMN].mean()),
        "diagnostic_cutoff": config.diagnostic_cutoff,
        "diagnostic_cutoff_notice": (
            "Model evaluation only; not a lending or recommendation threshold."
        ),
        "metrics": metrics,
        "configuration": config.as_dict(),
    }


def split_summary(splits: DatasetSplits) -> dict[str, dict[str, float | int]]:
    return {
        name: {
            "sample_count": int(len(part)),
            "target_rate": float(part[TARGET_COLUMN].mean()),
        }
        for name, part in asdict(splits).items()
    }
