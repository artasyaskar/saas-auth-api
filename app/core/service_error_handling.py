"""
Enterprise service layer error handling patterns.

Provides comprehensive error handling patterns with support for:
- Consistent error logging and reporting
- Error categorization and severity levels
- Retry mechanisms with exponential backoff
- Circuit breaker patterns
- Error recovery strategies
- Error aggregation and monitoring
- Graceful degradation
- Error context preservation
"""

import asyncio
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type, Union, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import structlog

from app.core.exceptions import BaseAppException
from app.core.error_responses import (
    create_system_error, create_external_service_error,
    create_timeout_error, create_business_logic_error
)

logger = structlog.get_logger()

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category enumeration."""
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    PERMISSION = "permission"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"


class RetryStrategy(Enum):
    """Retry strategy enumeration."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class ErrorContext:
    """Error context information."""
    operation: str
    service: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    stack_trace: Optional[str] = None


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: List[Type[Exception]] = field(default_factory=list)
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: Type[Exception] = Exception
    half_open_max_calls: int = 3
    monitoring_window: int = 10


@dataclass
class ErrorMetrics:
    """Error metrics tracking."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_service: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)
    last_error_time: Optional[datetime] = None


class ServiceErrorHandler:
    """
    Enterprise service error handler with comprehensive patterns.
    
    Features:
    - Consistent error logging and reporting
    - Error categorization and severity levels
    - Retry mechanisms with exponential backoff
    - Circuit breaker patterns
    - Error recovery strategies
    - Error aggregation and monitoring
    - Graceful degradation
    - Error context preservation
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.metrics = ErrorMetrics()
        self.circuit_breakers: Dict[str, Any] = {}
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on type and message."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Network errors
        if any(keyword in error_message for keyword in [
            'connection', 'timeout', 'network', 'dns', 'socket'
        ]) or any(keyword in error_type for keyword in [
            'ConnectionError', 'TimeoutError', 'NetworkError'
        ]):
            return ErrorCategory.NETWORK
        
        # Database errors
        elif any(keyword in error_type for keyword in [
            'DatabaseError', 'IntegrityError', 'OperationalError',
            'ProgrammingError', 'DataError'
        ]):
            return ErrorCategory.DATABASE
        
        # External service errors
        elif any(keyword in error_message for keyword in [
            'external', 'third-party', 'api', 'service'
        ]):
            return ErrorCategory.EXTERNAL_SERVICE
        
        # Validation errors
        elif any(keyword in error_type for keyword in [
            'ValidationError', 'ValueError', 'TypeError'
        ]):
            return ErrorCategory.VALIDATION
        
        # Timeout errors
        elif any(keyword in error_type for keyword in [
            'TimeoutError', 'asyncio.TimeoutError'
        ]):
            return ErrorCategory.TIMEOUT
        
        # Resource errors
        elif any(keyword in error_message for keyword in [
            'resource', 'memory', 'disk', 'quota', 'limit'
        ]):
            return ErrorCategory.RESOURCE
        
        # Permission errors
        elif any(keyword in error_message for keyword in [
            'permission', 'unauthorized', 'forbidden', 'access denied'
        ]):
            return ErrorCategory.PERMISSION
        
        # Authentication errors
        elif any(keyword in error_message for keyword in [
            'authentication', 'login', 'credential', 'token'
        ]):
            return ErrorCategory.AUTHENTICATION
        
        # System errors
        elif any(keyword in error_type for keyword in [
            'SystemError', 'OSError', 'IOError'
        ]):
            return ErrorCategory.SYSTEM
        
        # Default to business logic
        return ErrorCategory.BUSINESS_LOGIC
    
    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on error and category."""
        # Critical categories
        if category in [ErrorCategory.SYSTEM, ErrorCategory.DATABASE]:
            return ErrorSeverity.CRITICAL
        
        # High severity categories
        elif category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_SERVICE]:
            return ErrorSeverity.HIGH
        
        # Medium severity categories
        elif category in [ErrorCategory.TIMEOUT, ErrorCategory.RESOURCE]:
            return ErrorSeverity.MEDIUM
        
        # Check for specific error patterns
        error_message = str(error).lower()
        if any(keyword in error_message for keyword in [
            'critical', 'fatal', 'emergency', 'severe'
        ]):
            return ErrorSeverity.CRITICAL
        
        # Default to medium for unknown errors
        return ErrorSeverity.MEDIUM
    
    def log_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None
    ) -> None:
        """Log error with comprehensive context."""
        if category is None:
            category = self.categorize_error(error)
        
        if severity is None:
            severity = self.determine_severity(error, category)
        
        # Update metrics
        self.metrics.total_errors += 1
        self.metrics.errors_by_category[category.value] = self.metrics.errors_by_category.get(category.value, 0) + 1
        self.metrics.errors_by_severity[severity.value] = self.metrics.errors_by_severity.get(severity.value, 0) + 1
        self.metrics.errors_by_service[self.service_name] = self.metrics.errors_by_service.get(self.service_name, 0) + 1
        self.metrics.last_error_time = datetime.utcnow()
        
        # Add to recent errors
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "severity": severity.value,
            "service": self.service_name,
            "context": context.to_dict() if context else {}
        }
        self.metrics.recent_errors.append(error_info)
        
        # Keep only last 100 errors
        if len(self.metrics.recent_errors) > 100:
            self.metrics.recent_errors = self.metrics.recent_errors[-100:]
        
        # Log the error
        log_data = {
            "service": self.service_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "severity": severity.value
        }
        
        if context:
            log_data.update({
                "operation": context.operation,
                "user_id": context.user_id,
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
                "metadata": context.metadata
            })
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical("Service error occurred", **log_data, exc_info=error)
        elif severity == ErrorSeverity.HIGH:
            logger.error("Service error occurred", **log_data, exc_info=error)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning("Service error occurred", **log_data, exc_info=error)
        else:
            logger.info("Service error occurred", **log_data, exc_info=error)
    
    def create_error_context(
        self,
        operation: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Create error context."""
        return ErrorContext(
            operation=operation,
            service=self.service_name,
            user_id=user_id,
            request_id=request_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
            stack_trace=traceback.format_exc() if traceback.format_exc() != 'NoneType: NoneType: None\n' else None
        )
    
    async def retry_with_backoff(
        self,
        func: Callable,
        config: RetryConfig,
        context: Optional[ErrorContext] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry mechanism and exponential backoff.
        
        Args:
            func: Function to retry
            config: Retry configuration
            context: Error context
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises last exception
        """
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                if attempt > 0:
                    # Calculate delay
                    if config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                        delay = min(
                            config.base_delay * (config.backoff_multiplier ** (attempt - 1)),
                            config.max_delay
                        )
                    elif config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
                        delay = min(
                            config.base_delay * attempt,
                            config.max_delay
                        )
                    elif config.retry_strategy == RetryStrategy.FIXED_DELAY:
                        delay = config.base_delay
                    else:
                        delay = 0
                    
                    # Add jitter if enabled
                    if config.jitter and delay > 0:
                        import random
                        jitter = random.uniform(0, 0.1 * delay)
                        delay += jitter
                    
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # Run synchronous function in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, *args, **kwargs)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is non-retryable
                if any(isinstance(e, exc_type) for exc_type in config.non_retryable_exceptions):
                    raise e
                
                # Check if exception is retryable
                if not config.retryable_exceptions or any(isinstance(e, exc_type) for exc_type in config.retryable_exceptions):
                    self.log_error(e, context)
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt, re-raise
                        raise e
                else:
                    # Non-retryable exception, re-raise immediately
                    raise e
        
        # If we get here, raise the last exception
        if last_exception:
            raise last_exception
    
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> 'CircuitBreaker':
        """Get or create circuit breaker."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
    
    async def execute_with_circuit_breaker(
        self,
        func: Callable,
        circuit_breaker_name: str,
        circuit_config: CircuitBreakerConfig,
        context: Optional[ErrorContext] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            circuit_breaker_name: Circuit breaker name
            circuit_config: Circuit breaker configuration
            context: Error context
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises exception
        """
        circuit_breaker = self.get_circuit_breaker(circuit_breaker_name, circuit_config)
        
        return await circuit_breaker.call(func, context, *args, **kwargs)
    
    def register_error_handler(self, category: ErrorCategory, handler: Callable) -> None:
        """Register error handler for specific category."""
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        self.error_handlers[category].append(handler)
    
    def register_fallback_handler(self, operation: str, handler: Callable) -> None:
        """Register fallback handler for specific operation."""
        self.fallback_handlers[operation] = handler
    
    async def handle_error_with_fallback(
        self,
        error: Exception,
        operation: str,
        context: Optional[ErrorContext] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Handle error with fallback mechanism.
        
        Args:
            error: Exception that occurred
            operation: Operation name
            context: Error context
            *args: Arguments for fallback
            **kwargs: Keyword arguments for fallback
            
        Returns:
            Fallback result or raises original error
        """
        # Log the error
        self.log_error(error, context)
        
        # Try fallback handler
        if operation in self.fallback_handlers:
            try:
                return await self.fallback_handlers[operation](*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback handler failed for {operation}: {str(fallback_error)}")
                raise error  # Raise original error
        
        # Try category handlers
        category = self.categorize_error(error)
        if category in self.error_handlers:
            for handler in self.error_handlers[category]:
                try:
                    result = await handler(error, context, *args, **kwargs)
                    if result is not None:
                        return result
                except Exception as handler_error:
                    logger.error(f"Error handler failed: {str(handler_error)}")
                    continue
        
        # No fallback available, raise original error
        raise error
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get comprehensive error metrics."""
        return {
            "service": self.service_name,
            "total_errors": self.metrics.total_errors,
            "errors_by_category": dict(self.metrics.errors_by_category),
            "errors_by_severity": dict(self.metrics.errors_by_severity),
            "errors_by_service": dict(self.metrics.errors_by_service),
            "recent_errors_count": len(self.metrics.recent_errors),
            "last_error_time": self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None,
            "circuit_breakers": {
                name: breaker.get_state()
                for name, breaker in self.circuit_breakers.items()
            }
        }
    
    def reset_metrics(self) -> None:
        """Reset error metrics."""
        self.metrics = ErrorMetrics()
        
        # Reset circuit breakers
        for breaker in self.circuit_breakers.values():
            breaker.reset()


class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout
        }
    
    async def call(self, func: Callable, context: Optional[ErrorContext] = None, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit is open
        if self.state == "OPEN":
            if self.last_failure_time and time.time() - self.last_failure_time > self.config.recovery_timeout:
                # Try to close circuit
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
            else:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Success - reset failure count if in half-open state
            if self.state == "HALF_OPEN":
                self.half_open_calls += 1
                if self.half_open_calls >= self.config.half_open_max_calls:
                    self.state = "CLOSED"
                    self.failure_count = 0
            
            return result
            
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_failure(self) -> None:
        """Handle failure event."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
    
    def reset(self) -> None:
        """Reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        self.half_open_calls = 0


def with_error_handling(
    service_name: str,
    operation: Optional[str] = None,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    fallback_operation: Optional[str] = None
):
    """
    Decorator for comprehensive error handling.
    
    Args:
        service_name: Name of the service
        operation: Operation name
        retry_config: Retry configuration
        circuit_breaker_config: Circuit breaker configuration
        fallback_operation: Fallback operation name
        
    Returns:
        Decorated function
    """
    def decorator(func):
        handler = ServiceErrorHandler(service_name)
        
        if retry_config:
            handler.register_fallback_handler(fallback_operation or func.__name__, func)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = handler.create_error_context(
                operation=operation or func.__name__,
                request_id=kwargs.get('request_id'),
                correlation_id=kwargs.get('correlation_id'),
                user_id=kwargs.get('user_id')
            )
            
            try:
                if circuit_breaker_config:
                    return await handler.execute_with_circuit_breaker(
                        func, func.__name__, circuit_breaker_config, context, *args, **kwargs
                    )
                elif retry_config:
                    return await handler.retry_with_backoff(
                        func, retry_config, context, *args, **kwargs
                    )
                else:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, func, *args, **kwargs)
                        
            except Exception as e:
                if fallback_operation:
                    return await handler.handle_error_with_fallback(
                        e, fallback_operation, context, *args, **kwargs
                    )
                else:
                    handler.log_error(e, context)
                    raise
        
        return wrapper
    return decorator


def handle_service_errors(
    service_name: str,
    error: Exception,
    operation: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Handle service errors with consistent logging.
    
    Args:
        service_name: Name of the service
        error: Exception that occurred
        operation: Operation that failed
        context: Additional context
    """
    handler = ServiceErrorHandler(service_name)
    
    error_context = handler.create_error_context(
        operation=operation or "unknown",
        metadata=context or {}
    )
    
    handler.log_error(error, error_context)


def get_service_error_metrics(service_name: str) -> Dict[str, Any]:
    """
    Get error metrics for a service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Error metrics dictionary
    """
    handler = ServiceErrorHandler(service_name)
    return handler.get_error_metrics()


class ServiceErrorMonitor:
    """
    Service error monitoring and aggregation.
    
    Features:
    - Error aggregation across services
    - Error trend analysis
    - Alerting on error thresholds
    - Error reporting and dashboards
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceErrorHandler] = {}
        self.global_metrics = ErrorMetrics()
    
    def register_service(self, service_name: str) -> ServiceErrorHandler:
        """Register a service for monitoring."""
        if service_name not in self.services:
            self.services[service_name] = ServiceErrorHandler(service_name)
        return self.services[service_name]
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get aggregated error metrics across all services."""
        # Aggregate metrics from all services
        total_errors = 0
        errors_by_category = {}
        errors_by_severity = {}
        errors_by_service = {}
        
        for service_name, handler in self.services.items():
            metrics = handler.get_error_metrics()
            total_errors += metrics["total_errors"]
            
            # Aggregate by category
            for category, count in metrics["errors_by_category"].items():
                errors_by_category[category] = errors_by_category.get(category, 0) + count
            
            # Aggregate by severity
            for severity, count in metrics["errors_by_severity"].items():
                errors_by_severity[severity] = errors_by_severity.get(severity, 0) + count
            
            # Aggregate by service
            errors_by_service[service_name] = metrics["total_errors"]
        
        return {
            "total_services": len(self.services),
            "total_errors": total_errors,
            "errors_by_category": errors_by_category,
            "errors_by_severity": errors_by_severity,
            "errors_by_service": errors_by_service,
            "monitoring_timestamp": datetime.utcnow().isoformat()
        }
    
    def get_service_health_status(self, service_name: str) -> Dict[str, Any]:
        """Get health status for a specific service."""
        if service_name not in self.services:
            return {"status": "unknown", "message": f"Service '{service_name}' not registered"}
        
        metrics = self.services[service_name].get_error_metrics()
        
        # Determine health status based on error rate
        if metrics["total_errors"] == 0:
            status = "healthy"
        elif metrics["total_errors"] < 10:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "service": service_name,
            "status": status,
            "total_errors": metrics["total_errors"],
            "error_rate": metrics["total_errors"],  # Simplified - would need time window
            "last_error": metrics["last_error_time"]
        }


# Global error monitor
error_monitor = ServiceErrorMonitor()
