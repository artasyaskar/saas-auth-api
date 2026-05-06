"""
Configuration management for the SaaS Auth API.

Settings use Pydantic v2 and pydantic-settings with nested sections
and backward-compatible properties for modules that expect flat names.
"""

from enum import Enum
from typing import Optional, List, Any

from pydantic import Field, field_validator, model_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = Field(
        default="postgresql://user:password@localhost:5432/saas_auth_db",
        validation_alias=AliasChoices("DATABASE_URL", "url"),
    )
    pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias=AliasChoices("DATABASE_POOL_SIZE", "pool_size"),
    )
    max_overflow: int = Field(
        default=30,
        ge=1,
        le=100,
        validation_alias=AliasChoices("DATABASE_MAX_OVERFLOW", "max_overflow"),
    )
    echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(
            ("postgresql://", "postgresql+psycopg2://", "sqlite:///", "sqlite://")
        ):
            raise ValueError(
                "Database URL must start with postgresql://, postgresql+psycopg2://, or sqlite:///"
            )
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    url: str = Field(
        default="redis://localhost:6379",
        validation_alias=AliasChoices("REDIS_URL", "url"),
    )
    host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    port: int = Field(default=6379, ge=1, le=65535, validation_alias="REDIS_PORT")
    db: int = Field(default=0, ge=0, le=15, validation_alias="REDIS_DB")
    password: Optional[str] = Field(default=None, validation_alias="REDIS_PASSWORD")
    max_connections: int = Field(
        default=100, ge=1, le=1000, validation_alias="REDIS_MAX_CONNECTIONS"
    )

    @field_validator("url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    secret_key: str = Field(
        ...,
        min_length=32,
        validation_alias=AliasChoices("SECRET_KEY", "secret_key"),
    )
    jwt_secret: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM", "jwt_algorithm"),
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES", "access_token_expire_minutes"
        ),
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=365,
        validation_alias=AliasChoices(
            "REFRESH_TOKEN_EXPIRE_DAYS", "refresh_token_expire_days"
        ),
    )

    password_min_length: int = Field(
        default=8, ge=6, le=128, validation_alias="PASSWORD_MIN_LENGTH"
    )
    password_require_uppercase: bool = Field(
        default=True, validation_alias="PASSWORD_REQUIRE_UPPERCASE"
    )
    password_require_lowercase: bool = Field(
        default=True, validation_alias="PASSWORD_REQUIRE_LOWERCASE"
    )
    password_require_numbers: bool = Field(
        default=True, validation_alias="PASSWORD_REQUIRE_NUMBERS"
    )
    password_require_symbols: bool = Field(
        default=True, validation_alias="PASSWORD_REQUIRE_SYMBOLS"
    )

    session_timeout: int = Field(
        default=3600, ge=300, le=86400, validation_alias="SESSION_TIMEOUT"
    )
    max_sessions_per_user: int = Field(
        default=3, ge=1, le=10, validation_alias="MAX_SESSIONS_PER_USER"
    )

    encryption_key: Optional[str] = Field(
        default=None, min_length=32, validation_alias="ENCRYPTION_KEY"
    )

    @model_validator(mode="after")
    def default_jwt_secret_from_secret_key(self):
        if not self.jwt_secret or len(self.jwt_secret) < 32:
            self.jwt_secret = self.secret_key
        return self


