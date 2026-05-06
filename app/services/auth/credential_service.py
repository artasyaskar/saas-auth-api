"""
Credential service for user authentication.

Handles user credential validation, password verification,
and account status checks with proper security considerations.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from sqlalchemy.orm import Session
from app.db.models import User, UserRole, LoginAttempt
from app.repositories.auth import AuthRepository
from app.repositories.user import UserRepository
from app.core.security import verify_password
from app.core.exceptions import AuthenticationError, SecurityError, RateLimitError
from app.schemas.auth import LoginRequest

logger = structlog.get_logger()


class CredentialService:
    """
    Service for handling user credential validation.
    
    Separated from main auth service to focus specifically on
    credential verification and account validation logic.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
        self.user_repo = UserRepository(db)
    
    def validate_credentials(self, request: LoginRequest, ip_address: str = None) -> User:
        """
        Validate user credentials and return authenticated user.
        
        Args:
            request: Login request with credentials
            ip_address: Client IP address for security logging
            
        Returns:
            Authenticated user object
            
        Raises:
            AuthenticationError: If credentials are invalid
            SecurityError: If account has security issues
            RateLimitError: If rate limit exceeded
        """
        try:
            # Check rate limiting first
            if self._is_rate_limited(request.identifier, ip_address):
                self._record_failed_attempt(request.identifier, ip_address, "Rate limited")
                raise RateLimitError("Too many login attempts. Please try again later.")
            
            # Record login attempt start
            self._record_attempt_start(request.identifier, ip_address)
            
            # Find user by email or username
            user = self._find_user(request.identifier)
            
            # Validate account status
            self._validate_account_status(user)
            
            # Verify password
            self._verify_password(request.password, user.hashed_password)
            
            # Check for additional security requirements
            self._check_security_requirements(user)
            
            # Record successful validation
            self._record_successful_validation(request.identifier, ip_address)
            
            return user
            
        except (AuthenticationError, SecurityError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"Credential validation failed: {str(e)}")
            raise AuthenticationError("Authentication failed")
    
    def check_2fa_requirement(self, user: User) -> Dict[str, Any]:
        """
        Check if user requires two-factor authentication.
        
        Args:
            user: User to check
            
        Returns:
            Dictionary with 2FA requirements
        """
        try:
            # Check if user has 2FA enabled
            if not user.two_factor_enabled:
                return {"required": False}
            
            # Check if 2FA is required for this user based on risk factors
            risk_factors = self._assess_login_risk(user)
            
            if risk_factors["high_risk"]:
                return {
                    "required": True,
                    "methods": ["totp", "sms", "email"],
                    "reason": "High risk login detected"
                }
            
            return {
                "required": True,
                "methods": ["totp"],
                "reason": "User has 2FA enabled"
            }
            
        except Exception as e:
            logger.error(f"2FA requirement check failed: {str(e)}")
            return {"required": False}
    
    def _find_user(self, identifier: str) -> User:
        """Find user by email or username."""
        user = self.user_repo.get_by_email_or_username(identifier)
        
        if not user:
            self._record_failed_attempt(identifier, None, "User not found")
            raise AuthenticationError("Invalid credentials")
        
        return user
    
    def _validate_account_status(self, user: User) -> None:
        """Validate user account status."""
        if not user.is_active:
            raise AuthenticationError("Account is not active")
        
        if user.is_locked:
            raise SecurityError("Account is locked")
        
        if user.email_verified is False:
            raise AuthenticationError("Email address not verified")
    
    def _verify_password(self, provided_password: str, stored_hash: str) -> None:
        """Verify password against stored hash."""
        if not verify_password(provided_password, stored_hash):
            raise AuthenticationError("Invalid credentials")
    
    def _check_security_requirements(self, user: User) -> None:
        """Check additional security requirements."""
        # Check for expired password
        if user.password_expires_at and user.password_expires_at < datetime.utcnow():
            raise SecurityError("Password has expired")
        
        # Check for forced password reset
        if user.force_password_reset:
            raise SecurityError("Password reset required")
    
    def _assess_login_risk(self, user: User) -> Dict[str, Any]:
        """Assess login risk factors for the user."""
        try:
            risk_factors = {
                "high_risk": False,
                "factors": []
            }
            
            # Check recent failed login attempts
            recent_failures = self.auth_repo.get_recent_failed_attempts(
                user.email, hours=24
            )
            
            if len(recent_failures) > 5:
                risk_factors["high_risk"] = True
                risk_factors["factors"].append("multiple_failed_attempts")
            
            # Check if this is a new device/location (simplified)
            # In production, this would use device fingerprinting and IP geolocation
            if user.last_login_at is None:
                risk_factors["factors"].append("first_login")
            
            # Check account age
            if user.created_at and (datetime.utcnow() - user.created_at).days < 7:
                risk_factors["factors"].append("new_account")
                if len(recent_failures) > 2:
                    risk_factors["high_risk"] = True
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            return {"high_risk": False, "factors": []}
    
    def _is_rate_limited(self, identifier: str, ip_address: str) -> bool:
        """Check if identifier/IP is rate limited."""
        try:
            # Check per-identifier rate limit
            identifier_attempts = self.auth_repo.get_recent_attempts(
                identifier, minutes=15
            )
            
            if len(identifier_attempts) >= 5:
                return True
            
            # Check per-IP rate limit
            if ip_address:
                ip_attempts = self.auth_repo.get_recent_attempts_by_ip(
                    ip_address, minutes=15
                )
                
                if len(ip_attempts) >= 10:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return False
    
    def _record_attempt_start(self, identifier: str, ip_address: str) -> None:
        """Record login attempt start."""
        try:
            self.auth_repo.record_login_attempt(
                email=identifier,
                ip_address=ip_address,
                user_agent=None,  # Will be set by orchestrator
                success=False
            )
        except Exception as e:
            logger.error(f"Failed to record login attempt: {str(e)}")
    
    def _record_failed_attempt(self, identifier: str, ip_address: str, reason: str) -> None:
        """Record failed login attempt with reason."""
        try:
            self.auth_repo.record_login_attempt(
                email=identifier,
                ip_address=ip_address,
                user_agent=None,
                success=False,
                failure_reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to record failed attempt: {str(e)}")
    
    def _record_successful_validation(self, identifier: str, ip_address: str) -> None:
        """Record successful credential validation."""
        try:
            self.auth_repo.record_login_attempt(
                email=identifier,
                ip_address=ip_address,
                user_agent=None,
                success=True
            )
        except Exception as e:
            logger.error(f"Failed to record successful validation: {str(e)}")
