"""Centralised logging setup.

Provides three sinks, all stamped with the request id (see ``request_context``):

* **console** — human-readable, for `docker logs` / local dev
* **logs/app.log** — rotating file with everything at ``LOG_LEVEL``
* **logs/error.log** — rotating file with ERROR and above only

Set ``LOG_JSON=true`` to emit structured JSON on every sink (useful for log shippers).
Modules should simply do ``logger = logging.getLogger(__name__)`` — because the package
root logger ``app`` is configured here, child loggers (``app.services.rag`` etc.) inherit it.

The :func:`log_event` helper standardises structured "event" logging used throughout the
ingestion / RAG pipeline so every stage is machine-greppable.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import logging.config
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.request_context import RequestIdFilter

# LogRecord attributes that are built-in; everything else is treated as a structured "extra".
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"request_id", "user_id", "message", "asctime", "taskName", "color_message"}


class JsonFormatter(logging.Formatter):
    """Render each record as a single-line JSON object including any `extra=` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> None:
    """Apply the dictConfig. Call once, as early as possible at process start."""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = "json" if settings.log_json else "console"
    console_format = (
        "%(asctime)s | %(levelname)-8s | req=%(request_id)s user=%(user_id)s "
        "| %(name)s | %(message)s"
    )

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": RequestIdFilter},
        },
        "formatters": {
            "console": {"format": console_format, "datefmt": "%Y-%m-%d %H:%M:%S"},
            "json": {"()": JsonFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": fmt,
                "filters": ["request_id"],
                "stream": "ext://sys.stdout",
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": fmt,
                "filters": ["request_id"],
                "filename": str(log_dir / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": fmt,
                "filters": ["request_id"],
                "filename": str(log_dir / "error.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            # Our application logger — handles everything, does not propagate to root.
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False,
            },
            # Uvicorn: route through our handlers for a consistent format.
            "uvicorn": {"level": "INFO", "handlers": ["console", "file_app"], "propagate": False},
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False,
            },
            # Access logging is done by our own middleware; silence uvicorn's to avoid dupes.
            "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "sqlalchemy.engine": {"level": "WARNING", "handlers": ["file_app"], "propagate": False},
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file_app", "file_error"],
        },
    }

    logging.config.dictConfig(config)
    logging.getLogger("app.logging").info(
        "logging configured",
        extra={"log_level": settings.log_level, "json": settings.log_json, "dir": str(log_dir)},
    )


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured pipeline event, e.g. ``log_event(log, "extract.done", pages=3)``.

    The ``event`` name becomes the message and a field; remaining kwargs are attached as
    structured extras (visible in JSON logs and appended to the console message).

    Field names that collide with reserved ``LogRecord`` attributes (e.g. ``filename``,
    ``module``, ``name``) are suffixed with ``_`` so ``logging`` does not raise
    ``KeyError: "Attempt to overwrite ... in LogRecord"``.
    """
    if not logger.isEnabledFor(level):
        return
    safe_fields = {(f"{k}_" if k in _RESERVED else k): v for k, v in fields.items()}
    extra = {"event": event, **safe_fields}
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.log(level, "%s %s", event, detail, extra=extra)
