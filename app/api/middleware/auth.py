import uuid

import jwt
from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.db import get_engine
from app.models.user import User

PUBLIC_EXACT = {
    "/health",
    "/ping",
    "/openapi.json",
    "/webhooks/user-created",
    "/webhooks/user-updated",
    "/webhooks/user-deleted",
}
PUBLIC_PREFIXES = ("/docs", "/redoc", "/universities")

_jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")


def ensure_user_synced(sub: str | None, email: str | None) -> None:
    """Belt-and-suspenders for the Supabase user-created/user-updated webhooks.

    Guarantees that every authenticated request has a corresponding `users` row
    and that its email matches the JWT. Removes the need for per-endpoint
    self-heal logic.
    """
    if not sub or not email:
        return
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        return

    with Session(get_engine()) as session:
        user = session.get(User, user_id)
        if user is None:
            session.add(User(id=user_id, email=email, role="student"))
            session.commit()
        elif user.email != email:
            user.email = email
            session.add(user)
            session.commit()


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                options={"verify_aud": False},
            )
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"},
            )
        except (jwt.InvalidTokenError, PyJWKClientError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        await run_in_threadpool(
            ensure_user_synced, payload.get("sub"), payload.get("email")
        )

        return await call_next(request)
