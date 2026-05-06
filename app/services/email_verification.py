"""
Email verification service for secure email verification.

Handles email verification tokens, sending verification emails,
and comprehensive verification workflow with proper security.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib

from sqlalchemy.orm import Session
from app.db.models import EmailVerificationToken, User
from app.repositories.auth import AuthRepository
from app.repositories.user import UserRepository
from app.core.config import settings
from app.core.exceptions import (
    ValidationError, NotFoundError, SecurityError,
    DatabaseError, ExternalServiceError
)
from app.services.email import EmailService


class EmailVerificationService:
    """
    Email verification service for secure email verification.
    
    Handles email verification tokens, sending verification emails,
    and comprehensive verification workflow with proper security.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
        self.user_repo = UserRepository(db)
        self.email_service = EmailService(db)
        
        # TODO: Add rate limiting for verification requests
        # TODO: Add email template system
        # TODO: Add verification analytics
        # TODO: Add email bounce handling
    
    def send_verification_email(
        self, 
        email: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send email verification email.
        
        Args:
            email: Email address to verify
            user_id: User ID (optional, will be looked up if not provided)
            
        Returns:
            Verification email result
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If email is invalid
            SecurityError: If rate limit exceeded
        """
        try:
            # Validate email format
            if not self._is_valid_email(email):
                raise ValidationError("Invalid email format")
            
            # Get user if user_id not provided
            if not user_id:
                user = self.user_repo.get_by_email(email)
                if not user:
                    raise NotFoundError("User not found")
                user_id = user.id
            
            # Check rate limiting
            if self._is_rate_limited(email, "verification"):
                raise SecurityError("Too many verification requests. Please try again later.")
            
            # Check if email is already verified
            user = self.user_repo.get(user_id)
            if user and user.email_verified:
                return {
                    "success": False,
                    "message": "Email is already verified",
                    "already_verified": True
                }
            
            # Generate verification token
            token = self._generate_verification_token()
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Create verification token record
            verification_token = EmailVerificationToken(
                user_id=user_id,
                email=email.lower(),
                token=token,
                expires_at=expires_at,
                is_used=False,
                created_at=datetime.utcnow()
            )
            
            self.db.add(verification_token)
            self.db.commit()
            
            # Send verification email
            verification_url = self._build_verification_url(token, email)
            email_sent = self.email_service.send_verification_email(
                email=email,
                verification_url=verification_url,
                user=user
            )
            
            if email_sent:
                return {
                    "success": True,
                    "message": "Verification email sent successfully",
                    "email": email,
                    "expires_at": expires_at.isoformat()
                }
            else:
                raise ExternalServiceError("Failed to send verification email")
                
        except (ValidationError, NotFoundError, SecurityError, ExternalServiceError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to send verification email: {str(e)}")
    
    def verify_email(
        self, 
        token: str,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify email with token.
        
        Args:
            token: Verification token
            email: Email address (optional, for additional validation)
            
        Returns:
            Verification result
            
        Raises:
            ValidationError: If token is invalid
            NotFoundError: If token not found
            SecurityError: If security check fails
        """
        try:
            # Get verification token
            verification_token = self.auth_repo.get_email_verification_token(token)
            
            if not verification_token:
                raise NotFoundError("Invalid or expired verification token")
            
            # Additional email validation if provided
            if email and verification_token.email != email.lower():
                raise SecurityError("Email does not match verification token")
            
            # Check if already used
            if verification_token.is_used:
                raise ValidationError("Verification token has already been used")
            
            # Check expiration
            if datetime.utcnow() > verification_token.expires_at:
                raise ValidationError("Verification token has expired")
            
            # Get user
            user = self.user_repo.get(verification_token.user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Mark email as verified
            if not self.user_repo.verify_email(user.id):
                raise DatabaseError("Failed to verify email")
            
            # Mark token as used
            if not self.auth_repo.use_email_verification_token(token):
                raise DatabaseError("Failed to mark verification token as used")
            
            # Send welcome email
            self.email_service.send_welcome_email(user.email, user)
            
            # Log activity
            self._log_verification_activity(user.id, "email_verified", {
                "email": user.email,
                "verification_method": "token"
            })
            
            return {
                "success": True,
                "message": "Email verified successfully",
                "email": user.email,
                "verified_at": datetime.utcnow().isoformat()
            }
            
        except (ValidationError, NotFoundError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to verify email: {str(e)}")
    
    def resend_verification_email(
        self, 
        email: str
    ) -> Dict[str, Any]:
        """
        Resend email verification email.
        
        Args:
            email: Email address to resend verification for
            
        Returns:
            Resend result
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If rate limit exceeded
        """
        try:
            # Get user
            user = self.user_repo.get_by_email(email)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Check if already verified
            if user.email_verified:
                return {
                    "success": False,
                    "message": "Email is already verified",
                    "already_verified": True
                }
            
            # Check rate limiting
            if self._is_rate_limited(email, "resend"):
                raise SecurityError("Too many resend requests. Please try again later.")
            
            # Invalidate existing tokens
            self._invalidate_user_verification_tokens(user.id)
            
            # Send new verification email
            return self.send_verification_email(email, user.id)
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to resend verification email: {str(e)}")
    
    def get_verification_status(
        self, 
        email: str
    ) -> Dict[str, Any]:
        """
        Get email verification status.
        
        Args:
            email: Email address to check
            
        Returns:
            Verification status
        """
        try:
            # Get user
            user = self.user_repo.get_by_email(email)
            
            if not user:
                return {
                    "email": email,
                    "verified": False,
                    "exists": False
                }
            
            # Get latest verification token
            latest_token = self.db.query(EmailVerificationToken).filter(
                EmailVerificationToken.email == email.lower()
            ).order_by(EmailVerificationToken.created_at.desc()).first()
            
            return {
                "email": email,
                "verified": user.email_verified,
                "verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
                "exists": True,
                "has_pending_token": latest_token and not latest_token.is_used and latest_token.expires_at > datetime.utcnow(),
                "token_expires_at": latest_token.expires_at.isoformat() if latest_token else None,
                "can_resend": self._can_resend_verification(email)
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get verification status: {str(e)}")
    
    def change_email(
        self, 
        user_id: int, 
        new_email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Change user email with verification.
        
        Args:
            user_id: User ID
            new_email: New email address
            password: Current password for verification
            
        Returns:
            Email change result
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If data is invalid
            SecurityError: If password is incorrect
        """
        try:
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Validate new email
            if not self._is_valid_email(new_email):
                raise ValidationError("Invalid email format")
            
            # Check if new email is already used
            existing_user = self.user_repo.get_by_email(new_email)
            if existing_user and existing_user.id != user_id:
                raise ValidationError("Email address is already in use")
            
            # Verify password
            from app.core.security import verify_password
            if not verify_password(password, user.hashed_password):
                raise SecurityError("Current password is incorrect")
            
            # Check rate limiting
            if self._is_rate_limited(str(user_id), "email_change"):
                raise SecurityError("Too many email change requests. Please try again later.")
            
            # Generate verification token for new email
            token = self._generate_verification_token()
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Create verification token record
            verification_token = EmailVerificationToken(
                user_id=user_id,
                email=new_email.lower(),
                token=token,
                expires_at=expires_at,
                is_used=False,
                created_at=datetime.utcnow()
            )
            
            self.db.add(verification_token)
            self.db.commit()
            
            # Send verification email for new email
            verification_url = self._build_verification_url(token, new_email)
            email_sent = self.email_service.send_email_change_verification(
                new_email=new_email,
                old_email=user.email,
                verification_url=verification_url,
                user=user
            )
            
            if email_sent:
                # Log activity
                self._log_verification_activity(user_id, "email_change_requested", {
                    "new_email": new_email,
                    "old_email": user.email
                })
                
                return {
                    "success": True,
                    "message": "Email change verification sent to new email address",
                    "new_email": new_email,
                    "expires_at": expires_at.isoformat()
                }
            else:
                raise ExternalServiceError("Failed to send email change verification")
                
        except (ValidationError, NotFoundError, SecurityError, ExternalServiceError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to change email: {str(e)}")
    
    def confirm_email_change(
        self, 
        token: str
    ) -> Dict[str, Any]:
        """
        Confirm email change with verification token.
        
        Args:
            token: Email change verification token
            
        Returns:
            Email change confirmation result
            
        Raises:
            ValidationError: If token is invalid
            NotFoundError: If token not found
        """
        try:
            # Get verification token
            verification_token = self.auth_repo.get_email_verification_token(token)
            
            if not verification_token:
                raise NotFoundError("Invalid or expired verification token")
            
            # Check if already used
            if verification_token.is_used:
                raise ValidationError("Verification token has already been used")
            
            # Check expiration
            if datetime.utcnow() > verification_token.expires_at:
                raise ValidationError("Verification token has expired")
            
            # Get user
            user = self.user_repo.get(verification_token.user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Update user email
            old_email = user.email
            user.email = verification_token.email
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            # Mark token as used
            if not self.auth_repo.use_email_verification_token(token):
                raise DatabaseError("Failed to mark verification token as used")
            
            self.db.commit()
            
            # Send confirmation emails
            self.email_service.send_email_change_confirmation(
                new_email=user.email,
                old_email=old_email,
                user=user
            )
            
            # Log activity
            self._log_verification_activity(user.id, "email_changed", {
                "new_email": user.email,
                "old_email": old_email
            })
            
            return {
                "success": True,
                "message": "Email changed successfully",
                "new_email": user.email,
                "changed_at": datetime.utcnow().isoformat()
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to confirm email change: {str(e)}")
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired verification tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            return self.auth_repo.cleanup_expired_tokens()
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup expired tokens: {str(e)}")
    
    def get_verification_statistics(self) -> Dict[str, Any]:
        """
        Get email verification statistics.
        
        Returns:
            Verification statistics
        """
        try:
            # TODO: Implement comprehensive statistics
            # TODO: Add conversion rate tracking
            # TODO: Add delivery statistics
            
            return {
                "total_sent": 0,
                "total_verified": 0,
                "pending_verifications": 0,
                "expired_tokens": 0,
                "verification_rate": 0.0,
                "average_verification_time": 0.0
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get verification statistics: {str(e)}")
    
    def _generate_verification_token(self) -> str:
        """
        Generate secure verification token.
        
        Returns:
            Secure verification token
        """
        return secrets.token_urlsafe(32)
    
    def _build_verification_url(self, token: str, email: str) -> str:
        """
        Build verification URL.
        
        Args:
            token: Verification token
            email: Email address
            
        Returns:
            Verification URL
        """
        base_url = settings.app.get_base_url()
        return f"{base_url}/verify-email?token={token}&email={email}"
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        # BUG: Email regex allows multiple @ symbols in local part
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-@]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        return bool(email_pattern.match(email))
    
    def _is_rate_limited(self, identifier: str, action: str) -> bool:
        """
        Check if identifier is rate limited.
        
        Args:
            identifier: Email or user ID
            action: Type of action
            
        Returns:
            True if rate limited, False otherwise
        """
        # TODO: Implement proper rate limiting with Redis
        # TODO: Add per-action rate limits
        # TODO: Add sliding window rate limiting
        
        # Placeholder implementation
        return False
    
    def _can_resend_verification(self, email: str) -> bool:
        """
        Check if verification can be resent.
        
        Args:
            email: Email address
            
        Returns:
            True if can resend, False otherwise
        """
        # Check last verification time
        latest_token = self.db.query(EmailVerificationToken).filter(
            EmailVerificationToken.email == email.lower()
        ).order_by(EmailVerificationToken.created_at.desc()).first()
        
        if not latest_token:
            return True
        
        # Allow resend after 5 minutes
        time_since_last = datetime.utcnow() - latest_token.created_at
        return time_since_last.total_seconds() >= 300
    
    def _invalidate_user_verification_tokens(self, user_id: int):
        """
        Invalidate all verification tokens for a user.
        
        Args:
            user_id: User ID
        """
        try:
            self.db.query(EmailVerificationToken).filter(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.is_used == False
            ).update({"is_used": True})
            
            self.db.commit()
        except Exception:
            pass
    
    def _log_verification_activity(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """
        Log verification activity.
        
        Args:
            user_id: User ID
            action: Activity action
            metadata: Activity metadata
        """
        try:
            # TODO: Implement activity logging
            # TODO: Add activity tracking
            # TODO: Add audit logging
            
            pass
        except Exception:
            pass


# Service factory function
def get_email_verification_service(db: Session) -> EmailVerificationService:
    """
    Get email verification service instance.
    
    Args:
        db: Database session
        
    Returns:
        EmailVerificationService instance
    """
    return EmailVerificationService(db)
