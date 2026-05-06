"""
Standardized error response system for consistent API responses.

Provides comprehensive error response handling with support for:
- Standardized error format across all endpoints
- Consistent HTTP status codes
- Error categorization and severity levels
- Internationalization support
- Request correlation IDs
- Detailed error information for debugging
- Client-friendly error messages
- Development vs production error details
"""

import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import structlog

from app.core.exceptions import BaseAppException

logger = structlog.get_logger()


class ErrorCategory(Enum):
    """Error category enumeration."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    CONCURRENCY = "concurrency"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorDetail:
    """Detailed error information."""
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    constraint: Optional[str] = None


@dataclass
class StandardErrorResponse:
    """Standardized error response structure."""
    success: bool = False
    error: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class ErrorResponseBuilder:
    """
    Builder for creating standardized error responses.
    
    Features:
    - Consistent error format
    - Multiple error detail support
    - Request correlation
    - Development vs production modes
    - Internationalization support
    """
    
    def __init__(self, request: Optional[Request] = None):
        self.request = request
        self.is_development = True  # Would check from settings
        self.correlation_id = None
        
        if request:
            self.correlation_id = request.headers.get("X-Correlation-ID")
    
    def validation_error(
        self,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None
    ) -> StandardErrorResponse:
        """Create validation error response."""
        error_data = {
            "type": ErrorCategory.VALIDATION.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = [
                {
                    "code": detail.code,
                    "message": detail.message,
                    "field": detail.field,
                    "value": detail.value,
                    "constraint": detail.constraint
                }
                for detail in details
            ]
        elif field:
            error_data["details"] = [{
                "field": field,
                "value": value,
                "message": message
            }]
        
        # Add development-only information
        if self.is_development:
            error_data["debug"] = {
                "request_id": id(self.request) if self.request else None,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.VALIDATION.value
            }
        )
    
    def authentication_error(
        self,
        message: str,
        error_code: str = "AUTH_FAILED",
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create authentication error response."""
        error_data = {
            "type": ErrorCategory.AUTHENTICATION.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.AUTHENTICATION.value
            }
        )
    
    def authorization_error(
        self,
        message: str,
        error_code: str = "ACCESS_DENIED",
        required_permissions: Optional[List[str]] = None
    ) -> StandardErrorResponse:
        """Create authorization error response."""
        error_data = {
            "type": ErrorCategory.AUTHORIZATION.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if required_permissions:
            error_data["required_permissions"] = required_permissions
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.AUTHORIZATION.value
            }
        )
    
    def not_found_error(
        self,
        resource: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> StandardErrorResponse:
        """Create not found error response."""
        error_message = message or f"{resource} not found"
        if resource_id:
            error_message = f"{resource} with ID '{resource_id}' not found"
        
        error_data = {
            "type": ErrorCategory.NOT_FOUND.value,
            "severity": ErrorSeverity.LOW.value,
            "code": "RESOURCE_NOT_FOUND",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "resource": resource
        }
        
        if resource_id:
            error_data["resource_id"] = resource_id
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.NOT_FOUND.value
            }
        )
    
    def permission_error(
        self,
        message: str,
        permission: Optional[str] = None,
        resource: Optional[str] = None
    ) -> StandardErrorResponse:
        """Create permission error response."""
        error_data = {
            "type": ErrorCategory.PERMISSION.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": "INSUFFICIENT_PERMISSIONS",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if permission:
            error_data["required_permission"] = permission
        
        if resource:
            error_data["resource"] = resource
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.PERMISSION.value
            }
        )
    
    def rate_limit_error(
        self,
        message: str,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[str] = None
    ) -> StandardErrorResponse:
        """Create rate limit error response."""
        error_data = {
            "type": ErrorCategory.RATE_LIMIT.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": "RATE_LIMIT_EXCEEDED",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if retry_after:
            error_data["retry_after"] = retry_after
        
        if limit:
            error_data["limit"] = limit
        
        if window:
            error_data["window"] = window
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.RATE_LIMIT.value
            }
        )
    
    def business_logic_error(
        self,
        message: str,
        error_code: str = "BUSINESS_LOGIC_ERROR",
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create business logic error response."""
        error_data = {
            "type": ErrorCategory.BUSINESS_LOGIC.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.BUSINESS_LOGIC.value
            }
        )
    
    def external_service_error(
        self,
        message: str,
        service: str,
        service_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create external service error response."""
        error_data = {
            "type": ErrorCategory.EXTERNAL_SERVICE.value,
            "severity": ErrorSeverity.HIGH.value,
            "code": "EXTERNAL_SERVICE_ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "service": service
        }
        
        if service_error_code:
            error_data["service_error_code"] = service_error_code
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.EXTERNAL_SERVICE.value
            }
        )
    
    def system_error(
        self,
        message: str,
        error_code: str = "SYSTEM_ERROR",
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create system error response."""
        error_data = {
            "type": ErrorCategory.SYSTEM.value,
            "severity": ErrorSeverity.CRITICAL.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        # Add development-only information
        if self.is_development:
            error_data["debug"] = {
                "traceback": traceback.format_exc(),
                "request_id": id(self.request) if self.request else None
            }
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.SYSTEM.value
            }
        )
    
    def security_error(
        self,
        message: str,
        error_code: str = "SECURITY_VIOLATION",
        threat_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create security error response."""
        error_data = {
            "type": ErrorCategory.SECURITY.value,
            "severity": ErrorSeverity.HIGH.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if threat_type:
            error_data["threat_type"] = threat_type
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.SECURITY.value
            }
        )
    
    def timeout_error(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None
    ) -> StandardErrorResponse:
        """Create timeout error response."""
        error_data = {
            "type": ErrorCategory.TIMEOUT.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": "TIMEOUT_ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if timeout_duration:
            error_data["timeout_duration"] = timeout_duration
        
        if operation:
            error_data["operation"] = operation
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.TIMEOUT.value
            }
        )
    
    def concurrency_error(
        self,
        message: str,
        conflict_type: Optional[str] = None,
        conflicting_resource: Optional[str] = None
    ) -> StandardErrorResponse:
        """Create concurrency error response."""
        error_data = {
            "type": ErrorCategory.CONCURRENCY.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "code": "CONCURRENCY_ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if conflict_type:
            error_data["conflict_type"] = conflict_type
        
        if conflicting_resource:
            error_data["conflicting_resource"] = conflicting_resource
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.CONCURRENCY.value
            }
        )
    
    def configuration_error(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_value: Optional[Any] = None
    ) -> StandardErrorResponse:
        """Create configuration error response."""
        error_data = {
            "type": ErrorCategory.CONFIGURATION.value,
            "severity": ErrorSeverity.HIGH.value,
            "code": "CONFIGURATION_ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if config_key:
            error_data["config_key"] = config_key
        
        if expected_value is not None:
            error_data["expected_value"] = str(expected_value)
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": ErrorCategory.CONFIGURATION.value
            }
        )
    
    def custom_error(
        self,
        message: str,
        error_code: str = "CUSTOM_ERROR",
        category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ) -> StandardErrorResponse:
        """Create custom error response."""
        error_data = {
            "type": category.value,
            "severity": severity.value,
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.correlation_id:
            error_data["correlation_id"] = self.correlation_id
        
        if details:
            error_data["details"] = details
        
        return StandardErrorResponse(
            error=error_data,
            metadata={
                "request_id": self.correlation_id,
                "category": category.value
            }
        )


class StandardHTTPException(HTTPException):
    """
    Standardized HTTP exception with consistent error format.
    
    Features:
    - Consistent error response format
    - Automatic correlation ID handling
    - Development vs production modes
    - Multiple error types support
    """
    
    def __init__(
        self,
        status_code: int,
        response: StandardErrorResponse,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            status_code=status_code,
            content=response.to_dict(),
            headers=headers or {}
        )
        self.response = response


def create_error_response(
    error_response: StandardErrorResponse,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """Create standardized JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content=error_response.to_dict()
    )


def handle_validation_exception(
    exc: RequestValidationError,
    request: Request
) -> StandardHTTPException:
    """Handle FastAPI validation exceptions."""
    builder = ErrorResponseBuilder(request)
    
    # Convert Pydantic validation errors to our format
    details = []
    for error in exc.errors():
        details.append(ErrorDetail(
            code=error.get('type', 'validation_error'),
            message=error.get('msg', 'Validation error'),
            field='.'.join(str(loc) for loc in error.get('loc', [])),
            value=error.get('input'),
            constraint=error.get('ctx')
        ))
    
    error_response = builder.validation_error(
        message="Validation failed",
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        response=error_response
    )


def handle_application_exception(
    exc: BaseAppException,
    request: Request
) -> StandardHTTPException:
    """Handle application-specific exceptions."""
    builder = ErrorResponseBuilder(request)
    
    # Map exception type to appropriate error response
    if hasattr(exc, 'error_type'):
        error_type = exc.error_type
    else:
        error_type = ErrorCategory.BUSINESS_LOGIC
    
    if error_type == ErrorCategory.VALIDATION:
        return StandardHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            response=builder.validation_error(
                message=exc.message,
                details=getattr(exc, 'details', None)
            )
        )
    elif error_type == ErrorCategory.AUTHENTICATION:
        return StandardHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            response=builder.authentication_error(
                message=exc.message,
                details=getattr(exc, 'details', None)
            )
        )
    elif error_type == ErrorCategory.AUTHORIZATION:
        return StandardHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            response=builder.authorization_error(
                message=exc.message,
                required_permissions=getattr(exc, 'required_permissions', None)
            )
        )
    elif error_type == ErrorCategory.NOT_FOUND:
        return StandardHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            response=builder.not_found_error(
                resource=getattr(exc, 'resource', 'resource'),
                resource_id=getattr(exc, 'resource_id', None)
            )
        )
    elif error_type == ErrorCategory.PERMISSION:
        return StandardHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            response=builder.permission_error(
                message=exc.message,
                permission=getattr(exc, 'permission', None),
                resource=getattr(exc, 'resource', None)
            )
        )
    elif error_type == ErrorCategory.RATE_LIMIT:
        return StandardHTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            response=builder.rate_limit_error(
                message=exc.message,
                retry_after=getattr(exc, 'retry_after', None),
                limit=getattr(exc, 'limit', None),
                window=getattr(exc, 'window', None)
            )
        )
    elif error_type == ErrorCategory.SECURITY:
        return StandardHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            response=builder.security_error(
                message=exc.message,
                threat_type=getattr(exc, 'threat_type', None),
                details=getattr(exc, 'details', None)
            )
        )
    else:
        # Default to business logic error
        return StandardHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            response=builder.business_logic_error(
                message=exc.message,
                details=getattr(exc, 'details', None)
            )
        )


def handle_generic_exception(
    exc: Exception,
    request: Request
) -> StandardHTTPException:
    """Handle generic exceptions."""
    builder = ErrorResponseBuilder(request)
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=exc,
        extra={"correlation_id": getattr(request, 'headers', {}).get('X-Correlation-ID')}
    )
    
    # Don't expose internal error details in production
    error_message = "An internal error occurred" if not builder.is_development else str(exc)
    
    return StandardHTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        response=builder.system_error(
            message=error_message,
            details={"exception_type": type(exc).__name__} if builder.is_development else None
        )
    )


# Error response factory functions
def create_validation_error(
    request: Request,
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None
) -> StandardHTTPException:
    """Create validation error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.validation_error(
        message=message,
        field=field,
        value=value
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        response=error_response
    )


def create_authentication_error(
    request: Request,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> StandardHTTPException:
    """Create authentication error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.authentication_error(
        message=message,
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        response=error_response
    )


def create_authorization_error(
    request: Request,
    message: str,
    required_permissions: Optional[List[str]] = None
) -> StandardHTTPException:
    """Create authorization error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.authorization_error(
        message=message,
        required_permissions=required_permissions
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        response=error_response
    )


def create_not_found_error(
    request: Request,
    resource: str,
    resource_id: Optional[str] = None,
    message: Optional[str] = None
) -> StandardHTTPException:
    """Create not found error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.not_found_error(
        resource=resource,
        resource_id=resource_id,
        message=message
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        response=error_response
    )


def create_permission_error(
    request: Request,
    message: str,
    permission: Optional[str] = None,
    resource: Optional[str] = None
) -> StandardHTTPException:
    """Create permission error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.permission_error(
        message=message,
        permission=permission,
        resource=resource
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        response=error_response
    )


def create_rate_limit_error(
    request: Request,
    message: str,
    retry_after: Optional[int] = None,
    limit: Optional[int] = None,
    window: Optional[str] = None
) -> StandardHTTPException:
    """Create rate limit error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.rate_limit_error(
        message=message,
        retry_after=retry_after,
        limit=limit,
        window=window
    )
    
    response = StandardHTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        response=error_response
    )
    
    # Add retry-after header
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)
    
    return response


def create_business_logic_error(
    request: Request,
    message: str,
    error_code: str = "BUSINESS_LOGIC_ERROR",
    details: Optional[Dict[str, Any]] = None
) -> StandardHTTPException:
    """Create business logic error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.business_logic_error(
        message=message,
        error_code=error_code,
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        response=error_response
    )


def create_external_service_error(
    request: Request,
    message: str,
    service: str,
    service_error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> StandardHTTPException:
    """Create external service error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.external_service_error(
        message=message,
        service=service,
        service_error_code=service_error_code,
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        response=error_response
    )


def create_security_error(
    request: Request,
    message: str,
    threat_type: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> StandardHTTPException:
    """Create security error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.security_error(
        message=message,
        threat_type=threat_type,
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        response=error_response
    )


def create_system_error(
    request: Request,
    message: str,
    error_code: str = "SYSTEM_ERROR",
    details: Optional[Dict[str, Any]] = None
) -> StandardHTTPException:
    """Create system error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.system_error(
        message=message,
        error_code=error_code,
        details=details
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        response=error_response
    )


def create_timeout_error(
    request: Request,
    message: str,
    timeout_duration: Optional[float] = None,
    operation: Optional[str] = None
) -> StandardHTTPException:
    """Create timeout error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.timeout_error(
        message=message,
        timeout_duration=timeout_duration,
        operation=operation
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        response=error_response
    )


def create_concurrency_error(
    request: Request,
    message: str,
    conflict_type: Optional[str] = None,
    conflicting_resource: Optional[str] = None
) -> StandardHTTPException:
    """Create concurrency error response."""
    builder = ErrorResponseBuilder(request)
    error_response = builder.concurrency_error(
        message=message,
        conflict_type=conflict_type,
        conflicting_resource=conflicting_resource
    )
    
    return StandardHTTPException(
        status_code=status.HTTP_409_CONFLICT,
        response=error_response
    )
