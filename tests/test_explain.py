import numpy as np

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import generate_synthetic_applications
from creditpilot.ml.evaluation import stratified_split
from creditpilot.ml.explain import explain_with_shap
from creditpilot.ml.model import train_baseline


def test_shap_values_come_from_trained_model() -> None:
    config = Phase1Config(sample_count=500, random_seed=23)
    splits = stratified_split(generate_synthetic_applications(config), config)
    model = train_baseline(splits.train, config)
    result = explain_with_shap(model, splits.test, max_rows=25)

    values = np.asarray(result["shap_values"])
    assert result["sample_count"] == 25
    assert values.shape == (25, len(result["feature_names"]))
    assert np.isfinite(values).all()
    assert result["model_version"] == config.model_version
