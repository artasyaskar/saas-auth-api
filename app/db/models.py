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
