"""Operational controls for the local synthetic V1 deployment."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    deployment_mode: str = "synthetic_demo"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_environment(cls) -> RuntimeConfig:
        config = cls(
            deployment_mode=os.getenv("CREDITPILOT_DEPLOYMENT_MODE", "synthetic_demo"),
            log_level=os.getenv("CREDITPILOT_LOG_LEVEL", "INFO").upper(),
            host=os.getenv("CREDITPILOT_HOST", "127.0.0.1"),
            port=int(os.getenv("CREDITPILOT_PORT", "8000")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.deployment_mode != "synthetic_demo":
            raise ValueError("V1 supports synthetic_demo deployment mode only")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("unsupported log level")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.host not in {"127.0.0.1", "0.0.0.0"}:
            raise ValueError("host must be an explicit local or container binding")


class JsonFormatter(logging.Formatter):
    """Emit structured logs without request bodies or sensitive case data."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("creditpilot.interface")
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class RuntimeMetrics:
    """Small in-process counters for the non-production synthetic demo."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[str] = Counter()
        self._status_codes: Counter[str] = Counter()
        self._human_review_submissions = 0

    def record_request(self, method: str, path: str, status_code: int) -> None:
        route_group = route_template(path)
        with self._lock:
            self._requests[f"{method} {route_group}"] += 1
            self._status_codes[str(status_code)] += 1
            if method == "POST" and path.endswith("/human-review"):
                self._human_review_submissions += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "requests": dict(self._requests),
                "status_codes": dict(self._status_codes),
                "human_review_submissions": self._human_review_submissions,
                "persistence": "in_memory",
                "data_scope": "synthetic_only",
            }


def route_template(path: str) -> str:
    """Remove controlled case identifiers from operational labels and logs."""

    if path.startswith("/api/cases/"):
        if path.endswith("/human-review"):
            return "/api/cases/{id}/human-review"
        if path.endswith("/demo-review"):
            return "/api/cases/{id}/demo-review"
        return "/api/cases/{id}"
    return path
