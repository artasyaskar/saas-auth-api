"""
Password reset service with secure token generation.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import User, PasswordResetToken
from app.services.email import get_email_service
from app.middleware.logging import audit_logger


class PasswordResetService:
    """Service for handling password reset flow."""
    
    TOKEN_LENGTH = 32
    TOKEN_EXPIRY_HOURS = 24
    MAX_ACTIVE_TOKENS_PER_USER = 3  # Limit concurrent reset attempts
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()
    
    def request_password_reset(self, email: str, ip_address: str = None) -> bool:
        """
        Initiate a password reset for a user.
        Always returns True (even if user doesn't exist) to prevent email enumeration.
        """
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            # Don't reveal if email exists
            return True
        
        # Check for too many active tokens
        active_tokens_count = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).count()
        
        if active_tokens_count >= self.MAX_ACTIVE_TOKENS_PER_USER:
            # Silently succeed but don't send email
            # This prevents abuse while not revealing the issue
            return True
        
        # Generate secure token
        token = self._generate_token()
        
        # Create reset token record
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=self._hash_token(token),
            expires_at=datetime.utcnow() + timedelta(hours=self.TOKEN_EXPIRY_HOURS),
            ip_address=ip_address,
            used=False
        )
        
        self.db.add(reset_token)
        self.db.commit()
        
        # Send email (async in production)
        self.email_service.send_password_reset(
            to_email=user.email,
            username=user.username,
            reset_token=token,
            expiry_hours=self.TOKEN_EXPIRY_HOURS
        )
        
        # Log audit event
        audit_logger.log_password_reset(
            user_id=user.id,
            username=user.username,
            action="request",
            ip_address=ip_address,
            success=True
        )
        
        return True
    
    def validate_reset_token(self, token: str) -> Optional[User]:
        """
        Validate a password reset token.
        Returns the user if valid, None otherwise.
        """
        token_hash = self._hash_token(token)
        
        reset_record = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()
        
        if not reset_record:
            return None
        
        user = self.db.query(User).filter(User.id == reset_record.user_id).first()
        return user
    
    def reset_password(self, token: str, new_password: str, 
                      ip_address: str = None) -> tuple[bool, str]:
        """
        Reset a user's password using a valid token.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        from app.core.security import get_password_hash
        
        token_hash = self._hash_token(token)
        
        reset_record = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()
        
        if not reset_record:
            return False, "Invalid or expired token"
        
        user = self.db.query(User).filter(User.id == reset_record.user_id).first()
        
        if not user:
            return False, "User not found"
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Mark token as used
        reset_record.used = True
        reset_record.used_at = datetime.utcnow()
        reset_record.used_ip = ip_address
        
        self.db.commit()
        
        # Log audit event
        audit_logger.log_password_reset(
            user_id=user.id,
            username=user.username,
            action="complete",
            ip_address=ip_address,
            success=True
        )
        
        # TODO: Send confirmation email
        # TODO: Invalidate all existing sessions for this user
        
        return True, "Password reset successful"
    
    def _generate_token(self) -> str:
        """Generate a cryptographically secure random token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(self.TOKEN_LENGTH))
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage (don't store raw tokens)."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
    
    def cleanup_expired_tokens(self, days_to_keep: int = 7) -> int:
        """Clean up old password reset tokens."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted


def get_password_reset_service(db: Session) -> PasswordResetService:
    """Dependency to get password reset service."""
    return PasswordResetService(db)
