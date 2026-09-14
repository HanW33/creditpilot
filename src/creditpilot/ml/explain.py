"""Quantitative SHAP attribution for the approved baseline model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from creditpilot.ml.data import MODEL_FEATURES, validate_dataset
from creditpilot.ml.model import BaselineModel


def explain_with_shap(
    model: BaselineModel,
    frame: pd.DataFrame,
    *,
    max_rows: int = 200,
) -> dict[str, object]:
    """Return model-derived SHAP values with transformed feature names."""

    validate_dataset(frame, require_target=False)
    if max_rows < 1:
        raise ValueError("max_rows must be positive")

    sample = frame.loc[:, MODEL_FEATURES].head(max_rows)
    preprocess = model.pipeline.named_steps["preprocess"]
    estimator = model.pipeline.named_steps["model"]
    transformed = np.asarray(preprocess.transform(sample), dtype=float)
    feature_names = preprocess.get_feature_names_out().tolist()
    background = shap.maskers.Independent(transformed, max_samples=len(transformed))
    explanation = shap.LinearExplainer(estimator, background)(transformed)

    return {
        "model_version": model.model_version,
        "feature_version": model.feature_version,
        "sample_count": int(len(sample)),
        "feature_names": feature_names,
        "base_values": np.asarray(explanation.base_values).tolist(),
        "shap_values": np.asarray(explanation.values).tolist(),
        "mean_absolute_shap": {
            name: float(value)
            for name, value in sorted(
                zip(
                    feature_names,
                    np.abs(np.asarray(explanation.values)).mean(axis=0),
                    strict=True,
                ),
                key=lambda item: item[1],
                reverse=True,
            )
        },
    }
