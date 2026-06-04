from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    # Server-side Storage writes to a private bucket need service-role (anon
    # is denied by Storage RLS). Optional so the app still boots if unset.
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
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

    # AI field-mapping layer (Phase 3). Provider-agnostic; default Gemini Flash.
    # All optional so the app still boots without a key.
    AI_PROVIDER: str = "gemini"  # gemini | anthropic
    AI_MODEL: Optional[str] = None  # overrides the provider's default model
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    # Entries below this confidence are flagged for review on the frontend.
    FIELD_CONFIDENCE_THRESHOLD: float = 0.85

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
