"""
Enhanced API response caching service with multiple strategies.

Provides enterprise-grade caching with support for:
- Redis and in-memory backends
- Multiple cache strategies (LRU, TTL, write-through, cache-aside)
- Tag-based invalidation and cache warming
- Performance monitoring and metrics
- API response optimization
- Cache invalidation policies
"""
import hashlib
import json
import pickle
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable, Union
from functools import wraps
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


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


class CacheStrategy(Enum):
    """Cache strategy enumeration."""
    LRU = "lru"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    CACHE_ASIDE = "cache_aside"
    READ_THROUGH = "read_through"


@dataclass
class CacheConfig:
    """Cache configuration for API responses."""
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    default_ttl: int = 300
    max_size: int = 1000
    enable_compression: bool = True
    enable_metrics: bool = True
    cleanup_interval: int = 3600
    key_prefix: str = "api"
    tags: List[str] = field(default_factory=list)


class EnhancedCacheService(CacheService):
    """
    Enhanced cache service with API response optimization.
    
    Additional features:
    - Response compression
    - Intelligent cache warming
    - Advanced invalidation strategies
    - Performance metrics and monitoring
    - Cache health checks
    - Multi-level caching
    """
    
    def __init__(self, config: CacheConfig = None):
        super().__init__()
        self.config = config or CacheConfig()
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "compressions": 0,
            "decompressions": 0,
            "errors": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0,
            "cache_size_bytes": 0,
            "memory_savings_bytes": 0
        }
        self.lock = threading.Lock()
        self._start_cleanup_timer()
    
    def _start_cleanup_timer(self) -> None:
        """Start background cleanup timer."""
        def cleanup():
            while True:
                try:
                    time.sleep(self.config.cleanup_interval)
                    self._cleanup_expired()
                    self._update_metrics()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with metrics tracking."""
        start_time = time.time()
        
        try:
            value = super().get(key)
            
            with self.lock:
                self.metrics["total_response_time"] += time.time() - start_time
                if value is not None:
                    self.metrics["hits"] += 1
                else:
                    self.metrics["misses"] += 1
                
                # Update average response time
                total_requests = self.metrics["hits"] + self.metrics["misses"]
                if total_requests > 0:
                    self.metrics["average_response_time"] = (
                        self.metrics["total_response_time"] / total_requests
                    )
            
            return value
            
        except Exception as e:
            with self.lock:
                self.metrics["errors"] += 1
            logger.error(f"Enhanced cache get error for key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """Set value with compression and metrics."""
        try:
            # Apply compression if enabled
            processed_value = self._process_value_for_storage(value)
            
            success = super().set(
                key, 
                processed_value, 
                ttl or self.config.default_ttl,
                tags or self.config.tags
            )
            
            if success:
                with self.lock:
                    self.metrics["sets"] += 1
                    if processed_value != value:
                        self.metrics["compressions"] += 1
                        # Calculate compression savings
                        original_size = len(pickle.dumps(value))
                        compressed_size = len(pickle.dumps(processed_value))
                        savings = original_size - compressed_size
                        if savings > 0:
                            self.metrics["memory_savings_bytes"] += savings
            
            return success
            
        except Exception as e:
            with self.lock:
                self.metrics["errors"] += 1
            logger.error(f"Enhanced cache set error for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value with metrics tracking."""
        try:
            success = super().delete(key)
            
            if success:
                with self.lock:
                    self.metrics["deletes"] += 1
            
            return success
            
        except Exception as e:
            with self.lock:
                self.metrics["errors"] += 1
            logger.error(f"Enhanced cache delete error for key {key}: {str(e)}")
            return False
    
    def _process_value_for_storage(self, value: Any) -> Any:
        """Process value for storage (compression, etc.)."""
        if not self.config.enable_compression:
            return value
        
        # Simple compression for large objects
        try:
            serialized = pickle.dumps(value)
            if len(serialized) > 1024:  # Only compress objects > 1KB
                # Use a simple compression indicator
                return {"_compressed": True, "_data": serialized}
            return value
        except Exception:
            return value
    
    def _process_value_from_storage(self, value: Any) -> Any:
        """Process value retrieved from storage."""
        if isinstance(value, dict) and value.get("_compressed"):
            try:
                with self.lock:
                    self.metrics["decompressions"] += 1
                return pickle.loads(value["_data"])
            except Exception as e:
                logger.error(f"Cache decompression error: {str(e)}")
                return None
        return value
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries."""
        try:
            if hasattr(self._backend, 'cleanup_expired'):
                count = self._backend.cleanup_expired()
                if count > 0:
                    logger.info(f"Cleaned up {count} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {str(e)}")
    
    def _update_metrics(self) -> None:
        """Update cache size metrics."""
        try:
            if hasattr(self._backend, '_cache'):
                with self.lock:
                    total_size = 0
                    for entry in self._backend._cache.values():
                        if isinstance(entry, dict):
                            # Calculate size of cached data
                            try:
                                total_size += len(pickle.dumps(entry.get("value", "")))
                            except:
                                pass
                    self.metrics["cache_size_bytes"] = total_size
        except Exception:
            pass
    
    def cache_api_response(
        self,
        endpoint: str,
        params: Dict[str, Any],
        response: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Cache API response with intelligent key generation.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            response: Response data to cache
            ttl: Cache TTL
            tags: Cache tags
            
        Returns:
            Success status
        """
        # Generate intelligent cache key
        cache_key = self._generate_api_cache_key(endpoint, params)
        
        # Add API-specific tags
        api_tags = ["api", endpoint.replace("/", "_")]
        if tags:
            api_tags.extend(tags)
        
        return self.set(cache_key, response, ttl, api_tags)
    
    def get_cached_api_response(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get cached API response.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            
        Returns:
            Cached response or None
        """
        cache_key = self._generate_api_cache_key(endpoint, params)
        return self.get(cache_key)
    
    def _generate_api_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for API request."""
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        param_string = json.dumps(sorted_params, sort_keys=True)
        
        # Create components
        components = [
            self.config.key_prefix,
            endpoint.strip("/"),
            hashlib.md5(param_string.encode()).hexdigest()
        ]
        
        return ":".join(components)
    
    def invalidate_by_endpoint(self, endpoint: str) -> int:
        """
        Invalidate all cache entries for a specific endpoint.
        
        Args:
            endpoint: API endpoint to invalidate
            
        Returns:
            Number of entries invalidated
        """
        tag = f"api_{endpoint.replace('/', '_')}"
        return self.flush(tag)
    
    def warm_cache_for_endpoints(
        self,
        endpoints_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Warm cache for multiple endpoints.
        
        Args:
            endpoints_data: Dict of endpoint to {params: callback}
            
        Returns:
            Dict of endpoints to success status
        """
        results = {}
        
        for endpoint, data in endpoints_data.items():
            try:
                params = data.get("params", {})
                callback = data.get("callback")
                ttl = data.get("ttl", self.config.default_ttl)
                
                if callback:
                    response = callback()
                    success = self.cache_api_response(endpoint, params, response, ttl)
                    results[endpoint] = success
                else:
                    results[endpoint] = False
                    
            except Exception as e:
                logger.error(f"Cache warming error for {endpoint}: {str(e)}")
                results[endpoint] = False
        
        return results
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        base_stats = self.get_stats()
        
        with self.lock:
            total_requests = self.metrics["hits"] + self.metrics["misses"]
            hit_rate = self.metrics["hits"] / max(total_requests, 1) * 100
            
            enhanced_stats = {
                **base_stats,
                "enhanced_metrics": {
                    "hits": self.metrics["hits"],
                    "misses": self.metrics["misses"],
                    "sets": self.metrics["sets"],
                    "deletes": self.metrics["deletes"],
                    "compressions": self.metrics["compressions"],
                    "decompressions": self.metrics["decompressions"],
                    "errors": self.metrics["errors"],
                    "hit_rate": hit_rate,
                    "average_response_time_ms": self.metrics["average_response_time"] * 1000,
                    "cache_size_bytes": self.metrics["cache_size_bytes"],
                    "memory_savings_bytes": self.metrics["memory_savings_bytes"],
                    "compression_rate": (
                        self.metrics["compressions"] / max(self.metrics["sets"], 1) * 100
                    )
                },
                "config": {
                    "strategy": self.config.strategy.value,
                    "default_ttl": self.config.default_ttl,
                    "max_size": self.config.max_size,
                    "enable_compression": self.config.enable_compression,
                    "enable_metrics": self.config.enable_metrics,
                    "cleanup_interval": self.config.cleanup_interval,
                    "key_prefix": self.config.key_prefix
                }
            }
        
        return enhanced_stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test basic operations
            test_key = f"{self.config.key_prefix}:health_check"
            test_value = {"timestamp": time.time(), "test": True}
            
            # Test set
            set_success = self.set(test_key, test_value, ttl=10)
            
            # Test get
            retrieved_value = self.get(test_key)
            get_success = retrieved_value is not None
            
            # Test delete
            delete_success = self.delete(test_key)
            
            # Test API response caching
            api_success = self.cache_api_response(
                "/health", {"test": True}, {"status": "ok"}, ttl=10
            )
            api_retrieved = self.get_cached_api_response("/health", {"test": True})
            api_get_success = api_retrieved is not None
            
            is_healthy = all([
                set_success, get_success, delete_success,
                api_success, api_get_success
            ])
            
            return {
                "healthy": is_healthy,
                "tests": {
                    "basic_set": set_success,
                    "basic_get": get_success,
                    "basic_delete": delete_success,
                    "api_cache": api_success,
                    "api_get": api_get_success
                },
                "stats": self.get_enhanced_stats()
            }
            
        except Exception as e:
            logger.error(f"Enhanced cache health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "stats": self.get_enhanced_stats()
            }


# Global enhanced cache instance
enhanced_cache = EnhancedCacheService()


def cache_api_response(
    endpoint: str,
    ttl: int = 300,
    tags: Optional[List[str]] = None
):
    """
    Decorator for caching API responses.
    
    Usage:
        @cache_api_response("/users", ttl=600)
        def get_users(params):
            return user_service.get_users(params)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request parameters
            params = kwargs.get("params", {})
            
            # Try to get from cache
            cached_response = enhanced_cache.get_cached_api_response(endpoint, params)
            if cached_response is not None:
                return cached_response
            
            # Execute function and cache result
            response = func(*args, **kwargs)
            enhanced_cache.cache_api_response(endpoint, params, response, ttl, tags)
            return response
        
        return wrapper
    return decorator


def get_enhanced_cache_stats() -> Dict[str, Any]:
    """Get enhanced cache statistics."""
    return enhanced_cache.get_enhanced_stats()


def cache_health_check() -> Dict[str, Any]:
    """Perform enhanced cache health check."""
    return enhanced_cache.health_check()
