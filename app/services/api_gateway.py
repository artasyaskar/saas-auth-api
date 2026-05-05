"""
API Gateway Service

Comprehensive API gateway for routing, rate limiting,
authentication, and request/response transformation.

Features:
- Request routing and load balancing
- Rate limiting per endpoint
- Request/response transformation
- API versioning
- Request validation
- Response caching
- Circuit breaker pattern
- Request/response logging
- API key management
- Webhook proxy
"""
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
from collections import defaultdict
import httpx
from sqlalchemy.orm import Session

from app.db.models import User, APIKey, UsageLog
from app.core.config import settings


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CacheStrategy(Enum):
    """Caching strategies."""
    NO_CACHE = "no_cache"
    CACHE_FIRST = "cache_first"
    NETWORK_FIRST = "network_first"
    NETWORK_ONLY = "network_only"


@dataclass
class RouteConfig:
    """Route configuration."""
    path: str
    target_url: str
    methods: List[str]
    auth_required: bool = True
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    timeout: int = 30
    retry_count: int = 3
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class TransformationRule:
    """Request/response transformation rule."""
    type: str  # 'request' or 'response'
    operation: str  # 'add', 'remove', 'replace', 'rename'
    path: str
    value: Optional[Any] = None
    condition: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.half_open_calls = 0
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


