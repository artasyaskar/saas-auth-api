"""
Unit tests for Rate Limiter Configuration Service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.rate_limiter_config import (
    RateLimiterConfigService,
    RateLimitRule,
    RateLimitPolicy,
    LimitType,
    TimeUnit,
    LimitScope
)


@pytest.fixture
def db_session():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def rate_limiter_service(db_session):
    """Rate limiter config service fixture"""
    db_session.query = MagicMock(return_value=MagicMock(filter=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    return RateLimiterConfigService(db_session)


class TestRateLimiterConfigService:
    """Test suite for RateLimiterConfigService"""
    
    def test_create_policy(self, rate_limiter_service):
        """Test creating a new rate limit policy"""
        policy = RateLimitPolicy(
            name="test_policy",
            description="Test policy",
            rules=[
                RateLimitRule(
                    name="rule1",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=100,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER
                )
            ]
        )
        
        policy_name = rate_limiter_service.create_policy(policy)
        assert policy_name == "test_policy"
        assert "test_policy" in rate_limiter_service._policies
    
    def test_update_policy(self, rate_limiter_service):
        """Test updating an existing policy"""
        policy = RateLimitPolicy(
            name="test_policy",
            description="Test",
            rules=[]
        )
        rate_limiter_service.create_policy(policy)
        
        result = rate_limiter_service.update_policy("test_policy", description="Updated description")
        assert result is True
        assert rate_limiter_service._policies["test_policy"].description == "Updated description"
    
    def test_delete_policy(self, rate_limiter_service):
        """Test deleting a policy"""
        policy = RateLimitPolicy(name="test_policy", description="Test", rules=[])
        rate_limiter_service.create_policy(policy)
        
        result = rate_limiter_service.delete_policy("test_policy")
        assert result is True
        assert "test_policy" not in rate_limiter_service._policies
    
    def test_get_policy(self, rate_limiter_service):
        """Test getting a policy by name"""
        policy = RateLimitPolicy(name="test_policy", description="Test", rules=[])
        rate_limiter_service.create_policy(policy)
        
        retrieved = rate_limiter_service.get_policy("test_policy")
        assert retrieved is not None
        assert retrieved.name == "test_policy"
    
    def test_get_all_policies(self, rate_limiter_service):
        """Test getting all policies"""
        policy1 = RateLimitPolicy(name="policy1", description="Test 1", rules=[], priority=100)
        policy2 = RateLimitPolicy(name="policy2", description="Test 2", rules=[], priority=50)
        rate_limiter_service.create_policy(policy1)
        rate_limiter_service.create_policy(policy2)
        
        policies = rate_limiter_service.get_all_policies()
        assert len(policies) == 2
    
    def test_get_all_policies_active_only(self, rate_limiter_service):
        """Test getting only active policies"""
        policy1 = RateLimitPolicy(name="policy1", description="Test 1", rules=[], is_active=True)
        policy2 = RateLimitPolicy(name="policy2", description="Test 2", rules=[], is_active=False)
        rate_limiter_service.create_policy(policy1)
        rate_limiter_service.create_policy(policy2)
        
        policies = rate_limiter_service.get_all_policies(active_only=True)
        assert len(policies) == 1
        assert policies[0].name == "policy1"
    
    def test_get_applicable_policy(self, rate_limiter_service):
        """Test getting applicable policy for request"""
        policy = RateLimitPolicy(name="test_policy", description="Test", rules=[], is_active=True)
        rate_limiter_service.create_policy(policy)
        
        applicable = rate_limiter_service.get_applicable_policy(user_id=123)
        assert applicable is not None
        assert applicable.name == "test_policy"
    
    def test_add_user_override(self, rate_limiter_service):
        """Test adding user-specific override"""
        result = rate_limiter_service.add_user_override(
            user_id=123,
            policy_name="custom_policy",
            custom_limits={"requests_per_minute": 200}
        )
        assert result is True
        assert 123 in rate_limiter_service._user_overrides
    
    def test_remove_user_override(self, rate_limiter_service):
        """Test removing user override"""
        rate_limiter_service.add_user_override(123, policy_name="custom_policy")
        
        result = rate_limiter_service.remove_user_override(123)
        assert result is True
        assert 123 not in rate_limiter_service._user_overrides
    
    def test_add_endpoint_override(self, rate_limiter_service):
        """Test adding endpoint-specific override"""
        result = rate_limiter_service.add_endpoint_override(
            endpoint="/api/users",
            policy_name="strict_policy"
        )
        assert result is True
        assert "/api/users" in rate_limiter_service._endpoint_overrides
    
    def test_remove_endpoint_override(self, rate_limiter_service):
        """Test removing endpoint override"""
        rate_limiter_service.add_endpoint_override("/api/users", policy_name="strict_policy")
        
        result = rate_limiter_service.remove_endpoint_override("/api/users")
        assert result is True
        assert "/api/users" not in rate_limiter_service._endpoint_overrides
    
    def test_add_to_whitelist(self, rate_limiter_service):
        """Test adding identifier to whitelist"""
        result = rate_limiter_service.add_to_whitelist("user@example.com")
        assert result is True
        assert "user@example.com" in rate_limiter_service._whitelist
    
    def test_remove_from_whitelist(self, rate_limiter_service):
        """Test removing from whitelist"""
        rate_limiter_service.add_to_whitelist("user@example.com")
        
        result = rate_limiter_service.remove_from_whitelist("user@example.com")
        assert result is True
        assert "user@example.com" not in rate_limiter_service._whitelist
    
    def test_is_whitelisted(self, rate_limiter_service):
        """Test checking if identifier is whitelisted"""
        rate_limiter_service.add_to_whitelist("user@example.com")
        
        result = rate_limiter_service.is_whitelisted("user@example.com")
        assert result is True
        
        result = rate_limiter_service.is_whitelisted("other@example.com")
        assert result is False
    
    def test_add_to_blacklist(self, rate_limiter_service):
        """Test adding identifier to blacklist"""
        result = rate_limiter_service.add_to_blacklist("spam@example.com")
        assert result is True
        assert "spam@example.com" in rate_limiter_service._blacklist
    
    def test_remove_from_blacklist(self, rate_limiter_service):
        """Test removing from blacklist"""
        rate_limiter_service.add_to_blacklist("spam@example.com")
        
        result = rate_limiter_service.remove_from_blacklist("spam@example.com")
        assert result is True
        assert "spam@example.com" not in rate_limiter_service._blacklist
    
    def test_is_blacklisted(self, rate_limiter_service):
        """Test checking if identifier is blacklisted"""
        rate_limiter_service.add_to_blacklist("spam@example.com")
        
        result = rate_limiter_service.is_blacklisted("spam@example.com")
        assert result is True
        
        result = rate_limiter_service.is_blacklisted("good@example.com")
        assert result is False
    
    def test_get_effective_limits_whitelisted(self, rate_limiter_service):
        """Test effective limits for whitelisted user"""
        rate_limiter_service.add_to_whitelist("user@example.com")
        
        limits = rate_limiter_service.get_effective_limits(user_id=123)
        assert limits.get("unlimited") is True
    
    def test_get_effective_limits_blacklisted(self, rate_limiter_service):
        """Test effective limits for blacklisted user"""
        rate_limiter_service.add_to_blacklist("user@example.com")
        
        limits = rate_limiter_service.get_effective_limits(user_id=123)
        assert limits.get("blocked") is True
    
    def test_cleanup_expired_entries(self, rate_limiter_service):
        """Test cleaning up expired entries"""
        rate_limiter_service.add_to_whitelist("user@example.com", expires_at=datetime.utcnow() - timedelta(days=1))
        rate_limiter_service.add_to_blacklist("spam@example.com", expires_at=datetime.utcnow() - timedelta(days=1))
        
        count = rate_limiter_service.cleanup_expired_entries()
        assert count == 2
    
    def test_get_config_stats(self, rate_limiter_service):
        """Test getting configuration statistics"""
        policy = RateLimitPolicy(name="test", description="Test", rules=[], is_active=True)
        rate_limiter_service.create_policy(policy)
        rate_limiter_service.add_to_whitelist("user@example.com")
        
        stats = rate_limiter_service.get_config_stats()
        assert stats["total_policies"] == 1
        assert stats["active_policies"] == 1
        assert stats["whitelist_size"] == 1
    
    def test_export_config(self, rate_limiter_service):
        """Test exporting configuration to JSON"""
        policy = RateLimitPolicy(
            name="test_policy",
            description="Test",
            rules=[
                RateLimitRule(
                    name="rule1",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=100,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER
                )
            ]
        )
        rate_limiter_service.create_policy(policy)
        
        exported = rate_limiter_service.export_config("json")
        assert isinstance(exported, str)
        assert "test_policy" in exported
    
    def test_import_config(self, rate_limiter_service):
        """Test importing configuration from JSON"""
        import json
        config = json.dumps({
            "policies": [
                {
                    "name": "imported_policy",
                    "description": "Imported",
                    "priority": 100,
                    "is_active": True,
                    "effective_from": None,
                    "effective_until": None,
                    "rules": [
                        {
                            "name": "rule1",
                            "limit_type": "request_count",
                            "limit": 100,
                            "period": 1,
                            "time_unit": "minute",
                            "scope": "per_user",
                            "burst_limit": None,
                            "burst_period": None
                        }
                    ]
                }
            ],
            "whitelist": [],
            "blacklist": []
        })
        
        count = rate_limiter_service.import_config(config, "json")
        assert count == 1
        assert "imported_policy" in rate_limiter_service._policies
