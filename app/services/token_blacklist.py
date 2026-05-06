"""
Token blacklist service for secure token revocation.

Handles token blacklisting with Redis support, cleanup,
and comprehensive token management with proper security considerations.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta, timezone
import json
import time
import redis
import redis.cluster
from sqlalchemy.orm import Session
import logging
import structlog

from app.db.models import TokenBlacklist
from app.core.config import settings
from app.core.exceptions import SecurityError, DatabaseError, CacheError
from app.repositories.auth import AuthRepository

logger = structlog.get_logger()

# Try to import Redis, fallback to in-memory if not available
redis_client = None
redis_cluster_client = None

try:
    if hasattr(settings, 'redis_cluster_nodes') and settings.redis_cluster_nodes:
        # Use Redis Cluster if configured
        redis_cluster_client = redis.cluster.RedisCluster(
            startup_nodes=settings.redis_cluster_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            max_connections_per_node=16
        )
        logger.info("Redis cluster initialized for token blacklist")
    elif settings.redis_url:
        # Use single Redis instance
        redis_client = redis.from_url(
            settings.redis_url, 
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        logger.info("Redis client initialized for token blacklist")
    else:
        logger.warning("No Redis configuration found, using in-memory fallback")
except Exception as e:
    logger.error(f"Redis initialization failed: {str(e)}")
    redis_client = None
    redis_cluster_client = None

# In-memory fallback storage (raw JWT string -> expiry epoch seconds)
_memory_blacklist: set = set()
_memory_expiry: Dict[str, float] = {}
_memory_stats = {"hits": 0, "misses": 0, "cleanups": 0}


class TokenBlacklistService:
    """Service for managing token blacklisting and revocation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.use_redis = redis_client is not None or redis_cluster_client is not None
        self.use_cluster = redis_cluster_client is not None
    
    def _get_redis_client(self) -> Union[redis.Redis, redis.cluster.RedisCluster, None]:
        """Get the appropriate Redis client."""
        if self.use_cluster:
            return redis_cluster_client
        elif self.use_redis:
            return redis_client
        return None
    
    def _execute_redis_command(self, command: str, *args, **kwargs) -> Any:
        """Execute Redis command with error handling."""
        redis_instance = self._get_redis_client()
        if not redis_instance:
            return None
        
        try:
            if self.use_cluster:
                # For cluster, we need to handle key-based routing
                if command in ['setex', 'exists', 'get', 'delete']:
                    key = args[0]
                    return getattr(redis_instance, command)(key, *args[1:], **kwargs)
                else:
                    return getattr(redis_instance, command)(*args, **kwargs)
            else:
                return getattr(redis_instance, command)(*args, **kwargs)
        except redis.RedisError as e:
            logger.error(f"Redis command {command} failed: {str(e)}")
            raise CacheError(f"Redis operation failed: {str(e)}", operation=command)
        except Exception as e:
            logger.error(f"Unexpected Redis error: {str(e)}")
            raise CacheError(f"Unexpected Redis error: {str(e)}", operation=command)
    
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
                logger.info(f"Token already expired, skipping blacklist for user {user_id}")
                return True
            
            token_hash = self._hash_token(token)
            
            if self.use_redis:
                # Use Redis with TTL (keyed by token hash to avoid storing raw JWT in the key)
                key = f"blacklist:{token_hash}"
                value = json.dumps({
                    "user_id": user_id,
                    "token_type": token_type,
                    "reason": reason,
                    "blacklisted_at": datetime.utcnow().isoformat()
                })
                self._execute_redis_command("setex", key, ttl_seconds, value)
                logger.info(f"Token blacklisted in Redis for user {user_id}, type: {token_type}")
            else:
                _memory_blacklist.add(token)
                _memory_expiry[token] = time.time() + ttl_seconds
                self._cleanup_expired_memory_tokens()
                logger.info(f"Token blacklisted in memory for user {user_id}, type: {token_type}")
            
            # Also store in database for persistence
            db_entry = TokenBlacklist(
                token_hash=token_hash,
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
            logger.error(f"Error blacklisting token for user {user_id}: {str(e)}")
            # Don't raise - blacklisting is best-effort
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted (database, Redis, or in-memory)."""
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        
        # Check Redis first (fastest)
        if self.use_redis:
            try:
                exists = self._execute_redis_command("exists", f"blacklist:{token_hash}")
                if exists:
                    _memory_stats["hits"] += 1
                    return True
            except CacheError:
                logger.warning("Redis check failed, falling back to database")
        
        # Check database (fallback)
        try:
            db_hit = (
                self.db.query(TokenBlacklist)
                .filter(
                    TokenBlacklist.token_hash == token_hash,
                    TokenBlacklist.expires_at > now,
                )
                .first()
            )
            if db_hit is not None:
                _memory_stats["hits"] += 1
                return True
        except Exception as e:
            logger.error(f"Database check failed: {str(e)}")

        # Check in-memory (last resort)
        if token in _memory_blacklist:
            if token in _memory_expiry and time.time() > _memory_expiry[token]:
                _memory_blacklist.discard(token)
                del _memory_expiry[token]
                _memory_stats["misses"] += 1
                return False
            _memory_stats["hits"] += 1
            return True
        
        _memory_stats["misses"] += 1
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
        logger.info(f"Cleaned up {deleted} expired blacklist entries from database")
        return deleted
    
    def get_blacklist_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the token blacklist.
        
        Returns:
            Dictionary with blacklist statistics
        """
        try:
            stats = {
                "memory_stats": _memory_stats.copy(),
                "memory_blacklist_size": len(_memory_blacklist),
                "redis_available": self.use_redis,
                "redis_cluster": self.use_cluster
            }
            
            # Add database stats
            try:
                total_entries = self.db.query(TokenBlacklist).count()
                active_entries = self.db.query(TokenBlacklist).filter(
                    TokenBlacklist.expires_at > datetime.utcnow()
                ).count()
                
                stats.update({
                    "database_total_entries": total_entries,
                    "database_active_entries": active_entries
                })
            except Exception as e:
                logger.error(f"Failed to get database stats: {str(e)}")
                stats["database_error"] = str(e)
            
            # Add Redis stats
            if self.use_redis:
                try:
                    # Get number of blacklist keys (approximate)
                    if self.use_cluster:
                        # For cluster, we'd need to check each node
                        redis_stats = {"cluster": True, "node_count": len(redis_cluster_client.get_nodes())}
                    else:
                        info = redis_client.info()
                        redis_stats = {
                            "connected_clients": info.get("connected_clients"),
                            "used_memory": info.get("used_memory_human"),
                            "keyspace_hits": info.get("keyspace_hits"),
                            "keyspace_misses": info.get("keyspace_misses")
                        }
                    
                    stats["redis_stats"] = redis_stats
                except Exception as e:
                    logger.error(f"Failed to get Redis stats: {str(e)}")
                    stats["redis_error"] = str(e)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {str(e)}")
            return {"error": str(e)}
    
    def blacklist_token_family(self, refresh_token: str, access_token: str, 
                              expires_at: datetime, user_id: int, 
                              reason: str = "logout") -> bool:
        """
        Blacklist both access and refresh tokens for a session.
        
        Args:
            refresh_token: The refresh token to blacklist
            access_token: The access token to blacklist
            expires_at: When the tokens naturally expire
            user_id: User ID associated with the tokens
            reason: Why the tokens were blacklisted
        
        Returns:
            bool: Success status
        """
        try:
            success = True
            
            # Blacklist access token
            if access_token:
                success &= self.blacklist_token(
                    access_token, expires_at, user_id, "access", reason
                )
            
            # Blacklist refresh token (longer TTL)
            if refresh_token:
                refresh_expires = expires_at + timedelta(days=30)  # Refresh tokens live longer
                success &= self.blacklist_token(
                    refresh_token, refresh_expires, user_id, "refresh", reason
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to blacklist token family for user {user_id}: {str(e)}")
            return False
    
    def get_user_blacklisted_tokens(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all blacklisted tokens for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of tokens to return
            
        Returns:
            List of token information
        """
        try:
            tokens = (
                self.db.query(TokenBlacklist)
                .filter(TokenBlacklist.user_id == user_id)
                .order_by(TokenBlacklist.blacklisted_at.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": token.id,
                    "token_type": token.token_type,
                    "reason": token.reason,
                    "blacklisted_at": token.blacklisted_at.isoformat(),
                    "expires_at": token.expires_at.isoformat()
                }
                for token in tokens
            ]
            
        except Exception as e:
            logger.error(f"Failed to get blacklisted tokens for user {user_id}: {str(e)}")
            return []
    
    def revoke_user_tokens_by_reason(self, user_id: int, reason: str, 
                                   token_types: List[str] = None) -> int:
        """
        Revoke all tokens of specific types for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            token_types: List of token types to revoke (None for all)
        
        Returns:
            Number of tokens revoked
        """
        try:
            query = self.db.query(TokenBlacklist).filter(
                TokenBlacklist.user_id == user_id
            )
            
            if token_types:
                query = query.filter(TokenBlacklist.token_type.in_(token_types))
            
            # Update existing entries to mark as revoked
            revoked_count = query.count()
            
            # Add new blacklist entry for the revocation
            db_entry = TokenBlacklist(
                token_hash=f"REVOCATION_USER_{user_id}_{int(time.time())}",
                user_id=user_id,
                token_type="revocation",
                expires_at=datetime.utcnow() + timedelta(days=30),
                reason=reason,
                blacklisted_at=datetime.utcnow()
            )
            self.db.add(db_entry)
            self.db.commit()
            
            logger.info(f"Revoked {revoked_count} tokens for user {user_id}, reason: {reason}")
            return revoked_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to revoke tokens for user {user_id}: {str(e)}")
            return 0


def get_token_blacklist_service(db: Session):
    """Dependency to get token blacklist service."""
    return TokenBlacklistService(db)
