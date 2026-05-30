"""Reusable FastAPI dependencies: DB session, current user, API-key guard."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import set_user_id
from app.core.security import ACCESS, JWTError, decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve and validate the bearer token into an active ``User``."""
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS:
            raise _credentials_error
        user_id = uuid.UUID(str(payload.get("sub")))
    except (JWTError, ValueError, TypeError) as exc:
        raise _credentials_error from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error

    # Stamp the user id onto the request's log context.
    set_user_id(str(user.id))
    return user


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Guard for programmatic endpoints. Enabled only when ``API_KEYS`` is set."""
    keys = settings.api_keys_list
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="API key authentication is not enabled"
        )
    if x_api_key not in keys:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# Convenient annotated aliases used across route signatures.
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
