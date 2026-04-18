import sentry_sdk
from fastapi import FastAPI

from app.config import settings
from app.api.middleware.auth import AuthMiddleware
from app.api.webhooks.router import router as webhooks_router
from app.api.auth.router import router as auth_router

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
    )

app = FastAPI(title="UniFlo", version="0.1.0")

app.add_middleware(AuthMiddleware)
app.include_router(webhooks_router) #user table links endpoints
app.include_router(auth_router) #auth endpoints

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
@app.head("/ping")
def service_ping():
    return {"status": "200 ok", "environment": settings.ENVIRONMENT}
