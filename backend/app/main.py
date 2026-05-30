"""FastAPI application entrypoint.

Wires together logging, the request-id / access-logging middleware, CORS, a global
exception handler, and the route tree. Import side effect: logging is configured at
import time so even startup logs are captured.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.api.routes import health
from app.core.config import settings
from app.core.logging_config import configure_logging, log_event
from app.core.request_context import get_request_id, new_request_id, set_request_id, set_user_id

configure_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log_event(
        logger,
        "startup",
        app=settings.app_name,
        env=settings.environment,
        primary_llm=settings.llm_primary,
        fallback=settings.llm_fallback_enabled,
        embedding_model=settings.embedding_model,
    )
    yield
    log_event(logger, "shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        set_request_id(request_id)
        set_user_id("-")
        start = time.perf_counter()
        client = request.client.host if request.client else "-"
        logger.info(
            "request.start",
            extra={
                "event": "request.start",
                "method": request.method,
                "path": request.url.path,
                "client": client,
            },
        )
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            # Full traceback goes to error.log, tagged with the request id.
            logger.exception(
                "request.error",
                extra={
                    "event": "request.error",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": get_request_id()},
                headers={"X-Request-ID": request_id},
            )
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.end",
            extra={
                "event": "request.end",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
