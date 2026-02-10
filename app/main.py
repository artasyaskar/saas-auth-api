from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.db.models import Base, User, RateLimit
from app.api import auth, users, admin
from app.services.usage import UsageService
from app.core.rate_limit import rate_limiter
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
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
    finally:
        db.close()
    
    yield


app = FastAPI(
    title="SaaS Auth API",
    description="Secure backend service with authentication, rate limiting, and billing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def usage_tracking_middleware(request: Request, call_next):
    """Middleware to track API usage and enforce rate limits"""
    start_time = time.time()
    
    # Get user from token if present
    user = None
    if "authorization" in request.headers:
        try:
            from app.api.auth import get_current_user
            token = request.headers["authorization"].split(" ")[1]
            db = next(get_db())
            user = get_current_user(token, db)
        except:
            pass
    
    # Check rate limits if user is authenticated
    if user:
        try:
            rate_limiter.check_rate_limit(user.id, next(get_db()))
        except HTTPException as e:
            return e
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log usage if user is authenticated
    if user and user:
        db = next(get_db())
        try:
            usage_service = UsageService(db)
            usage_service.log_usage(
                user_id=user.id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=process_time * 1000
            )
        finally:
            db.close()
    
    return response


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/")
async def root():
    return {
        "message": "SaaS Auth API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/protected")
async def protected_endpoint():
    """Example of a protected endpoint"""
    return {"message": "This is a protected endpoint"}
