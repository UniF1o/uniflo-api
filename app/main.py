import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.applications.router import router as applications_router
from app.api.auth.router import router as auth_router
from app.api.documents.router import router as documents_router
from app.api.middleware.auth import AuthMiddleware
from app.api.profiles.router import router as profiles_router
from app.api.universities.router import router as universities_router
from app.api.webhooks.router import router as webhooks_router
from app.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
    )

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="UniFlo", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(documents_router)
app.include_router(universities_router)
app.include_router(applications_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.head("/ping")
def service_ping():
    return {"status": "ok"}
