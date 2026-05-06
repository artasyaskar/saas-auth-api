"""
Configuration management for the SaaS Auth API.

Comprehensive settings management with environment variable support,
validation, and different configurations for development, staging, and production.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Environment(str, Enum):
    """Application environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(20, ge=1, le=100, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(30, ge=1, le=100, env="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(False, env="DATABASE_ECHO")
    
    @validator('url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(('postgresql://', 'sqlite:///')):
            raise ValueError('Database URL must start with postgresql:// or sqlite:///')
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field("redis://localhost:6379", env="REDIS_URL")
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, ge=1, le=65535, env="REDIS_PORT")
    db: int = Field(0, ge=0, le=15, env="REDIS_DB")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    max_connections: int = Field(100, ge=1, le=1000, env="REDIS_MAX_CONNECTIONS")
    
    @validator('url')
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        if not v.startswith('redis://'):
            raise ValueError('Redis URL must start with redis://')
        return v


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(..., min_length=32, env="SECRET_KEY")
    jwt_secret: str = Field(..., min_length=32, env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, ge=5, le=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, ge=1, le=365, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password settings
    password_min_length: int = Field(8, ge=6, le=128, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(True, env="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(True, env="PASSWORD_REQUIRE_LOWERCASE")
    password_require_numbers: bool = Field(True, env="PASSWORD_REQUIRE_NUMBERS")
    password_require_symbols: bool = Field(True, env="PASSWORD_REQUIRE_SYMBOLS")
    
    # Session settings
    session_timeout: int = Field(3600, ge=300, le=86400, env="SESSION_TIMEOUT")
    max_sessions_per_user: int = Field(3, ge=1, le=10, env="MAX_SESSIONS_PER_USER")
    
    # Encryption settings
    encryption_key: Optional[str] = Field(None, min_length=32, env="ENCRYPTION_KEY")


class EmailSettings(BaseSettings):
    """Email configuration settings."""
    
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(587, ge=1, le=65535, env="SMTP_PORT")
    smtp_user: str = Field(..., env="SMTP_USER")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_tls: bool = Field(True, env="SMTP_TLS")
    smtp_ssl: bool = Field(False, env="SMTP_SSL")
    
    from_email: str = Field("noreply@example.com", env="FROM_EMAIL")
    from_name: str = Field("SaaS Auth", env="FROM_NAME")
    
    # Email service settings
    email_service: str = Field("smtp", env="EMAIL_SERVICE", regex="^(smtp|sendgrid|ses|mailgun)$")
    sendgrid_api_key: Optional[str] = Field(None, env="SENDGRID_API_KEY")
    ses_region: str = Field("us-east-1", env="SES_REGION")
    ses_access_key: Optional[str] = Field(None, env="SES_ACCESS_KEY")
    ses_secret_key: Optional[str] = Field(None, env="SES_SECRET_KEY")
    
    # Email verification settings
    verification_template: str = Field("verification", env="EMAIL_VERIFICATION_TEMPLATE")
    reset_template: str = Field("password_reset", env="PASSWORD_RESET_TEMPLATE")
    welcome_template: str = Field("welcome", env="WELCOME_TEMPLATE")


class OAuthSettings(BaseSettings):
    """OAuth provider configuration settings."""
    
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(None, env="GOOGLE_REDIRECT_URI")
    google_enabled: bool = Field(True, env="GOOGLE_ENABLED")
    
    github_client_id: Optional[str] = Field(None, env="GITHUB_CLIENT_ID")
    github_client_secret: Optional[str] = Field(None, env="GITHUB_CLIENT_SECRET")
    github_redirect_uri: Optional[str] = Field(None, env="GITHUB_REDIRECT_URI")
    github_enabled: bool = Field(True, env="GITHUB_ENABLED")
    
    microsoft_client_id: Optional[str] = Field(None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(None, env="MICROSOFT_CLIENT_SECRET")
    microsoft_redirect_uri: Optional[str] = Field(None, env="MICROSOFT_REDIRECT_URI")
    microsoft_enabled: bool = Field(True, env="MICROSOFT_ENABLED")
    
    # TODO: Add Apple OAuth settings
    # TODO: Add Okta OAuth settings


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""
    
    default_limit: int = Field(1000, ge=1, le=10000, env="RATE_LIMIT_DEFAULT")
    window_seconds: int = Field(3600, ge=60, le=86400, env="RATE_LIMIT_WINDOW")
    burst_limit: int = Field(100, ge=1, le=1000, env="RATE_LIMIT_BURST")
    
    # Per-endpoint limits
    login_limit: int = Field(5, ge=1, le=20, env="LOGIN_RATE_LIMIT")
    registration_limit: int = Field(3, ge=1, le=10, env="REGISTRATION_RATE_LIMIT")
    password_reset_limit: int = Field(3, ge=1, le=10, env="PASSWORD_RESET_RATE_LIMIT")
    
    # TODO: Add IP-based limits
    # TODO: Add user-based limits


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT", regex="^(json|text)$")
    file_path: Optional[str] = Field(None, env="LOG_FILE_PATH")
    max_file_size: int = Field(10485760, ge=1048576, le=1073741824, env="LOG_MAX_FILE_SIZE")
    
    # Structured logging
    enable_request_id: bool = Field(True, env="ENABLE_REQUEST_ID")
    enable_correlation_id: bool = Field(True, env="ENABLE_CORRELATION_ID")
    enable_performance_logging: bool = Field(True, env="ENABLE_PERFORMANCE_LOGGING")
    
    # TODO: Add log rotation settings
    # TODO: Add external logging service


class ApplicationSettings(BaseSettings):
    """Main application configuration settings."""
    
    name: str = Field("SaaS Auth API", env="APP_NAME")
    version: str = Field("1.1.0", env="APP_VERSION")
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # API settings
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    docs_url: str = Field("/docs", env="DOCS_URL")
    redoc_url: str = Field("/redoc", env="REDOC_URL")
    openapi_url: str = Field("/openapi.json", env="OPENAPI_URL")
    
    # CORS settings
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(["*"], env="CORS_ALLOW_HEADERS")
    cors_max_age: int = Field(600, ge=0, le=86400, env="CORS_MAX_AGE")
    
    # Frontend settings
    frontend_url: str = Field("http://localhost:3000", env="FRONTEND_URL")
    base_url: str = Field("http://localhost:8000", env="BASE_URL")
    
    # Feature flags
    enable_email_verification: bool = Field(False, env="ENABLE_EMAIL_VERIFICATION")
    enable_two_factor_auth: bool = Field(False, env="ENABLE_TWO_FACTOR_AUTH")
    enable_oauth: bool = Field(True, env="ENABLE_OAUTH")
    enable_rate_limiting: bool = Field(True, env="ENABLE_RATE_LIMITING")
    enable_audit_logging: bool = Field(True, env="ENABLE_AUDIT_LOGGING")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    enable_health_checks: bool = Field(True, env="ENABLE_HEALTH_CHECKS")
    
    # Maintenance settings
    maintenance_mode: bool = Field(False, env="MAINTENANCE_MODE")
    maintenance_message: str = Field("System under maintenance", env="MAINTENANCE_MESSAGE")
    
    # TODO: Add deployment settings
    # TODO: Add monitoring settings


class Settings(BaseSettings):
    """
    Main application settings class.
    
    Combines all configuration sections with validation
    and environment-specific overrides.
    """
    
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Database
    database: DatabaseSettings = DatabaseSettings()
    
    # Redis
    redis: RedisSettings = RedisSettings()
    
    # Security
    security: SecuritySettings = SecuritySettings()
    
    # Email
    email: EmailSettings = EmailSettings()
    
    # OAuth
    oauth: OAuthSettings = OAuthSettings()
    
    # Rate limiting
    rate_limit: RateLimitSettings = RateLimitSettings()
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

# Validate production settings
if settings.is_production():
    if settings.secret_key == "your-super-secret-key-here-change-in-production":
        raise ValueError("SECRET_KEY must be changed in production environment")
