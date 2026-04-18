from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    WEBHOOK_SECRET: str 
    DELETE_WEBHOOK_SECRET: str 
    SUPABASE_STORAGE_BUCKET: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
