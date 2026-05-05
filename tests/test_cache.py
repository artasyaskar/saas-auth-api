"""
Tests for caching service.
"""
import pytest
import time
from datetime import datetime, timedelta
from app.services.cache import CacheService, MemoryCacheBackend, cached


class TestMemoryCacheBackend:
    """Tests for in-memory cache backend."""
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = MemoryCacheBackend()
        
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result == "value1"
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = MemoryCacheBackend()
        
        result = cache.get("nonexistent")
        assert result is None
    
    def test_delete_key(self):
        """Test deleting a cache key."""
        cache = MemoryCacheBackend()
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_exists(self):
        """Test checking if key exists."""
        cache = MemoryCacheBackend()
        
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        assert cache.exists("key2") is False
    
    def test_ttl_expiration(self):
        """Test that keys expire after TTL."""
        cache = MemoryCacheBackend()
        
        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_clear_all(self):
        """Test clearing all cache entries."""
        cache = MemoryCacheBackend()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_keys_pattern(self):
        """Test retrieving keys by pattern."""
        cache = MemoryCacheBackend()
        
        cache.set("user:1", "value1")
        cache.set("user:2", "value2")
        cache.set("post:1", "value3")
        
        user_keys = cache.keys("user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys


class TestCacheService:
    """Tests for cache service."""
    
    def test_namespaced_keys(self):
        """Test that keys are properly namespaced."""
        cache = CacheService(namespace="test")
        
        cache.set("key1", "value1")
        
        # Should be accessible through service
        assert cache.get("key1") == "value1"
    
    def test_remember_pattern(self):
        """Test remember pattern (get or compute)."""
        cache = CacheService()
        
        call_count = 0
        
        def expensive_operation():
            nonlocal call_count
            call_count += 1
            return "computed_value"
        
        # First call should compute
        result1 = cache.remember("key1", expensive_operation, ttl=60)
        assert result1 == "computed_value"
        assert call_count == 1
        
        # Second call should use cache
        result2 = cache.remember("key1", expensive_operation, ttl=60)
        assert result2 == "computed_value"
        assert call_count == 1  # Not incremented
    
    def test_many_operations(self):
        """Test getting multiple values at once."""
        cache = CacheService()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        results = cache.many(["key1", "key2", "key3"])
        
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert results["key3"] == "value3"
    
    def test_put_many(self):
        """Test setting multiple values at once."""
        cache = CacheService()
        
        items = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        cache.put_many(items)
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_increment_decrement(self):
        """Test atomic increment and decrement."""
        cache = CacheService()
        
        cache.set("counter", 10)
        
        new_val = cache.increment("counter", 5)
        assert new_val == 15
        
        new_val = cache.decrement("counter", 3)
        assert new_val == 12
    
    def test_flush_by_tag(self):
        """Test clearing cache by tag."""
        cache = CacheService()
        
        cache.set("user:1", "value1", tags=["users"])
        cache.set("user:2", "value2", tags=["users"])
        cache.set("post:1", "value3", tags=["posts"])
        
        cache.flush(tag="users")
        
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("post:1") == "value3"
    
    def test_tags_indexing(self):
        """Test that tags properly index keys."""
        cache = CacheService()
        
        cache.set("key1", "value1", tags=["tag1", "tag2"])
        cache.set("key2", "value2", tags=["tag1"])
        
        # Flush by tag1 should remove both keys
        cache.flush(tag="tag1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCacheDecorator:
    """Tests for cache decorator."""
    
    def test_cache_decorator_basic(self):
        """Test basic cache decorator functionality."""
        cache = CacheService()
        call_count = 0
        
        @cache.cache_decorator(ttl=60)
        def get_user(user_id: int):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": f"User {user_id}"}
        
        # First call
        result1 = get_user(1)
        assert result1["id"] == 1
        assert call_count == 1
        
        # Second call with same args - should use cache
        result2 = get_user(1)
        assert result2["id"] == 1
        assert call_count == 1  # Not incremented
        
        # Different args - should compute
        result3 = get_user(2)
        assert result3["id"] == 2
        assert call_count == 2
    
    def test_cache_decorator_with_prefix(self):
        """Test cache decorator with key prefix."""
        cache = CacheService()
        
        @cache.cache_decorator(ttl=60, key_prefix="users")
        def get_user(user_id: int):
            return {"id": user_id}
        
        result = get_user(1)
        assert result["id"] == 1


class TestCacheStats:
    """Tests for cache statistics."""
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = CacheService(namespace="test_stats")
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3", tags=["users"])
        
        stats = cache.get_stats()
        
        assert stats["namespace"] == "test_stats"
        assert stats["total_keys"] == 3
        assert stats["tags_indexed"] == 1
        assert "users" in stats["tags"]
        assert stats["backend_type"] == "MemoryCacheBackend"


class TestCacheWarmup:
    """Tests for cache warmup."""
    
    def test_warmup(self):
        """Test cache warmup functionality."""
        cache = CacheService()
        
        call_count = 0
        
        def get_user_1():
            nonlocal call_count
            call_count += 1
            return "User 1"
        
        def get_user_2():
            nonlocal call_count
            call_count += 1
            return "User 2"
        
        callbacks = {
            "user:1": get_user_1,
            "user:2": get_user_2
        }
        
        results = cache.warmup(callbacks)
        
        assert results["user:1"] is True
        assert results["user:2"] is True
        assert call_count == 2
        
        # Values should be in cache
        assert cache.get("user:1") == "User 1"
        assert cache.get("user:2") == "User 2"


class TestCachedDecorator:
    """Tests for global cached decorator."""
    
    def test_cached_decorator(self):
        """Test the global cached decorator."""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test_cached")
        def expensive_computation(x: int, y: int):
            nonlocal call_count
            call_count += 1
            return x + y
        
        result1 = expensive_computation(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        result2 = expensive_computation(1, 2)
        assert result2 == 3
        assert call_count == 1  # Cached
        
        result3 = expensive_computation(2, 3)
        assert result3 == 5
        assert call_count == 2
