"""
Distributed tracing service with correlation IDs.

Provides enterprise-grade distributed tracing with support for
correlation IDs, span tracking, and integration with monitoring systems.
"""

import uuid
import time
import json
import threading
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
import structlog

from app.core.config import settings
from app.core.exceptions import TracingError

logger = structlog.get_logger()


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SpanKind(Enum):
    """Span kind enumeration."""
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


@dataclass
class Span:
    """Distributed tracing span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.OK
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    service_name: str = "saas-auth-api"
    resource: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish the span."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
    
    def set_tag(self, key: str, value: Any) -> None:
        """Set a tag on the span."""
        self.tags[key] = value
    
    def log_event(self, level: str, message: str, **kwargs) -> None:
        """Log an event on the span."""
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "service_name": self.service_name,
            "resource": self.resource,
            "timestamp": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat()
        }


class TracingContext:
    """Thread-local tracing context."""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get the current span."""
        return getattr(self._local, 'current_span', None)
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        span = self.current_span
        return span.trace_id if span else None
    
    @property
    def span_id(self) -> Optional[str]:
        """Get the current span ID."""
        span = self.current_span
        return span.span_id if span else None
    
    def set_current_span(self, span: Span) -> None:
        """Set the current span."""
        self._local.current_span = span
    
    def clear(self) -> None:
        """Clear the current context."""
        self._local.current_span = None


