"""FastAPI factory for the approved local synthetic analyst interface."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

from creditpilot.interface.operations import (
    RuntimeConfig,
    RuntimeMetrics,
    configure_logging,
    route_template,
)
from creditpilot.interface.repository import (
    CaseNotFoundError,
    InMemoryCaseRepository,
)
from creditpilot.interface.service import (
    AnalystInterfaceService,
    InterfaceValidationError,
    case_summary,
)
from creditpilot.state import StateUpdateRejected

TEMPLATE_DIR = Path(__file__).with_name("templates")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateCaseRequest(StrictModel):
    application_id: str = Field(min_length=1, max_length=80)
    customer_token: str = Field(min_length=1, max_length=120)
    reported_values: dict[str, Any]
    sanitized_attributes: dict[str, Any]
    source_reference: str = Field(min_length=1, max_length=160)


class DemoReviewRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=500)


class HumanReviewRequest(StrictModel):
    outcome: Literal[
        "ACKNOWLEDGED",
        "RETURN_FOR_INFORMATION",
        "CLOSED_AFTER_REVIEW",
    ]
    rationale: str = Field(min_length=1, max_length=1000)
    reviewer_token: str = Field(min_length=1, max_length=120)
    expected_state_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


def create_app(
    repository: InMemoryCaseRepository | None = None,
    *,
    evaluation_report_path: Path | None = None,
    runtime_config: RuntimeConfig | None = None,
) -> FastAPI:
    repository = repository or InMemoryCaseRepository()
    runtime_config = runtime_config or RuntimeConfig()
    runtime_config.validate()
    service = AnalystInterfaceService(repository)
    metrics = RuntimeMetrics()
    logger = configure_logging(runtime_config.log_level)
    templates = Jinja2Templates(directory=TEMPLATE_DIR)
    report_path = evaluation_report_path or Path("reports/phase12_evaluation.json")
    app = FastAPI(
        title="CreditPilot Synthetic Analyst Interface",
        version="1.0.0",
        description="Synthetic decision support only; not a lending system.",
    )
    app.state.repository = repository
    app.state.service = service
    app.state.metrics = metrics
    app.state.runtime_config = runtime_config

    @app.middleware("http")
    async def operational_observability(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        metrics.record_request(request.method, request.url.path, response.status_code)
        logger.info(
            "request_complete",
            extra={
                "method": request.method,
                "path": route_template(request.url.path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-CreditPilot-Data-Scope"] = "synthetic-only"
        return response

    def state_or_404(application_id: str):
        try:
            return repository.get(application_id)
        except CaseNotFoundError as error:
            raise HTTPException(status_code=404, detail="case not found") from error

    @app.exception_handler(StateUpdateRejected)
    async def state_rejected_handler(_request: Request, error: StateUpdateRejected):
        return _json_error(status.HTTP_409_CONFLICT, str(error))

    @app.exception_handler(InterfaceValidationError)
    async def validation_handler(_request: Request, error: InterfaceValidationError):
        return _json_error(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "data_scope": "synthetic_only"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        if not TEMPLATE_DIR.is_dir() or not report_path.is_file():
            raise HTTPException(
                status_code=503, detail="required artifacts unavailable"
            )
        return {
            "status": "ready",
            "deployment_mode": runtime_config.deployment_mode,
            "persistence": "in_memory",
            "data_scope": "synthetic_only",
        }

    @app.get("/metrics")
    def runtime_metrics() -> dict[str, Any]:
        return metrics.snapshot()

    @app.post("/api/cases", status_code=201)
    def create_case(payload: CreateCaseRequest) -> dict[str, Any]:
        try:
            state = service.create_case(**payload.model_dump())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return case_summary(state)

    @app.get("/api/cases")
    def list_cases() -> list[dict[str, Any]]:
        return [case_summary(state) for state in repository.list()]

    @app.get("/api/cases/{application_id}")
    def get_case(application_id: str) -> dict[str, Any]:
        return case_summary(state_or_404(application_id))

    @app.post("/api/cases/{application_id}/demo-review")
    def require_demo_review(
        application_id: str, payload: DemoReviewRequest
    ) -> dict[str, Any]:
        state_or_404(application_id)
        return case_summary(service.require_demo_review(application_id, payload.reason))

    @app.post("/api/cases/{application_id}/human-review")
    def record_review(
        application_id: str,
        payload: HumanReviewRequest,
        x_analyst_role: str = Header(default=""),
    ) -> dict[str, Any]:
        state_or_404(application_id)
        try:
            state, record, replayed = service.record_human_review(
                application_id,
                actor_role=x_analyst_role,
                **payload.model_dump(),
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        return {
            "review_reference": record.reference,
            "outcome": record.outcome,
            "recorded_at": record.recorded_at,
            "replayed": replayed,
            "case": case_summary(state),
        }

    @app.get("/api/evaluation")
    def get_evaluation() -> dict[str, Any]:
        if not report_path.is_file():
            raise HTTPException(status_code=503, detail="evaluation report unavailable")
        return json.loads(report_path.read_text())

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"cases": [case_summary(item) for item in repository.list()]},
        )

    @app.get("/cases/{application_id}", response_class=HTMLResponse)
    def case_page(request: Request, application_id: str):
        return templates.TemplateResponse(
            request=request,
            name="case.html",
            context={"case": case_summary(state_or_404(application_id))},
        )

    return app


def _json_error(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


app = create_app(runtime_config=RuntimeConfig.from_environment())
