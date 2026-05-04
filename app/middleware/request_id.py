"""
Request ID middleware for distributed tracing.
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Ensure every request has a unique request ID for tracing.
    Uses X-Request-ID header if provided by client, otherwise generates one.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


def get_request_id(request: Request) -> str:
    """Get the request ID from the current request."""
    return getattr(request.state, "request_id", "unknown")
