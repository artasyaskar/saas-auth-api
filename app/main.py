from fastapi import FastAPI, Request, HTTPException, status, Depends
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
from app.api.auth import get_current_active_user


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
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
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
async def protected_endpoint(current_user: User = Depends(get_current_active_user)):
    """Example of a protected endpoint"""
    return {"message": "This is a protected endpoint"}
