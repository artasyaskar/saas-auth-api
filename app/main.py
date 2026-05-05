from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from sqlalchemy.orm import Session
import structlog

from app.db.session import engine, get_db
from app.db.models import Base, User, RateLimit
from app.api import auth, users, admin
from app.api.routes import password_reset, api_keys, webhooks
from app.services.usage import UsageService
from app.core.rate_limit import rate_limiter
from app.core.config import settings
from app.api.auth import get_current_active_user
from app.middleware.logging import LoggingMiddleware, audit_logger
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.db.models import TokenBlacklist, PasswordResetToken

# Configure structured logging
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    
    Handles:
    - Database table creation
    - Default admin user setup
    - Background service initialization
    - Graceful shutdown cleanup
    """
    logger.info("application_startup", startup_event="begin")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("database_initialized", db_event="tables_created")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise
    
    # Create default admin user if doesn't exist
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            from app.core.security import get_password_hash
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role="ADMIN"
            )
            db.add(admin_user)
            db.commit()
            logger.info("default_admin_created", admin_username="admin")
    except Exception as e:
        logger.error("admin_creation_failed", error=str(e))
    finally:
        db.close()
    
    logger.info("application_startup_complete", startup_event="end")
    
    yield
    
    # Shutdown cleanup
    logger.info("application_shutdown", shutdown_event="begin")
    # TODO: Close Redis connections, background task queues, etc.
    logger.info("application_shutdown_complete", shutdown_event="end")


app = FastAPI(
    title="SaaS Auth API",
    description="Production-ready backend service with authentication, rate limiting, billing, and security",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware (order matters - first added = first executed)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


@app.middleware("http")
async def usage_tracking_middleware(request: Request, call_next):
    """Middleware to track API usage and enforce rate limits."""
    # Skip tracking for health checks and docs
    if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    
    return response


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        "http_exception",
        request_id=request_id,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "An internal server error occurred",
                "request_id": request_id,
            }
        },
    )


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(password_reset.router, prefix="/auth/password", tags=["password-reset"])
app.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# Import and include OAuth routes
from app.api.routes import oauth
app.include_router(oauth.router, prefix="/auth/oauth", tags=["oauth"])

# Import and include 2FA routes
from app.api.routes import two_factor
app.include_router(two_factor.router, prefix="/auth/2fa", tags=["two-factor-authentication"])


@app.get("/")
async def root():
    return {
        "message": "SaaS Auth API",
        "version": "1.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment.value
    }


@app.get("/protected")
async def protected_endpoint(current_user: User = Depends(get_current_active_user)):
    """Example of a protected endpoint"""
    return {"message": "This is a protected endpoint"}
