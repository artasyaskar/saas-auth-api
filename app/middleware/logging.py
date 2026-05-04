"""
Structured logging middleware for API requests.
Logs all requests with timing, status codes, and user information.
"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.core.config import settings

# Configure structlog for structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests with structured logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract user info if available
        user_id = None
        username = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            username = getattr(request.state.user, "username", None)
        
        # Log request start
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
            user_id=user_id,
            username=username,
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Log response
            logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=user_id,
                username=username,
            )
            
            return response
            
        except Exception as exc:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                error_type=type(exc).__name__,
                user_id=user_id,
                username=username,
            )
            raise


class AuditLogger:
    """Audit logging for security-sensitive operations."""
    
    @staticmethod
    def log_login_attempt(username: str, success: bool, ip_address: str = None, 
                       user_agent: str = None, failure_reason: str = None):
        """Log a login attempt."""
        log_data = {
            "event": "login_attempt",
            "username": username,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        if failure_reason:
            log_data["failure_reason"] = failure_reason
        
        if success:
            logger.info("security_login_success", **log_data)
        else:
            logger.warning("security_login_failure", **log_data)
    
    @staticmethod
    def log_token_action(user_id: int, username: str, action: str, 
                        token_type: str, ip_address: str = None):
        """Log token-related actions (refresh, revoke, etc.)."""
        logger.info(
            "security_token_action",
            user_id=user_id,
            username=username,
            action=action,
            token_type=token_type,
            ip_address=ip_address,
        )
    
    @staticmethod
    def log_admin_action(admin_id: int, admin_username: str, action: str, 
                        target_type: str, target_id: int = None, details: dict = None):
        """Log admin actions."""
        log_data = {
            "event": "admin_action",
            "admin_id": admin_id,
            "admin_username": admin_username,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
        }
        if details:
            log_data["details"] = details
        logger.info("security_admin_action", **log_data)
    
    @staticmethod
    def log_password_reset(user_id: int, username: str, action: str, 
                          ip_address: str = None, success: bool = True):
        """Log password reset attempts."""
        log_data = {
            "event": "password_reset",
            "user_id": user_id,
            "username": username,
            "action": action,  # "request", "complete"
            "ip_address": ip_address,
            "success": success,
        }
        if success:
            logger.info("security_password_reset", **log_data)
        else:
            logger.warning("security_password_reset_failed", **log_data)


audit_logger = AuditLogger()
