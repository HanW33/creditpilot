import numpy as np

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import generate_synthetic_applications
from creditpilot.ml.evaluation import evaluate_model, stratified_split
from creditpilot.ml.model import train_baseline


def test_baseline_trains_predicts_and_evaluates() -> None:
    config = Phase1Config(sample_count=800, random_seed=11)
    splits = stratified_split(generate_synthetic_applications(config), config)
    model = train_baseline(splits.train, config)
    probability = model.predict_pd(splits.test)
    report = evaluate_model(model, splits.test, config)

    assert len(probability) == len(splits.test)
    assert np.all((probability >= 0) & (probability <= 1))
    assert set(report["metrics"]) == {
        "roc_auc",
        "pr_auc",
        "precision",
        "recall",
        "f1",
        "ks",
        "brier_score",
        "confusion_matrix",
        "calibration",
    }
    assert report["model_version"] == config.model_version
    assert "not a lending" in report["diagnostic_cutoff_notice"]


def test_split_is_reproducible_and_stratified() -> None:
    config = Phase1Config(sample_count=1_000, random_seed=19)
    data = generate_synthetic_applications(config)
    first = stratified_split(data, config)
    second = stratified_split(data, config)

    assert first.train.equals(second.train)
    assert first.validation.equals(second.validation)
    assert first.test.equals(second.test)
    assert (len(first.train), len(first.validation), len(first.test)) == (600, 200, 200)
