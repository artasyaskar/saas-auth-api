from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, Float, JSON, LargeBinary, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

__all__ = [
    "Base",
    "User",
    "UserRole",
    "UsageLog",
    "Subscription",
    "SubscriptionPlan",
    "RateLimit",
    "TokenBlacklist",
    "PasswordResetToken",
    "EmailVerification",
    "UserSession",
    "AuditLog",
    "Webhook",
    "WebhookEvent",
    "WebhookDelivery",
    "EmailLog",
    "EmailTemplate",
    "FeatureFlag",
    "APIVersion",
    "APIEndpoint",
    "FileMetadata",
    "FileVersion",
    "Message",
    "MessageThread",
    "Notification",
    "Workflow",
    "WorkflowExecution",
    "WorkflowTask",
    "ConsentRecord",
    "DataExportRequest",
    "APIKey",
    "SecurityEvent",
]

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


class Invoice(Base):
    """Billing invoice records."""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    stripe_invoice_id = Column(String, nullable=True, unique=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    subscription = relationship("Subscription")


class PaymentMethod(Base):
    """User payment methods."""
    __tablename__ = "payment_methods"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_payment_method_id = Column(String, nullable=True)
    type = Column(String(20), nullable=False)  # card, bank_account
    is_default = Column(Boolean, default=False, nullable=False)
    last_four = Column(String(4), nullable=True)
    expiry_month = Column(Integer, nullable=True)
    expiry_year = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class Coupon(Base):
    """Discount coupons."""
    __tablename__ = "coupons"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(String(20), nullable=False)  # percentage, fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, default=0, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageRecord(Base):
    """Usage tracking for billing."""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    metric_name = Column(String(50), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    subscription = relationship("Subscription")


class BillingAccount(Base):
    """Billing account information."""
    __tablename__ = "billing_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_customer_id = Column(String, nullable=True, unique=True)
    balance = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")


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
    
    @property
    def timestamp(self):
        """Alias for created_at for backward compatibility."""
        return self.created_at
    
    # Index for efficient queries
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class Webhook(Base):
    """Webhook configuration for event notifications."""
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    secret = Column(String(100), nullable=True)
    events = Column(JSON, nullable=False)  # List of event types
    event_types_version = Column(String(20), default="v1", nullable=True)
    headers = Column(JSON, nullable=True)
    retry_policy = Column(JSON, nullable=True)
    timeout = Column(Integer, default=30, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WebhookEvent(Base):
    """Webhook event record."""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, unique=True)
    data = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WebhookDelivery(Base):
    """Webhook delivery tracking."""
    __tablename__ = "webhook_deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)
    event_id = Column(String(64), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)


class EmailLog(Base):
    """Email delivery log."""
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(64), nullable=False, unique=True)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    provider = Column(String(50), nullable=False)
    template_id = Column(String(100), nullable=True)
    email_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)


class EmailTemplate(Base):
    """Email template storage."""
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    subject = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)
    variables = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FeatureFlag(Base):
    """Feature flag configuration."""
    __tablename__ = "feature_flags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    default_value = Column(Boolean, default=False, nullable=False)
    strategy = Column(String(50), nullable=False)
    rollout_percentage = Column(Integer, default=0, nullable=False)
    target_users = Column(JSON, nullable=True)
    target_attributes = Column(JSON, nullable=True)
    schedule_start = Column(DateTime(timezone=True), nullable=True)
    schedule_end = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    exposure_count = Column(Integer, default=0, nullable=False)
    evaluation_count = Column(Integer, default=0, nullable=False)
    enabled_count = Column(Integer, default=0, nullable=False)
    variants = Column(JSON, nullable=True)
    environment_overrides = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class APIVersion(Base):
    """API version management."""
    __tablename__ = "api_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), nullable=False, unique=True)
    status = Column(String(20), nullable=False)
    release_date = Column(DateTime(timezone=True), nullable=False)
    deprecation_date = Column(DateTime(timezone=True), nullable=True)
    sunset_date = Column(DateTime(timezone=True), nullable=True)
    retirement_date = Column(DateTime(timezone=True), nullable=True)
    breaking_changes = Column(JSON, nullable=True)
    migration_guide = Column(Text, nullable=True)
    canary_percentage = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIEndpoint(Base):
    """API endpoint configuration."""
    __tablename__ = "api_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    versions = Column(JSON, nullable=False)
    default_version = Column(String(20), nullable=False)
    deprecated_in = Column(String(20), nullable=True)
    removed_in = Column(String(20), nullable=True)
    alternatives = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FileMetadata(Base):
    """File storage metadata."""
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(64), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)
    access_level = Column(String(20), default="private", nullable=False)
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    status = Column(String(20), default="completed", nullable=False)
    version_count = Column(Integer, default=0, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class FileVersion(Base):
    """File version tracking."""
    __tablename__ = "file_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    original_file_id = Column(String(64), nullable=False)
    new_file_id = Column(String(64), nullable=False)
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    """In-app messaging."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(64), nullable=False, unique=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    thread_id = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)
    status = Column(String(20), default="sent", nullable=False)
    message_metadata = Column(JSON, nullable=True)
    attachments = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class MessageThread(Base):
    """Message thread for conversations."""
    __tablename__ = "message_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(64), nullable=False, unique=True)
    thread_type = Column(String(20), nullable=False)
    participant_ids = Column(JSON, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    """User notifications."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(64), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    data = Column(JSON, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Workflow(Base):
    """Workflow definition."""
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    definition = Column(JSON, nullable=False)
    variables = Column(JSON, nullable=True)
    timeout_minutes = Column(Integer, nullable=True)
    retry_policy = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowExecution(Base):
    """Workflow execution tracking."""
    __tablename__ = "workflow_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), nullable=False, unique=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    initiator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class WorkflowTask(Base):
    """Workflow task execution."""
    __tablename__ = "workflow_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=False)
    task_type = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    config = Column(JSON, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ConsentRecord(Base):
    """User consent tracking for GDPR/CCPA."""
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False)
    granted_from = Column(String(255), nullable=False)
    consent_metadata = Column(JSON, nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DataExportRequest(Base):
    """GDPR data export requests."""
    __tablename__ = "data_export_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_id = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), default="pending", nullable=False)
    include_deleted = Column(Boolean, default=False, nullable=False)
    download_url = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class APIKey(Base):
    """API key management."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    scopes = Column(JSON, nullable=True)
    rate_limit = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SecurityEvent(Base):
    """Security event tracking."""
    __tablename__ = "security_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    severity = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
