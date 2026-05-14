import json
from typing import Optional

from pydantic import field_validator
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
    CORS_ORIGINS: str = "http://localhost:3000,https://uniflo-web.vercel.app"
    FAKE_AUTOMATION: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        v = self.CORS_ORIGINS.strip()
        if v.startswith("["):
            return json.loads(v)
        return [origin.strip() for origin in v.split(",") if origin.strip()]


settings = Settings()
