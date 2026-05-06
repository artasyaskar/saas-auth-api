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


class TokenError(BaseAppException):
    """Raised when token operations fail."""
    
    def __init__(self, message: str, token_type: Optional[str] = None, error_code: Optional[str] = None):
        details = {}
        if token_type:
            details["token_type"] = token_type
        if error_code:
            details["error_code"] = error_code
        
        super().__init__(message, details)


class SessionError(BaseAppException):
    """Raised when session operations fail."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
        
        super().__init__(message, details)


class CacheError(BaseAppException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, cache_key: Optional[str] = None, operation: Optional[str] = None):
        details = {}
        if cache_key:
            details["cache_key"] = cache_key
        if operation:
            details["operation"] = operation
        
        super().__init__(message, details)


class WebhookError(BaseAppException):
    """Raised when webhook operations fail."""
    
    def __init__(self, message: str, webhook_url: Optional[str] = None, attempt: Optional[int] = None):
        details = {}
        if webhook_url:
            details["webhook_url"] = webhook_url
        if attempt:
            details["attempt"] = attempt
        
        super().__init__(message, details)


class EmailError(BaseAppException):
    """Raised when email operations fail."""
    
    def __init__(self, message: str, recipient: Optional[str] = None, template: Optional[str] = None):
        details = {}
        if recipient:
            details["recipient"] = recipient
        if template:
            details["template"] = template
        
        super().__init__(message, details)


class FileStorageError(BaseAppException):
    """Raised when file storage operations fail."""
    
    def __init__(self, message: str, file_name: Optional[str] = None, operation: Optional[str] = None):
        details = {}
        if file_name:
            details["file_name"] = file_name
        if operation:
            details["operation"] = operation
        
        super().__init__(message, details)


class FeatureFlagError(BaseAppException):
    """Raised when feature flag operations fail."""
    
    def __init__(self, message: str, flag_name: Optional[str] = None):
        details = {}
        if flag_name:
            details["flag_name"] = flag_name
        
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


class HTTPTokenError(HTTPException):
    """HTTP exception for token errors."""
    
    def __init__(self, message: str, token_type: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_error",
                "message": message,
                "token_type": token_type,
                "error_code": error_code
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class HTTPSessionError(HTTPException):
    """HTTP exception for session errors."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "session_error",
                "message": message,
                "session_id": session_id
            }
        )


class HTTPCacheError(HTTPException):
    """HTTP exception for cache errors."""
    
    def __init__(self, message: str, cache_key: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "cache_error",
                "message": message,
                "cache_key": cache_key,
                "operation": operation
            }
        )


class HTTPWebhookError(HTTPException):
    """HTTP exception for webhook errors."""
    
    def __init__(self, message: str, webhook_url: Optional[str] = None, attempt: Optional[int] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "webhook_error",
                "message": message,
                "webhook_url": webhook_url,
                "attempt": attempt
            }
        )


class HTMLEmailError(HTTPException):
    """HTTP exception for email errors."""
    
    def __init__(self, message: str, recipient: Optional[str] = None, template: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "email_error",
                "message": message,
                "recipient": recipient,
                "template": template
            }
        )


class HTTPFileStorageError(HTTPException):
    """HTTP exception for file storage errors."""
    
    def __init__(self, message: str, file_name: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "file_storage_error",
                "message": message,
                "file_name": file_name,
                "operation": operation
            }
        )


