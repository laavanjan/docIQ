"""Per-request correlation id propagated through logs via a contextvar.

A unique ``request_id`` is generated for every HTTP request (see the middleware in
``app.main``) and stored in a :class:`contextvars.ContextVar`. The :class:`RequestIdFilter`
copies it onto every :class:`logging.LogRecord`, so any log line emitted while handling a
request can be traced back to that request — even from deep inside the pipeline.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

# "-" is the sentinel used for logs emitted outside any request (startup, workers, ...).
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


def set_user_id(user_id: str) -> None:
    _user_id_ctx.set(user_id)


def get_user_id() -> str:
    return _user_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Inject the current request/user id onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        record.user_id = _user_id_ctx.get()
        return True
