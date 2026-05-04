from pydantic_settings import BaseSettings
from typing import Optional, List
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # Application
    app_name: str = "SaaS Auth API"
    app_version: str = "1.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Security
    database_url: str = "sqlite:///./saas_auth.db"
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    
    # Redis / Cache
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    from_email: str = "noreply@saasauth.example.com"
    from_name: str = "SaaS Auth"
    
    # Feature Flags
    enable_email_verification: bool = False
    enable_password_reset: bool = True
    enable_2fa: bool = False
    enable_audit_logging: bool = True
    enable_rate_limiting: bool = True
    enable_token_blacklist: bool = True
    
    # Password Policy
    min_password_length: int = 8
    max_password_length: int = 128
    require_uppercase: bool = False
    require_lowercase: bool = False
    require_numbers: bool = False
    require_special_chars: bool = False
    password_history_size: int = 5  # Prevent reuse of last N passwords
    
    # Session Management
    max_concurrent_sessions: int = 5
    session_timeout_hours: int = 24
    absolute_timeout_hours: int = 168  # 7 days
    
    # Stripe / Payments
    stripe_api_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    # Cleanup
    audit_log_retention_days: int = 90
    token_blacklist_cleanup_days: int = 7
    password_reset_token_expiry_hours: int = 24
    email_verification_expiry_hours: int = 48
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT


settings = Settings()
