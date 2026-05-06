"""
Comprehensive request validation middleware.

Provides advanced request validation including:
- Request body validation
- Query parameter validation
- Header validation
- Rate limiting validation
- Security validation
- Content type validation
"""

from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json
import re
import time
from urllib.parse import parse_qs

from app.core.exceptions import ValidationError, SecurityError
from app.core.config import settings


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive request validation middleware.
    
    Validates incoming requests for security, format, and content compliance.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.max_request_size = getattr(settings, 'max_request_size', 10 * 1024 * 1024)  # 10MB
        self.allowed_content_types = getattr(settings, 'allowed_content_types', [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
            'text/plain'
        ])
        self.required_headers = getattr(settings, 'required_headers', [])
        self.blocked_user_agents = getattr(settings, 'blocked_user_agents', [])
        self.max_query_params = getattr(settings, 'max_query_params', 100)
        
        # Security patterns
        self.sql_injection_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(--|#|\/\*|\*\/)',
            r'(\bOR\b.*=.*\bOR\b)',
            r'(\bAND\b.*=.*\bAND\b)',
        ]
        
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Validate request before processing.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or validation error
        """
        # Skip validation for health checks and docs
        if self._should_skip_validation(request):
            return await call_next(request)
        
        try:
            # Perform validation checks
            await self._validate_request_size(request)
            await self._validate_content_type(request)
            await self._validate_headers(request)
            await self._validate_user_agent(request)
            await self._validate_query_parameters(request)
            await self._validate_security_patterns(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = self._add_security_headers(response)
            
            return response
            
        except ValidationError as e:
            return self._create_validation_error_response(e)
        except SecurityError as e:
            return self._create_security_error_response(e)
        except Exception as e:
            return self._create_generic_error_response(e)
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if request should skip validation."""
        skip_paths = [
            '/health',
            '/',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico'
        ]
        return request.url.path in skip_paths
    
    async def _validate_request_size(self, request: Request) -> None:
        """Validate request size."""
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_request_size:
            raise ValidationError(
                f"Request size {content_length} exceeds maximum allowed size {self.max_request_size}",
                field="content-length"
            )
    
    async def _validate_content_type(self, request: Request) -> None:
        """Validate content type."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '').split(';')[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                raise ValidationError(
                    f"Content type '{content_type}' is not allowed",
                    field="content-type"
                )
    
    async def _validate_headers(self, request: Request) -> None:
        """Validate required headers."""
        for header in self.required_headers:
            if header not in request.headers:
                raise ValidationError(
                    f"Required header '{header}' is missing",
                    field=header
                )
    
    async def _validate_user_agent(self, request: Request) -> None:
        """Validate user agent against blocked patterns."""
        user_agent = request.headers.get('user-agent', '')
        for blocked_pattern in self.blocked_user_agents:
            if re.search(blocked_pattern, user_agent, re.IGNORECASE):
                raise SecurityError(
                    "Blocked user agent detected",
                    security_code="blocked_user_agent"
                )
    
    async def _validate_query_parameters(self, request: Request) -> None:
        """Validate query parameters."""
        query_string = str(request.url.query)
        if query_string:
            params = parse_qs(query_string)
            if len(params) > self.max_query_params:
                raise ValidationError(
                    f"Too many query parameters: {len(params)} > {self.max_query_params}",
                    field="query"
                )
            
            # Validate parameter values
            for key, values in params.items():
                for value in values:
                    await self._validate_parameter_value(key, value)
    
    async def _validate_parameter_value(self, key: str, value: str) -> None:
        """Validate individual parameter value."""
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise SecurityError(
                    f"Potential SQL injection detected in parameter '{key}'",
                    security_code="sql_injection"
                )
        
        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise SecurityError(
                    f"Potential XSS detected in parameter '{key}'",
                    security_code="xss"
                )
    
    async def _validate_security_patterns(self, request: Request) -> None:
        """Validate request for security patterns."""
        # Check request body for security issues
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    
                    # Check for SQL injection
                    for pattern in self.sql_injection_patterns:
                        if re.search(pattern, body_str, re.IGNORECASE):
                            raise SecurityError(
                                "Potential SQL injection detected in request body",
                                security_code="sql_injection"
                            )
                    
                    # Check for XSS
                    for pattern in self.xss_patterns:
                        if re.search(pattern, body_str, re.IGNORECASE):
                            raise SecurityError(
                                "Potential XSS detected in request body",
                                security_code="xss"
                            )
            except Exception:
                # If we can't read the body, skip validation
                pass
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response
    
    def _create_validation_error_response(self, error: ValidationError) -> JSONResponse:
        """Create validation error response."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": error.message,
                "details": error.details,
                "timestamp": time.time()
            }
        )
    
    def _create_security_error_response(self, error: SecurityError) -> JSONResponse:
        """Create security error response."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "security_error",
                "message": error.message,
                "details": error.details,
                "timestamp": time.time()
            }
        )
    
    def _create_generic_error_response(self, error: Exception) -> JSONResponse:
        """Create generic error response."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An internal server error occurred",
                "timestamp": time.time()
            }
        )


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """
    API key validation middleware for protected endpoints.
    """
    
    def __init__(self, app, protected_paths: List[str] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or []
        self.api_key_header = 'X-API-Key'
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Validate API key for protected endpoints.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or validation error
        """
        # Check if path is protected
        if self._is_protected_path(request):
            api_key = request.headers.get(self.api_key_header)
            if not api_key:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "missing_api_key",
                        "message": f"API key required in '{self.api_key_header}' header",
                        "timestamp": time.time()
                    }
                )
            
            # Validate API key (this would integrate with your API key service)
            if not await self._validate_api_key(api_key):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_api_key",
                        "message": "Invalid API key provided",
                        "timestamp": time.time()
                    }
                )
        
        return await call_next(request)
    
    def _is_protected_path(self, request: Request) -> bool:
        """Check if request path is protected."""
        for path in self.protected_paths:
            if request.url.path.startswith(path):
                return True
        return False
    
    async def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key (placeholder implementation)."""
        # TODO: Implement actual API key validation
        # This would check against your database or API key service
        return len(api_key) >= 32  # Simple length check for now


class RateLimitValidationMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting validation middleware.
    """
    
    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Validate rate limits.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or rate limit error
        """
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_requests(current_time)
        
        # Check rate limit
        if not self._check_rate_limit(client_ip, current_time):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Try again in {self.window_seconds} seconds",
                    "retry_after": self.window_seconds,
                    "timestamp": current_time
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Record request
        self._record_request(client_ip, current_time)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else 'unknown'
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Clean old request records."""
        cutoff_time = current_time - self.window_seconds
        
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if req_time > cutoff_time
            ]
            
            if not self.requests[ip]:
                del self.requests[ip]
    
    def _check_rate_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client is within rate limit."""
        if client_ip not in self.requests:
            return True
        
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time <= self.window_seconds
        ]
        
        return len(recent_requests) < self.default_limit
    
    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record request for rate limiting."""
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        self.requests[client_ip].append(current_time)
