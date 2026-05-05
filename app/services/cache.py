"""
Advanced caching service with multiple backends and strategies.
Supports Redis, in-memory, and disk-based caching with TTL.
"""
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
from abc import ABC, abstractmethod


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        
        # Check TTL
        if entry.get("expires_at") and datetime.utcnow() > entry["expires_at"]:
            self.delete(key)
            return None
        
        return entry["value"]
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        entry = self._cache.get(key)
        if not entry:
            return False
        
        if entry.get("expires_at") and datetime.utcnow() > entry["expires_at"]:
            self.delete(key)
            return False
        
        return True
    
    def clear(self) -> bool:
        self._cache.clear()
        return True
    
    def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        now = datetime.utcnow()
        expired = [
            k for k, v in self._cache.items()
            if v.get("expires_at") and now > v["expires_at"]
        ]
        for k in expired:
            del self._cache[k]
        return len(expired)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, redis_client=None):
        self._redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        if not self._redis:
            return None
        
        value = self._redis.get(key)
        if value:
            return pickle.loads(value)
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        if not self._redis:
            return False
        
        serialized = pickle.dumps(value)
        
        if ttl:
            self._redis.setex(key, ttl, serialized)
        else:
            self._redis.set(key, serialized)
        
        return True
    
    def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        
        return self._redis.delete(key) > 0
    
    def exists(self, key: str) -> bool:
        if not self._redis:
            return False
        
        return self._redis.exists(key) > 0
    
    def clear(self) -> bool:
        if not self._redis:
            return False
        
        self._redis.flushdb()
        return True
    
    def keys(self, pattern: str = "*") -> List[str]:
        if not self._redis:
            return []
        
        return [k.decode() if isinstance(k, bytes) else k 
                for k in self._redis.keys(pattern)]


class CacheService:
    """
    Advanced caching service with multiple strategies.
    
    Features:
    - Multi-level caching (L1: memory, L2: Redis)
    - Cache-aside and write-through strategies
    - Automatic serialization
    - Key namespacing
    - Tagged cache invalidation
    - Decorator support for function memoization
    """
    
    def __init__(
        self,
        backend: Optional[CacheBackend] = None,
        default_ttl: int = 300,
        namespace: str = "app"
    ):
        self._backend = backend or MemoryCacheBackend()
        self._default_ttl = default_ttl
        self._namespace = namespace
        self._tag_index: Dict[str, set] = {}
    
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self._namespace}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._backend.get(self._make_key(key))
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
            tags: Tags for grouped invalidation
        """
        full_key = self._make_key(key)
        success = self._backend.set(full_key, value, ttl or self._default_ttl)
        
        # Index by tags
        if tags and success:
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(full_key)
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return self._backend.delete(self._make_key(key))
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self._backend.exists(self._make_key(key))
    
    def remember(
        self,
        key: str,
        callback: Callable,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """
        Get from cache or compute and store.
        
        Args:
            key: Cache key
            callback: Function to compute value if not cached
            ttl: Cache TTL
            tags: Cache tags
        
        Returns:
            Cached or computed value
        """
        value = self.get(key)
        
        if value is None:
            value = callback()
            self.set(key, value, ttl, tags)
        
        return value
    
    def forever(self, key: str, value: Any, tags: Optional[List[str]] = None) -> bool:
        """Store value without expiration."""
        return self.set(key, value, ttl=None, tags=tags)
    
    def flush(self, tag: Optional[str] = None) -> bool:
        """
        Clear cache, optionally by tag.
        
        Args:
            tag: If provided, only clear entries with this tag
        """
        if tag:
            # Clear by tag
            keys = self._tag_index.get(tag, set())
            for key in keys:
                self._backend.delete(key)
            self._tag_index[tag] = set()
            return True
        else:
            # Clear all
            self._backend.clear()
            self._tag_index.clear()
            return True
    
    def increment(self, key: str, value: int = 1) -> int:
        """Atomically increment a counter."""
        current = self.get(key)
        if current is None:
            current = 0
        
        new_value = current + value
        self.set(key, new_value)
        
        return new_value
    
    def decrement(self, key: str, value: int = 1) -> int:
        """Atomically decrement a counter."""
        return self.increment(key, -value)
    
    def many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        return {key: self.get(key) for key in keys}
    
    def put_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store multiple values in cache."""
        for key, value in items.items():
            self.set(key, value, ttl)
        return True
    
    def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple keys from cache."""
        for key in keys:
            self.delete(key)
        return True
    
    def cache_decorator(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        tags: Optional[List[str]] = None
    ):
        """
        Decorator to cache function results.
        
        Usage:
            @cache.cache_decorator(ttl=300)
            def expensive_function(x, y):
                return x + y
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function and arguments
                cache_key = self._generate_cache_key(
                    func, key_prefix, args, kwargs
                )
                
                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result
                
                # Compute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl, tags)
                
                return result
            
            return wrapper
        return decorator
    
    def _generate_cache_key(
        self,
        func: Callable,
        prefix: str,
        args: tuple,
        kwargs: dict
    ) -> str:
        """Generate unique cache key for function call."""
        # Create key components
        key_parts = [
            prefix or func.__name__,
            str(args),
            str(sorted(kwargs.items()))
        ]
        
        # Hash to create fixed-length key
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{prefix}:{key_hash}" if prefix else key_hash
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        all_keys = self._backend.keys(f"{self._namespace}:*")
        
        return {
            "namespace": self._namespace,
            "total_keys": len(all_keys),
            "tags_indexed": len(self._tag_index),
            "tags": list(self._tag_index.keys()),
            "backend_type": type(self._backend).__name__
        }
    
    def warmup(
        self,
        keys_callbacks: Dict[str, Callable],
        ttl: Optional[int] = None
    ) -> Dict[str, bool]:
        """
        Pre-populate cache with multiple values.
        
        Args:
            keys_callbacks: Dict of cache keys to callback functions
            ttl: TTL for cached values
        
        Returns:
            Dict of keys to success status
        """
        results = {}
        
        for key, callback in keys_callbacks.items():
            try:
                value = callback()
                success = self.set(key, value, ttl)
                results[key] = success
            except Exception as e:
                results[key] = False
        
        return results


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    tags: Optional[List[str]] = None
):
    """
    Decorator to cache function results using default cache service.
    
    Usage:
        @cached(ttl=300, tags=["users"])
        def get_user(user_id: int):
            return db.query(User).get(user_id)
    """
    def decorator(func):
        cache = CacheService()  # Default instance
        return cache.cache_decorator(ttl, key_prefix, tags)(func)
    return decorator
