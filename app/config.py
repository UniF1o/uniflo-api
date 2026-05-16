from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_STORAGE_BUCKET: str
    WEBHOOK_SECRET: str
    DELETE_WEBHOOK_SECRET: str
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"
    # Stored as str so pydantic-settings v2 does not attempt json.loads() on it.
    # Use the cors_origins property wherever a list is needed.
    CORS_ORIGINS: str = "http://localhost:3000,https://uniflo-web.vercel.app"
    # Vercel preview deployments (uniflo-web-<hash>.vercel.app) aren't known
    # ahead of time; allow them via regex in addition to the exact origins.
    CORS_ORIGIN_REGEX: Optional[str] = r"https://uniflo-web-[a-z0-9-]+\.vercel\.app"
    FAKE_AUTOMATION: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
