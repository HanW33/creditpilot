"""Run the reproducible Phase 1 baseline and write an evaluation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from creditpilot.ml.config import Phase1Config
from creditpilot.ml.data import generate_synthetic_applications
from creditpilot.ml.evaluation import evaluate_model, split_summary, stratified_split
from creditpilot.ml.explain import explain_with_shap
from creditpilot.ml.model import train_baseline


def run(config: Phase1Config) -> dict[str, object]:
    data = generate_synthetic_applications(config)
    splits = stratified_split(data, config)
    model = train_baseline(splits.train, config)
    report = evaluate_model(model, splits.test, config)
    report["splits"] = split_summary(splits)
    shap_report = explain_with_shap(model, splits.test, max_rows=200)
    report["shap"] = {
        "model_version": shap_report["model_version"],
        "feature_version": shap_report["feature_version"],
        "sample_count": shap_report["sample_count"],
        "mean_absolute_shap": shap_report["mean_absolute_shap"],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase1_baseline_metrics.json"),
    )
    parser.add_argument("--samples", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=33)
    args = parser.parse_args()

    report = run(Phase1Config(sample_count=args.samples, random_seed=args.seed))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {"output": str(args.output), "metrics": report["metrics"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
