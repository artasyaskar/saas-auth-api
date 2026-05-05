"""
Audit Logging Middleware

Comprehensive request/response audit logging for compliance and security monitoring.
Captures detailed information about all API requests including:
- User identity and authentication context
- Request details (method, path, headers, body)
- Response details (status, duration)
- Geographic and device information
- PII redaction for privacy compliance
"""
import json
import time
import hashlib
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
import ipaddress

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import AuditLog, User, UserRole
from app.core.config import settings


# Sensitive fields to redact from logs
SENSITIVE_FIELDS = [
    'password', 'token', 'secret', 'api_key', 'apikey',
    'authorization', 'cookie', 'session', 'credit_card',
    'ssn', 'social_security', 'dob', 'date_of_birth'
]

# Patterns to redact from request/response bodies
SENSITIVE_PATTERNS = [
    (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', 'password": "[REDACTED]"'),
    (r'token["\']?\s*[:=]\s*["\'][^"\']+["\']', 'token": "[REDACTED]"'),
    (r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']', 'secret": "[REDACTED]"'),
    (r'api_key["\']?\s*[:=]\s*["\'][^"\']+["\']', 'api_key": "[REDACTED]"'),
    (r'Bearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'Bearer [REDACTED]'),
]


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive audit logging.
    
    Logs all API requests and responses with:
    - User authentication context
    - Request/response details
    - Performance metrics
    - Geographic information
    - PII redaction
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None,
        exclude_methods: Optional[List[str]] = None,
        max_body_size: int = 10000
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            '/health',
            '/metrics',
            '/docs',
            '/openapi.json',
            '/redoc',
            '/favicon.ico',
            '/static/'
        ]
        self.exclude_methods = exclude_methods or ['OPTIONS']
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log audit entry."""
        # Check if path should be excluded
        if self._should_exclude(request):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Capture request details
        audit_data = await self._capture_request(request)
        
        # Process request
        try:
            response = await call_next(request)
            audit_data['response_status'] = response.status_code
            audit_data['success'] = response.status_code < 400
        except Exception as e:
            audit_data['response_status'] = 500
            audit_data['success'] = False
            audit_data['error'] = str(e)
            response = Response(
                content=json.dumps({"error": str(e)}),
                status_code=500
            )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        audit_data['duration_ms'] = duration_ms
        
        # Store audit log
        await self._store_audit_log(audit_data)
        
        return response
    
    def _should_exclude(self, request: Request) -> bool:
        """Check if request should be excluded from audit logging."""
        path = request.url.path
        method = request.method
        
        # Check method exclusion
        if method in self.exclude_methods:
            return True
        
        # Check path exclusion
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path) or path == exclude_path:
                return True
        
        return False
    
    async def _capture_request(self, request: Request) -> Dict[str, Any]:
        """Capture request details for audit log."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get user agent
        user_agent = request.headers.get('user-agent', '')
        
        # Parse user agent
        device_info = self._parse_user_agent(user_agent)
        
        # Get user context
        user_context = await self._get_user_context(request)
        
        # Get request body
        body = await self._get_request_body(request)
        
        # Get relevant headers
        headers = self._filter_headers(dict(request.headers))
        
        return {
            'timestamp': datetime.utcnow(),
            'request_id': request.headers.get('x-request-id', self._generate_request_id()),
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
            'client_ip': client_ip,
            'user_agent': user_agent,
            'device_type': device_info.get('device_type'),
            'browser': device_info.get('browser'),
            'os': device_info.get('os'),
            'user_id': user_context.get('user_id'),
            'username': user_context.get('username'),
            'user_role': user_context.get('role'),
            'auth_method': user_context.get('auth_method'),
            'headers': headers,
            'request_body': self._redact_sensitive_data(body),
            'response_status': None,
            'duration_ms': None,
            'success': None,
            'error': None
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request."""
        # Check X-Forwarded-For header (common with proxies)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return 'unknown'
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string for device info."""
        device_info = {
            'device_type': 'unknown',
            'browser': 'unknown',
            'os': 'unknown'
        }
        
        if not user_agent:
            return device_info
        
        ua = user_agent.lower()
        
        # Detect device type
        if 'mobile' in ua or 'android' in ua and 'mobile' in ua:
            device_info['device_type'] = 'mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device_info['device_type'] = 'tablet'
        elif 'bot' in ua or 'crawler' in ua or 'spider' in ua:
            device_info['device_type'] = 'bot'
        else:
            device_info['device_type'] = 'desktop'
        
        # Detect browser
        if 'chrome' in ua and 'edg' not in ua:
            device_info['browser'] = 'chrome'
        elif 'firefox' in ua:
            device_info['browser'] = 'firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            device_info['browser'] = 'safari'
        elif 'edg' in ua:
            device_info['browser'] = 'edge'
        elif 'opera' in ua or 'opr' in ua:
            device_info['browser'] = 'opera'
        
        # Detect OS
        if 'windows' in ua:
            device_info['os'] = 'windows'
        elif 'macintosh' in ua or 'mac os' in ua:
            device_info['os'] = 'macos'
        elif 'linux' in ua:
            device_info['os'] = 'linux'
        elif 'android' in ua:
            device_info['os'] = 'android'
        elif 'ios' in ua or 'iphone' in ua or 'ipad' in ua:
            device_info['os'] = 'ios'
        
        return device_info
    
    async def _get_user_context(self, request: Request) -> Dict[str, Any]:
        """Extract user context from request."""
        context = {
            'user_id': None,
            'username': None,
            'role': None,
            'auth_method': None
        }
        
        # Check for authorization header
        auth_header = request.headers.get('authorization', '')
        
        if auth_header.startswith('Bearer '):
            context['auth_method'] = 'jwt'
            # Try to extract user from token
            try:
                from app.core.security import verify_token
                token = auth_header.replace('Bearer ', '')
                payload = verify_token(token, 'access')
                context['username'] = payload.get('sub')
                
                # Would need to query DB to get user_id and role
                # For now, store username
            except:
                pass
        elif auth_header.startswith('ApiKey '):
            context['auth_method'] = 'api_key'
        
        # Check for API key header
        api_key = request.headers.get('x-api-key')
        if api_key:
            context['auth_method'] = 'api_key'
        
        return context
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Capture request body if present."""
        try:
            # Check content type
            content_type = request.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='replace')
                    if len(body_str) > self.max_body_size:
                        body_str = body_str[:self.max_body_size] + '...[truncated]'
                    return body_str
        except:
            pass
        
        return None
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter and redact sensitive headers."""
        filtered = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            
            # Skip sensitive headers
            if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                filtered[key] = '[REDACTED]'
            else:
                filtered[key] = value
        
        return filtered
    
    def _redact_sensitive_data(self, data: Optional[str]) -> Optional[str]:
        """Redact sensitive data from string."""
        if not data:
            return None
        
        result = data
        
        # Apply redaction patterns
        for pattern, replacement in SENSITIVE_PATTERNS:
            try:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            except:
                pass
        
        return result
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]
        return f'req_{timestamp}_{random}'
    
    async def _store_audit_log(self, audit_data: Dict[str, Any]):
        """Store audit log in database."""
        try:
            db = SessionLocal()
            
            audit_log = AuditLog(
                timestamp=audit_data['timestamp'],
                action=f"{audit_data['method']} {audit_data['path']}",
                entity_type='api_request',
                entity_id=audit_data['request_id'],
                user_id=audit_data['user_id'],
                username=audit_data['username'],
                ip_address=audit_data['client_ip'],
                details=json.dumps({
                    'method': audit_data['method'],
                    'path': audit_data['path'],
                    'query_params': audit_data['query_params'],
                    'status_code': audit_data['response_status'],
                    'duration_ms': audit_data['duration_ms'],
                    'user_agent': audit_data['user_agent'],
                    'device_type': audit_data['device_type'],
                    'browser': audit_data['browser'],
                    'os': audit_data['os'],
                    'auth_method': audit_data['auth_method'],
                    'request_body': audit_data['request_body'],
                    'success': audit_data['success'],
                    'error': audit_data.get('error')
                }, default=str),
                severity='info' if audit_data['success'] else 'warning',
                status='success' if audit_data['success'] else 'failure'
            )
            
            db.add(audit_log)
            db.commit()
            db.close()
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"[Audit Error] Failed to store audit log: {e}")


