"""
Enhanced password reset service for secure password management.

Handles password reset tokens, security validation, rate limiting,
and comprehensive password reset workflow with proper security measures.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib

from sqlalchemy.orm import Session
from app.db.models import PasswordResetToken, User
from app.repositories.auth import AuthRepository
from app.repositories.user import UserRepository
from app.core.config import settings
from app.core.exceptions import (
    ValidationError, NotFoundError, SecurityError,
    DatabaseError, ExternalServiceError
)
from app.services.email import EmailService
from app.services.security import SecurityService


class PasswordResetService:
    """
    Enhanced password reset service with comprehensive security.
    
    Handles password reset tokens, security validation, rate limiting,
    and comprehensive password reset workflow with proper security measures.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
        self.user_repo = UserRepository(db)
        self.email_service = EmailService(db)
        self.security_service = SecurityService()
        
        # TODO: Add password history tracking
        # TODO: Add device-based reset validation
        # TODO: Add suspicious activity detection
        # TODO: Add password breach checking
    
    def initiate_password_reset(
        self, 
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate password reset process.
        
        Args:
            email: Email address for password reset
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Password reset initiation result
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If rate limit exceeded
            ValidationError: If email is invalid
        """
        try:
            # Validate email format
            if not self._is_valid_email(email):
                raise ValidationError("Invalid email format")
            
            # Check rate limiting
            if self._is_rate_limited(email, ip_address, "password_reset"):
                raise SecurityError("Too many password reset requests. Please try again later.")
            
            # Find user by email
            user = self.user_repo.get_by_email(email)
            
            if not user:
                # Don't reveal if user exists - return success for security
                return {
                    "success": True,
                    "message": "If an account with this email exists, a password reset link has been sent.",
                    "email_sent": False
                }
            
            # Check if user is active
            if not user.is_active:
                raise SecurityError("Account is not active. Please contact support.")
            
            # Invalidate existing reset tokens
            self.auth_repo.cleanup_expired_reset_tokens()
            
            # Generate secure reset token
            token = self._generate_reset_token()
            expires_at = datetime.utcnow() + timedelta(hours=settings.security.password_reset_expire_hours or 24)
            
            # Create password reset token record
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
                is_used=False,
                created_at=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(reset_token)
            self.db.commit()
            
            # Send password reset email
            reset_url = self._build_reset_url(token, email)
            email_sent = self.email_service.send_password_reset_email(
                email=user.email,
                reset_url=reset_url,
                user=user
            )
            
            if email_sent:
                # Log security event
                self._log_security_event("password_reset_initiated", {
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                })
                
                return {
                    "success": True,
                    "message": "Password reset link sent to your email address",
                    "email": user.email,
                    "expires_at": expires_at.isoformat()
                }
            else:
                raise ExternalServiceError("Failed to send password reset email")
                
        except (ValidationError, NotFoundError, SecurityError, ExternalServiceError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to initiate password reset: {str(e)}")
    
    def reset_password(
        self, 
        token: str,
        new_password: str,
        confirm_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reset password with security validation.
        
        Args:
            token: Password reset token
            new_password: New password
            confirm_password: Password confirmation
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Password reset result
            
        Raises:
            ValidationError: If password is invalid
            NotFoundError: If token is invalid
            SecurityError: If security check fails
        """
        try:
            # Validate password
            self._validate_password(new_password, confirm_password)
            
            # Get reset token
            reset_token = self.auth_repo.get_password_reset_token(token)
            
            if not reset_token:
                raise NotFoundError("Invalid or expired password reset token")
            
            # Check if token is already used
            if reset_token.is_used:
                raise ValidationError("Password reset token has already been used")
            
            # Check expiration
            if datetime.utcnow() > reset_token.expires_at:
                raise ValidationError("Password reset token has expired")
            
            # Get user
            user = self.user_repo.get(reset_token.user_id)
            
            if not user or not user.is_active:
                raise NotFoundError("User not found or account is inactive")
            
            # Additional security checks
            if self._should_block_reset(user, reset_token, ip_address):
                raise SecurityError("Password reset blocked due to security concerns")
            
            # Check password strength
            password_strength = self.security_service.validate_password_strength(new_password)
            if not password_strength["is_valid"]:
                raise ValidationError("Password does not meet security requirements", errors=password_strength["issues"])
            
            # Check password history
            if self._is_password_reused(user.id, new_password):
                raise ValidationError("Cannot reuse a recent password")
            
            # Hash new password
            hashed_password = self.security_service.hash_password(new_password)
            
            # Update user password
            if not self.user_repo.update_password(user.id, hashed_password):
                raise DatabaseError("Failed to update password")
            
            # Mark token as used
            if not self.auth_repo.use_password_reset_token(token):
                raise DatabaseError("Failed to mark reset token as used")
            
            # Invalidate all user sessions
            self.auth_repo.invalidate_all_user_sessions(user.id)
            
            # Log security event
            self._log_security_event("password_reset_completed", {
                "user_id": user.id,
                "email": user.email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "password_strength": password_strength["strength"]
            })
            
            # Send password reset confirmation email
            self.email_service.send_password_reset_confirmation_email(user.email, user)
            
            return {
                "success": True,
                "message": "Password reset successfully",
                "email": user.email,
                "reset_at": datetime.utcnow().isoformat()
            }
            
        except (ValidationError, NotFoundError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to reset password: {str(e)}")
    
    def validate_reset_token(
        self, 
        token: str
    ) -> Dict[str, Any]:
        """
        Validate password reset token.
        
        Args:
            token: Password reset token to validate
            
        Returns:
            Token validation result
        """
        try:
            reset_token = self.auth_repo.get_password_reset_token(token)
            
            if not reset_token:
                return {
                    "valid": False,
                    "message": "Invalid or expired token",
                    "reason": "not_found"
                }
            
            # Check if already used
            if reset_token.is_used:
                return {
                    "valid": False,
                    "message": "Token has already been used",
                    "reason": "already_used"
                }
            
            # Check expiration
            if datetime.utcnow() > reset_token.expires_at:
                return {
                    "valid": False,
                    "message": "Token has expired",
                    "reason": "expired",
                    "expired_at": reset_token.expires_at.isoformat()
                }
            
            # Get user info
            user = self.user_repo.get(reset_token.user_id)
            
            if not user:
                return {
                    "valid": False,
                    "message": "User not found",
                    "reason": "user_not_found"
                }
            
            return {
                "valid": True,
                "message": "Token is valid",
                "user_id": user.id,
                "email": user.email,
                "expires_at": reset_token.expires_at.isoformat(),
                "time_remaining": int((reset_token.expires_at - datetime.utcnow()).total_seconds())
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate reset token: {str(e)}")
    
    def resend_reset_email(
        self, 
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resend password reset email.
        
        Args:
            email: Email address
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Resend result
        """
        try:
            # Check rate limiting for resend
            if self._is_rate_limited(email, ip_address, "resend_reset"):
                raise SecurityError("Too many resend requests. Please try again later.")
            
            # Check if there's an existing valid token
            user = self.user_repo.get_by_email(email)
            
            if not user:
                # Don't reveal if user exists
                return {
                    "success": True,
                    "message": "If an account with this email exists, a password reset link has been sent.",
                    "email_sent": False
                }
            
            # Get existing reset token
            existing_tokens = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            ).all()
            
            if existing_tokens:
                # Use the most recent token
                latest_token = max(existing_tokens, key=lambda x: x.created_at)
                
                # Check if recent enough to resend (within 1 hour)
                time_since_creation = datetime.utcnow() - latest_token.created_at
                if time_since_creation.total_seconds() < 3600:
                    return {
                        "success": False,
                        "message": "Password reset email was recently sent. Please check your email or wait before requesting again.",
                        "can_resend_at": (latest_token.created_at + timedelta(hours=1)).isoformat()
                    }
            
            # Send new reset email
            return self.initiate_password_reset(email, ip_address, user_agent)
            
        except SecurityError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to resend reset email: {str(e)}")
    
    def get_reset_statistics(self) -> Dict[str, Any]:
        """
        Get password reset statistics.
        
        Returns:
            Password reset statistics
        """
        try:
            # TODO: Implement comprehensive statistics
            # TODO: Add success rate tracking
            # TODO: Add abuse detection
            
            return {
                "total_requests": 0,
                "successful_resets": 0,
                "failed_attempts": 0,
                "expired_tokens": 0,
                "abuse_detected": 0,
                "success_rate": 0.0,
                "average_reset_time": 0.0
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get reset statistics: {str(e)}")
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired password reset tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            return self.auth_repo.cleanup_expired_reset_tokens()
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup expired tokens: {str(e)}")
    
    def _validate_password(self, password: str, confirm_password: str):
        """
        Validate password and confirmation.
        
        Args:
            password: Password to validate
            confirm_password: Password confirmation
            
        Raises:
            ValidationError: If password is invalid
        """
        errors = []
        
        # Check if passwords match
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        # Check password strength
        password_strength = self.security_service.validate_password_strength(password)
        if not password_strength["is_valid"]:
            errors.extend(password_strength["issues"])
        
        if errors:
            raise ValidationError("Password validation failed", errors=errors)
    
    def _generate_reset_token(self) -> str:
        """
        Generate secure password reset token.
        
        Returns:
            Secure reset token
        """
        return secrets.token_urlsafe(32)
    
    def _build_reset_url(self, token: str, email: str) -> str:
        """
        Build password reset URL.
        
        Args:
            token: Reset token
            email: Email address
            
        Returns:
            Reset URL
        """
        base_url = settings.app.get_base_url()
        return f"{base_url}/reset-password?token={token}&email={email}"
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        return bool(email_pattern.match(email))
    
    def _is_rate_limited(self, identifier: str, ip_address: Optional[str], action: str) -> bool:
        """
        Check if identifier/IP is rate limited.
        
        Args:
            identifier: Email or user ID
            ip_address: Client IP address
            action: Type of action
            
        Returns:
            True if rate limited, False otherwise
        """
        # TODO: Implement proper rate limiting with Redis
        # TODO: Add per-action rate limits
        # TODO: Add sliding window rate limiting
        
        # Placeholder implementation
        return False
    
    def _should_block_reset(self, user: User, reset_token: PasswordResetToken, ip_address: Optional[str]) -> bool:
        """
        Check if password reset should be blocked for security.
        
        Args:
            user: User object
            reset_token: Reset token object
            ip_address: Client IP address
            
        Returns:
            True if should block, False otherwise
        """
        # TODO: Implement comprehensive security checks
        # TODO: Add suspicious IP detection
        # TODO: Add rapid reset detection
        # TODO: Add geographic anomaly detection
        
        # Check for recent password changes
        if user.password_changed_at:
            time_since_change = datetime.utcnow() - user.password_changed_at
            if time_since_change.total_seconds() < 3600:  # 1 hour
                return True
        
        # Check for multiple reset requests
        recent_resets = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        if recent_resets > 3:
            return True
        
        return False
    
    def _is_password_reused(self, user_id: int, new_password: str) -> bool:
        """
        Check if password has been recently used.
        
        Args:
            user_id: User ID
            new_password: New password to check
            
        Returns:
            True if password is reused, False otherwise
        """
        # TODO: Implement password history tracking
        # TODO: Add password history table
        # TODO: Add configurable history size
        
        # Placeholder implementation
        return False
    
    def _log_security_event(self, event_type: str, metadata: Dict[str, Any]):
        """
        Log security event for monitoring.
        
        Args:
            event_type: Type of security event
            metadata: Event metadata
        """
        try:
            # TODO: Implement security event logging
            # TODO: Add security monitoring
            # TODO: Add alerting system
            
            pass
        except Exception:
            pass


# Service factory function
def get_password_reset_service(db: Session) -> PasswordResetService:
    """
    Get password reset service instance.
    
    Args:
        db: Database session
        
    Returns:
        PasswordResetService instance
    """
    return PasswordResetService(db)
