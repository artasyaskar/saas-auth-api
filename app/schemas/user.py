"""
User-related schemas for API requests and responses.

Defines Pydantic models for user operations including
registration, login, profile management, and preferences.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum

from app.db.models import UserRole


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserCreate(BaseModel):
    """
    User registration request model.
    
    Used for user registration with validation
    and security requirements.
    """
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    accept_terms: bool = Field(True, description="Accept terms of service")
    marketing_consent: bool = Field(False, description="Marketing consent")
    
    @validator('password')
    def validate_password(cls, v):
        """
        Validate password strength.
        
        TODO: Move to centralized validation service
        TODO: Add configurable password policies
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """
        Validate username format.
        
        TODO: Add username blacklist
        TODO: Add profanity filter
        """
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        
        # TODO: Add reserved words check
        return v.lower()


class UserUpdate(BaseModel):
    """
    User profile update request model.
    
    Used for updating user profile information.
    """
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    bio: Optional[str] = Field(None, max_length=500, description="Bio")
    timezone: Optional[str] = Field(None, max_length=50, description="Timezone")
    language: Optional[str] = Field(None, max_length=10, description="Language code")
    avatar_url: Optional[str] = Field(None, max_length=255, description="Avatar URL")
    
    class Config:
        # Allow partial updates
        extra = "forbid"


class UserLogin(BaseModel):
    """
    User login request model.
    
    Used for user authentication.
    """
    identifier: str = Field(..., description="Email or username")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember login")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")


class UserResponse(BaseModel):
    """
    User response model.
    
    Used for returning user data in API responses.
    """
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    bio: Optional[str] = Field(None, description="Bio")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: Optional[str] = Field(None, description="User role")
    is_active: bool = Field(..., description="Account status")
    email_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: Optional[int] = Field(None, description="Total login count")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserProfile(BaseModel):
    """
    Extended user profile model.
    
    Includes additional profile information and preferences.
    """
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    bio: Optional[str] = Field(None, description="Bio")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    timezone: Optional[str] = Field(None, description="Timezone")
    language: Optional[str] = Field(None, description="Language code")
    role: Optional[str] = Field(None, description="User role")
    is_active: bool = Field(..., description="Account status")
    email_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: Optional[int] = Field(None, description="Total login count")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserPreferences(BaseModel):
    """
    User preferences model.
    
    Used for managing user settings and preferences.
    """
    theme: str = Field("light", pattern="^(light|dark|auto)$", description="UI theme")
    language: str = Field("en", max_length=10, description="Language code")
    timezone: str = Field("UTC", max_length=50, description="Timezone")
    email_notifications: bool = Field(True, description="Email notification preferences")
    push_notifications: bool = Field(True, description="Push notification preferences")
    marketing_emails: bool = Field(False, description="Marketing email preferences")
    two_factor_enabled: bool = Field(False, description="Two-factor authentication status")
    session_timeout: int = Field(3600, ge=300, le=86400, description="Session timeout in seconds")
    privacy_settings: Dict[str, bool] = Field(default_factory=dict, description="Privacy settings")
    
    class Config:
        extra = "allow"  # Allow additional preference fields


class UserStats(BaseModel):
    """
    User statistics model.
    
    Provides user activity and usage statistics.
    """
    user_id: int = Field(..., description="User ID")
    total_logins: int = Field(..., description="Total login count")
    successful_logins: int = Field(..., description="Successful login count")
    failed_logins: int = Field(..., description="Failed login count")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    account_age_days: int = Field(..., description="Account age in days")
    api_calls_total: int = Field(..., description="Total API calls")
    api_calls_this_month: int = Field(..., description="API calls this month")
    storage_used_mb: Optional[float] = Field(None, description="Storage used in MB")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserSearchResult(BaseModel):
    """
    User search result model.
    
    Used for user search responses with ranking.
    """
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: Optional[str] = Field(None, description="User role")
    relevance_score: Optional[float] = Field(None, description="Search relevance score")
    
    class Config:
        from_attributes = True


class UserActivity(BaseModel):
    """
    User activity model.
    
    Used for tracking user activity logs.
    """
    id: int = Field(..., description="Activity ID")
    user_id: int = Field(..., description="User ID")
    action: str = Field(..., description="Activity action")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Activity timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserSecuritySettings(BaseModel):
    """
    User security settings model.
    
    Used for managing user security preferences.
    """
    two_factor_enabled: bool = Field(False, description="Two-factor authentication status")
    two_factor_method: Optional[str] = Field(None, pattern="^(totp|sms|email|backup)$", description="2FA method")
    email_login_enabled: bool = Field(True, description="Email login enabled")
    social_login_enabled: bool = Field(True, description="Social login enabled")
    api_key_enabled: bool = Field(False, description="API key access enabled")
    session_management: Dict[str, bool] = Field(
        default_factory=lambda: {
            "multiple_sessions": False,
            "session_timeout": True,
            "auto_logout": False
        },
        description="Session management settings"
    )
    login_notifications: bool = Field(True, description="Login notifications enabled")
    security_questions: Optional[List[Dict[str, str]]] = Field(None, description="Security questions")
    
    class Config:
        extra = "allow"


class UserPublicProfile(BaseModel):
    """
    Public user profile model.
    
    Used for sharing limited user information publicly.
    """
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    bio: Optional[str] = Field(None, description="Bio")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    joined_at: datetime = Field(..., description="Join date")
    is_verified: bool = Field(..., description="Verification status")
    
    # TODO: Add privacy controls
    # TODO: Add customizable public fields
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserBulkCreate(BaseModel):
    """
    Bulk user creation model.
    
    Used for creating multiple users at once.
    """
    users: List[UserCreate] = Field(..., min_items=1, max_items=100, description="List of users to create")
    send_invitation_emails: bool = Field(True, description="Send invitation emails")
    default_password: Optional[str] = Field(None, description="Default password for all users")
    
    @validator('users')
    def validate_users(cls, v):
        """
        Validate bulk user creation.
        
        TODO: Add duplicate email check
        TODO: Add rate limiting
        """
        if len(v) > 100:
            raise ValueError('Cannot create more than 100 users at once')
        return v


class UserBulkResponse(BaseModel):
    """
    Bulk user creation response model.
    
    Used for bulk operation results.
    """
    success_count: int = Field(..., description="Number of successful creations")
    error_count: int = Field(..., description="Number of failed creations")
    total_count: int = Field(..., description="Total number of operations")
    created_users: List[UserResponse] = Field(default_factory=list, description="Successfully created users")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
