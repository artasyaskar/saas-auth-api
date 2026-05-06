"""
Enhanced logging middleware for comprehensive request tracking.

Handles request logging, performance monitoring, and
detailed audit logging with proper security considerations.
"""

import time
import uuid
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from app.core.config import settings
from app.core.exceptions import SecurityError
from app.services.authorization import AuthorizationService


class EnhancedLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced logging middleware for comprehensive request tracking.
    
    Handles request logging, performance monitoring, and
    detailed audit logging with proper security considerations.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = structlog.get_logger()
        
        # TODO: Add log aggregation
        # TODO: Add distributed tracing
        # TODO: Add log sampling
        # TODO: Add PII detection and redaction
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with enhanced logging.
        
        Args:
            request: HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract request information
        request_info = self._extract_request_info(request)
        
        # Log request start
        self._log_request_start(request_id, request_info)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate timing
            process_time = time.time() - start_time
            
            # Extract response information
            response_info = self._extract_response_info(response, process_time)
            
            # Log request completion
            self._log_request_complete(request_id, request_info, response_info)
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{process_time:.4f}"
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            process_time = time.time() - start_time
            error_info = self._extract_error_info(e, process_time)
            
            self._log_request_error(request_id, request_info, error_info)
            
            # Re-raise the exception
            raise
            
        except Exception as e:
            # Handle unexpected exceptions
            process_time = time.time() - start_time
            error_info = self._extract_unexpected_error_info(e, process_time)
            
            self._log_request_error(request_id, request_info, error_info)
            
            # Re-raise the exception
            raise
    
    def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """
        Extract comprehensive request information.
        
        Args:
            request: HTTP request
            
        Returns:
            Request information dictionary
        """
        # Basic request info
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract sensitive data with redaction
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_info["body"] = self._redact_sensitive_data(body)
            except:
                request_info["body"] = None
        
        # Extract authentication info
        auth_info = self._extract_auth_info(request)
        if auth_info:
            request_info["auth"] = auth_info
        
        # Extract security info
        security_info = self._extract_security_info(request)
        if security_info:
            request_info["security"] = security_info
        
        return request_info
    
    def _extract_response_info(self, response: Response, process_time: float) -> Dict[str, Any]:
        """
        Extract comprehensive response information.
        
        Args:
            response: HTTP response
            process_time: Request processing time
            
        Returns:
            Response information dictionary
        """
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
            "process_time": process_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_error_info(self, exception: HTTPException, process_time: float) -> Dict[str, Any]:
        """
        Extract HTTP exception information.
        
        Args:
            exception: HTTP exception
            process_time: Request processing time
            
        Returns:
            Error information dictionary
        """
        return {
            "type": "http_exception",
            "status_code": exception.status_code,
            "detail": exception.detail,
            "headers": getattr(exception, "headers", None),
            "process_time": process_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_unexpected_error_info(self, exception: Exception, process_time: float) -> Dict[str, Any]:
        """
        Extract unexpected exception information.
        
        Args:
            exception: Unexpected exception
            process_time: Request processing time
            
        Returns:
            Error information dictionary
        """
        return {
            "type": "unexpected_error",
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "traceback": self._get_traceback_info(exception),
            "process_time": process_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _extract_auth_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract authentication information from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Authentication information or None
        """
        # TODO: Extract JWT token info
        # TODO: Extract API key info
        # TODO: Extract session info
        # TODO: Extract OAuth info
        
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        
        # Basic auth info extraction
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer "
            return {
                "type": "bearer",
                "token_length": len(token),
                "token_hash": self._hash_token(token) if token else None
            }
        elif auth_header.startswith("Basic "):
            return {
                "type": "basic",
                "has_credentials": True
            }
        
        return {
            "type": "unknown",
            "header_length": len(auth_header)
        }
    
    def _extract_security_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract security-related information from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Security information or None
        """
        security_info = {}
        
        # Check for suspicious headers
        suspicious_headers = []
        for header_name, header_value in request.headers.items():
            if self._is_suspicious_header(header_name, header_value):
                suspicious_headers.append(header_name)
        
        if suspicious_headers:
            security_info["suspicious_headers"] = suspicious_headers
        
        # Check for suspicious patterns
        suspicious_patterns = self._check_suspicious_patterns(request)
        if suspicious_patterns:
            security_info["suspicious_patterns"] = suspicious_patterns
        
        # Check for rate limiting indicators
        rate_limit_info = self._check_rate_limit_indicators(request)
        if rate_limit_info:
            security_info["rate_limit_indicators"] = rate_limit_info
        
        # Check for bot indicators
        bot_info = self._check_bot_indicators(request)
        if bot_info:
            security_info["bot_indicators"] = bot_info
        
        return security_info if security_info else None
    
    def _redact_sensitive_data(self, data: bytes) -> Dict[str, Any]:
        """
        Redact sensitive data from request body.
        
        Args:
            data: Request body data
            
        Returns:
            Redacted data dictionary
        """
        try:
            # Try to parse as JSON
            body_str = data.decode('utf-8')
            body_data = json.loads(body_str)
            
            # Redact sensitive fields
            sensitive_fields = [
                'password', 'token', 'secret', 'key', 'credit_card',
                'ssn', 'social_security', 'bank_account'
            ]
            
            redacted_data = self._recursive_redact(body_data, sensitive_fields)
            
            return {
                "type": "json",
                "size": len(data),
                "redacted_fields": self._find_redacted_fields(body_data, sensitive_fields),
                "data": redacted_data
            }
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON, return basic info
            return {
                "type": "binary",
                "size": len(data),
                "redacted_fields": [],
                "data": None
            }
    
    def _recursive_redact(self, data: Any, sensitive_fields: List[str]) -> Any:
        """
        Recursively redact sensitive fields from data.
        
        Args:
            data: Data to redact
            sensitive_fields: List of sensitive field names
            
        Returns:
            Redacted data
        """
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if key.lower() in sensitive_fields:
                    redacted[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    redacted[key] = self._recursive_redact(value, sensitive_fields)
                else:
                    redacted[key] = value
            return redacted
        elif isinstance(data, list):
            return [self._recursive_redact(item, sensitive_fields) for item in data]
        else:
            return data
    
    def _find_redacted_fields(self, data: Any, sensitive_fields: List[str]) -> List[str]:
        """
        Find all redacted fields in data.
        
        Args:
            data: Data to search
            sensitive_fields: List of sensitive field names
            
        Returns:
            List of redacted field paths
        """
        redacted_fields = []
        
        def _find_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.lower() in sensitive_fields:
                        redacted_fields.append(current_path)
                    _find_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _find_recursive(item, f"{path}[{i}]")
        
        _find_recursive(data)
        return redacted_fields
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to client IP
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_header(self, header_name: str, header_value: str) -> bool:
        """
        Check if header is suspicious.
        
        Args:
            header_name: Header name
            header_value: Header value
            
        Returns:
            True if suspicious, False otherwise
        """
        suspicious_patterns = [
            "sql", "script", "alert", "onerror", "onload",
            "<script", "javascript:", "vbscript:", "data:text/html"
        ]
        
        header_lower = header_value.lower()
        return any(pattern in header_lower for pattern in suspicious_patterns)
    
    def _check_suspicious_patterns(self, request: Request) -> List[str]:
        """
        Check for suspicious patterns in request.
        
        Args:
            request: HTTP request
            
        Returns:
            List of suspicious patterns found
        """
        patterns = []
        
        # Check URL for suspicious patterns
        url = str(request.url)
        suspicious_url_patterns = [
            "../", "..\\", "admin", "config", "backup",
            "test", "debug", "trace", "phpinfo"
        ]
        
        url_lower = url.lower()
        for pattern in suspicious_url_patterns:
            if pattern in url_lower:
                patterns.append(f"url_contains_{pattern}")
        
        # Check query parameters for suspicious patterns
        for param, value in request.query_params.items():
            if self._is_suspicious_header(param, str(value)):
                patterns.append(f"param_{param}_suspicious")
        
        return patterns
    
    def _check_rate_limit_indicators(self, request: Request) -> List[str]:
        """
        Check for rate limiting indicators.
        
        Args:
            request: HTTP request
            
        Returns:
            List of rate limiting indicators
        """
        indicators = []
        
        # Check for rate limit headers
        if "x-rate-limit-remaining" in request.headers:
            indicators.append("client_aware_of_rate_limit")
        
        # Check for rapid request patterns
        # TODO: Implement request rate tracking
        # TODO: Add sliding window analysis
        
        return indicators
    
    def _check_bot_indicators(self, request: Request) -> List[str]:
        """
        Check for bot indicators.
        
        Args:
            request: HTTP request
            
        Returns:
            List of bot indicators
        """
        indicators = []
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Common bot patterns
        bot_patterns = [
            "bot", "crawler", "spider", "scraper", "curl",
            "wget", "python", "java", "node", "go", "rust"
        ]
        
        for pattern in bot_patterns:
            if pattern in user_agent:
                indicators.append(f"user_agent_contains_{pattern}")
        
        return indicators
    
    def _hash_token(self, token: str) -> str:
        """
        Hash token for logging.
        
        Args:
            token: Token to hash
            
        Returns:
            Hashed token
        """
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def _get_traceback_info(self, exception: Exception) -> Optional[str]:
        """
        Get traceback information for logging.
        
        Args:
            exception: Exception
            
        Returns:
            Traceback string or None
        """
        import traceback
        
        if settings.app.debug:
            return traceback.format_exc()
        else:
            return None
    
    def _log_request_start(self, request_id: str, request_info: Dict[str, Any]):
        """
        Log request start event.
        
        Args:
            request_id: Request identifier
            request_info: Request information
        """
        self.logger.info(
            "request_started",
            request_id=request_id,
            method=request_info["method"],
            path=request_info["path"],
            client_ip=request_info["client_ip"],
            user_agent=request_info["user_agent"],
            timestamp=request_info["timestamp"]
        )
    
    def _log_request_complete(self, request_id: str, request_info: Dict[str, Any], response_info: Dict[str, Any]):
        """
        Log request completion event.
        
        Args:
            request_id: Request identifier
            request_info: Request information
            response_info: Response information
        """
        log_data = {
            "request_id": request_id,
            "method": request_info["method"],
            "path": request_info["path"],
            "status_code": response_info["status_code"],
            "process_time": response_info["process_time"],
            "client_ip": request_info["client_ip"],
            "user_agent": request_info["user_agent"],
            "timestamp": response_info["timestamp"]
        }
        
        # Add security info if present
        if "security" in request_info:
            log_data["security"] = request_info["security"]
        
        # Add performance info
        if response_info["process_time"] > 1.0:  # Slow request
            self.logger.warning(
                "slow_request",
                **log_data
            )
        else:
            self.logger.info(
                "request_completed",
                **log_data
            )
    
    def _log_request_error(self, request_id: str, request_info: Dict[str, Any], error_info: Dict[str, Any]):
        """
        Log request error event.
        
        Args:
            request_id: Request identifier
            request_info: Request information
            error_info: Error information
        """
        log_data = {
            "request_id": request_id,
            "method": request_info["method"],
            "path": request_info["path"],
            "error_type": error_info["type"],
            "process_time": error_info["process_time"],
            "client_ip": request_info["client_ip"],
            "user_agent": request_info["user_agent"],
            "timestamp": error_info["timestamp"]
        }
        
        # Add error-specific info
        if error_info["type"] == "http_exception":
            log_data["status_code"] = error_info["status_code"]
            log_data["detail"] = error_info["detail"]
        elif error_info["type"] == "unexpected_error":
            log_data["exception_type"] = error_info["exception_type"]
            log_data["message"] = error_info["message"]
            if error_info["traceback"]:
                log_data["traceback"] = error_info["traceback"]
        
        self.logger.error(
            "request_error",
            **log_data
        )


# Factory function
def create_enhanced_logging_middleware(app) -> EnhancedLoggingMiddleware:
    """
    Create enhanced logging middleware instance.
    
    Args:
        app: ASGI application
        
    Returns:
        EnhancedLoggingMiddleware instance
    """
    return EnhancedLoggingMiddleware(app)
