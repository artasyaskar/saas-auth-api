"""
Rate Limiter Configuration Service

Comprehensive rate limiter configuration service for managing
rate limit rules, policies, and dynamic adjustments.

Features:
- Rate limit rule management
- Dynamic policy updates
- User-specific limits
- Endpoint-specific limits
- Time-based adjustments
- Burst handling
- Whitelist/blacklist management
- Limit analytics
- Policy templates
- Automatic scaling
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.db.models import User
from app.core.config import settings


class LimitType(Enum):
    """Rate limit types."""
    REQUEST_COUNT = "request_count"
    BANDWIDTH = "bandwidth"
    CONCURRENT_CONNECTIONS = "concurrent_connections"
    API_CALLS = "api_calls"
    CUSTOM = "custom"


class TimeUnit(Enum):
    """Time units for rate limits."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class LimitScope(Enum):
    """Rate limit scopes."""
    GLOBAL = "global"
    PER_USER = "per_user"
    PER_IP = "per_ip"
    PER_API_KEY = "per_api_key"
    PER_ENDPOINT = "per_endpoint"
    PER_TIER = "per_tier"


@dataclass
class RateLimitRule:
    """Rate limit rule data structure."""
    name: str
    limit_type: LimitType
    limit: int
    period: int
    time_unit: TimeUnit
    scope: LimitScope
    burst_limit: Optional[int] = None
    burst_period: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitPolicy:
    """Rate limit policy data structure."""
    name: str
    description: str
    rules: List[RateLimitRule]
    priority: int = 0
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class RateLimiterConfigService:
    """
    Enterprise-grade rate limiter configuration service.
    
    Features:
    - Rate limit rule management
    - Dynamic policy updates
    - User-specific limits
    - Endpoint-specific limits
    - Time-based adjustments
    - Burst handling
    - Whitelist/blacklist management
    - Limit analytics
    - Policy templates
    - Automatic scaling
    """
    
    # Default policy templates
    POLICY_TEMPLATES = {
        "default": RateLimitPolicy(
            name="default",
            description="Default rate limiting policy",
            rules=[
                RateLimitRule(
                    name="global_requests",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=1000,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.GLOBAL
                ),
                RateLimitRule(
                    name="user_requests",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=100,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER
                )
            ],
            priority=100
        ),
        "strict": RateLimitPolicy(
            name="strict",
            description="Strict rate limiting for sensitive endpoints",
            rules=[
                RateLimitRule(
                    name="strict_requests",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=10,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER
                ),
                RateLimitRule(
                    name="strict_burst",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=20,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER,
                    burst_limit=5,
                    burst_period=10
                )
            ],
            priority=200
        ),
        "generous": RateLimitPolicy(
            name="generous",
            description="Generous rate limiting for trusted users",
            rules=[
                RateLimitRule(
                    name="generous_requests",
                    limit_type=LimitType.REQUEST_COUNT,
                    limit=10000,
                    period=1,
                    time_unit=TimeUnit.MINUTE,
                    scope=LimitScope.PER_USER
                )
            ],
            priority=50
        )
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._policies: Dict[str, RateLimitPolicy] = {}
        self._whitelist: Dict[str, datetime] = {}  # identifier: expiry
        self._blacklist: Dict[str, datetime] = {}  # identifier: expiry
        self._user_overrides: Dict[int, Dict[str, Any]] = {}
        self._endpoint_overrides: Dict[str, Dict[str, Any]] = {}
        
        # Load default policies
        for name, policy in self.POLICY_TEMPLATES.items():
            self._policies[name] = policy
    
    def create_policy(self, policy: RateLimitPolicy) -> str:
        """
        Create a new rate limit policy.
        
        Args:
            policy: Policy to create
        
        Returns:
            Policy name
        """
        self._policies[policy.name] = policy
        return policy.name
    
    def update_policy(self, policy_name: str, **updates) -> bool:
        """
        Update an existing policy.
        
        Args:
            policy_name: Name of policy to update
            **updates: Fields to update
        
        Returns:
            Success status
        """
        if policy_name not in self._policies:
            return False
        
        policy = self._policies[policy_name]
        
        if 'description' in updates:
            policy.description = updates['description']
        if 'priority' in updates:
            policy.priority = updates['priority']
        if 'is_active' in updates:
            policy.is_active = updates['is_active']
        if 'effective_from' in updates:
            policy.effective_from = updates['effective_from']
        if 'effective_until' in updates:
            policy.effective_until = updates['effective_until']
        if 'rules' in updates:
            policy.rules = updates['rules']
        
        return True
    
    def delete_policy(self, policy_name: str) -> bool:
        """Delete a policy."""
        if policy_name in self._policies:
            del self._policies[policy_name]
            return True
        return False
    
    def get_policy(self, policy_name: str) -> Optional[RateLimitPolicy]:
        """Get a policy by name."""
        return self._policies.get(policy_name)
    
    def get_all_policies(self, active_only: bool = False) -> List[RateLimitPolicy]:
        """Get all policies."""
        policies = list(self._policies.values())
        
        if active_only:
            policies = [p for p in policies if p.is_active]
        
        return sorted(policies, key=lambda p: p.priority, reverse=True)
    
    def get_applicable_policy(
        self,
        user_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[RateLimitPolicy]:
        """
        Get the applicable policy for a request.
        
        Args:
            user_id: User ID
            endpoint: Endpoint path
            api_key: API key
        
        Returns:
            Applicable policy
        """
        # Check user-specific overrides
        if user_id and user_id in self._user_overrides:
            override = self._user_overrides[user_id]
            if 'policy_name' in override:
                policy = self._policies.get(override['policy_name'])
                if policy and self._is_policy_effective(policy):
                    return policy
        
        # Check endpoint-specific overrides
        if endpoint and endpoint in self._endpoint_overrides:
            override = self._endpoint_overrides[endpoint]
            if 'policy_name' in override:
                policy = self._policies.get(override['policy_name'])
                if policy and self._is_policy_effective(policy):
                    return policy
        
        # Get highest priority active policy
        for policy in self.get_all_policies(active_only=True):
            if self._is_policy_effective(policy):
                return policy
        
        return None
    
    def _is_policy_effective(self, policy: RateLimitPolicy) -> bool:
        """Check if a policy is currently effective."""
        now = datetime.utcnow()
        
        if policy.effective_from and now < policy.effective_from:
            return False
        
        if policy.effective_until and now > policy.effective_until:
            return False
        
        return True
    
    def add_user_override(
        self,
        user_id: int,
        policy_name: Optional[str] = None,
        custom_limits: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Add a rate limit override for a specific user.
        
        Args:
            user_id: User ID
            policy_name: Policy to apply
            custom_limits: Custom limit overrides
            expires_at: When override expires
        
        Returns:
            Success status
        """
        self._user_overrides[user_id] = {
            'policy_name': policy_name,
            'custom_limits': custom_limits,
            'expires_at': expires_at
        }
        return True
    
    def remove_user_override(self, user_id: int) -> bool:
        """Remove user override."""
        if user_id in self._user_overrides:
            del self._user_overrides[user_id]
            return True
        return False
    
    def add_endpoint_override(
        self,
        endpoint: str,
        policy_name: Optional[str] = None,
        custom_limits: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a rate limit override for a specific endpoint."""
        self._endpoint_overrides[endpoint] = {
            'policy_name': policy_name,
            'custom_limits': custom_limits
        }
        return True
    
    def remove_endpoint_override(self, endpoint: str) -> bool:
        """Remove endpoint override."""
        if endpoint in self._endpoint_overrides:
            del self._endpoint_overrides[endpoint]
            return True
        return False
    
    def add_to_whitelist(
        self,
        identifier: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Add an identifier to the whitelist.
        
        Args:
            identifier: User ID, IP, or API key
            expires_at: When whitelist entry expires
        
        Returns:
            Success status
        """
        self._whitelist[identifier] = expires_at or datetime.utcnow() + timedelta(days=30)
        return True
    
    def remove_from_whitelist(self, identifier: str) -> bool:
        """Remove from whitelist."""
        if identifier in self._whitelist:
            del self._whitelist[identifier]
            return True
        return False
    
    def add_to_blacklist(
        self,
        identifier: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Add an identifier to the blacklist."""
        self._blacklist[identifier] = expires_at or datetime.utcnow() + timedelta(days=30)
        return True
    
    def remove_from_blacklist(self, identifier: str) -> bool:
        """Remove from blacklist."""
        if identifier in self._blacklist:
            del self._blacklist[identifier]
            return True
        return False
    
    def is_whitelisted(self, identifier: str) -> bool:
        """Check if identifier is whitelisted."""
        if identifier not in self._whitelist:
            return False
        
        # Check if expired
        expiry = self._whitelist[identifier]
        if expiry and datetime.utcnow() > expiry:
            del self._whitelist[identifier]
            return False
        
        return True
    
    def is_blacklisted(self, identifier: str) -> bool:
        """Check if identifier is blacklisted."""
        if identifier not in self._blacklist:
            return False
        
        # Check if expired
        expiry = self._blacklist[identifier]
        if expiry and datetime.utcnow() > expiry:
            del self._blacklist[identifier]
            return False
        
        return True
    
    def get_effective_limits(
        self,
        user_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get effective rate limits for a request.
        
        Args:
            user_id: User ID
            endpoint: Endpoint path
            api_key: API key
        
        Returns:
            Effective limits
        """
        # Check blacklist
        if user_id and self.is_blacklisted(str(user_id)):
            return {'blocked': True, 'reason': 'User blacklisted'}
        
        if api_key and self.is_blacklist(api_key):
            return {'blocked': True, 'reason': 'API key blacklisted'}
        
        # Check whitelist
        if user_id and self.is_whitelisted(str(user_id)):
            return {'unlimited': True, 'reason': 'User whitelisted'}
        
        if api_key and self.is_whitelisted(api_key):
            return {'unlimited': True, 'reason': 'API key whitelisted'}
        
        # Get applicable policy
        policy = self.get_applicable_policy(user_id, endpoint, api_key)
        
        if not policy:
            return {'limits': []}
        
        # Apply user overrides
        effective_rules = []
        for rule in policy.rules:
            rule_dict = {
                'name': rule.name,
                'limit_type': rule.limit_type.value,
                'limit': rule.limit,
                'period': rule.period,
                'time_unit': rule.time_unit.value,
                'scope': rule.scope.value
            }
            
            # Apply user-specific custom limits
            if user_id and user_id in self._user_overrides:
                override = self._user_overrides[user_id]
                custom_limits = override.get('custom_limits', {})
                if rule.name in custom_limits:
                    rule_dict.update(custom_limits[rule.name])
            
            effective_rules.append(rule_dict)
        
        return {
            'policy': policy.name,
            'limits': effective_rules
        }
    
    def cleanup_expired_entries(self) -> int:
        """Clean up expired whitelist/blacklist entries."""
        now = datetime.utcnow()
        count = 0
        
        # Clean whitelist
        expired_whitelist = [
            ident for ident, expiry in self._whitelist.items()
            if expiry and now > expiry
        ]
        for ident in expired_whitelist:
            del self._whitelist[ident]
            count += 1
        
        # Clean blacklist
        expired_blacklist = [
            ident for ident, expiry in self._blacklist.items()
            if expiry and now > expiry
        ]
        for ident in expired_blacklist:
            del self._blacklist[ident]
            count += 1
        
        # Clean user overrides
        expired_overrides = [
            user_id for user_id, override in self._user_overrides.items()
            if override.get('expires_at') and now > override['expires_at']
        ]
        for user_id in expired_overrides:
            del self._user_overrides[user_id]
            count += 1
        
        return count
    
    def get_config_stats(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        return {
            'total_policies': len(self._policies),
            'active_policies': len([p for p in self._policies.values() if p.is_active]),
            'whitelist_size': len(self._whitelist),
            'blacklist_size': len(self._blacklist),
            'user_overrides': len(self._user_overrides),
            'endpoint_overrides': len(self._endpoint_overrides)
        }
    
    def export_config(self, format: str = 'json') -> str:
        """Export configuration to a specific format."""
        config = {
            'policies': [
                {
                    'name': p.name,
                    'description': p.description,
                    'priority': p.priority,
                    'is_active': p.is_active,
                    'effective_from': p.effective_from.isoformat() if p.effective_from else None,
                    'effective_until': p.effective_until.isoformat() if p.effective_until else None,
                    'rules': [
                        {
                            'name': r.name,
                            'limit_type': r.limit_type.value,
                            'limit': r.limit,
                            'period': r.period,
                            'time_unit': r.time_unit.value,
                            'scope': r.scope.value,
                            'burst_limit': r.burst_limit,
                            'burst_period': r.burst_period
                        }
                        for r in p.rules
                    ]
                }
                for p in self._policies.values()
            ],
            'whitelist': list(self._whitelist.keys()),
            'blacklist': list(self._blacklist.keys())
        }
        
        if format == 'json':
            return json.dumps(config, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_config(self, data: str, format: str = 'json') -> int:
        """Import configuration from exported data."""
        if format == 'json':
            config = json.loads(data)
            count = 0
            
            for policy_data in config.get('policies', []):
                rules = [
                    RateLimitRule(
                        name=r['name'],
                        limit_type=LimitType(r['limit_type']),
                        limit=r['limit'],
                        period=r['period'],
                        time_unit=TimeUnit(r['time_unit']),
                        scope=LimitScope(r['scope']),
                        burst_limit=r.get('burst_limit'),
                        burst_period=r.get('burst_period')
                    )
                    for r in policy_data['rules']
                ]
                
                policy = RateLimitPolicy(
                    name=policy_data['name'],
                    description=policy_data['description'],
                    rules=rules,
                    priority=policy_data['priority'],
                    is_active=policy_data['is_active'],
                    effective_from=datetime.fromisoformat(policy_data['effective_from']) if policy_data['effective_from'] else None,
                    effective_until=datetime.fromisoformat(policy_data['effective_until']) if policy_data['effective_until'] else None
                )
                
                self._policies[policy.name] = policy
                count += 1
            
            for identifier in config.get('whitelist', []):
                self._whitelist[identifier] = None
            
            for identifier in config.get('blacklist', []):
                self._blacklist[identifier] = None
            
            return count
        else:
            raise ValueError(f"Unsupported format: {format}")


def get_rate_limiter_config_service(db: Session):
    """Dependency to get rate limiter config service."""
    return RateLimiterConfigService(db)
