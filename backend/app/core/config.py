from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CareConnect"
    environment: str = "development"
    database_url: str = "sqlite:///./careconnect.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-only-change-this-secret-before-deploying"
    voice_webhook_secret: str = ""
    access_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    rate_limit_per_minute: int = 120

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
