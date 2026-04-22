import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth.router import router as auth_router
from app.api.documents.router import router as documents_router
from app.api.middleware.auth import AuthMiddleware
from app.api.profiles.router import router as profiles_router
from app.api.webhooks.router import router as webhooks_router
from app.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
    )

app = FastAPI(title="UniFlo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(documents_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.head("/ping")
def service_ping():
    return {"status": "ok"}
