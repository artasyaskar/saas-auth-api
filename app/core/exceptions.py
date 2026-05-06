"""
Custom exceptions for the application.

Defines specific exception types for better error handling
and user feedback throughout the application.
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, errors: Optional[List[str]] = None):
        details = {}
        if field:
            details["field"] = field
        if errors:
            details["errors"] = errors
        
        super().__init__(message, details)


class AuthenticationError(BaseAppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        details = {}
        if error_code:
            details["error_code"] = error_code
        
        super().__init__(message, details)


class AuthorizationError(BaseAppException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None):
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(message, details)


class NotFoundError(BaseAppException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(message, details)


class ConflictError(BaseAppException):
    """Raised when a resource conflict occurs."""
    
    def __init__(self, message: str, conflict_type: Optional[str] = None):
        details = {}
        if conflict_type:
            details["conflict_type"] = conflict_type
        
        super().__init__(message, details)


class RateLimitError(BaseAppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(message, details)


class SecurityError(BaseAppException):
    """Raised when a security issue is detected."""
    
    def __init__(self, message: str, security_code: Optional[str] = None):
        details = {}
        if security_code:
            details["security_code"] = security_code
        
        super().__init__(message, details)


class BusinessError(BaseAppException):
    """Raised when a business rule is violated."""
    
    def __init__(self, message: str, business_rule: Optional[str] = None):
        details = {}
        if business_rule:
            details["business_rule"] = business_rule
        
        super().__init__(message, details)


class ExternalServiceError(BaseAppException):
    """Raised when an external service call fails."""
    
    def __init__(self, message: str, service: Optional[str] = None, status_code: Optional[int] = None):
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(message, details)


class DatabaseError(BaseAppException):
    """Raised when a database operation fails."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        
        super().__init__(message, details)


class ConfigurationError(BaseAppException):
    """Raised when there's a configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(message, details)


# HTTP Exception classes for FastAPI
class HTTPValidationError(HTTPException):
    """HTTP exception for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_error",
                "message": message,
                "details": details or {}
            }
        )


class HTTPAuthenticationError(HTTPException):
    """HTTP exception for authentication errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_error",
                "message": message,
                "error_code": error_code
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class HTTPAuthorizationError(HTTPException):
    """HTTP exception for authorization errors."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": message,
                "required_permission": required_permission
            }
        )


class HTTPNotFoundError(HTTPException):
    """HTTP exception for not found errors."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found_error",
                "message": message,
                "resource_type": resource_type
            }
        )


class HTTPConflictError(HTTPException):
    """HTTP exception for conflict errors."""
    
    def __init__(self, message: str, conflict_type: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict_error",
                "message": message,
                "conflict_type": conflict_type
            }
        )


class HTTPRateLimitError(HTTPException):
    """HTTP exception for rate limit errors."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_error",
                "message": message,
                "retry_after": retry_after
            },
            headers=headers
        )


class HTTPSecurityError(HTTPException):
    """HTTP exception for security errors."""
    
    def __init__(self, message: str, security_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "security_error",
                "message": message,
                "security_code": security_code
            }
        )


class HTTPBusinessError(HTTPException):
    """HTTP exception for business logic errors."""
    
    def __init__(self, message: str, business_rule: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "business_error",
                "message": message,
                "business_rule": business_rule
            }
        )


class HTTPExternalServiceError(HTTPException):
    """HTTP exception for external service errors."""
    
    def __init__(self, message: str, service: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "external_service_error",
                "message": message,
                "service": service,
                "status_code": status_code
            }
        )


class HTTPDatabaseError(HTTPException):
    """HTTP exception for database errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": message,
                "operation": operation
            }
        )


class HTTPConfigurationError(HTTPException):
    """HTTP exception for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "configuration_error",
                "message": message,
                "config_key": config_key
            }
        )


# Exception handler utilities
def handle_database_error(func):
    """Decorator to handle database errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise DatabaseError(f"Database operation failed: {str(e)}", operation=func.__name__)
    return wrapper


def handle_external_service_error(service_name: str):
    """Decorator to handle external service errors consistently."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise ExternalServiceError(
                    f"Service {service_name} failed: {str(e)}",
                    service=service_name
                )
        return wrapper
    return decorator


def handle_validation_error(func):
    """Decorator to handle validation errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise ValidationError(f"Validation failed: {str(e)}")
    return wrapper


def handle_security_error(func):
    """Decorator to handle security errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise SecurityError(f"Security violation detected: {str(e)}")
    return wrapper
