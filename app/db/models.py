from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class SubscriptionPlan(enum.Enum):
    FREE = "FREE"
    PRO = "PRO"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    subscription_plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    usage_logs = relationship("UsageLog", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    response_time_ms = Column(Float, nullable=True)
    
    user = relationship("User", back_populates="usage_logs")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(Enum(SubscriptionPlan), nullable=False)
    stripe_subscription_id = Column(String, nullable=True)
    status = Column(String, nullable=False)  # active, canceled, past_due, etc.
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="subscriptions")


class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requests_per_minute = Column(Integer, default=60, nullable=False)
    monthly_quota = Column(Integer, default=1000, nullable=False)
    current_monthly_usage = Column(Integer, default=0, nullable=False)
    last_minute_reset = Column(DateTime(timezone=True), server_default=func.now())
    last_monthly_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id_unique = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)


class TokenBlacklist(Base):
    """Stores blacklisted/revoked JWT tokens."""
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash of token
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_type = Column(String(20), nullable=False, default="access")  # access, refresh, all
    expires_at = Column(DateTime(timezone=True), nullable=False)  # When token naturally expires
    reason = Column(String(100), nullable=True)  # logout, revoke, password_change, etc.
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    
    # Index for efficient cleanup queries
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class PasswordResetToken(Base):
    """Password reset token storage."""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)
    used_ip = Column(String(45), nullable=True)


class EmailVerification(Base):
    """Email verification tokens."""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String, nullable=False)  # The email being verified
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)


class UserSession(Base):
    """User session tracking for security."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(64), nullable=False, unique=True, index=True)  # Hashed
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    location = Column(String(100), nullable=True)  # City/Country info
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    ended_reason = Column(String(50), nullable=True)  # logout, expired, revoked, etc.


class AuditLog(Base):
    """Security audit log for sensitive operations."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Can be null for anon actions
    action = Column(String(50), nullable=False, index=True)  # login, logout, password_change, etc.
    resource_type = Column(String(50), nullable=True)  # user, subscription, etc.
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # JSON string with additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    failure_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index for efficient queries
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
