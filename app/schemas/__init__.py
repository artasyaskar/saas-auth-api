"""
Schema layer for request/response models.

This layer defines Pydantic models for API validation
and serialization/deserialization of data.
"""

from .user import (
    UserCreate, UserUpdate, UserResponse, UserLogin,
    UserProfile, UserPreferences, UserStats
)
from .auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest,
    PasswordResetRequest, EmailVerificationRequest
)
from .base import BaseResponse, PaginationParams, PaginatedResponse

__all__ = [
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin",
    "UserProfile", "UserPreferences", "UserStats",
    
    # Auth schemas
    "LoginRequest", "LoginResponse", "RefreshTokenRequest",
    "PasswordResetRequest", "EmailVerificationRequest",
    
    # Base schemas
    "BaseResponse", "PaginationParams", "PaginatedResponse"
]
