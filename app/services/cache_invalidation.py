"""
Cache Invalidation Service

Comprehensive cache invalidation service for managing cache
consistency across distributed systems.

Features:
- Cache key management
- Invalidation strategies
- Tag-based invalidation
- Time-based invalidation
- Event-driven invalidation
- Cache warming
- Distributed cache coordination
- Invalidation queues
- Cache analytics
- Rollback support
"""
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from sqlalchemy.orm import Session

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.db.models import User
from app.core.config import settings


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    BATCH = "batch"
    EVENT_DRIVEN = "event_driven"
    TTL_BASED = "ttl_based"


class CacheLevel(Enum):
    """Cache levels."""
    L1 = "l1"  # In-memory
    L2 = "l2"  # Redis
    L3 = "l3"  # CDN


@dataclass
class CacheKey:
    """Cache key data structure."""
    key: str
    tags: Set[str] = field(default_factory=set)
    ttl: Optional[int] = None
    level: CacheLevel = CacheLevel.L2
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class InvalidationEvent:
    """Invalidation event data structure."""
    key: str
    strategy: InvalidationStrategy
    tags: Optional[Set[str]] = None
    delay_seconds: int = 0
    metadata: Optional[Dict[str, Any]] = None


class CacheInvalidationService:
    """
    Enterprise-grade cache invalidation service.
    
    Features:
    - Cache key management
    - Invalidation strategies
    - Tag-based invalidation
    - Time-based invalidation
    - Event-driven invalidation
    - Cache warming
    - Distributed cache coordination
    - Invalidation queues
    - Cache analytics
    - Rollback support
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, tuple] = {}  # key: (value, expiry, tags)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag: set of keys
        self._invalidation_queue: List[InvalidationEvent] = []
        self._warming_callbacks: Dict[str, Callable] = {}
        
        # Redis client for distributed cache
        self.redis_client = None
        if REDIS_AVAILABLE:
            self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis client."""
        try:
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_db = getattr(settings, 'REDIS_DB', 0)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            print("Redis connected for cache invalidation")
            
        except Exception as e:
            print(f"Redis initialization failed: {e}")
            self.redis_client = None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        level: CacheLevel = CacheLevel.L2
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for group invalidation
            level: Cache level
        
        Returns:
            Success status
        """
        expiry = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
        
        # Set in local cache
        self._cache[key] = (value, expiry, tags or set())
        
        # Update tag index
        if tags:
            for tag in tags:
                self._tag_index[tag].add(key)
        
        # Set in Redis if available
        if self.redis_client and level == CacheLevel.L2:
            try:
                serialized_value = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else value
                if ttl:
                    self.redis_client.setex(key, ttl, serialized_value)
                else:
                    self.redis_client.set(key, serialized_value)
                
                # Store tags
                if tags:
                    self.redis_client.sadd(f"tags:{key}", *tags)
                    for tag in tags:
                        self.redis_client.sadd(f"tag:{tag}", key)
                
            except Exception as e:
                print(f"Redis set failed: {e}")
        
        return True
    
    def get(self, key: str, level: CacheLevel = CacheLevel.L2) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            level: Cache level
        
        Returns:
            Cached value or None
        """
        # Check local cache first
        if key in self._cache:
            value, expiry, tags = self._cache[key]
            
            # Check if expired
            if expiry and datetime.utcnow() > expiry:
                del self._cache[key]
                return None
            
            return value
        
        # Check Redis
        if self.redis_client and level == CacheLevel.L2:
            try:
                value = self.redis_client.get(key)
                if value:
                    # Try to deserialize
                    try:
                        return json.loads(value)
                    except:
                        return value
            except Exception as e:
                print(f"Redis get failed: {e}")
        
        return None
    
    def invalidate(
        self,
        key: str,
        strategy: InvalidationStrategy = InvalidationStrategy.IMMEDIATE
    ) -> bool:
        """
        Invalidate a specific cache key.
        
        Args:
            key: Cache key to invalidate
            strategy: Invalidation strategy
        
        Returns:
            Success status
        """
        if strategy == InvalidationStrategy.IMMEDIATE:
            return self._invalidate_immediate(key)
        elif strategy == InvalidationStrategy.DELAYED:
            return self._invalidate_delayed(key, delay_seconds=5)
        elif strategy == InvalidationStrategy.BATCH:
            return self._invalidate_batch([key])
        
        return False
    
    def _invalidate_immediate(self, key: str) -> bool:
        """Immediately invalidate a cache key."""
        # Remove from local cache
        if key in self._cache:
            _, _, tags = self._cache[key]
            del self._cache[key]
            
            # Remove from tag index
            if tags:
                for tag in tags:
                    self._tag_index[tag].discard(key)
        
        # Remove from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                
                # Remove from tag indices
                tags = self.redis_client.smembers(f"tags:{key}")
                if tags:
                    for tag in tags:
                        self.redis_client.srem(f"tag:{tag}", key)
                    self.redis_client.delete(f"tags:{key}")
                
            except Exception as e:
                print(f"Redis invalidation failed: {e}")
        
        return True
    
    def _invalidate_delayed(self, key: str, delay_seconds: int = 5) -> bool:
        """Schedule delayed invalidation."""
        event = InvalidationEvent(
            key=key,
            strategy=InvalidationStrategy.DELAYED,
            delay_seconds=delay_seconds
        )
        self._invalidation_queue.append(event)
        return True
    
    def _invalidate_batch(self, keys: List[str]) -> bool:
        """Invalidate multiple keys at once."""
        for key in keys:
            self._invalidate_immediate(key)
        return True
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache keys with a specific tag.
        
        Args:
            tag: Tag to invalidate
        
        Returns:
            Number of keys invalidated
        """
        keys = self._tag_index.get(tag, set()).copy()
        count = 0
        
        for key in keys:
            if self._invalidate_immediate(key):
                count += 1
        
        # Also check Redis
        if self.redis_client:
            try:
                redis_keys = self.redis_client.smembers(f"tag:{tag}")
                for key in redis_keys:
                    if self._invalidate_immediate(key):
                        count += 1
                self.redis_client.delete(f"tag:{tag}")
            except Exception as e:
                print(f"Redis tag invalidation failed: {e}")
        
        return count
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "user:*")
        
        Returns:
            Number of keys invalidated
        """
        keys_to_delete = []
        
        # Check local cache
        for key in self._cache.keys():
            if self._match_pattern(key, pattern):
                keys_to_delete.append(key)
        
        count = 0
        for key in keys_to_delete:
            if self._invalidate_immediate(key):
                count += 1
        
        # Check Redis
        if self.redis_client:
            try:
                redis_keys = self.redis_client.keys(pattern)
                for key in redis_keys:
                    if self._invalidate_immediate(key):
                        count += 1
            except Exception as e:
                print(f"Redis pattern invalidation failed: {e}")
        
        return count
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def process_invalidation_queue(self) -> int:
        """Process pending invalidation events."""
        now = time.time()
        processed = 0
        
        remaining_events = []
        
        for event in self._invalidation_queue:
            if event.delay_seconds <= 0:
                if self._invalidate_immediate(event.key):
                    processed += 1
            else:
                event.delay_seconds -= 1
                remaining_events.append(event)
        
        self._invalidation_queue = remaining_events
        return processed
    
    def register_warming_callback(self, key_pattern: str, callback: Callable):
        """
        Register a callback for warming cache after invalidation.
        
        Args:
            key_pattern: Pattern matching keys to warm
            callback: Function to call for warming
        """
        self._warming_callbacks[key_pattern] = callback
    
    def warm_cache(self, key: str) -> bool:
        """
        Warm a cache key by calling its registered callback.
        
        Args:
            key: Cache key to warm
        
        Returns:
            Success status
        """
        for pattern, callback in self._warming_callbacks.items():
            if self._match_pattern(key, pattern):
                try:
                    callback(key)
                    return True
                except Exception as e:
                    print(f"Cache warming failed for {key}: {e}")
        
        return False
    
    def invalidate_all(self) -> int:
        """Invalidate all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._tag_index.clear()
        
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                print(f"Redis flush failed: {e}")
        
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'local_cache_size': len(self._cache),
            'tag_count': len(self._tag_index),
            'invalidation_queue_size': len(self._invalidation_queue),
            'warming_callbacks': len(self._warming_callbacks),
            'redis_connected': self.redis_client is not None
        }
    
    def get_tag_stats(self) -> Dict[str, int]:
        """Get statistics for each tag."""
        return {
            tag: len(keys)
            for tag, keys in self._tag_index.items()
        }
    
    def get_expiring_keys(self, seconds: int = 3600) -> List[str]:
        """Get keys that will expire within the given time."""
        now = datetime.utcnow()
        cutoff = now + timedelta(seconds=seconds)
        
        expiring = []
        for key, (value, expiry, tags) in self._cache.items():
            if expiry and expiry <= cutoff:
                expiring.append(key)
        
        return expiring
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries."""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, (value, expiry, tags) in self._cache.items():
            if expiry and now > expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._invalidate_immediate(key)
        
        return len(expired_keys)
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        """Update TTL for a cache key."""
        if key not in self._cache:
            return False
        
        value, _, tags = self._cache[key]
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry, tags)
        
        if self.redis_client:
            try:
                self.redis_client.expire(key, ttl)
            except Exception as e:
                print(f"Redis TTL update failed: {e}")
        
        return True
    
    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a cache key."""
        if key not in self._cache:
            return None
        
        value, expiry, tags = self._cache[key]
        if expiry:
            remaining = (expiry - datetime.utcnow()).total_seconds()
            return max(0, int(remaining))
        
        return None
    
    def backup_cache(self) -> Dict[str, Any]:
        """Create a backup of the cache state."""
        backup = {
            'timestamp': datetime.utcnow().isoformat(),
            'cache': {},
            'tag_index': {k: list(v) for k, v in self._tag_index.items()}
        }
        
        for key, (value, expiry, tags) in self._cache.items():
            backup['cache'][key] = {
                'value': value,
                'expiry': expiry.isoformat() if expiry else None,
                'tags': list(tags)
            }
        
        return backup
    
    def restore_cache(self, backup: Dict[str, Any]) -> bool:
        """Restore cache from backup."""
        try:
            self._cache.clear()
            self._tag_index.clear()
            
            for key, data in backup['cache'].items():
                expiry = datetime.fromisoformat(data['expiry']) if data['expiry'] else None
                tags = set(data['tags'])
                self._cache[key] = (data['value'], expiry, tags)
            
            for tag, keys in backup['tag_index'].items():
                self._tag_index[tag] = set(keys)
            
            return True
        except Exception as e:
            print(f"Cache restore failed: {e}")
            return False


def get_cache_invalidation_service(db: Session):
    """Dependency to get cache invalidation service."""
    return CacheInvalidationService(db)