class AuditLogger:
    """
    Manual audit logging utility for specific events.
    
    Use for logging business events not captured by middleware:
    - User actions (login, logout, password change)
    - Data modifications
    - Security events
    - Admin actions
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_event(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = 'info',
        status: str = 'success'
    ) -> AuditLog:
        """Log a specific audit event."""
        audit_log = AuditLog(
            timestamp=datetime.utcnow(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=json.dumps(details, default=str) if details else None,
            severity=severity,
            status=status
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def log_user_action(
        self,
        user_id: int,
        username: str,
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a user action."""
        return self.log_event(
            action=action,
            entity_type='user',
            entity_id=str(user_id),
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details,
            severity='info'
        )
    
    def log_security_event(
        self,
        action: str,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = 'warning'
    ):
        """Log a security-related event."""
        return self.log_event(
            action=action,
            entity_type='security',
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details,
            severity=severity,
            status='alert'
        )
    
    def log_admin_action(
        self,
        admin_user_id: int,
        admin_username: str,
        action: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log an admin action."""
        return self.log_event(
            action=f"admin:{action}",
            entity_type=target_type,
            entity_id=target_id,
            user_id=admin_user_id,
            username=admin_username,
            ip_address=ip_address,
            details=details,
            severity='info'
        )
    
    def log_data_change(
        self,
        user_id: int,
        username: str,
        action: str,  # create, update, delete
        entity_type: str,
        entity_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log a data modification event."""
        return self.log_event(
            action=f"data:{action}",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={
                'old_values': old_values,
                'new_values': new_values
            },
            severity='info'
        )
    
    def log_auth_event(
        self,
        action: str,  # login, logout, login_failed, password_changed
        username: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """Log an authentication event."""
        severity = 'info' if success else 'warning'
        if action in ['login_failed', 'password_reset_attempt', 'suspicious_activity']:
            severity = 'warning'
        
        return self.log_event(
            action=f"auth:{action}",
            entity_type='authentication',
            entity_id=str(user_id) if user_id else username,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details,
            severity=severity,
            status='success' if success else 'failure'
        )
    
    def log_token_action(
        self,
        user_id: int,
        username: str,
        action: str,  # created, revoked, refreshed, blacklisted
        token_type: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a token-related action."""
        return self.log_event(
            action=f"token:{action}",
            entity_type='token',
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={
                'token_type': token_type,
                **(details or {})
            },
            severity='info'
        )
    
    def log_api_key_action(
        self,
        user_id: int,
        username: str,
        action: str,  # created, revoked, updated
        api_key_id: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an API key action."""
        return self.log_event(
            action=f"api_key:{action}",
            entity_type='api_key',
            entity_id=api_key_id,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details,
            severity='info'
        )


def audit_log(
    action: str,
    entity_type: str = 'api_request',
    entity_id: Optional[str] = None
):
    """
    Decorator for adding audit logging to specific endpoints.
    
    Usage:
        @audit_log(action="user_delete", entity_type="user")
        async def delete_user(user_id: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            logger = AuditLogger(db)
            
            try:
                result = await func(*args, **kwargs)
                
                # Log success
                logger.log_event(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id or str(kwargs.get('id', 'unknown')),
                    status='success'
                )
                
                return result
            except Exception as e:
                # Log failure
                logger.log_event(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id or str(kwargs.get('id', 'unknown')),
                    status='failure',
                    severity='error',
                    details={'error': str(e)}
                )
                raise
            finally:
                db.close()
        
        return wrapper
    return decorator