class EmailSettings(BaseSettings):
    """Email configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    smtp_host: str = Field(default="smtp.gmail.com", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, ge=1, le=65535, validation_alias="SMTP_PORT")
    smtp_user: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_USER", "SMTP_USERNAME", "smtp_user"),
    )
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASSWORD", "smtp_password"),
    )
    smtp_tls: bool = Field(default=True, validation_alias="SMTP_TLS")
    smtp_ssl: bool = Field(default=False, validation_alias="SMTP_SSL")

    from_email: str = Field(
        default="noreply@example.com",
        validation_alias=AliasChoices("FROM_EMAIL", "SMTP_FROM"),
    )
    from_name: str = Field(default="SaaS Auth", validation_alias="FROM_NAME")

    email_service: str = Field(
        default="smtp",
        validation_alias="EMAIL_SERVICE",
        pattern="^(smtp|sendgrid|ses|mailgun)$",
    )
    sendgrid_api_key: Optional[str] = Field(
        default=None, validation_alias="SENDGRID_API_KEY"
    )
    ses_region: str = Field(default="us-east-1", validation_alias="SES_REGION")
    ses_access_key: Optional[str] = Field(default=None, validation_alias="SES_ACCESS_KEY")
    ses_secret_key: Optional[str] = Field(default=None, validation_alias="SES_SECRET_KEY")

    verification_template: str = Field(
        default="verification", validation_alias="EMAIL_VERIFICATION_TEMPLATE"
    )
    reset_template: str = Field(
        default="password_reset", validation_alias="PASSWORD_RESET_TEMPLATE"
    )
    welcome_template: str = Field(default="welcome", validation_alias="WELCOME_TEMPLATE")


class OAuthSettings(BaseSettings):
    """OAuth provider configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    google_client_id: Optional[str] = Field(
        default=None, validation_alias="GOOGLE_CLIENT_ID"
    )
    google_client_secret: Optional[str] = Field(
        default=None, validation_alias="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: Optional[str] = Field(
        default=None, validation_alias="GOOGLE_REDIRECT_URI"
    )
    google_enabled: bool = Field(default=True, validation_alias="GOOGLE_ENABLED")

    github_client_id: Optional[str] = Field(
        default=None, validation_alias="GITHUB_CLIENT_ID"
    )
    github_client_secret: Optional[str] = Field(
        default=None, validation_alias="GITHUB_CLIENT_SECRET"
    )
    github_redirect_uri: Optional[str] = Field(
        default=None, validation_alias="GITHUB_REDIRECT_URI"
    )
    github_enabled: bool = Field(default=True, validation_alias="GITHUB_ENABLED")

    microsoft_client_id: Optional[str] = Field(
        default=None, validation_alias="MICROSOFT_CLIENT_ID"
    )
    microsoft_client_secret: Optional[str] = Field(
        default=None, validation_alias="MICROSOFT_CLIENT_SECRET"
    )
    microsoft_redirect_uri: Optional[str] = Field(
        default=None, validation_alias="MICROSOFT_REDIRECT_URI"
    )
    microsoft_enabled: bool = Field(default=True, validation_alias="MICROSOFT_ENABLED")


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    default_limit: int = Field(
        default=1000, ge=1, le=10000, validation_alias="RATE_LIMIT_DEFAULT"
    )
    window_seconds: int = Field(
        default=3600, ge=60, le=86400, validation_alias="RATE_LIMIT_WINDOW"
    )
    burst_limit: int = Field(
        default=100, ge=1, le=1000, validation_alias="RATE_LIMIT_BURST"
    )
    login_limit: int = Field(default=5, ge=1, le=20, validation_alias="LOGIN_RATE_LIMIT")
    registration_limit: int = Field(
        default=3, ge=1, le=10, validation_alias="REGISTRATION_RATE_LIMIT"
    )
    password_reset_limit: int = Field(
        default=3, ge=1, le=10, validation_alias="PASSWORD_RESET_RATE_LIMIT"
    )


class Settings(BaseSettings):
    """
    Main application settings.

    Nested sections load from the same .env; flat property aliases exist for
    legacy call sites (e.g. settings.secret_key, settings.database_url).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    require_lowercase: bool = False
    require_numbers: bool = False
    require_special_chars: bool = False
    password_history_size: int = 5

    max_concurrent_sessions: int = 5
    session_timeout_hours: int = 24
    absolute_timeout_hours: int = 168

    stripe_api_key: Optional[str] = Field(default=None, validation_alias="STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = Field(
        default=None, validation_alias="STRIPE_WEBHOOK_SECRET"
    )
    stripe_publishable_key: Optional[str] = Field(
        default=None, validation_alias="STRIPE_PUBLISHABLE_KEY"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    audit_log_retention_days: int = 90
    token_blacklist_cleanup_days: int = 7
    password_reset_token_expiry_hours: int = 24
    email_verification_expiry_hours: int = 48

    app_version: str = Field(default="1.1.0", validation_alias="APP_VERSION")

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        if v is None:
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "*":
                return ["*"]
            return [p.strip() for p in s.split(",") if p.strip()]
        return v

    @property
    def database_url(self) -> str:
        return self.database.url

    @property
    def redis_url(self) -> str:
        return self.redis.url

    @property
    def secret_key(self) -> str:
        return self.security.secret_key

    @property
    def algorithm(self) -> str:
        return self.security.jwt_algorithm

    @property
    def access_token_expire_minutes(self) -> int:
        return self.security.access_token_expire_minutes

    @property
    def refresh_token_expire_days(self) -> int:
        return self.security.refresh_token_expire_days

    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT


settings = Settings()

if settings.is_production():
    if settings.security.secret_key == "your-super-secret-key-here-change-in-production":
        raise ValueError("SECRET_KEY must be changed in production environment")