class HTTPFeatureFlagError(HTTPException):
    """HTTP exception for feature flag errors."""
    
    def __init__(self, message: str, flag_name: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "feature_flag_error",
                "message": message,
                "flag_name": flag_name
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


def handle_token_error(func):
    """Decorator to handle token errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise TokenError(f"Token operation failed: {str(e)}")
    return wrapper


def handle_session_error(func):
    """Decorator to handle session errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise SessionError(f"Session operation failed: {str(e)}")
    return wrapper


def handle_cache_error(func):
    """Decorator to handle cache errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise CacheError(f"Cache operation failed: {str(e)}")
    return wrapper


def handle_webhook_error(func):
    """Decorator to handle webhook errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise WebhookError(f"Webhook operation failed: {str(e)}")
    return wrapper


def handle_email_error(func):
    """Decorator to handle email errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise EmailError(f"Email operation failed: {str(e)}")
    return wrapper


def handle_file_storage_error(func):
    """Decorator to handle file storage errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise FileStorageError(f"File storage operation failed: {str(e)}")
    return wrapper


def handle_feature_flag_error(func):
    """Decorator to handle feature flag errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise FeatureFlagError(f"Feature flag operation failed: {str(e)}")
    return wrapper


# Exception mapping utilities
def map_exception_to_http(exception: BaseAppException) -> HTTPException:
    """Map application exceptions to HTTP exceptions."""
    exception_mapping = {
        ValidationError: HTTPValidationError,
        AuthenticationError: HTTPAuthenticationError,
        AuthorizationError: HTTPAuthorizationError,
        NotFoundError: HTTPNotFoundError,
        ConflictError: HTTPConflictError,
        RateLimitError: HTTPRateLimitError,
        SecurityError: HTTPSecurityError,
        BusinessError: HTTPBusinessError,
        ExternalServiceError: HTTPExternalServiceError,
        DatabaseError: HTTPDatabaseError,
        ConfigurationError: HTTPConfigurationError,
        TokenError: HTTPTokenError,
        SessionError: HTTPSessionError,
        CacheError: HTTPCacheError,
        WebhookError: HTTPWebhookError,
        EmailError: HTMLEmailError,
        FileStorageError: HTTPFileStorageError,
        FeatureFlagError: HTTPFeatureFlagError,
    }
    
    exception_type = type(exception)
    http_exception_class = exception_mapping.get(exception_type, HTTPException)
    
    if exception_type == ValidationError:
        return http_exception_class(exception.message, exception.details)
    elif exception_type == AuthenticationError:
        return http_exception_class(exception.message, exception.details.get("error_code"))
    elif exception_type == AuthorizationError:
        return http_exception_class(exception.message, exception.details.get("required_permission"))
    elif exception_type == NotFoundError:
        return http_exception_class(exception.message, exception.details.get("resource_type"))
    elif exception_type == ConflictError:
        return http_exception_class(exception.message, exception.details.get("conflict_type"))
    elif exception_type == RateLimitError:
        return http_exception_class(exception.message, exception.details.get("retry_after"))
    elif exception_type == SecurityError:
        return http_exception_class(exception.message, exception.details.get("security_code"))
    elif exception_type == BusinessError:
        return http_exception_class(exception.message, exception.details.get("business_rule"))
    elif exception_type == ExternalServiceError:
        return http_exception_class(
            exception.message, 
            exception.details.get("service"),
            exception.details.get("status_code")
        )
    elif exception_type == DatabaseError:
        return http_exception_class(exception.message, exception.details.get("operation"))
    elif exception_type == ConfigurationError:
        return http_exception_class(exception.message, exception.details.get("config_key"))
    elif exception_type == TokenError:
        return http_exception_class(
            exception.message,
            exception.details.get("token_type"),
            exception.details.get("error_code")
        )
    elif exception_type == SessionError:
        return http_exception_class(exception.message, exception.details.get("session_id"))
    elif exception_type == CacheError:
        return http_exception_class(
            exception.message,
            exception.details.get("cache_key"),
            exception.details.get("operation")
        )
    elif exception_type == WebhookError:
        return http_exception_class(
            exception.message,
            exception.details.get("webhook_url"),
            exception.details.get("attempt")
        )
    elif exception_type == EmailError:
        return http_exception_class(
            exception.message,
            exception.details.get("recipient"),
            exception.details.get("template")
        )
    elif exception_type == FileStorageError:
        return http_exception_class(
            exception.message,
            exception.details.get("file_name"),
            exception.details.get("operation")
        )
    elif exception_type == FeatureFlagError:
        return http_exception_class(exception.message, exception.details.get("flag_name"))
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": exception.message,
                "details": exception.details
            }
        )
