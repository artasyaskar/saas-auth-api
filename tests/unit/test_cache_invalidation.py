"""
Unit tests for Cache Invalidation Service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.cache_invalidation import (
    CacheInvalidationService,
    InvalidationStrategy,
    CacheLevel,
    CacheKey
)


@pytest.fixture
def db_session():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def cache_service(db_session):
    """Cache invalidation service fixture"""
    return CacheInvalidationService(db_session)


class TestCacheInvalidationService:
    """Test suite for CacheInvalidationService"""
    
    def test_set_cache_value(self, cache_service):
        """Test setting a cache value"""
        cache_service.set("test_key", "test_value", ttl=60, tags=["user:123"])
        
        assert "test_key" in cache_service._cache
        assert cache_service._cache["test_key"][0] == "test_value"
        assert "user:123" in cache_service._tag_index
    
    def test_get_cache_value(self, cache_service):
        """Test getting a cache value"""
        cache_service.set("test_key", "test_value")
        
        value = cache_service.get("test_key")
        assert value == "test_value"
    
    def test_get_expired_value(self, cache_service):
        """Test getting expired value returns None"""
        cache_service.set("test_key", "test_value", ttl=1)
        
        # Simulate expiry
        cache_service._cache["test_key"] = ("test_value", datetime.utcnow() - timedelta(seconds=2), set())
        
        value = cache_service.get("test_key")
        assert value is None
    
    def test_invalidate_immediate(self, cache_service):
        """Test immediate invalidation"""
        cache_service.set("test_key", "test_value", tags=["user:123"])
        
        result = cache_service.invalidate("test_key", InvalidationStrategy.IMMEDIATE)
        assert result is True
        assert "test_key" not in cache_service._cache
    
    def test_invalidate_delayed(self, cache_service):
        """Test delayed invalidation"""
        cache_service.set("test_key", "test_value")
        
        result = cache_service.invalidate("test_key", InvalidationStrategy.DELAYED)
        assert result is True
        assert len(cache_service._invalidation_queue) == 1
    
    def test_invalidate_batch(self, cache_service):
        """Test batch invalidation"""
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        
        result = cache_service.invalidate("key1", InvalidationStrategy.BATCH)
        assert result is True
    
    def test_invalidate_by_tag(self, cache_service):
        """Test invalidating by tag"""
        cache_service.set("key1", "value1", tags=["user:123"])
        cache_service.set("key2", "value2", tags=["user:123"])
        cache_service.set("key3", "value3", tags=["user:456"])
        
        count = cache_service.invalidate_by_tag("user:123")
        assert count == 2
        assert "key1" not in cache_service._cache
        assert "key2" not in cache_service._cache
        assert "key3" in cache_service._cache
    
    def test_invalidate_pattern(self, cache_service):
        """Test pattern-based invalidation"""
        cache_service.set("user:123:profile", "value1")
        cache_service.set("user:123:settings", "value2")
        cache_service.set("user:456:profile", "value3")
        
        count = cache_service.invalidate_pattern("user:123:*")
        assert count == 2
    
    def test_process_invalidation_queue(self, cache_service):
        """Test processing invalidation queue"""
        cache_service.set("test_key", "test_value")
        cache_service.invalidate("test_key", InvalidationStrategy.DELAYED)
        
        # Process queue (delay should decrement)
        processed = cache_service.process_invalidation_queue()
        assert processed == 0  # Still has delay
    
    def test_register_warming_callback(self, cache_service):
        """Test registering cache warming callback"""
        def warm_callback(key):
            return f"warmed_{key}"
        
        cache_service.register_warming_callback("user:*", warm_callback)
        assert "user:*" in cache_service._warming_callbacks
    
    def test_warm_cache(self, cache_service):
        """Test warming cache"""
        def warm_callback(key):
            return f"warmed_{key}"
        
        cache_service.register_warming_callback("user:*", warm_callback)
        result = cache_service.warm_cache("user:123")
        assert result is True
    
    def test_invalidate_all(self, cache_service):
        """Test invalidating all cache entries"""
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        
        count = cache_service.invalidate_all()
        assert count == 2
        assert len(cache_service._cache) == 0
    
    def test_get_cache_stats(self, cache_service):
        """Test getting cache statistics"""
        cache_service.set("key1", "value1", tags=["tag1"])
        
        stats = cache_service.get_cache_stats()
        assert stats["local_cache_size"] == 1
        assert stats["tag_count"] == 1
    
    def test_get_tag_stats(self, cache_service):
        """Test getting tag statistics"""
        cache_service.set("key1", "value1", tags=["tag1"])
        cache_service.set("key2", "value2", tags=["tag1"])
        cache_service.set("key3", "value3", tags=["tag2"])
        
        stats = cache_service.get_tag_stats()
        assert stats["tag1"] == 2
        assert stats["tag2"] == 1
    
    def test_get_expiring_keys(self, cache_service):
        """Test getting expiring keys"""
        cache_service.set("key1", "value1", ttl=3600)
        cache_service.set("key2", "value2", ttl=60)
        
        expiring = cache_service.get_expiring_keys(seconds=300)
        assert "key2" in expiring
    
    def test_cleanup_expired(self, cache_service):
        """Test cleaning up expired entries"""
        cache_service.set("key1", "value1", ttl=1)
        cache_service._cache["key1"] = ("value1", datetime.utcnow() - timedelta(seconds=2), set())
        
        count = cache_service.cleanup_expired()
        assert count == 1
        assert "key1" not in cache_service._cache
    
    def test_set_ttl(self, cache_service):
        """Test updating TTL for a key"""
        cache_service.set("test_key", "test_value")
        
        result = cache_service.set_ttl("test_key", 300)
        assert result is True
    
    def test_get_ttl(self, cache_service):
        """Test getting remaining TTL"""
        cache_service.set("test_key", "test_value", ttl=60)
        
        ttl = cache_service.get_ttl("test_key")
        assert ttl is not None
        assert ttl <= 60
    
    def test_backup_cache(self, cache_service):
        """Test creating cache backup"""
        cache_service.set("key1", "value1", tags=["tag1"])
        
        backup = cache_service.backup_cache()
        assert "timestamp" in backup
        assert "cache" in backup
        assert "tag_index" in backup
    
    def test_restore_cache(self, cache_service):
        """Test restoring cache from backup"""
        cache_service.set("key1", "value1", tags=["tag1"])
        backup = cache_service.backup_cache()
        
        cache_service.invalidate_all()
        assert len(cache_service._cache) == 0
        
        result = cache_service.restore_cache(backup)
        assert result is True
        assert len(cache_service._cache) == 1
