import logging
import re

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.academic_records.router import router as academic_records_router
from app.api.account.router import router as account_router
from app.api.applications.router import router as applications_router
from app.api.auth.router import router as auth_router
from app.api.careers.router import router as careers_router
from app.api.contacts.router import router as contacts_router
from app.api.documents.router import router as documents_router
from app.api.middleware.auth import AuthMiddleware
from app.api.profiles.router import router as profiles_router
from app.api.recommendations.router import router as recommendations_router
from app.api.universities.router import router as universities_router
from app.api.webhooks.router import router as webhooks_router
from app.config import settings
from app.rate_limit import limiter

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
    )

app = FastAPI(title="UniFlo", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

_cors_origin_regex = (
    re.compile(settings.CORS_ORIGIN_REGEX) if settings.CORS_ORIGIN_REGEX else None
)


def _error_cors_headers(request: Request) -> dict[str, str]:
    # Starlette's ServerErrorMiddleware wraps the whole app *outside*
    # CORSMiddleware, so an unhandled 500 never gets CORS headers and the
    # browser only sees a network/CORS error -- the real cause is invisible.
    # Reordering user middleware can't fix this; re-apply the CORS policy here.
    origin = request.headers.get("origin")
    if not origin:
        return {}
    allowed = origin in settings.cors_origins or (
        _cors_origin_regex is not None
        and _cors_origin_regex.fullmatch(origin) is not None
    )
    if not allowed:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal_error"},
        headers=_error_cors_headers(request),
    )


app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(profiles_router)
app.include_router(academic_records_router)
app.include_router(contacts_router)
app.include_router(documents_router)
app.include_router(universities_router)
app.include_router(recommendations_router)
app.include_router(careers_router)
app.include_router(applications_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.head("/ping")
def service_ping():
    return {"status": "ok"}
