"""
Enterprise user session management service with Redis integration.

Provides comprehensive session management with support for:
- Redis-based session storage
- Session persistence and recovery
- Concurrent session handling
- Session security and validation
- Session analytics and monitoring
- Automatic session cleanup
- Cross-device session management
- Session revocation and blacklisting
- Session-based rate limiting
"""

import json
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import redis
import structlog
import secrets

from app.core.config import settings
from app.core.exceptions import SessionError

logger = structlog.get_logger()


class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class SessionType(Enum):
    """Session type enumeration."""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    DESKTOP = "desktop"


@dataclass
class SessionData:
    """Session data structure."""
    session_id: str
    user_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    last_activity: datetime = field(default_factory=lambda: datetime.utcnow())
    expires_at: Optional[datetime] = None
    status: SessionStatus = SessionStatus.ACTIVE
    session_type: SessionType = SessionType.WEB
    metadata: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    rate_limit_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "session_type": self.session_type.value,
            "metadata": self.metadata,
            "permissions": self.permissions,
            "rate_limit_data": self.rate_limit_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary from Redis."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            device_id=data.get("device_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=SessionStatus(data["status"]),
            session_type=SessionType(data.get("session_type", SessionType.WEB.value)),
            metadata=data.get("metadata", {}),
            permissions=data.get("permissions", []),
            rate_limit_data=data.get("rate_limit_data", {})
        )


@dataclass
class SessionConfig:
    """Session configuration."""
    default_ttl: int = 3600  # 1 hour
    max_ttl: int = 86400  # 24 hours
    max_sessions_per_user: int = 10
    cleanup_interval: int = 300  # 5 minutes
    session_prefix: str = "session:"
    user_sessions_prefix: str = "user_sessions:"
    revoked_prefix: str = "revoked:"
    rate_limit_prefix: str = "rate_limit:"
    enable_persistence: bool = True
    enable_concurrent_sessions: bool = True
    enable_device_tracking: bool = True


