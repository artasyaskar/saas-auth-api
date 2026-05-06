"""
Authentication-related schemas for API requests and responses.

Defines Pydantic models for authentication operations including
login, registration, password reset, and token management.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator


class LoginRequest(BaseModel):
    """
    User login request model.
    
    Used for user authentication with email/username
    and password combination.
    """
    identifier: str = Field(..., min_length=1, max_length=255, description="Email or username")
    password: str = Field(..., min_length=1, max_length=128, description="Password")
    remember_me: bool = Field(False, description="Remember login")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")
    recaptcha_token: Optional[str] = Field(None, description="reCAPTCHA token")
    
    # TODO: Add rate limiting metadata
    # TODO: Add device fingerprinting


class LoginResponse(BaseModel):
    """
    Login response model.
    
    Returns authentication tokens and user information
    after successful login.
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: Optional[Dict[str, Any]] = Field(None, description="User information")
    requires_2fa: bool = Field(False, description="Whether 2FA is required")
    two_factor_methods: Optional[list] = Field(None, description="Available 2FA methods")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # TODO: Add token permissions
    # TODO: Add device registration info


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request model.
    
    Used for refreshing access tokens using refresh token.
    """
    refresh_token: str = Field(..., min_length=1, description="Refresh token")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")
    
    # TODO: Add token rotation support
    # TODO: Add device verification


class PasswordResetRequest(BaseModel):
    """
    Password reset request model.
    
    Used for initiating password reset process.
    """
    email: EmailStr = Field(..., description="Email address")
    recaptcha_token: Optional[str] = Field(None, description="reCAPTCHA token")
    
    # TODO: Add security question support
    # TODO: Add rate limiting metadata


class PasswordResetConfirmRequest(BaseModel):
    """
    Password reset confirmation model.
    
    Used for confirming password reset with token.
    """
    token: str = Field(..., min_length=1, description="Reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """
        Validate that passwords match.
        """
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    # TODO: Add password strength validation
    # TODO: Add token expiration check


class EmailVerificationRequest(BaseModel):
    """
    Email verification request model.
    
    Used for sending email verification.
    """
    email: EmailStr = Field(..., description="Email address to verify")
    
    # TODO: Add resend cooldown check
    # TODO: Add rate limiting metadata


class EmailVerificationConfirmRequest(BaseModel):
    """
    Email verification confirmation model.
    
    Used for confirming email verification with token.
    """
    token: str = Field(..., min_length=1, description="Verification token")
    
    # TODO: Add token expiration check
    # TODO: Add user agent validation


class ChangePasswordRequest(BaseModel):
    """
    Change password request model.
    
    Used for changing user password when authenticated.
    """
    current_password: str = Field(..., min_length=1, max_length=128, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """
        Validate that passwords match.
        """
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    # TODO: Add password history check
    # TODO: Add current password validation


class TwoFactorSetupRequest(BaseModel):
    """
    Two-factor authentication setup request model.
    
    Used for setting up 2FA methods.
    """
    method: str = Field(..., regex="^(totp|sms|email|backup)$", description="2FA method")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number for SMS")
    backup_codes_count: int = Field(10, ge=5, le=20, description="Number of backup codes to generate")
    
    # TODO: Add method-specific validation
    # TODO: Add phone number verification


class TwoFactorVerifyRequest(BaseModel):
    """
    Two-factor verification request model.
    
    Used for verifying 2FA codes.
    """
    method: str = Field(..., regex="^(totp|sms|email|backup)$", description="2FA method")
    code: str = Field(..., min_length=4, max_length=10, description="Verification code")
    backup_code: Optional[str] = Field(None, description="Backup code")
    remember_device: bool = Field(False, description="Remember this device")
    
    # TODO: Add code format validation
    # TODO: Add rate limiting metadata


class TwoFactorResponse(BaseModel):
    """
    Two-factor authentication response model.
    
    Returns 2FA setup or verification results.
    """
    success: bool = Field(..., description="Operation success status")
    method: Optional[str] = Field(None, description="2FA method")
    qr_code: Optional[str] = Field(None, description="QR code for TOTP")
    secret: Optional[str] = Field(None, description="TOTP secret")
    backup_codes: Optional[list] = Field(None, description="Backup codes")
    phone_last_four: Optional[str] = Field(None, description="Last 4 digits of phone number")
    verified: bool = Field(False, description="Whether verification was successful")
    
    # TODO: Add method-specific response fields
    # TODO: Add setup completion status


class SessionInfo(BaseModel):
    """
    Session information model.
    
    Used for returning active session details.
    """
    session_id: str = Field(..., description="Session identifier")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="IP address")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    is_current: bool = Field(False, description="Whether this is the current session")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")
    
    # TODO: Add geolocation data
    # TODO: Add device fingerprint


class LogoutRequest(BaseModel):
    """
    Logout request model.
    
    Used for user logout with session management.
    """
    session_id: Optional[str] = Field(None, description="Specific session to logout")
    all_sessions: bool = Field(False, description="Logout from all sessions")
    device_id: Optional[str] = Field(None, description="Specific device to logout")
    
    # TODO: Add token invalidation options
    # TODO: Add device-specific logout


class LogoutResponse(BaseModel):
    """
    Logout response model.
    
    Returns logout operation results.
    """
    success: bool = Field(..., description="Logout success status")
    sessions_ended: int = Field(..., description="Number of sessions ended")
    message: Optional[str] = Field(None, description="Logout message")
    
    # TODO: Add session cleanup status
    # TODO: Add device logout confirmation


class TokenInfo(BaseModel):
    """
    Token information model.
    
    Used for returning token metadata.
    """
    token_type: str = Field(..., description="Token type")
    expires_at: datetime = Field(..., description="Token expiration time")
    issued_at: datetime = Field(..., description="Token issue time")
    issuer: str = Field(..., description="Token issuer")
    audience: Optional[str] = Field(None, description="Token audience")
    scopes: Optional[list] = Field(None, description="Token scopes")
    user_id: Optional[int] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    
    # TODO: Add permission claims
    # TODO: Add device binding info


class SecurityEvent(BaseModel):
    """
    Security event model.
    
    Used for logging security-related events.
    """
    event_type: str = Field(..., description="Event type")
    severity: str = Field(..., regex="^(low|medium|high|critical)$", description="Event severity")
    description: str = Field(..., description="Event description")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Event timestamp")
    user_id: Optional[int] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # TODO: Add event categorization
    # TODO: Add automated response actions


class AuthStatusResponse(BaseModel):
    """
    Authentication status response model.
    
    Used for checking current authentication status.
    """
    authenticated: bool = Field(..., description="Authentication status")
    user_id: Optional[int] = Field(None, description="User ID if authenticated")
    session_id: Optional[str] = Field(None, description="Session ID if authenticated")
    token_info: Optional[TokenInfo] = Field(None, description="Token information")
    requires_2fa: bool = Field(False, description="Whether 2FA is required")
    two_factor_setup: bool = Field(False, description="Whether 2FA is set up")
    
    # TODO: Add permission checks
    # TODO: Add session validation


class DeviceRegistrationRequest(BaseModel):
    """
    Device registration request model.
    
    Used for registering new devices.
    """
    device_name: str = Field(..., min_length=1, max_length=100, description="Device name")
    device_type: str = Field(..., regex="^(desktop|mobile|tablet|other)$", description="Device type")
    device_id: Optional[str] = Field(None, description="Device identifier")
    push_token: Optional[str] = Field(None, description="Push notification token")
    
    # TODO: Add device fingerprinting
    # TODO: Add security challenge


class DeviceResponse(BaseModel):
    """
    Device response model.
    
    Used for returning device information.
    """
    device_id: str = Field(..., description="Device identifier")
    device_name: str = Field(..., description="Device name")
    device_type: str = Field(..., description="Device type")
    is_trusted: bool = Field(False, description="Whether device is trusted")
    last_seen: datetime = Field(..., description="Last seen timestamp")
    created_at: datetime = Field(..., description="Registration timestamp")
    
    # TODO: Add device security status
    # TODO: Add device management options
