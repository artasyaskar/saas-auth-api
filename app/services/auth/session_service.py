"""
Session service for user session management.

Handles user session creation, tracking, and management
with proper security considerations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import structlog

from sqlalchemy.orm import Session
from app.db.models import User, UserSession
from app.repositories.auth import AuthRepository
from app.core.exceptions import AuthenticationError, SecurityError, SessionError
from app.core.config import settings

logger = structlog.get_logger()


class SessionService:
    """
    Service for handling user session management.
    
    Separated from main auth service to focus specifically on
    session creation, tracking, and lifecycle management.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
    
    def create_user_session(
        self, 
        user_id: int, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: User agent string
            device_id: Device identifier
            
        Returns:
            Created session object
            
        Raises:
            SessionError: If session creation fails
        """
        try:
            # Check existing sessions
            existing_sessions = self._get_active_sessions(user_id)
            
            # Enforce session limits
            self._enforce_session_limits(user_id, existing_sessions)
            
            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            
            # Create session record
            session = UserSession(
                user_id=user_id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                created_at=datetime.utcnow(),
                last_accessed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=settings.security.session_expire_days),
                is_active=True
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            logger.info(f"Created session for user {user_id}")
            return session
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Session creation failed for user {user_id}: {str(e)}")
            raise SessionError(f"Failed to create session: {str(e)}")
    
    def validate_session(self, session_token: str, ip_address: Optional[str] = None) -> Optional[UserSession]:
        """
        Validate a session token and return session.
        
        Args:
            session_token: Session token to validate
            ip_address: Current IP address for validation
            
        Returns:
            Valid session object or None
            
        Raises:
            SessionError: If session validation fails
        """
        try:
            # Find session by token
            session = self.db.query(UserSession).filter(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            ).first()
            
            if not session:
                raise SessionError("Invalid session token")
            
            # Check expiration
            if datetime.utcnow() > session.expires_at:
                self._deactivate_session(session.id, "Session expired")
                raise SessionError("Session has expired")
            
            # Check IP address binding (if enabled)
            if settings.security.session_ip_binding and session.ip_address:
                if ip_address and session.ip_address != ip_address:
                    self._deactivate_session(session.id, "IP address mismatch")
                    raise SessionError("Session IP address mismatch")
            
            # Update last accessed time
            session.last_accessed_at = datetime.utcnow()
            self.db.commit()
            
            return session
            
        except SessionError:
            raise
        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            raise SessionError(f"Failed to validate session: {str(e)}")
    
    def revoke_session(self, session_token: str, reason: str = "logout") -> bool:
        """
        Revoke a specific session.
        
        Args:
            session_token: Session token to revoke
            reason: Reason for revocation
            
        Returns:
            True if session was revoked successfully
        """
        try:
            session = self.db.query(UserSession).filter(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            ).first()
            
            if not session:
                return False
            
            return self._deactivate_session(session.id, reason)
            
        except Exception as e:
            logger.error(f"Session revocation failed: {str(e)}")
            return False
    
    def revoke_user_sessions(self, user_id: int, reason: str = "logout_all", exclude_session: Optional[str] = None) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            exclude_session: Session token to exclude from revocation
            
        Returns:
            Number of sessions revoked
        """
        try:
            query = self.db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            
            # Exclude specific session if provided
            if exclude_session:
                query = query.filter(UserSession.session_token != exclude_session)
            
            sessions = query.all()
            
            revoked_count = 0
            for session in sessions:
                if self._deactivate_session(session.id, reason):
                    revoked_count += 1
            
            logger.info(f"Revoked {revoked_count} sessions for user {user_id}, reason: {reason}")
            return revoked_count
            
        except Exception as e:
            logger.error(f"User session revocation failed: {str(e)}")
            return 0
    
    def get_user_sessions(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active sessions
            
        Returns:
            List of session information
        """
        try:
            query = self.db.query(UserSession).filter(UserSession.user_id == user_id)
            
            if active_only:
                query = query.filter(UserSession.is_active == True)
            
            sessions = query.order_by(UserSession.last_accessed_at.desc()).all()
            
            return [
                {
                    "id": session.id,
                    "session_token": session.session_token,
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "device_id": session.device_id,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_accessed_at": session.last_accessed_at.isoformat() if session.last_accessed_at else None,
                    "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                    "is_active": session.is_active,
                    "is_expired": datetime.utcnow() > session.expires_at if session.expires_at else False
                }
                for session in sessions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            expired_sessions = self.db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow(),
                UserSession.is_active == True
            ).all()
            
            cleaned_count = 0
            for session in expired_sessions:
                if self._deactivate_session(session.id, "Session expired"):
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {str(e)}")
            return 0
    
    def get_session_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Args:
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Dictionary with session statistics
        """
        try:
            query = self.db.query(UserSession)
            
            if user_id:
                query = query.filter(UserSession.user_id == user_id)
            
            total_sessions = query.count()
            active_sessions = query.filter(UserSession.is_active == True).count()
            expired_sessions = query.filter(
                UserSession.expires_at < datetime.utcnow()
            ).count()
            
            # Get recent activity
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_sessions = query.filter(
                UserSession.last_accessed_at > recent_cutoff
            ).count()
            
            stats = {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "recent_sessions_24h": recent_sessions,
                "max_sessions_per_user": settings.security.max_sessions_per_user
            }
            
            if user_id:
                stats["user_at_limit"] = active_sessions >= settings.security.max_sessions_per_user
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {str(e)}")
            return {"error": str(e)}
    
    def _get_active_sessions(self, user_id: int) -> List[UserSession]:
        """Get active sessions for a user."""
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).all()
    
    def _enforce_session_limits(self, user_id: int, existing_sessions: List[UserSession]) -> None:
        """Enforce session limits for a user."""
        max_sessions = settings.security.max_sessions_per_user
        
        if len(existing_sessions) >= max_sessions:
            # Revoke oldest session
            oldest_session = min(existing_sessions, key=lambda s: s.created_at)
            self._deactivate_session(oldest_session.id, "Session limit exceeded")
            logger.info(f"Revoked oldest session for user {user_id} due to limit")
    
    def _deactivate_session(self, session_id: int, reason: str) -> bool:
        """Deactivate a session."""
        try:
            session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
            
            if not session:
                return False
            
            session.is_active = False
            session.revoked_at = datetime.utcnow()
            session.revocation_reason = reason
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to deactivate session {session_id}: {str(e)}")
            return False
