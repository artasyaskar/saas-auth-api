from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./saas_auth.db"
    secret_key: str = "your-super-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    stripe_api_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"


settings = Settings()
