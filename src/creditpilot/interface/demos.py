"""One-click execution of the approved synthetic Golden Demo contracts."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from creditpilot.evaluation.cli import reference_observations
from creditpilot.evaluation.harness import evaluate_scenario

DEMO_TITLES = {
    "golden-1-low-risk": "Straightforward low-risk case",
    "golden-2-income-verification": "Verification changes risk assessment",
    "golden-3-policy-conflict": "Policy or evidence conflict",
}


class GoldenDemoRunner:
    """Run contract checks live against approved synthetic trace fixtures."""

    def __init__(self) -> None:
        self._observations = {
            item.scenario_id: item for item in reference_observations()
        }
        self._runs: dict[str, dict] = {}

    def catalog(self) -> list[dict[str, str]]:
        return [
            {
                "scenario_id": scenario_id,
                "title": DEMO_TITLES[scenario_id],
                "execution_kind": "synthetic_architecture_contract",
            }
            for scenario_id in DEMO_TITLES
        ]

    def run(self, scenario_id: str) -> dict:
        observation = self._observations.get(scenario_id)
        if observation is None:
            raise KeyError(scenario_id)
        result = evaluate_scenario(observation)
        run_id = f"demo-run-{uuid4().hex[:12]}"
        payload = {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "title": DEMO_TITLES[scenario_id],
            "status": result.status,
            "executed_at": datetime.now(UTC).isoformat(),
            "execution_kind": "synthetic_architecture_contract",
            "execution_notice": (
                "Checks execute live against the approved synthetic trace fixture. "
                "This validates the architecture contract; it is not a live provider "
                "call or a production lending decision."
            ),
            "trace": [asdict(check) for check in result.checks],
        }
        self._runs[run_id] = payload
        return payload

    def get(self, run_id: str) -> dict:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise KeyError(run_id) from error