class SessionManagementService:
    """
    Enterprise session management service with Redis backend.
    
    Features:
    - Redis-based session storage with TTL
    - Session persistence and recovery
    - Concurrent session handling
    - Session security and validation
    - Session analytics and monitoring
    - Automatic session cleanup
    - Cross-device session management
    - Session revocation and blacklisting
    - Session-based rate limiting
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.redis = redis_client or self._create_redis_client()
        self._lock = threading.RLock()
        
        # Metrics
        self.metrics = {
            "sessions_created": 0,
            "sessions_validated": 0,
            "sessions_revoked": 0,
            "sessions_expired": 0,
            "cleanup_runs": 0,
            "validation_errors": 0,
            "concurrent_violations": 0,
            "security_violations": 0
        }
        
        # Start background cleanup
        self._start_cleanup_thread()
    
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with configuration."""
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""
        def cleanup_expired_sessions():
            while True:
                try:
                    self.cleanup_expired_sessions()
                    time.sleep(self.config.cleanup_interval)
                except Exception as e:
                    logger.error(f"Error in session cleanup: {str(e)}")
                    time.sleep(60)  # Wait 1 minute on error
        
        cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
        cleanup_thread.start()
        logger.info("Session cleanup thread started")
    
    def create_session(
        self,
        user_id: str,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_type: SessionType = SessionType.WEB,
        ttl: Optional[int] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User identifier
            device_id: Device identifier
            ip_address: Client IP address
            user_agent: User agent string
            session_type: Type of session
            ttl: Session TTL in seconds
            permissions: User permissions for this session
            metadata: Additional session metadata
            
        Returns:
            Session ID
        """
        try:
            # Check concurrent session limit
            if self.config.enable_concurrent_sessions:
                active_sessions = self.get_user_sessions(user_id, active_only=True)
                if len(active_sessions) >= self.config.max_sessions_per_user:
                    # Revoke oldest session
                    oldest_session = min(active_sessions, key=lambda s: s.last_activity)
                    self.revoke_session(oldest_session.session_id, "Concurrent session limit exceeded")
                    with self._lock:
                        self.metrics["concurrent_violations"] += 1
            
            # Generate session ID
            session_id = self._generate_session_id()
            
            # Calculate expiration
            session_ttl = min(ttl or self.config.default_ttl, self.config.max_ttl)
            expires_at = datetime.utcnow() + timedelta(seconds=session_ttl)
            
            # Create session data
            session_data = SessionData(
                session_id=session_id,
                user_id=user_id,
                device_id=device_id if self.config.enable_device_tracking else None,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
                session_type=session_type,
                permissions=permissions or [],
                metadata=metadata or {}
            )
            
            # Store in Redis
            session_key = f"{self.config.session_prefix}{session_id}"
            user_sessions_key = f"{self.config.user_sessions_prefix}{user_id}"
            
            with self.redis.pipeline() as pipe:
                # Store session data
                pipe.setex(
                    session_key,
                    session_ttl,
                    json.dumps(session_data.to_dict())
                )
                
                # Add to user's session list
                pipe.sadd(user_sessions_key, session_id)
                pipe.expire(user_sessions_key, session_ttl)
                
                pipe.execute()
            
            with self._lock:
                self.metrics["sessions_created"] += 1
            
            logger.info(
                f"Session created: {session_id}",
                user_id=user_id,
                session_type=session_type.value,
                ttl=session_ttl
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise SessionError(f"Failed to create session: {str(e)}")
    
    def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[SessionData]:
        """
        Validate and retrieve session data.
        
        Args:
            session_id: Session ID to validate
            ip_address: Current IP address for security check
            user_agent: Current user agent for security check
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            # Check if session is revoked
            if self.is_session_revoked(session_id):
                with self._lock:
                    self.metrics["security_violations"] += 1
                return None
            
            # Get session from Redis
            session_key = f"{self.config.session_prefix}{session_id}"
            session_json = self.redis.get(session_key)
            
            if not session_json:
                with self._lock:
                    self.metrics["validation_errors"] += 1
                return None
            
            session_data = SessionData.from_dict(json.loads(session_json))
            
            # Check session status
            if session_data.status != SessionStatus.ACTIVE:
                with self._lock:
                    self.metrics["validation_errors"] += 1
                return None
            
            # Check expiration
            if session_data.expires_at and datetime.utcnow() > session_data.expires_at:
                self.revoke_session(session_id, "Session expired")
                with self._lock:
                    self.metrics["sessions_expired"] += 1
                return None
            
            # Security checks
            if ip_address and session_data.ip_address and ip_address != session_data.ip_address:
                # Log potential session hijacking
                logger.warning(
                    f"IP address mismatch for session {session_id}",
                    expected_ip=session_data.ip_address,
                    actual_ip=ip_address
                )
                with self._lock:
                    self.metrics["security_violations"] += 1
                
                # Optionally revoke session for security
                # self.revoke_session(session_id, "IP address mismatch")
                # return None
            
            # Update last activity
            session_data.last_activity = datetime.utcnow()
            
            # Update in Redis with extended TTL
            remaining_ttl = self._calculate_remaining_ttl(session_data)
            if remaining_ttl > 0:
                self.redis.setex(
                    session_key,
                    remaining_ttl,
                    json.dumps(session_data.to_dict())
                )
            
            with self._lock:
                self.metrics["sessions_validated"] += 1
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {str(e)}")
            with self._lock:
                self.metrics["validation_errors"] += 1
            return None
    
    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session ID to update
            updates: Fields to update
            
        Returns:
            Success status
        """
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(session_data, key):
                    setattr(session_data, key, value)
            
            # Update in Redis
            session_key = f"{self.config.session_prefix}{session_id}"
            remaining_ttl = self._calculate_remaining_ttl(session_data)
            
            if remaining_ttl > 0:
                self.redis.setex(
                    session_key,
                    remaining_ttl,
                    json.dumps(session_data.to_dict())
                )
            
            logger.info(f"Session updated: {session_id}", updates=updates.keys())
            return True
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {str(e)}")
            return False
    
    def revoke_session(
        self,
        session_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Revoke a session.
        
        Args:
            session_id: Session ID to revoke
            reason: Reason for revocation
            
        Returns:
            Success status
        """
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            # Mark as revoked
            session_data.status = SessionStatus.REVOKED
            session_data.metadata["revoked_at"] = datetime.utcnow().isoformat()
            session_data.metadata["revocation_reason"] = reason
            
            # Add to revoked list
            revoked_key = f"{self.config.revoked_prefix}{session_id}"
            self.redis.setex(revoked_key, 86400, json.dumps({
                "session_id": session_id,
                "revoked_at": session_data.metadata["revoked_at"],
                "reason": reason
            }))
            
            # Remove from active sessions
            session_key = f"{self.config.session_prefix}{session_id}"
            user_sessions_key = f"{self.config.user_sessions_prefix}{session_data.user_id}"
            
            with self.redis.pipeline() as pipe:
                pipe.delete(session_key)
                pipe.srem(user_sessions_key, session_id)
                pipe.execute()
            
            with self._lock:
                self.metrics["sessions_revoked"] += 1
            
            logger.info(
                f"Session revoked: {session_id}",
                user_id=session_data.user_id,
                reason=reason
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking session {session_id}: {str(e)}")
            return False
    
    def revoke_user_sessions(
        self,
        user_id: str,
        reason: Optional[str] = None,
        exclude_session_id: Optional[str] = None
    ) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            exclude_session_id: Session ID to exclude (current session)
            
        Returns:
            Number of sessions revoked
        """
        try:
            sessions = self.get_user_sessions(user_id)
            revoked_count = 0
            
            for session in sessions:
                if exclude_session_id and session.session_id == exclude_session_id:
                    continue
                
                if self.revoke_session(session.session_id, reason):
                    revoked_count += 1
            
            logger.info(
                f"Revoked {revoked_count} sessions for user: {user_id}",
                reason=reason
            )
            
            return revoked_count
            
        except Exception as e:
            logger.error(f"Error revoking user sessions: {str(e)}")
            return 0
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data without validation."""
        try:
            session_key = f"{self.config.session_prefix}{session_id}"
            session_json = self.redis.get(session_key)
            
            if not session_json:
                return None
            
            return SessionData.from_dict(json.loads(session_json))
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {str(e)}")
            return None
    
    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        session_type: Optional[SessionType] = None
    ) -> List[SessionData]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            session_type: Filter by session type
            
        Returns:
            List of session data
        """
        try:
            user_sessions_key = f"{self.config.user_sessions_prefix}{user_id}"
            session_ids = self.redis.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_data = self.get_session(session_id)
                if session_data:
                    if active_only and session_data.status != SessionStatus.ACTIVE:
                        continue
                    
                    if session_type and session_data.session_type != session_type:
                        continue
                    
                    sessions.append(session_data)
            
            # Sort by last activity (newest first)
            sessions.sort(key=lambda s: s.last_activity, reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def is_session_revoked(self, session_id: str) -> bool:
        """Check if a session is revoked."""
        try:
            revoked_key = f"{self.config.revoked_prefix}{session_id}"
            return self.redis.exists(revoked_key)
        except Exception as e:
            logger.error(f"Error checking revoked session: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            cleaned_count = 0
            
            # Get all session keys
            session_keys = self.redis.keys(f"{self.config.session_prefix}*")
            
            for session_key in session_keys:
                try:
                    session_json = self.redis.get(session_key)
                    if not session_json:
                        continue
                    
                    session_data = SessionData.from_dict(json.loads(session_json))
                    
                    # Check if expired
                    if (session_data.expires_at and 
                        datetime.utcnow() > session_data.expires_at):
                        
                        session_id = session_key.replace(self.config.session_prefix, "")
                        self.revoke_session(session_id, "Session expired")
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing session {session_key}: {str(e)}")
            
            with self._lock:
                self.metrics["cleanup_runs"] += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error in session cleanup: {str(e)}")
            return 0
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _calculate_remaining_ttl(self, session_data: SessionData) -> int:
        """Calculate remaining TTL for session."""
        if not session_data.expires_at:
            return self.config.default_ttl
        
        remaining_time = session_data.expires_at - datetime.utcnow()
        return max(0, int(remaining_time.total_seconds()))
    
    def get_session_analytics(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get session analytics.
        
        Args:
            user_id: Filter by user ID
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            Analytics data
        """
        try:
            # Get all session keys
            session_keys = self.redis.keys(f"{self.config.session_prefix}*")
            
            total_sessions = 0
            active_sessions = 0
            expired_sessions = 0
            revoked_sessions = 0
            sessions_by_type = defaultdict(int)
            sessions_by_user = defaultdict(int)
            
            for session_key in session_keys:
                try:
                    session_json = self.redis.get(session_key)
                    if not session_json:
                        continue
                    
                    session_data = SessionData.from_dict(json.loads(session_json))
                    
                    # Apply filters
                    if user_id and session_data.user_id != user_id:
                        continue
                    
                    if start_time and session_data.created_at < start_time:
                        continue
                    
                    if end_time and session_data.created_at > end_time:
                        continue
                    
                    total_sessions += 1
                    sessions_by_type[session_data.session_type.value] += 1
                    sessions_by_user[session_data.user_id] += 1
                    
                    # Status analysis
                    if session_data.status == SessionStatus.ACTIVE:
                        if session_data.expires_at and datetime.utcnow() > session_data.expires_at:
                            expired_sessions += 1
                        else:
                            active_sessions += 1
                    elif session_data.status == SessionStatus.REVOKED:
                        revoked_sessions += 1
                    elif session_data.status == SessionStatus.EXPIRED:
                        expired_sessions += 1
                        
                except Exception as e:
                    logger.error(f"Error analyzing session {session_key}: {str(e)}")
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "revoked_sessions": revoked_sessions,
                "sessions_by_type": dict(sessions_by_type),
                "sessions_by_user": dict(sessions_by_user),
                "unique_users": len(sessions_by_user),
                "average_sessions_per_user": total_sessions / max(len(sessions_by_user), 1),
                "metrics": self.metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting session analytics: {str(e)}")
            return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get session management metrics."""
        with self._lock:
            return dict(self.metrics)
    
    def export_sessions(
        self,
        user_id: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """Export session data."""
        try:
            sessions = []
            
            if user_id:
                sessions = self.get_user_sessions(user_id)
            else:
                # Get all sessions
                session_keys = self.redis.keys(f"{self.config.session_prefix}*")
                for session_key in session_keys:
                    session_data = self.get_session(
                        session_key.replace(self.config.session_prefix, "")
                    )
                    if session_data:
                        sessions.append(session_data)
            
            if format == "json":
                return json.dumps([session.to_dict() for session in sessions], indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting sessions: {str(e)}")
            raise SessionError(f"Failed to export sessions: {str(e)}")


# Global session management service instance
session_management_service = SessionManagementService()


def create_user_session(
    user_id: str,
    device_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_type: SessionType = SessionType.WEB,
    ttl: Optional[int] = None,
    permissions: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new user session."""
    return session_management_service.create_session(
        user_id=user_id,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=user_agent,
        session_type=session_type,
        ttl=ttl,
        permissions=permissions,
        metadata=metadata
    )


def validate_user_session(
    session_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[SessionData]:
    """Validate and retrieve user session."""
    return session_management_service.validate_session(
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent
    )


def revoke_user_session(
    session_id: str,
    reason: Optional[str] = None
) -> bool:
    """Revoke a user session."""
    return session_management_service.revoke_session(
        session_id=session_id,
        reason=reason
    )


def get_user_sessions(
    user_id: str,
    active_only: bool = False,
    session_type: Optional[SessionType] = None
) -> List[SessionData]:
    """Get all sessions for a user."""
    return session_management_service.get_user_sessions(
        user_id=user_id,
        active_only=active_only,
        session_type=session_type
    )


def get_session_analytics(
    user_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get session analytics."""
    return session_management_service.get_session_analytics(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time
    )


def get_session_metrics() -> Dict[str, Any]:
    """Get session management metrics."""
    return session_management_service.get_metrics()