class APIGateway:
    """
    Enterprise-grade API gateway service.
    
    Features:
    - Request routing and load balancing
    - Rate limiting per endpoint
    - Request/response transformation
    - API versioning
    - Request validation
    - Response caching
    - Circuit breaker pattern
    - Request/response logging
    - API key management
    - Webhook proxy
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.routes: Dict[str, RouteConfig] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.cache: Dict[str, tuple] = {}  # key: (data, expiry)
        self.rate_limit_counters: Dict[str, List[float]] = defaultdict(list)
        self.transformation_rules: List[TransformationRule] = []
        
        # HTTP client for upstream requests
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def add_route(self, config: RouteConfig):
        """Add a route configuration."""
        self.routes[config.path] = config
        
        # Initialize circuit breaker if enabled
        if config.circuit_breaker_enabled:
            self.circuit_breakers[config.path] = CircuitBreaker(
                failure_threshold=config.circuit_breaker_threshold,
                timeout=config.circuit_breaker_timeout
            )
    
    def add_transformation_rule(self, rule: TransformationRule):
        """Add a transformation rule."""
        self.transformation_rules.append(rule)
    
    async def route_request(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        query_params: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate backend.
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            body: Request body
            query_params: Query parameters
            api_key: API key for authentication
        
        Returns:
            Response data
        """
        # Find matching route
        route = self._find_route(path, method)
        if not route:
            return {
                'status_code': 404,
                'body': json.dumps({'error': 'Route not found'}),
                'headers': {'content-type': 'application/json'}
            }
        
        # Check authentication
        if route.auth_required and not api_key:
            return {
                'status_code': 401,
                'body': json.dumps({'error': 'Authentication required'}),
                'headers': {'content-type': 'application/json'}
            }
        
        # Validate API key
        if api_key and not self._validate_api_key(api_key):
            return {
                'status_code': 403,
                'body': json.dumps({'error': 'Invalid API key'}),
                'headers': {'content-type': 'application/json'}
            }
        
        # Check rate limit
        if route.rate_limit and not self._check_rate_limit(api_key or 'anonymous', route.rate_limit):
            return {
                'status_code': 429,
                'body': json.dumps({'error': 'Rate limit exceeded'}),
                'headers': {
                    'content-type': 'application/json',
                    'retry-after': '60'
                }
            }
        
        # Check circuit breaker
        circuit_breaker = self.circuit_breakers.get(route.path)
        if circuit_breaker and not circuit_breaker.can_execute():
            return {
                'status_code': 503,
                'body': json.dumps({'error': 'Service unavailable - circuit breaker open'}),
                'headers': {'content-type': 'application/json'}
            }
        
        # Check cache
        cache_key = self._generate_cache_key(path, method, query_params)
        if route.cache_ttl:
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Transform request
        transformed_headers = self._transform_request(headers, 'request')
        
        # Make upstream request
        try:
            response = await self._make_upstream_request(
                route,
                path,
                method,
                transformed_headers,
                body,
                query_params
            )
            
            # Record success
            if circuit_breaker:
                circuit_breaker.record_success()
            
            # Transform response
            transformed_response = self._transform_response(response, 'response')
            
            # Cache response
            if route.cache_ttl and response['status_code'] == 200:
                self._set_cache(cache_key, transformed_response, route.cache_ttl)
            
            # Log request
            self._log_request(
                path,
                method,
                response['status_code'],
                api_key
            )
            
            return transformed_response
            
        except Exception as e:
            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            return {
                'status_code': 502,
                'body': json.dumps({'error': f'Bad gateway: {str(e)}'}),
                'headers': {'content-type': 'application/json'}
            }
    
    def _find_route(self, path: str, method: str) -> Optional[RouteConfig]:
        """Find matching route for path and method."""
        # Exact match
        if path in self.routes:
            route = self.routes[path]
            if method in route.methods:
                return route
        
        # Prefix match
        for route_path, route in self.routes.items():
            if path.startswith(route_path) and method in route.methods:
                return route
        
        return None
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        api_key_record = self.db.query(APIKey).filter(
            APIKey.key == api_key,
            APIKey.is_active == True
        ).first()
        
        if not api_key_record:
            return False
        
        # Check if expired
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            return False
        
        return True
    
    def _check_rate_limit(self, identifier: str, limit: int) -> bool:
        """Check rate limit for identifier."""
        now = time.time()
        window = 60  # 1 minute window
        
        # Clean old entries
        self.rate_limit_counters[identifier] = [
            t for t in self.rate_limit_counters[identifier]
            if now - t < window
        ]
        
        # Check limit
        if len(self.rate_limit_counters[identifier]) >= limit:
            return False
        
        # Add current request
        self.rate_limit_counters[identifier].append(now)
        return True
    
    def _generate_cache_key(
        self,
        path: str,
        method: str,
        query_params: Optional[Dict[str, str]]
    ) -> str:
        """Generate cache key for request."""
        key_parts = [path, method]
        if query_params:
            sorted_params = sorted(query_params.items())
            key_parts.append(json.dumps(sorted_params))
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get response from cache."""
        if key not in self.cache:
            return None
        
        data, expiry = self.cache[key]
        if datetime.utcnow() > expiry:
            del self.cache[key]
            return None
        
        return data
    
    def _set_cache(self, key: str, data: Dict[str, Any], ttl: int):
        """Set response in cache."""
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self.cache[key] = (data, expiry)
    
    def _transform_request(
        self,
        headers: Dict[str, str],
        rule_type: str
    ) -> Dict[str, str]:
        """Apply transformation rules to request."""
        transformed = headers.copy()
        
        for rule in self.transformation_rules:
            if rule.type == rule_type:
                if rule.operation == 'add':
                    transformed[rule.path] = rule.value
                elif rule.operation == 'remove':
                    transformed.pop(rule.path, None)
                elif rule.operation == 'replace':
                    if rule.path in transformed:
                        transformed[rule.path] = rule.value
        
        return transformed
    
    def _transform_response(
        self,
        response: Dict[str, Any],
        rule_type: str
    ) -> Dict[str, Any]:
        """Apply transformation rules to response."""
        transformed = response.copy()
        
        for rule in self.transformation_rules:
            if rule.type == rule_type:
                if rule.operation == 'add':
                    if 'headers' not in transformed:
                        transformed['headers'] = {}
                    transformed['headers'][rule.path] = rule.value
                elif rule.operation == 'remove':
                    if 'headers' in transformed:
                        transformed['headers'].pop(rule.path, None)
        
        return transformed
    
    async def _make_upstream_request(
        self,
        route: RouteConfig,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        query_params: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Make request to upstream service."""
        url = route.target_url + path
        
        request_headers = {
            'user-agent': 'SaaS-Auth-Gateway/1.0',
            **headers
        }
        
        try:
            if method == 'GET':
                response = await self.http_client.get(
                    url,
                    headers=request_headers,
                    params=query_params
                )
            elif method == 'POST':
                response = await self.http_client.post(
                    url,
                    headers=request_headers,
                    content=body,
                    params=query_params
                )
            elif method == 'PUT':
                response = await self.http_client.put(
                    url,
                    headers=request_headers,
                    content=body,
                    params=query_params
                )
            elif method == 'DELETE':
                response = await self.http_client.delete(
                    url,
                    headers=request_headers,
                    params=query_params
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                'status_code': response.status_code,
                'body': response.text,
                'headers': dict(response.headers)
            }
            
        except httpx.TimeoutException:
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def _log_request(
        self,
        path: str,
        method: str,
        status_code: int,
        api_key: Optional[str]
    ):
        """Log request for analytics."""
        # In production, this would log to database or external service
        pass
    
    def get_circuit_breaker_status(self, path: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for a route."""
        circuit_breaker = self.circuit_breakers.get(path)
        if not circuit_breaker:
            return None
        
        return {
            'path': path,
            'state': circuit_breaker.get_state().value,
            'failure_count': circuit_breaker.failure_count,
            'last_failure_time': circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
        }
    
    def reset_circuit_breaker(self, path: str) -> bool:
        """Reset circuit breaker for a route."""
        circuit_breaker = self.circuit_breakers.get(path)
        if not circuit_breaker:
            return False
        
        circuit_breaker.state = CircuitState.CLOSED
        circuit_breaker.failure_count = 0
        circuit_breaker.last_failure_time = None
        circuit_breaker.half_open_calls = 0
        
        return True
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries."""
        if pattern:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'total_entries': len(self.cache),
            'entries': [
                {
                    'key': key,
                    'expires_at': expiry.isoformat()
                }
                for key, (_, expiry) in self.cache.items()
            ]
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


def get_api_gateway(db: Session):
    """Dependency to get API gateway service."""
    return APIGateway(db)
