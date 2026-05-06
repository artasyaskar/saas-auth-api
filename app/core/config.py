"""
Configuration management for the SaaS Auth API.

Settings use Pydantic v2 and pydantic-settings with nested sections
and backward-compatible properties for modules that expect flat names.

Enhanced with comprehensive validation, environment handling,
and security configuration validation.
"""

import os
import re
import secrets
from enum import Enum
from typing import Optional, List, Any, Dict, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator, AliasChoices, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger()


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
    """Enhanced security configuration settings."""

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

    # Enhanced security settings
    rotation_usage_limit: int = Field(
        default=10, ge=1, le=100, validation_alias="ROTATION_USAGE_LIMIT"
    )
    rotation_age_days: int = Field(
        default=30, ge=1, le=365, validation_alias="ROTATION_AGE_DAYS"
    )
    rotation_inactivity_days: int = Field(
        default=7, ge=1, le=90, validation_alias="ROTATION_INACTIVITY_DAYS"
    )
    rotation_expiry_threshold: int = Field(
        default=7, ge=1, le=30, validation_alias="ROTATION_EXPIRY_THRESHOLD"
    )
    rotation_extension_days: int = Field(
        default=30, ge=1, le=365, validation_alias="ROTATION_EXTENSION_DAYS"
    )

    session_expire_days: int = Field(
        default=7, ge=1, le=365, validation_alias="SESSION_EXPIRE_DAYS"
    )
    session_ip_binding: bool = Field(
        default=False, validation_alias="SESSION_IP_BINDING"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        # Check for common/default values
        common_keys = [
            "your-super-secret-key-here-change-in-production",
            "secret-key-change-in-production",
            "dev-secret-key",
            "test-secret-key",
            "changeme",
            "password",
            "secret"
        ]
        
        if v.lower() in common_keys:
            raise ValueError("Secret key appears to be a default value. Please use a secure, unique secret key.")
        
        # Check entropy (basic check)
        if len(set(v)) < len(v) * 0.3:  # Less than 30% unique characters
            raise ValueError("Secret key has low entropy. Please use a more complex secret key.")
        
        return v
    
    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"JWT algorithm must be one of: {', '.join(allowed_algorithms)}")
        return v

    @model_validator(mode="after")
    def default_jwt_secret_from_secret_key(self):
        """Default JWT secret to secret key if not provided."""
        if not self.jwt_secret or len(self.jwt_secret) < 32:
            self.jwt_secret = self.secret_key
        return self

    @model_validator(mode="after")
    def validate_security_configuration(self):
        """Validate overall security configuration."""
        # Check token expiration ratios
        access_hours = self.access_token_expire_minutes / 60
        refresh_hours = self.refresh_token_expire_days * 24
        
        if refresh_hours <= access_hours:
            raise ValueError("Refresh token must expire after access token")
        
        if refresh_hours > access_hours * 24:  # Refresh token too long compared to access token
            logger.warning("Refresh token expiration is significantly longer than access token")
        
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

    apple_client_id: Optional[str] = Field(
        default=None, validation_alias="APPLE_CLIENT_ID"
    )
    apple_client_secret: Optional[str] = Field(
        default=None, validation_alias="APPLE_CLIENT_SECRET"
    )
    okta_client_id: Optional[str] = Field(
        default=None, validation_alias="OKTA_CLIENT_ID"
    )
    okta_client_secret: Optional[str] = Field(
        default=None, validation_alias="OKTA_CLIENT_SECRET"
    )
    okta_domain: Optional[str] = Field(default=None, validation_alias="OKTA_DOMAIN")


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
    Enhanced main application settings.

    Nested sections load from the same .env; flat property aliases exist for
    legacy call sites (e.g. settings.secret_key, settings.database_url).
    
    Enhanced with comprehensive validation, environment handling,
    and security configuration validation.
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

    # Enhanced application settings
    require_lowercase: bool = False
    require_numbers: bool = False
    require_special_chars: bool = False
    password_history_size: int = Field(default=5, ge=1, le=20, validation_alias="PASSWORD_HISTORY_SIZE")

    max_concurrent_sessions: int = Field(default=5, ge=1, le=20, validation_alias="MAX_CONCURRENT_SESSIONS")
    session_timeout_hours: int = Field(default=24, ge=1, le=168, validation_alias="SESSION_TIMEOUT_HOURS")
    absolute_timeout_hours: int = Field(default=168, ge=24, le=720, validation_alias="ABSOLUTE_TIMEOUT_HOURS")

    # Payment settings
    stripe_api_key: Optional[str] = Field(default=None, validation_alias="STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = Field(
        default=None, validation_alias="STRIPE_WEBHOOK_SECRET"
    )
    stripe_publishable_key: Optional[str] = Field(
        default=None, validation_alias="STRIPE_PUBLISHABLE_KEY"
    )

    # Logging settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, validation_alias="LOG_FILE")
    log_max_size: str = Field(default="100MB", validation_alias="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, ge=1, le=50, validation_alias="LOG_BACKUP_COUNT")

    # Retention settings
    audit_log_retention_days: int = Field(default=90, ge=7, le=365, validation_alias="AUDIT_LOG_RETENTION_DAYS")
    token_blacklist_cleanup_days: int = Field(default=7, ge=1, le=30, validation_alias="TOKEN_BLACKLIST_CLEANUP_DAYS")
    password_reset_token_expiry_hours: int = Field(default=24, ge=1, le=168, validation_alias="PASSWORD_RESET_TOKEN_EXPIRY_HOURS")
    email_verification_expiry_hours: int = Field(default=48, ge=1, le=168, validation_alias="EMAIL_VERIFICATION_EXPIRY_HOURS")

    # Application settings
    app_version: str = Field(default="1.1.0", validation_alias="APP_VERSION")
    app_name: str = Field(default="SaaS Auth API", validation_alias="APP_NAME")

    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_URL", "frontend_url"),
    )
    base_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("BASE_URL", "base_url"),
    )

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # Performance settings
    max_request_size: int = Field(default=10485760, ge=1024, le=104857600, validation_alias="MAX_REQUEST_SIZE")  # 10MB
    request_timeout: int = Field(default=30, ge=5, le=300, validation_alias="REQUEST_TIMEOUT")
    worker_processes: int = Field(default=1, ge=1, le=16, validation_alias="WORKER_PROCESSES")

    # Feature flags
    enable_2fa: bool = Field(default=True, validation_alias="ENABLE_2FA")
    enable_oauth: bool = Field(default=True, validation_alias="ENABLE_OAUTH")
    enable_audit_logging: bool = Field(default=True, validation_alias="ENABLE_AUDIT_LOGGING")
    enable_rate_limiting: bool = Field(default=True, validation_alias="ENABLE_RATE_LIMITING")
    enable_background_jobs: bool = Field(default=True, validation_alias="ENABLE_BACKGROUND_JOBS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Parse CORS origins from string or list."""
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
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = ["json", "text", "console"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {', '.join(valid_formats)}")
        return v.lower()
    
    @field_validator("frontend_url", "base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if parsed.scheme not in ["http", "https"]:
                raise ValueError("URL must use http or https scheme")
            return v.rstrip("/")
        except Exception:
            raise ValueError(f"Invalid URL: {v}")
    
    @field_validator("app_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format (semantic versioning)."""
        pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?$'
        if not re.match(pattern, v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v
    
    @model_validator(mode="after")
    def validate_environment_specific_settings(self):
        """Validate environment-specific settings."""
        if self.environment == Environment.PRODUCTION:
            # Production-specific validations
            if self.debug:
                raise ValueError("Debug mode should not be enabled in production")
            
            if self.cors_origins == ["*"]:
                logger.warning("Wildcard CORS origins in production - consider restricting to specific domains")
            
            if not self.security.encryption_key:
                logger.warning("Encryption key not set in production")
            
            # Check for secure URLs in production
            if not self.frontend_url.startswith("https://"):
                logger.warning("Frontend URL should use HTTPS in production")
            
            if not self.base_url.startswith("https://"):
                logger.warning("Base URL should use HTTPS in production")
        
        elif self.environment == Environment.DEVELOPMENT:
            # Development-specific validations
            if not self.debug:
                logger.info("Debug mode is disabled in development environment")
        
        return self
    
    @model_validator(mode="after")
    def validate_oauth_configuration(self):
        """Validate OAuth configuration consistency."""
        if self.enable_oauth:
            # Check if at least one OAuth provider is properly configured
            providers_configured = []
            
            if self.oauth.google_client_id and self.oauth.google_client_secret:
                if not self.oauth.google_redirect_uri:
                    raise ValueError("Google OAuth redirect URI is required when Google client credentials are provided")
                providers_configured.append("google")
            
            if self.oauth.github_client_id and self.oauth.github_client_secret:
                if not self.oauth.github_redirect_uri:
                    raise ValueError("GitHub OAuth redirect URI is required when GitHub client credentials are provided")
                providers_configured.append("github")
            
            if not providers_configured:
                logger.warning("OAuth is enabled but no providers are properly configured")
            else:
                logger.info(f"OAuth providers configured: {', '.join(providers_configured)}")
        
        return self
    
    @model_validator(mode="after")
    def validate_email_configuration(self):
        """Validate email configuration consistency."""
        if self.email.email_service == "smtp":
            if not self.email.smtp_host or not self.email.smtp_user or not self.email.smtp_password:
                raise ValueError("SMTP configuration is incomplete for SMTP email service")
        
        elif self.email.email_service == "sendgrid":
            if not self.email.sendgrid_api_key:
                raise ValueError("SendGrid API key is required for SendGrid email service")
        
        elif self.email.email_service == "ses":
            if not self.email.ses_access_key or not self.email.ses_secret_key:
                raise ValueError("AWS SES credentials are required for SES email service")
        
        return self

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

    def is_staging(self) -> bool:
        return self.environment == Environment.STAGING

    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        config = {
            "environment": self.environment.value,
            "debug": self.debug,
            "log_level": self.log_level,
            "cors_origins": self.cors_origins,
        }
        
        if self.environment == Environment.PRODUCTION:
            config.update({
                "security_headers": True,
                "ssl_required": True,
                "strict_cors": True,
                "enhanced_logging": True,
            })
        elif self.environment == Environment.STAGING:
            config.update({
                "security_headers": True,
                "ssl_required": True,
                "strict_cors": False,
                "enhanced_logging": True,
            })
        else:  # DEVELOPMENT
            config.update({
                "security_headers": False,
                "ssl_required": False,
                "strict_cors": False,
                "enhanced_logging": False,
            })
        
        return config
    
    def validate_configuration(self) -> List[str]:
        """Validate entire configuration and return list of warnings/errors."""
        issues = []
        
        # Security validations
        if len(self.security.secret_key) < 64:
            issues.append("Secret key should be at least 64 characters for better security")
        
        if self.security.access_token_expire_minutes > 60:
            issues.append("Access token expiration is quite long, consider shorter expiration for better security")
        
        if self.security.refresh_token_expire_days > 30:
            issues.append("Refresh token expiration is quite long, consider shorter expiration for better security")
        
        # Database validations
        if self.database.url.startswith("sqlite://") and self.environment == Environment.PRODUCTION:
            issues.append("SQLite is not recommended for production use")
        
        if self.database.pool_size < 10 and self.environment == Environment.PRODUCTION:
            issues.append("Database pool size should be at least 10 for production")
        
        # Redis validations
        if not self.redis.url and self.environment == Environment.PRODUCTION:
            issues.append("Redis is recommended for production caching and session storage")
        
        # Email validations
        if self.email.smtp_user == "" and self.email.email_service == "smtp":
            issues.append("SMTP user is not configured")
        
        # OAuth validations
        if self.enable_oauth and not any([
            self.oauth.google_client_id,
            self.oauth.github_client_id,
            self.oauth.microsoft_client_id
        ]):
            issues.append("OAuth is enabled but no providers are configured")
        
        # Feature flag validations
        if self.enable_2fa and not self.email.smtp_user:
            issues.append("2FA is enabled but email service may not be properly configured")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of key configuration values."""
        return {
            "environment": self.environment.value,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "database": {
                "url": self.database.url.split("@")[-1] if "@" in self.database.url else "local",
                "pool_size": self.database.pool_size,
                "echo": self.database.echo,
            },
            "redis": {
                "url": self.redis.url.split("@")[-1] if "@" in self.redis.url else "local",
                "max_connections": self.redis.max_connections,
            },
            "security": {
                "access_token_expire_minutes": self.security.access_token_expire_minutes,
                "refresh_token_expire_days": self.security.refresh_token_expire_days,
                "session_timeout": self.security.session_timeout,
                "max_sessions_per_user": self.security.max_sessions_per_user,
            },
            "features": {
                "2fa": self.enable_2fa,
                "oauth": self.enable_oauth,
                "audit_logging": self.enable_audit_logging,
                "rate_limiting": self.enable_rate_limiting,
                "background_jobs": self.enable_background_jobs,
            },
            "oauth_providers": {
                "google": self.oauth.google_enabled,
                "github": self.oauth.github_enabled,
                "microsoft": self.oauth.microsoft_enabled,
            },
            "cors_origins_count": len(self.cors_origins),
        }


def generate_secret_key(length: int = 64) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)


def validate_environment_file(env_file_path: str = ".env") -> List[str]:
    """Validate environment file and return list of issues."""
    issues = []
    
    if not os.path.exists(env_file_path):
        issues.append(f"Environment file {env_file_path} does not exist")
        return issues
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required variables
        required_vars = ["SECRET_KEY"]
        for var in required_vars:
            if var not in content:
                issues.append(f"Required environment variable {var} is missing")
        
        # Check for default/placeholder values
        placeholder_patterns = [
            "your-super-secret-key-here",
            "change-in-production",
            "your-api-key-here",
            "placeholder",
        ]
        
        for pattern in placeholder_patterns:
            if pattern.lower() in content.lower():
                issues.append(f"Found placeholder value containing '{pattern}' - please replace with actual values")
        
        # Check for empty values
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if '=' in line and line.endswith('='):
                var_name = line.split('=')[0].strip()
                issues.append(f"Empty value for variable {var_name} at line {line_num}")
        
    except Exception as e:
        issues.append(f"Error reading environment file: {str(e)}")
    
    return issues


settings = Settings()

# Enhanced production validation
if settings.is_production():
    production_issues = []
    
    if settings.security.secret_key == "your-super-secret-key-here-change-in-production":
        production_issues.append("SECRET_KEY must be changed in production environment")
    
    if settings.debug:
        production_issues.append("Debug mode should not be enabled in production")
    
    if settings.cors_origins == ["*"]:
        production_issues.append("Wildcard CORS origins are not recommended in production")
    
    # Get additional validation issues
    config_issues = settings.validate_configuration()
    production_issues.extend([issue for issue in config_issues if "production" in issue.lower() or "recommended" in issue.lower()])
    
    if production_issues:
        error_msg = "Production configuration issues found:\n" + "\n".join(f"- {issue}" for issue in production_issues)
        raise ValueError(error_msg)

# Log configuration summary
try:
    config_summary = settings.get_config_summary()
    logger.info(f"Configuration loaded for {config_summary['environment']}", **config_summary)
    
    # Validate environment file
    env_issues = validate_environment_file()
    if env_issues:
        logger.warning("Environment file validation issues detected", issues=env_issues)
        
except Exception as e:
    logger.error(f"Failed to load configuration summary: {str(e)}")
