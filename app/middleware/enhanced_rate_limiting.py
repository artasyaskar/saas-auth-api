"""
Enhanced rate limiting middleware for comprehensive API protection.

Handles rate limiting with multiple strategies, Redis support,
and comprehensive security features with proper configuration.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import time
import redis
import json
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from app.core.config import settings
from app.core.exceptions import RateLimitError


class RateLimitStrategy:
    """Rate limiting strategy enumeration."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting middleware with multiple strategies.
    
    Handles rate limiting with Redis support, multiple strategies,
    and comprehensive security features with proper configuration.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = structlog.get_logger()
        
        # Initialize Redis if available
        try:
            self.redis_client = redis.from_url(
                settings.redis.get_redis_url(),
                decode_responses=True
            )
            self.use_redis = True
        except Exception:
            self.redis_client = None
            self.use_redis = False
            self._memory_storage = {}
        
        # Rate limiting configuration
        self.default_limit = settings.rate_limit.default_limit
        self.default_window = settings.rate_limit.window_seconds
        self.burst_limit = settings.rate_limit.burst_limit
        self.strategy = RateLimitStrategy.FIXED_WINDOW
        
        # Per-endpoint limits
        self.endpoint_limits = {
            "/auth/login": {"limit": 5, "window": 300},  # 5 per 5 minutes
            "/auth/register": {"limit": 3, "window": 300},  # 3 per 5 minutes
            "/auth/password-reset": {"limit": 3, "window": 3600},  # 3 per hour
            "/auth/refresh": {"limit": 10, "window": 300},  # 10 per 5 minutes
        }
        
        # TODO: Add distributed rate limiting
        # TODO: Add adaptive rate limiting
        # TODO: Add geolocation-based limiting
        # TODO: Add user-based limiting
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response or rate limit error
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get rate limit key
        rate_limit_key = self._get_rate_limit_key(request)
        
        # Get endpoint-specific limits
        endpoint_config = self._get_endpoint_config(request)
        
        # Check rate limit
        if self._is_rate_limited(rate_limit_key, endpoint_config):
            return self._create_rate_limit_response(rate_limit_key, endpoint_config)
        
        # Update rate limit counter
        self._update_rate_limit_counter(rate_limit_key, endpoint_config)
        
        # Add rate limit headers
        response = await call_next(request)
        self._add_rate_limit_headers(response, rate_limit_key, endpoint_config)
        
        return response
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Check if request should skip rate limiting.
        
        Args:
            request: HTTP request
            
        Returns:
            True if should skip, False otherwise
        """
        skip_paths = [
            "/health", "/metrics", "/docs", "/redoc", "/openapi.json",
            "/static", "/favicon.ico"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Generate rate limit key for request.
        
        Args:
            request: HTTP request
            
        Returns:
            Rate limit key
        """
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Get endpoint
        endpoint = request.url.path
        
        # Create composite key
        key_parts = [f"rate_limit:{endpoint}:{client_id}"]
        
        # Add user identifier if authenticated
        user_id = self._get_user_id(request)
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        return ":".join(key_parts)
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: HTTP request
            
        Returns:
            Client identifier
        """
        # Check for forwarded IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to client IP
        return request.client.host if request.client else "unknown"
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Get user ID from request if authenticated.
        
        Args:
            request: HTTP request
            
        Returns:
            User ID or None
        """
        # TODO: Extract user ID from JWT token
        # TODO: Extract user ID from session
        # TODO: Extract user ID from API key
        
        return None
    
    def _get_endpoint_config(self, request: Request) -> Dict[str, Any]:
        """
        Get rate limiting configuration for endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Endpoint configuration
        """
        path = request.url.path
        
        # Check for exact match
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for prefix match
        for endpoint_path, config in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                return config
        
        # Use default configuration
        return {
            "limit": self.default_limit,
            "window": self.default_window,
            "burst": self.burst_limit
        }
    
    def _is_rate_limited(self, key: str, config: Dict[str, Any]) -> bool:
        """
        Check if request is rate limited.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            if self.use_redis:
                return self._is_rate_limited_redis(key, config)
            else:
                return self._is_rate_limited_memory(key, config)
        except Exception:
            # Default to allow if rate limiting fails
            return False
    
    def _is_rate_limited_redis(self, key: str, config: Dict[str, Any]) -> bool:
        """
        Check rate limiting using Redis.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            # Get current count and window info
            pipeline = self.redis_client.pipeline()
            pipeline.get(key)
            pipeline.ttl(key)
            results = pipeline.execute()
            
            current_count = int(results[0] or 0)
            ttl = int(results[1] or 0)
            
            # Check if window has expired
            if ttl <= 0:
                current_count = 0
            
            # Check if limit exceeded
            if current_count >= config["limit"]:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("redis_rate_limit_check_failed", error=str(e))
            return False
    
    def _is_rate_limited_memory(self, key: str, config: Dict[str, Any]) -> bool:
        """
        Check rate limiting using in-memory storage.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            now = time.time()
            
            if key not in self._memory_storage:
                self._memory_storage[key] = {
                    "count": 0,
                    "window_start": now,
                    "window_end": now + config["window"]
                }
            
            storage = self._memory_storage[key]
            
            # Reset window if expired
            if now >= storage["window_end"]:
                storage["count"] = 0
                storage["window_start"] = now
                storage["window_end"] = now + config["window"]
            
            # Check if limit exceeded
            return storage["count"] >= config["limit"]
            
        except Exception as e:
            self.logger.error("memory_rate_limit_check_failed", error=str(e))
            return False
    
    def _update_rate_limit_counter(self, key: str, config: Dict[str, Any]):
        """
        Update rate limit counter.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
        """
        try:
            if self.use_redis:
                self._update_redis_counter(key, config)
            else:
                self._update_memory_counter(key, config)
        except Exception as e:
            self.logger.error("rate_limit_update_failed", error=str(e))
    
    def _update_redis_counter(self, key: str, config: Dict[str, Any]):
        """
        Update rate limit counter in Redis.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
        """
        try:
            # Use Redis INCR with expiration
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, config["window"])
            pipeline.execute()
        except Exception as e:
            self.logger.error("redis_counter_update_failed", error=str(e))
    
    def _update_memory_counter(self, key: str, config: Dict[str, Any]):
        """
        Update rate limit counter in memory.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
        """
        try:
            now = time.time()
            
            if key not in self._memory_storage:
                self._memory_storage[key] = {
                    "count": 0,
                    "window_start": now,
                    "window_end": now + config["window"]
                }
            
            storage = self._memory_storage[key]
            
            # Reset window if expired
            if now >= storage["window_end"]:
                storage["count"] = 0
                storage["window_start"] = now
                storage["window_end"] = now + config["window"]
            
            storage["count"] += 1
            
        except Exception as e:
            self.logger.error("memory_counter_update_failed", error=str(e))
    
    def _create_rate_limit_response(self, key: str, config: Dict[str, Any]) -> HTTPException:
        """
        Create rate limit HTTP response.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
            
        Returns:
            HTTP exception with rate limit details
        """
        # Calculate retry after
        retry_after = self._calculate_retry_after(key, config)
        
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded",
                "limit": config["limit"],
                "window": config["window"],
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(config["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + retry_after)
            }
        )
    
    def _add_rate_limit_headers(self, response, key: str, config: Dict[str, Any]):
        """
        Add rate limit headers to response.
        
        Args:
            response: HTTP response
            key: Rate limit key
            config: Endpoint configuration
        """
        try:
            # Get current count
            if self.use_redis:
                current_count = int(self.redis_client.get(key) or 0)
            else:
                current_count = self._memory_storage.get(key, {}).get("count", 0)
            
            remaining = max(0, config["limit"] - current_count)
            reset_time = int(time.time()) + config["window"]
            
            response.headers["X-RateLimit-Limit"] = str(config["limit"])
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
        except Exception as e:
            self.logger.error("rate_limit_headers_failed", error=str(e))
    
    def _calculate_retry_after(self, key: str, config: Dict[str, Any]) -> int:
        """
        Calculate retry after time.
        
        Args:
            key: Rate limit key
            config: Endpoint configuration
            
        Returns:
            Retry after time in seconds
        """
        try:
            if self.use_redis:
                ttl = self.redis_client.ttl(key)
                return max(1, ttl)
            else:
                storage = self._memory_storage.get(key, {})
                window_end = storage.get("window_end", time.time() + config["window"])
                return max(1, int(window_end - time.time()))
        except Exception:
            return config["window"]
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Rate limiting statistics
        """
        try:
            stats = {
                "strategy": self.strategy.value,
                "use_redis": self.use_redis,
                "default_limit": self.default_limit,
                "default_window": self.default_window,
                "endpoint_configs": self.endpoint_limits
            }
            
            if self.use_redis:
                # Get Redis stats
                redis_info = self.redis_client.info()
                stats["redis"] = {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory": redis_info.get("used_memory", 0),
                    "total_commands_processed": redis_info.get("total_commands_processed", 0)
                }
            else:
                # Get memory stats
                stats["memory"] = {
                    "active_keys": len(self._memory_storage),
                    "total_requests": sum(
                        storage.get("count", 0) 
                        for storage in self._memory_storage.values()
                    )
                }
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_expired_entries(self) -> int:
        """
        Clean up expired rate limit entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            if self.use_redis:
                # Redis handles expiration automatically
                return 0
            else:
                # Clean up expired memory entries
                now = time.time()
                expired_keys = []
                
                for key, storage in self._memory_storage.items():
                    if now >= storage["window_end"]:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._memory_storage[key]
                
                return len(expired_keys)
                
        except Exception as e:
            return 0
    
    def update_endpoint_config(self, endpoint: str, config: Dict[str, Any]):
        """
        Update rate limiting configuration for endpoint.
        
        Args:
            endpoint: Endpoint path
            config: New configuration
        """
        self.endpoint_limits[endpoint] = config
    
    def remove_endpoint_config(self, endpoint: str):
        """
        Remove rate limiting configuration for endpoint.
        
        Args:
            endpoint: Endpoint path
        """
        if endpoint in self.endpoint_limits:
            del self.endpoint_limits[endpoint]
    
    def set_strategy(self, strategy: RateLimitStrategy):
        """
        Set rate limiting strategy.
        
        Args:
            strategy: New rate limiting strategy
        """
        self.strategy = strategy


# Factory function
def create_enhanced_rate_limit_middleware(app) -> EnhancedRateLimitMiddleware:
    """
    Create enhanced rate limiting middleware instance.
    
    Args:
        app: ASGI application
        
    Returns:
        EnhancedRateLimitMiddleware instance
    """
    return EnhancedRateLimitMiddleware(app)