class DistributedTracer:
    """
    Enterprise-grade distributed tracer.
    
    Features:
    - Correlation ID management
    - Span creation and management
    - Thread-local context
    - Integration with monitoring systems
    - Performance metrics
    - Error tracking
    """
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or getattr(settings, 'app_name', 'saas-auth-api')
        self.context = TracingContext()
        self.spans: List[Span] = []
        self.enabled = True
        
        # Tracing configuration
        self.max_spans = 1000
        self.sample_rate = 1.0  # 100% sampling
        self.export_timeout = 5.0  # seconds
        
        # Metrics
        self.metrics = {
            "spans_created": 0,
            "spans_finished": 0,
            "spans_failed": 0,
            "total_duration_ms": 0.0,
            "average_duration_ms": 0.0
        }
    
    def generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return str(uuid.uuid4()).replace('-', '')
    
    def generate_span_id(self) -> str:
        """Generate a unique span ID."""
        return str(uuid.uuid4()).replace('-', '')[:16]
    
    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
        resource: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Start a new span.
        
        Args:
            operation_name: Name of the operation
            parent_span_id: Parent span ID
            kind: Span kind
            tags: Initial tags
            resource: Resource information
            
        Returns:
            Created span
        """
        if not self.enabled:
            return None
        
        # Get trace ID from context or generate new one
        if self.context.current_span:
            trace_id = self.context.current_span.trace_id
        else:
            trace_id = self.generate_trace_id()
        
        # Create new span
        span = Span(
            trace_id=trace_id,
            span_id=self.generate_span_id(),
            parent_span_id=parent_span_id or (self.context.span_id if self.context.current_span else None),
            operation_name=operation_name,
            kind=kind,
            service_name=self.service_name,
            tags=tags or {},
            resource=resource or {}
        )
        
        # Add to spans list
        self.spans.append(span)
        if len(self.spans) > self.max_spans:
            self.spans = self.spans[-self.max_spans:]
        
        # Set as current span
        self.context.set_current_span(span)
        
        # Update metrics
        self.metrics["spans_created"] += 1
        
        # Log span start
        logger.info(
            "Span started",
            trace_id=span.trace_id,
            span_id=span.span_id,
            operation_name=operation_name,
            parent_span_id=span.parent_span_id
        )
        
        return span
    
    @contextmanager
    def span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None,
        resource: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for creating and finishing a span.
        
        Args:
            operation_name: Name of the operation
            parent_span_id: Parent span ID
            kind: Span kind
            tags: Initial tags
            resource: Resource information
        """
        span = self.start_span(operation_name, parent_span_id, kind, tags, resource)
        
        if span is None:
            yield None
            return
        
        try:
            yield span
            span.finish(SpanStatus.OK)
        except Exception as e:
            span.finish(SpanStatus.ERROR)
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.log_event("error", str(e), exception_type=type(e).__name__)
            raise
        finally:
            self._span_finished(span)
    
    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish a span."""
        if span:
            span.finish(status)
            self._span_finished(span)
    
    def _span_finished(self, span: Span) -> None:
        """Handle span completion."""
        # Update metrics
        self.metrics["spans_finished"] += 1
        if span.duration_ms:
            self.metrics["total_duration_ms"] += span.duration_ms
            self.metrics["average_duration_ms"] = (
                self.metrics["total_duration_ms"] / self.metrics["spans_finished"]
            )
        
        if span.status == SpanStatus.ERROR:
            self.metrics["spans_failed"] += 1
        
        # Log span completion
        logger.info(
            "Span finished",
            trace_id=span.trace_id,
            span_id=span.span_id,
            operation_name=span.operation_name,
            status=span.status.value,
            duration_ms=span.duration_ms
        )
        
        # Clear context if this was the current span
        if self.context.current_span and self.context.current_span.span_id == span.span_id:
            self.context.clear()
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        return self.context.trace_id
    
    def get_current_span_id(self) -> Optional[str]:
        """Get the current span ID."""
        return self.context.span_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get the correlation ID (same as trace ID)."""
        return self.get_current_trace_id()
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the correlation ID for the current context."""
        # Create a root span with the given correlation ID
        span = Span(
            trace_id=correlation_id,
            span_id=self.generate_span_id(),
            operation_name="correlation_context",
            service_name=self.service_name
        )
        self.context.set_current_span(span)
    
    def add_trace_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add tracing headers to a request."""
        if not self.enabled or not self.context.current_span:
            return headers
        
        trace_headers = {
            "X-Trace-ID": self.context.trace_id,
            "X-Parent-Span-ID": self.context.span_id,
            "X-Correlation-ID": self.context.trace_id
        }
        
        # Merge with existing headers
        updated_headers = headers.copy()
        updated_headers.update(trace_headers)
        
        return updated_headers
    
    def extract_trace_context(self, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract trace context from headers."""
        if not headers:
            return None
        
        trace_context = {}
        
        # Try various header names
        header_mappings = {
            "trace_id": ["X-Trace-ID", "X-Request-ID", "traceparent", "uber-trace-id"],
            "span_id": ["X-Parent-Span-ID", "X-Span-ID"],
            "correlation_id": ["X-Correlation-ID", "Correlation-ID"]
        }
        
        for context_key, header_names in header_mappings.items():
            for header_name in header_names:
                if header_name in headers:
                    trace_context[context_key] = headers[header_name]
                    break
        
        return trace_context if trace_context else None
    
    def continue_trace(
        self,
        operation_name: str,
        headers: Dict[str, str],
        kind: SpanKind = SpanKind.SERVER,
        tags: Optional[Dict[str, Any]] = None
    ) -> Optional[Span]:
        """Continue an existing trace from headers."""
        if not self.enabled:
            return None
        
        trace_context = self.extract_trace_context(headers)
        if not trace_context:
            return self.start_span(operation_name, kind=kind, tags=tags)
        
        # Create span with existing trace context
        span = Span(
            trace_id=trace_context.get("trace_id", self.generate_trace_id()),
            span_id=self.generate_span_id(),
            parent_span_id=trace_context.get("span_id"),
            operation_name=operation_name,
            kind=kind,
            service_name=self.service_name,
            tags=tags or {}
        )
        
        # Add to spans and set as current
        self.spans.append(span)
        self.context.set_current_span(span)
        
        # Add incoming trace context tags
        span.set_tag("trace.continued", True)
        for key, value in trace_context.items():
            span.set_tag(f"trace.incoming.{key}", value)
        
        return span
    
    def get_trace_spans(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [span for span in self.spans if span.trace_id == trace_id]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tracing metrics."""
        return {
            "enabled": self.enabled,
            "service_name": self.service_name,
            "spans_created": self.metrics["spans_created"],
            "spans_finished": self.metrics["spans_finished"],
            "spans_failed": self.metrics["spans_failed"],
            "total_duration_ms": self.metrics["total_duration_ms"],
            "average_duration_ms": self.metrics["average_duration_ms"],
            "active_spans": len([s for s in self.spans if s.end_time is None]),
            "failure_rate": (
                self.metrics["spans_failed"] / max(self.metrics["spans_finished"], 1)
            ) * 100
        }
    
    def export_spans(self) -> List[Dict[str, Any]]:
        """Export spans for external monitoring systems."""
        return [span.to_dict() for span in self.spans]
    
    def clear_spans(self) -> None:
        """Clear all spans."""
        self.spans.clear()
        self.context.clear()
    
    def enable(self) -> None:
        """Enable tracing."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable tracing."""
        self.enabled = False
        self.context.clear()


# Global tracer instance
tracer = DistributedTracer()


def get_trace_id() -> Optional[str]:
    """Get the current trace ID."""
    return tracer.get_current_trace_id()


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return tracer.get_correlation_id()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    tracer.set_correlation_id(correlation_id)


@contextmanager
def trace_operation(
    operation_name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracing operations.
    
    Args:
        operation_name: Name of the operation
        kind: Span kind
        tags: Initial tags
    """
    with tracer.span(operation_name, kind=kind, tags=tags) as span:
        yield span


def add_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Add tracing headers to a request."""
    return tracer.add_trace_headers(headers)


def continue_trace_from_headers(
    operation_name: str,
    headers: Dict[str, str],
    kind: SpanKind = SpanKind.SERVER,
    tags: Optional[Dict[str, Any]] = None
) -> Optional[Span]:
    """Continue a trace from incoming headers."""
    return tracer.continue_trace(operation_name, headers, kind, tags)


class TracingMiddleware:
    """
    Middleware for automatic request tracing.
    
    Automatically traces incoming requests and adds correlation IDs.
    """
    
    def __init__(self, app, tracer_instance: DistributedTracer = None):
        self.app = app
        self.tracer = tracer_instance or tracer
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract headers
        headers = dict(scope.get("headers", []))
        
        # Continue trace or start new one
        method = scope.get("method", "")
        path = scope.get("path", "")
        operation_name = f"{method} {path}"
        
        with self.tracer.span(
            operation_name,
            kind=SpanKind.SERVER,
            tags={
                "http.method": method,
                "http.url": path,
                "http.scheme": scope.get("scheme", ""),
                "http.host": scope.get("server", [""])[0],
                "http.user_agent": next((v for k, v in headers.items() if k.lower() == b"user-agent"), ""),
            }
        ) as span:
            if span:
                # Add trace headers to response
                async def send_with_tracing(message):
                    if message["type"] == "http.response.start":
                        # Add tracing headers to response
                        headers = dict(message.get("headers", []))
                        trace_headers = [
                            (b"x-trace-id", span.trace_id.encode()),
                            (b"x-correlation-id", span.trace_id.encode()),
                        ]
                        headers.extend(trace_headers)
                        message["headers"] = headers
                    
                    await send(message)
                
                await self.app(scope, receive, send_with_tracing)
            else:
                await self.app(scope, receive, send)
