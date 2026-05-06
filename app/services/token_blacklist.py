"""
Token blacklist service for secure token revocation.

Handles token blacklisting with Redis support, cleanup,
and comprehensive token management with proper security considerations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import json
import time
import redis
from sqlalchemy.orm import Session

from app.db.models import TokenBlacklist
from app.core.config import settings
from app.core.exceptions import SecurityError, DatabaseError
from app.repositories.auth import AuthRepository

# Try to import Redis, fallback to in-memory if not available
try:
    redis_client = (
        redis.from_url(settings.redis_url, decode_responses=True)
        if settings.redis_url
        else None
    )
except Exception:
    redis_client = None

# In-memory fallback storage (raw JWT string -> expiry epoch seconds)
_memory_blacklist: set = set()
_memory_expiry: Dict[str, float] = {}


class TokenBlacklistService:
    """Service for managing token blacklisting and revocation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.use_redis = redis_client is not None
    
    def blacklist_token(self, token: str, expires_at: datetime, user_id: int, 
                       token_type: str = "access", reason: str = "logout") -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token: The JWT token to blacklist
            expires_at: When the token naturally expires
            user_id: User ID associated with the token
            token_type: Type of token (access, refresh)
            reason: Why the token was blacklisted
        
        Returns:
            bool: Success status
        """
        try:
            # Calculate TTL in seconds
            ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
            if ttl_seconds <= 0:
                # Token already expired, no need to blacklist
                return True
            
            if self.use_redis:
                # Use Redis with TTL (keyed by token hash to avoid storing raw JWT in the key)
                key = f"blacklist:{self._hash_token(token)}"
                redis_client.setex(key, ttl_seconds, f"{user_id}:{token_type}:{reason}")
            else:
                _memory_blacklist.add(token)
                _memory_expiry[token] = time.time() + ttl_seconds
                self._cleanup_expired_memory_tokens()
            
            # Also store in database for persistence
            db_entry = TokenBlacklist(
                token_hash=self._hash_token(token),
                user_id=user_id,
                token_type=token_type,
                expires_at=expires_at,
                reason=reason,
                blacklisted_at=datetime.utcnow()
            )
            self.db.add(db_entry)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            # Log error but don't raise - blacklisting is best-effort
            print(f"Error blacklisting token: {e}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted (database, Redis, or in-memory)."""
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        db_hit = (
            self.db.query(TokenBlacklist)
            .filter(
                TokenBlacklist.token_hash == token_hash,
                TokenBlacklist.expires_at > now,
            )
            .first()
        )
        if db_hit is not None:
            return True

        if self.use_redis:
            return bool(redis_client.exists(f"blacklist:{token_hash}"))

        if token in _memory_blacklist:
            if token in _memory_expiry and time.time() > _memory_expiry[token]:
                _memory_blacklist.discard(token)
                del _memory_expiry[token]
                return False
            return True
        return False
    
    def blacklist_all_user_tokens(self, user_id: int, reason: str = "logout_all") -> int:
        """
        Blacklist all tokens for a user (force logout from all devices).
        
        Returns:
            int: Number of sessions invalidated
        """
        # This would typically interact with a session store
        # For now, we mark all tokens for this user as invalid
        # In production, this would use Redis to track user sessions
        
        if self.use_redis:
            # Store a marker that all tokens before this timestamp are invalid
            key = f"user:{user_id}:token_version"
            redis_client.set(key, str(int(time.time())))
        
        # Log in database
        db_entry = TokenBlacklist(
            token_hash=f"ALL_TOKENS_USER_{user_id}",
            user_id=user_id,
            token_type="all",
            expires_at=datetime.utcnow() + timedelta(days=30),
            reason=reason,
            blacklisted_at=datetime.utcnow()
        )
        self.db.add(db_entry)
        self.db.commit()
        
        return 1  # Simplified - would return actual session count in full implementation
    
    def get_user_token_version(self, user_id: int) -> Optional[int]:
        """Get the current token version for a user."""
        if self.use_redis:
            version = redis_client.get(f"user:{user_id}:token_version")
            return int(version) if version else None
        return None
    
    def verify_token_version(self, user_id: int, token_version: int) -> bool:
        """Verify if a token's version is still valid."""
        current_version = self.get_user_token_version(user_id)
        if current_version is None:
            return True  # No version check needed
        return token_version >= current_version
    
    def _hash_token(self, token: str) -> str:
        """Create a hash of the token for storage (don't store full tokens)."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:32]
    
    def _cleanup_expired_memory_tokens(self):
        """Clean up expired tokens from memory storage."""
        now = time.time()
        expired = [t for t, exp in _memory_expiry.items() if now > exp]
        for token in expired:
            _memory_blacklist.discard(token)
            del _memory_expiry[token]
    
    def cleanup_database_blacklist(self, days_to_keep: int = 7) -> int:
        """
        Remove old blacklist entries from database.
        Should be run periodically (e.g., via cron job).
        
        Returns:
            int: Number of entries removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted = self.db.query(TokenBlacklist).filter(
            TokenBlacklist.expires_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted


def get_token_blacklist_service(db: Session):
    """Dependency to get token blacklist service."""
    return TokenBlacklistService(db)
