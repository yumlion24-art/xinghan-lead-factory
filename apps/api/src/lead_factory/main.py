from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from lead_factory.api import accounts, configuration, dashboard, health, search_tasks
from lead_factory.api.errors import ApiError
from lead_factory.config_loader import load_catalog
from lead_factory.db import Base, get_engine
from lead_factory.logging import configure_logging
from lead_factory.providers.ai.disabled import DisabledAIProvider
from lead_factory.providers.ai.openai_provider import OpenAIProvider
from lead_factory.providers.search.base import SearchHit, SearchRequest
from lead_factory.providers.search.public_search import PublicSearchProvider
from lead_factory.providers.search.seed import SeedSearchProvider
from lead_factory.services.fetcher import Fetcher, HttpxTransport
from lead_factory.settings import Settings
from lead_factory.task_runner import TaskRunner


class CombinedSearchProvider:
    def __init__(self) -> None:
        self.seed = SeedSearchProvider()
        self.public = PublicSearchProvider()

    async def search(self, request: SearchRequest) -> list[SearchHit]:
        hits = await self.seed.search(request)
        if request.query and len(hits) < request.max_results:
            hits.extend(await self.public.search(request))
        unique: dict[str, SearchHit] = {}
        for hit in hits:
            unique.setdefault(hit.url, hit)
        return list(unique.values())[: request.max_results]


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def create_app(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    runner: object | None = None,
) -> FastAPI:
    settings = settings or Settings()
    catalog = load_catalog(settings.config_dir)
    engine = engine or get_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings)
        Base.metadata.create_all(engine)
        if hasattr(app.state.runner, "recover_interrupted"):
            app.state.runner.recover_interrupted()
        yield

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.catalog = catalog
    app.state.engine = engine
    if runner is None:
        sessions = sessionmaker(engine, expire_on_commit=False)
        ai_provider = (
            OpenAIProvider(
                settings.ai_api_key,
                settings.ai_model,
                settings.config_dir / "prompts/company_enrichment-v1.md",
            )
            if settings.ai_provider == "openai"
            else DisabledAIProvider()
        )
        runner = TaskRunner(
            session_factory=sessions,
            catalog=catalog,
            search_provider=CombinedSearchProvider(),
            fetcher=Fetcher(
                transport=HttpxTransport(catalog.crawler.user_agent),
                timeout_seconds=catalog.crawler.request_timeout_seconds,
                max_response_bytes=catalog.crawler.max_response_bytes,
                max_redirects=catalog.crawler.max_redirects,
                domain_delay_seconds=catalog.crawler.per_domain_delay_seconds,
                allowed_content_types=tuple(catalog.crawler.allowed_content_types),
            ),
            ai_provider=ai_provider,
        )
    app.state.runner = runner

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "request_id": _request_id(request),
                }
            },
        )

    api_prefix = "/api/v1"
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(accounts.router, prefix=api_prefix)
    app.include_router(search_tasks.router, prefix=api_prefix)
    app.include_router(configuration.router, prefix=api_prefix)
    return app


app = create_app()
