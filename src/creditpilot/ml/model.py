"""Approved interpretable Logistic Regression baseline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    validate_dataset,
)


@dataclass(slots=True)
class BaselineModel:
    """Trained quantitative model with explicit version metadata."""

    pipeline: Pipeline
    model_version: str
    feature_version: str
    data_version: str
    random_seed: int

    def predict_pd(self, frame: pd.DataFrame) -> np.ndarray:
        validate_dataset(frame, require_target=False)
        return self.pipeline.predict_proba(frame.loc[:, MODEL_FEATURES])[:, 1]


def build_pipeline(config: Phase1Config) -> Pipeline:
    """Build the deterministic preprocessing and Logistic Regression pipeline."""

    config.validate()
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            (
                "model",
                LogisticRegression(max_iter=1_000, random_state=config.random_seed),
            ),
        ]
    )


def train_baseline(frame: pd.DataFrame, config: Phase1Config) -> BaselineModel:
    """Train the approved baseline using only validated synthetic features."""

    validate_dataset(frame)
    pipeline = build_pipeline(config)
    pipeline.fit(frame.loc[:, MODEL_FEATURES], frame[TARGET_COLUMN])
    return BaselineModel(
        pipeline=pipeline,
        model_version=config.model_version,
        feature_version=config.feature_version,
        data_version=config.data_version,
        random_seed=config.random_seed,
    )
