"""
Authentication repository for auth-related database operations.

Handles tokens, sessions, password resets, and authentication
state management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    TokenBlacklist, PasswordResetToken, EmailVerificationToken,
    UserSession, LoginAttempt, RefreshToken
)
from app.repositories.base import BaseRepository


class AuthRepository(BaseRepository[TokenBlacklist]):
    """
    Repository for authentication-related database operations.
    
    Handles tokens, sessions, password resets, and authentication
    state management with proper security considerations.
    """
    
    def __init__(self, db: Session):
        super().__init__(TokenBlacklist, db)
        # TODO: Add connection pooling optimization
        # TODO: Implement caching for frequently accessed tokens
    
    # Token Blacklist Operations
    def blacklist_token(self, token: str, reason: str = None) -> bool:
        """
        Add token to blacklist.
        
        Args:
            token: JWT token to blacklist
            reason: Reason for blacklisting
            
        Returns:
            True if blacklisted, False if already exists
        """
        try:
            # Check if already blacklisted
            existing = self.db.query(TokenBlacklist).filter(
                TokenBlacklist.token == token
            ).first()
            
            if existing:
                return False
            
            # Add to blacklist
            blacklist_entry = TokenBlacklist(
                token=token,
                reason=reason,
                created_at=datetime.utcnow()
            )
            
            self.db.add(blacklist_entry)
            self.db.commit()
            return True
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        return self.db.query(TokenBlacklist).filter(
            TokenBlacklist.token == token
        ).first() is not None
    
    def cleanup_expired_blacklist(self, days: int = 30) -> int:
        """
        Clean up expired blacklist entries.
        
        Args:
            days: Age in days to delete
            
        Returns:
            Number of entries deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = self.db.query(TokenBlacklist).filter(
                TokenBlacklist.created_at < cutoff_date
            ).delete()
            
            self.db.commit()
            return deleted
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    # Password Reset Operations
    def create_password_reset_token(
        self, 
        user_id: int, 
        token: str, 
        expires_hours: int = 24
    ) -> bool:
        """
        Create password reset token.
        
        Args:
            user_id: User ID
            token: Reset token
            expires_hours: Token expiration in hours
            
        Returns:
            True if created, False if failed
        """
        try:
            # Invalidate existing tokens for this user
            self.db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user_id
            ).update({"is_used": True})
            
            # Create new token
            reset_token = PasswordResetToken(
                user_id=user_id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
                is_used=False,
                created_at=datetime.utcnow()
            )
            
            self.db.add(reset_token)
            self.db.commit()
            return True
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Get password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            PasswordResetToken instance or None
        """
        return self.db.query(PasswordResetToken).filter(
            and_(
                PasswordResetToken.token == token,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        ).first()
    
    def use_password_reset_token(self, token: str) -> bool:
        """
        Mark password reset token as used.
        
        Args:
            token: Reset token
            
        Returns:
            True if marked as used, False if not found
        """
        try:
            reset_token = self.get_password_reset_token(token)
            if reset_token:
                reset_token.is_used = True
                reset_token.used_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def cleanup_expired_reset_tokens(self) -> int:
        """
        Clean up expired password reset tokens.
        
        Returns:
            Number of tokens deleted
        """
        try:
            deleted = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.expires_at < datetime.utcnow()
            ).delete()
            
            self.db.commit()
            return deleted
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    # Email Verification Operations
    def create_email_verification_token(
        self, 
        user_id: int, 
        token: str, 
        expires_hours: int = 24
    ) -> bool:
        """
        Create email verification token.
        
        Args:
            user_id: User ID
            token: Verification token
            expires_hours: Token expiration in hours
            
        Returns:
            True if created, False if failed
        """
        try:
            # Invalidate existing tokens for this user
            self.db.query(EmailVerificationToken).filter(
                EmailVerificationToken.user_id == user_id
            ).update({"is_used": True})
            
            # Create new token
            verification_token = EmailVerificationToken(
                user_id=user_id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
                is_used=False,
                created_at=datetime.utcnow()
            )
            
            self.db.add(verification_token)
            self.db.commit()
            return True
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def get_email_verification_token(self, token: str) -> Optional[EmailVerificationToken]:
        """
        Get email verification token.
        
        Args:
            token: Verification token
            
        Returns:
            EmailVerificationToken instance or None
        """
        return self.db.query(EmailVerificationToken).filter(
            and_(
                EmailVerificationToken.token == token,
                EmailVerificationToken.is_used == False,
                EmailVerificationToken.expires_at > datetime.utcnow()
            )
        ).first()
    
    def use_email_verification_token(self, token: str) -> bool:
        """
        Mark email verification token as used.
        
        Args:
            token: Verification token
            
        Returns:
            True if marked as used, False if not found
        """
        try:
            verification_token = self.get_email_verification_token(token)
            if verification_token:
                verification_token.is_used = True
                verification_token.used_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    # User Session Operations
    def create_user_session(
        self, 
        user_id: int, 
        session_token: str,
        user_agent: str = None,
        ip_address: str = None
    ) -> Optional[UserSession]:
        """
        Create user session.
        
        Args:
            user_id: User ID
            session_token: Session token
            user_agent: User agent string
            ip_address: User IP address
            
        Returns:
            UserSession instance or None if failed
        """
        try:
            session = UserSession(
                user_id=user_id,
                session_token=session_token,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True,
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
            
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def get_user_session(self, session_token: str) -> Optional[UserSession]:
        """
        Get user session by token.
        
        Args:
            session_token: Session token
            
        Returns:
            UserSession instance or None
        """
        return self.db.query(UserSession).filter(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            )
        ).first()
    
    def update_session_activity(self, session_token: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_token: Session token
            
        Returns:
            True if updated, False if not found
        """
        try:
            session = self.get_user_session(session_token)
            if session:
                session.last_activity_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def invalidate_user_session(self, session_token: str) -> bool:
        """
        Invalidate user session.
        
        Args:
            session_token: Session token
            
        Returns:
            True if invalidated, False if not found
        """
        try:
            session = self.get_user_session(session_token)
            if session:
                session.is_active = False
                session.ended_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def invalidate_all_user_sessions(self, user_id: int) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions invalidated
        """
        try:
            count = self.db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            ).update({
                "is_active": False,
                "ended_at": datetime.utcnow()
            })
            
            self.db.commit()
            return count
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    def cleanup_expired_sessions(self, days: int = 30) -> int:
        """
        Clean up expired sessions.
        
        Args:
            days: Age in days to delete
            
        Returns:
            Number of sessions deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = self.db.query(UserSession).filter(
                UserSession.last_activity_at < cutoff_date
            ).delete()
            
            self.db.commit()
            return deleted
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    # Login Attempt Operations
    def record_login_attempt(
        self, 
        email: str, 
        ip_address: str = None,
        user_agent: str = None,
        success: bool = False,
        failure_reason: str = None
    ) -> bool:
        """
        Record login attempt.
        
        Args:
            email: Email address
            ip_address: IP address
            user_agent: User agent string
            success: Whether login was successful
            failure_reason: Reason for failure
            
        Returns:
            True if recorded, False if failed
        """
        try:
            attempt = LoginAttempt(
                email=email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
                attempted_at=datetime.utcnow()
            )
            
            self.db.add(attempt)
            self.db.commit()
            return True
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def get_recent_login_attempts(
        self, 
        email: str, 
        hours: int = 24
    ) -> List[LoginAttempt]:
        """
        Get recent login attempts for email.
        
        Args:
            email: Email address
            hours: Number of hours to look back
            
        Returns:
            List of login attempts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(LoginAttempt).filter(
            and_(
                LoginAttempt.email == email.lower(),
                LoginAttempt.attempted_at >= cutoff_time
            )
        ).order_by(desc(LoginAttempt.attempted_at)).all()
    
    def count_failed_login_attempts(
        self, 
        email: str, 
        hours: int = 1
    ) -> int:
        """
        Count failed login attempts for email.
        
        Args:
            email: Email address
            hours: Number of hours to look back
            
        Returns:
            Number of failed attempts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(LoginAttempt).filter(
            and_(
                LoginAttempt.email == email.lower(),
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff_time
            )
        ).count()
    
    def cleanup_old_login_attempts(self, days: int = 90) -> int:
        """
        Clean up old login attempts.
        
        Args:
            days: Age in days to delete
            
        Returns:
            Number of attempts deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = self.db.query(LoginAttempt).filter(
                LoginAttempt.attempted_at < cutoff_date
            ).delete()
            
            self.db.commit()
            return deleted
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    # Refresh Token Operations
    def create_refresh_token(
        self, 
        user_id: int, 
        token: str,
        expires_days: int = 30
    ) -> Optional[RefreshToken]:
        """
        Create refresh token.
        
        Args:
            user_id: User ID
            token: Refresh token
            expires_days: Token expiration in days
            
        Returns:
            RefreshToken instance or None if failed
        """
        try:
            refresh_token = RefreshToken(
                user_id=user_id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(days=expires_days),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            self.db.add(refresh_token)
            self.db.commit()
            self.db.refresh(refresh_token)
            return refresh_token
            
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """
        Get refresh token.
        
        Args:
            token: Refresh token
            
        Returns:
            RefreshToken instance or None
        """
        return self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.token == token,
                RefreshToken.is_active == True,
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).first()
    
    def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoke refresh token.
        
        Args:
            token: Refresh token
            
        Returns:
            True if revoked, False if not found
        """
        try:
            refresh_token = self.get_refresh_token(token)
            if refresh_token:
                refresh_token.is_active = False
                refresh_token.revoked_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def revoke_all_user_refresh_tokens(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        try:
            count = self.db.query(RefreshToken).filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_active == True
                )
            ).update({
                "is_active": False,
                "revoked_at": datetime.utcnow()
            })
            
            self.db.commit()
            return count
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
    
    def cleanup_expired_refresh_tokens(self) -> int:
        """
        Clean up expired refresh tokens.
        
        Returns:
            Number of tokens deleted
        """
        try:
            deleted = self.db.query(RefreshToken).filter(
                RefreshToken.expires_at < datetime.utcnow()
            ).delete()
            
            self.db.commit()
            return deleted
            
        except SQLAlchemyError:
            self.db.rollback()
            return 0
