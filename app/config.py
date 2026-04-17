from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    WEBHOOK_SECRET: str = "LU0PmJBEqI4IudUPdDM26AUUAK1/Nx2me0fnAYOIMXE="
    DELETE_WEBHOOK_SECRET: str = "vkDr4cpNpBmTVzOwd47g9+qjG/4upJnegy36IXqot/k="
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
