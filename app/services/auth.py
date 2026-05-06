"""
Authentication service for core business logic.

Handles user authentication, token management, and
security-related operations with proper error handling
and security considerations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib

from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.models import User, UserRole, LoginAttempt
from app.repositories.auth import AuthRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest,
    PasswordResetRequest, TwoFactorSetupRequest,
    TwoFactorVerifyRequest, SessionInfo
)
from app.core.security import (
    hash_password, verify_password, generate_secure_token
)
from app.core.jwt import (
    create_access_token, create_refresh_token, verify_token,
    blacklist_token, create_token_pair, refresh_access_token
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError, ValidationError as AppValidationError,
    RateLimitError, SecurityError
)


class AuthService:
    """
    Authentication service for core business logic.
    
    Handles user authentication, token management, and security
    operations with proper error handling and security considerations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
        self.user_repo = UserRepository(db)
        
        # TODO: Add caching layer for frequently accessed data
        # TODO: Add rate limiting per user/IP
        # TODO: Add device fingerprinting
    
    def authenticate_user(self, request: LoginRequest, ip_address: str = None) -> LoginResponse:
        """
        Authenticate user with email/username and password.
        
        Args:
            request: Login request with credentials
            ip_address: Client IP address for security logging
            
        Returns:
            Login response with tokens or error
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
        """
        try:
            # Check rate limiting
            if self._is_rate_limited(request.identifier, ip_address):
                raise RateLimitError("Too many login attempts. Please try again later.")
            
            # Record login attempt
            self.auth_repo.record_login_attempt(
                email=request.identifier,
                ip_address=ip_address,
                user_agent=getattr(request, 'user_agent', None),
                success=False
            )
            
            # Find user by email or username
            user = self.user_repo.get_by_email_or_username(request.identifier)
            
            if not user:
                raise AuthenticationError("Invalid credentials")
            
            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("Account is not active")
            
            # Verify password
            if not verify_password(request.password, user.hashed_password):
                raise AuthenticationError("Invalid credentials")
            
            # Check if 2FA is required
            if self._is_2fa_required(user):
                # TODO: Implement 2FA flow
                return LoginResponse(
                    requires_2fa=True,
                    two_factor_methods=["totp", "sms", "email"],
                    message="Two-factor authentication required"
                )
            
            # Update user login info
            self.user_repo.update_last_login(user.id)
            
            # Create tokens with proper user data
            user_data = {
                "sub": user.email,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role.value if user.role else None
            }
            
            token_pair = create_token_pair(user_data)
            access_token = token_pair["access_token"]
            refresh_token = token_pair["refresh_token"]
            
            # Record successful login
            self.auth_repo.record_login_attempt(
                email=request.identifier,
                ip_address=ip_address,
                user_agent=getattr(request, 'user_agent', None),
                success=True
            )
            
            # Create session
            session = self.auth_repo.create_user_session(
                user_id=user.id,
                session_token=secrets.token_urlsafe(32),
                user_agent=getattr(request, 'user_agent', None),
                ip_address=ip_address
            )
            
            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user={
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role.value if user.role else None
                },
                session_id=session.session_token if session else None
            )
            
        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    def refresh_token(self, request: RefreshTokenRequest) -> LoginResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            request: Refresh token request
            
        Returns:
            Login response with new access token
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Use new token refresh system
            token_data = refresh_access_token(request.refresh_token)
            
            if not token_data:
                raise AuthenticationError("Invalid refresh token")
            
            # Extract user data from refresh token
            refresh_payload = verify_token(request.refresh_token, "refresh")
            
            if not refresh_payload:
                raise AuthenticationError("Invalid refresh token")
            
            # Get user
            user = self.user_repo.get_by_email(refresh_payload.get("sub"))
            
            if not user or not user.is_active:
                raise AuthenticationError("Invalid user")
            
            # TODO: Implement token rotation
            # TODO: Add device validation
            # TODO: Add refresh token usage tracking
            
            return LoginResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", request.refresh_token),
                token_type=token_data.get("token_type", "bearer"),
                expires_in=token_data.get("expires_in", settings.security.access_token_expire_minutes * 60),
                user={
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role.value if user.role else None
                }
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")
    
    def logout_user(self, token: str, session_id: str = None) -> bool:
        """
        Logout user and invalidate tokens.
        
        Args:
            token: Access token to invalidate
            session_id: Specific session to logout
            
        Returns:
            True if logout successful
            
        Raises:
            AuthenticationError: If logout fails
        """
        try:
            # Add token to blacklist
            self.auth_repo.blacklist_token(token, "User logout")
            
            # Invalidate specific session or all sessions
            if session_id:
                self.auth_repo.invalidate_user_session(session_id)
            else:
                # Get user from token and invalidate all sessions
                token_data = verify_token(token, "access")
                if token_data and "user_id" in token_data:
                    self.auth_repo.invalidate_all_user_sessions(token_data["user_id"])
            
            # TODO: Add device-specific logout
            # TODO: Add logout audit logging
            
            return True
            
        except Exception as e:
            # TODO: Add proper logging
            raise AuthenticationError(f"Logout failed: {str(e)}")
    
    def initiate_password_reset(self, request: PasswordResetRequest) -> bool:
        """
        Initiate password reset process.
        
        Args:
            request: Password reset request
            
        Returns:
            True if reset initiated successfully
            
        Raises:
            AuthenticationError: If reset initiation fails
            ValidationError: If email is invalid
        """
        try:
            # Find user by email
            user = self.user_repo.get_by_email(request.email)
            
            if not user:
                # Don't reveal if email exists
                return True
            
            # Check rate limiting
            if self._is_rate_limited(request.email, action="password_reset"):
                raise RateLimitError("Too many password reset attempts. Please try again later.")
            
            # Generate reset token
            reset_token = generate_secure_token(32)
            
            # Create password reset token record
            if self.auth_repo.create_password_reset_token(
                user_id=user.id,
                token=reset_token,
                expires_hours=24
            ):
                # TODO: Send email with reset token
                # TODO: Add security headers to email
                # TODO: Add rate limiting for email sending
                
                return True
            else:
                raise AuthenticationError("Failed to create password reset token")
                
        except (RateLimitError, ValidationError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Password reset initiation failed: {str(e)}")
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if password reset successful
            
        Raises:
            AuthenticationError: If reset fails
            ValidationError: If password is invalid
        """
        try:
            # Validate password strength
            self._validate_password(new_password)
            
            # Get reset token record
            reset_token_record = self.auth_repo.get_password_reset_token(token)
            
            if not reset_token_record:
                raise AuthenticationError("Invalid or expired reset token")
            
            # Get user
            user = self.user_repo.get(reset_token_record.user_id)
            
            if not user or not user.is_active:
                raise AuthenticationError("Invalid user")
            
            # Hash new password
            hashed_password = hash_password(new_password)
            
            # Update user password
            if self.user_repo.update_password(user.id, hashed_password):
                # Mark reset token as used
                self.auth_repo.use_password_reset_token(token)
                
                # Invalidate all user sessions
                self.auth_repo.invalidate_all_user_sessions(user.id)
                
                # TODO: Send password reset confirmation email
                # TODO: Add security event logging
                
                return True
            else:
                raise AuthenticationError("Failed to update password")
                
        except (AuthenticationError, ValidationError):
            raise
        except Exception as e:
            raise AuthenticationError(f"Password reset failed: {str(e)}")
    
    def get_user_sessions(self, user_id: int) -> List[SessionInfo]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active sessions
        """
        try:
            # TODO: Add pagination
            # TODO: Add session filtering
            # TODO: Add device grouping
            
            sessions = self.db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).order_by(desc(UserSession.last_activity)).all()
            
            return [
                SessionInfo(
                    session_id=session.session_token,
                    user_agent=session.user_agent,
                    ip_address=session.ip_address,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    is_current=False  # TODO: Determine current session
                )
                for session in sessions
            ]
            
        except Exception as e:
            # TODO: Add proper logging
            return []
    
    def revoke_session(self, user_id: int, session_id: str) -> bool:
        """
        Revoke a specific user session.
        
        Args:
            user_id: User ID
            session_id: Session ID to revoke
            
        Returns:
            True if session revoked successfully
        """
        try:
            # Verify session belongs to user
            session = self.auth_repo.get_user_session(session_id)
            
            if not session or session.user_id != user_id:
                raise AuthenticationError("Invalid session")
            
            return self.auth_repo.invalidate_user_session(session_id)
            
        except AuthenticationError:
            raise
        except Exception as e:
            # TODO: Add proper logging
            return False
    
    def _is_rate_limited(self, identifier: str, ip_address: str = None, action: str = "login") -> bool:
        """
        Check if user/IP is rate limited.
        
        Args:
            identifier: Email or username
            ip_address: Client IP address
            action: Type of action (login, password_reset, etc.)
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            # Check failed login attempts
            failed_attempts = self.auth_repo.count_failed_login_attempts(identifier, hours=1)
            
            # Rate limits based on action type
            limits = {
                "login": 5,  # 5 failed attempts per hour
                "password_reset": 3,  # 3 reset attempts per hour
                "2fa": 10  # 10 2FA attempts per hour
            }
            
            limit = limits.get(action, 5)
            
            return failed_attempts >= limit
            
        except Exception:
            # If rate limiting check fails, allow the request
            return False
    
    def _is_2fa_required(self, user: User) -> bool:
        """
        Check if user requires two-factor authentication.
        
        Args:
            user: User object
            
        Returns:
            True if 2FA required, False otherwise
        """
        # TODO: Implement 2FA requirement logic
        # TODO: Add organization-level 2FA policies
        # TODO: Add device-based 2FA requirements
        
        # For now, require 2FA for admin users
        return user.role == UserRole.ADMIN
    
    def _validate_password(self, password: str):
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Raises:
            ValidationError: If password doesn't meet requirements
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        # TODO: Add special character requirement
        # TODO: Add password history check
        # TODO: Add common password check
        
        if errors:
            raise ValidationError(errors)
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired authentication data.
        
        Returns:
            Dictionary with cleanup counts
        """
        try:
            return {
                "blacklist_entries": self.auth_repo.cleanup_expired_blacklist(days=30),
                "reset_tokens": self.auth_repo.cleanup_expired_reset_tokens(),
                "sessions": self.auth_repo.cleanup_expired_sessions(days=30),
                "login_attempts": self.auth_repo.cleanup_old_login_attempts(days=90)
            }
        except Exception as e:
            # TODO: Add proper logging
            return {}
    
    def get_security_events(self, user_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get security events for a user.
        
        Args:
            user_id: User ID
            hours: Number of hours to look back
            
        Returns:
            List of security events
        """
        try:
            # TODO: Implement security event logging
            # TODO: Add event filtering
            # TODO: Add event pagination
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            events = self.db.query(LoginAttempt).filter(
                LoginAttempt.user_id == user_id,
                LoginAttempt.attempted_at >= cutoff_time
            ).order_by(desc(LoginAttempt.attempted_at)).all()
            
            return [
                {
                    "event_type": "login_attempt",
                    "success": event.success,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "timestamp": event.attempted_at.isoformat(),
                    "failure_reason": event.failure_reason
                }
                for event in events
            ]
            
        except Exception as e:
            # TODO: Add proper logging
            return []
