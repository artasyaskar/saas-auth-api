# SaaS Auth API Development Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Architecture](#architecture)
4. [Development Setup](#development-setup)
5. [Code Organization](#code-organization)
6. [Services](#services)
7. [Database](#database)
8. [Testing](#testing)
9. [Security](#security)
10. [Performance](#performance)
11. [Monitoring](#monitoring)
12. [Deployment](#deployment)
13. [Contributing](#contributing)

## Overview

The SaaS Auth API is a comprehensive authentication and authorization service built with FastAPI, designed for enterprise SaaS applications. It provides robust security features, scalable architecture, and extensive customization options.

### Key Features

- **Multi-tenant Authentication**: Support for multiple organizations and users
- **OAuth2 Integration**: Built-in OAuth2 providers (Google, GitHub, etc.)
- **JWT Token Management**: Secure token generation, validation, and refresh
- **Rate Limiting**: Configurable rate limiting with multiple strategies
- **Session Management**: Redis-based session management with concurrent session control
- **Security Monitoring**: Real-time threat detection and alerting
- **Audit Logging**: Comprehensive audit trail for compliance
- **Feature Flags**: Advanced feature flag management
- **Webhooks**: Event-driven notifications
- **Health Monitoring**: Comprehensive health checks and metrics

### Technology Stack

- **Backend**: FastAPI with Python 3.9+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for caching and session storage
- **Message Queue**: Redis for background jobs
- **Monitoring**: Structured logging with correlation IDs
- **Testing**: Pytest with comprehensive test coverage
- **Documentation**: OpenAPI/Swagger with auto-generated docs

## Getting Started

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher
- Redis 6 or higher
- Docker and Docker Compose (recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/saas-auth-api.git
cd saas-auth-api

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload
```

### Docker Setup

```bash
# Build and start with Docker Compose
docker-compose up --build

# Run migrations
docker-compose exec api alembic upgrade head

# Create default admin user
docker-compose exec api python -c "
from app.main import create_default_admin
create_default_admin()
"
```

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │   Third Party   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                               │
                    ┌─────────▼─────────┐
                    │   Load Balancer   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   API Gateway    │
                    │  (FastAPI)      │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
    │  Services  │    │  Database  │    │    Redis   │
    │   Layer    │    │ PostgreSQL │    │  (Cache)   │
    └────────────┘    └────────────┘    └────────────┘
```

### Service Layer Architecture

The application follows a layered architecture pattern:

1. **API Layer** (`app/api/`): FastAPI routers and endpoints
2. **Service Layer** (`app/services/`): Business logic and orchestration
3. **Data Layer** (`app/db/`): Database models and session management
4. **Core Layer** (`app/core/`): Shared utilities and configurations

### Key Components

#### Authentication Services
- `CredentialService`: User credential validation
- `TokenService`: JWT token management
- `SessionService`: User session management
- `AuthOrchestrator`: Authentication flow coordination

#### Security Services
- `SecurityMonitoringService`: Threat detection and alerting
- `AuditLoggingService`: Compliance audit trails
- `RateLimiterConfigService`: Rate limiting configuration
- `TokenBlacklistService`: Token revocation management

#### Utility Services
- `CacheService`: Multi-backend caching
- `BackgroundJobService`: Asynchronous job processing
- `WebhookService`: Event notifications
- `FeatureFlagService`: Feature flag management

## Development Setup

### Environment Configuration

Create a `.env` file with the following configuration:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/saas_auth

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=development
DEBUG=true
API_V1_STR=/api/v1

# External Services
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

### Database Setup

1. **Install PostgreSQL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS with Homebrew
   brew install postgresql
   brew services start postgresql
   ```

2. **Create Database**:
   ```sql
   CREATE DATABASE saas_auth;
   CREATE USER saas_auth_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE saas_auth TO saas_auth_user;
   ```

3. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

### Redis Setup

1. **Install Redis**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS with Homebrew
   brew install redis
   brew services start redis
   ```

2. **Configure Redis** (optional):
   ```bash
   # Edit /etc/redis/redis.conf
   # Set password and other security settings
   ```

## Code Organization

### Directory Structure

```
app/
├── api/                    # API routers and endpoints
│   ├── v1/               # API version 1
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── users.py      # User management endpoints
│   │   └── admin.py      # Admin endpoints
│   └── health.py          # Health check endpoints
├── core/                   # Core utilities and configurations
│   ├── config.py          # Application configuration
│   ├── security.py        # Security utilities
│   ├── jwt.py            # JWT token management
│   ├── exceptions.py      # Custom exceptions
│   ├── middleware.py     # FastAPI middleware
│   └── dependency_injection.py  # DI container
├── services/               # Business logic services
│   ├── auth/             # Authentication services
│   ├── security.py       # Security monitoring
│   ├── cache.py          # Caching service
│   ├── background_jobs.py # Background job processing
│   ├── webhooks.py       # Webhook management
│   ├── feature_flags.py  # Feature flag service
│   └── session_management.py  # Session management
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── session.py         # Database session management
│   └── utils.py          # Database utilities
├── schemas/               # Pydantic schemas
│   ├── auth.py           # Authentication schemas
│   ├── users.py          # User schemas
│   └── common.py         # Common schemas
├── middleware/            # Custom middleware
│   ├── validation.py     # Request validation
│   ├── security.py       # Security headers
│   └── logging.py       # Request logging
└── tests/                 # Test suite
    ├── unit/              # Unit tests
    ├── integration/       # Integration tests
    └── performance/       # Performance tests
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private Members**: `_leading_underscore`
- **Endpoints**: `/kebab-case`

### Code Style

The project follows PEP 8 with additional conventions:

```python
# Import order
import os
import sys
from typing import Optional, List

import fastapi
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.auth import AuthService

# Class definition
class UserService:
    """User service for managing user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Implementation
        pass
```

## Services

### Service Pattern

All services follow a consistent pattern:

```python
class BaseService:
    """Base service with common functionality."""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = structlog.get_logger()
    
    def _handle_error(self, error: Exception, context: str) -> None:
        """Handle service errors consistently."""
        self.logger.error(f"Error in {context}: {str(error)}")
        raise ServiceError(f"Service error in {context}: {str(error)}")
```

### Authentication Services

#### CredentialService
Handles user credential validation and authentication:

```python
from app.services.auth.credential_service import CredentialService

# Usage
credential_service = CredentialService(db)
result = await credential_service.validate_credentials(
    email="user@example.com",
    password="password123"
)
```

#### TokenService
Manages JWT token lifecycle:

```python
from app.services.auth.token_service import TokenService

# Usage
token_service = TokenService(db)
access_token = await token_service.create_access_token(
    user_id="user123",
    permissions=["read", "write"]
)
```

#### SessionService
Manages user sessions with Redis:

```python
from app.services.session_management import create_user_session

# Usage
session_id = await create_user_session(
    user_id="user123",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)
```

### Security Services

#### SecurityMonitoringService
Real-time threat detection:

```python
from app.services.security_monitoring import record_security_event

# Usage
await record_security_event(
    event_type=SecurityEventType.LOGIN_FAILED,
    severity=SecurityEventSeverity.MEDIUM,
    details={"ip": "192.168.1.1", "user_id": "user123"},
    source_ip="192.168.1.1"
)
```

#### AuditLoggingService
Comprehensive audit logging:

```python
from app.services.audit import log_audit_event

# Usage
await log_audit_event(
    event_type=AuditEventType.USER_LOGIN,
    user_id="user123",
    resource_id="session_456",
    details={"ip": "192.168.1.1", "method": "password"}
)
```

## Database

### Models

Database models use SQLAlchemy with proper relationships:

```python
from app.db.models import User, UserSession, AuditLog

# Query examples
users = db.query(User).filter(User.is_active == True).all()
user_sessions = db.query(UserSession).filter(
    UserSession.user_id == user_id
).order_by(UserSession.created_at.desc()).limit(10).all()
```

### Migrations

Database migrations are managed with Alembic:

```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Database Utilities

Use the database utilities for common operations:

```python
from app.db.utils import (
    execute_query,
    execute_transaction,
    paginate_query,
    bulk_insert
)

# Transaction example
async with execute_transaction(db) as session:
    user = User(email="test@example.com")
    session.add(user)
    # Auto-commits on success, rolls back on error
```

## Testing

### Test Structure

The test suite is organized into three main categories:

1. **Unit Tests** (`tests/unit/`): Test individual components in isolation
2. **Integration Tests** (`tests/integration/`): Test component interactions
3. **Performance Tests** (`tests/performance/`): Test performance characteristics

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run performance tests
pytest tests/performance/ -m slow
```

### Writing Tests

#### Unit Tests

```python
import pytest
from app.services.auth import AuthService
from app.schemas.auth import UserLogin

class TestAuthService:
    def test_user_login_success(self, db_session):
        """Test successful user login."""
        auth_service = AuthService(db_session)
        login_data = UserLogin(
            email="test@example.com",
            password="testpassword123"
        )
        
        result = auth_service.login(login_data)
        
        assert result.access_token is not None
        assert result.refresh_token is not None
    
    def test_user_login_invalid_credentials(self, db_session):
        """Test login with invalid credentials."""
        auth_service = AuthService(db_session)
        login_data = UserLogin(
            email="test@example.com",
            password="wrongpassword"
        )
        
        with pytest.raises(AuthenticationError):
            auth_service.login(login_data)
```

#### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAuthAPI:
    def test_login_endpoint(self):
        """Test login API endpoint."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
```

### Test Fixtures

Common test fixtures are defined in `tests/conftest.py`:

```python
import pytest
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.main import app

@pytest.fixture
def db_session():
    """Create a test database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
```

## Security

### Authentication Flow

The authentication flow follows these steps:

1. **User Registration**: Create user account with email verification
2. **Email Verification**: Verify user email address
3. **Login**: Authenticate with credentials
4. **Token Generation**: Issue JWT access and refresh tokens
5. **Session Creation**: Create Redis session for tracking
6. **Token Validation**: Validate tokens on each request

### Security Best Practices

#### Password Security
```python
from app.core.security import hash_password, verify_password

# Hash password
hashed = hash_password("user_password123")

# Verify password
is_valid = verify_password("user_password123", hashed)
```

#### Token Security
```python
from app.core.jwt import TokenManager

# Create token manager
token_manager = TokenManager()

# Generate tokens
access_token = token_manager.create_access_token(
    user_id="user123",
    expires_in=1800  # 30 minutes
)

# Validate token
payload = token_manager.validate_token(access_token)
```

#### Rate Limiting
```python
from app.services.rate_limiter_config import RateLimiterConfigService

# Check rate limit
rate_limiter = RateLimiterConfigService(db)
is_allowed = await rate_limiter.is_allowed(
    key="user123",
    limit=100,
    window=3600  # 1 hour
)
```

### Security Headers

Security headers are automatically added:

```python
# Custom security headers
app.add_middleware(
    SecurityHeadersMiddleware,
    headers={
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
)
```

## Performance

### Caching Strategy

Multi-tier caching is implemented:

```python
from app.services.cache import get_cache_service

# Get cache service
cache = get_cache_service()

# Cache with TTL
await cache.set("user:123", user_data, ttl=300)

# Get from cache
cached_user = await cache.get("user:123")

# Cache with tags
await cache.set("config:app", config_data, tags=["config"])
await cache.invalidate_by_tags(["config"])
```

### Database Optimization

Connection pooling and query optimization:

```python
from app.db.session import get_db

# Optimized query with connection pooling
async with get_db() as db:
    # Use indexes efficiently
    users = db.query(User).filter(
        User.email == "test@example.com"
    ).options(
        joinedload(User.sessions)
    ).first()
```

### Background Jobs

Asynchronous job processing:

```python
from app.services.background_jobs import enqueue_email

# Enqueue background job
await enqueue_email(
    to="user@example.com",
    subject="Welcome!",
    template="welcome_email",
    context={"user_name": "John"}
)
```

## Monitoring

### Logging

Structured logging with correlation IDs:

```python
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "User login successful",
    user_id="user123",
    ip_address="192.168.1.1",
    correlation_id="abc123"
)
```

### Metrics

Application metrics collection:

```python
from app.services.metrics import increment_counter, record_timing

# Record metrics
increment_counter("api_requests", tags={"endpoint": "/auth/login"})
record_timing("database_query", 0.05, tags={"table": "users"})
```

### Health Checks

Comprehensive health monitoring:

```python
# Health check endpoints
GET /health          # Overall health
GET /health/liveness   # Kubernetes liveness probe
GET /health/readiness  # Kubernetes readiness probe
GET /health/metrics    # System metrics
```

## Deployment

### Production Deployment

#### Docker Production

```dockerfile
# Dockerfile.production
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_HOST=${REDIS_HOST}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: saas-auth-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: saas-auth-api
  template:
    metadata:
      labels:
        app: saas-auth-api
    spec:
      containers:
      - name: api
        image: saas-auth-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Environment Variables

Production environment variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_HOST=redis-host
REDIS_PASSWORD=redis-password
SECRET_KEY=your-production-secret-key

# Optional
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
SMTP_PASSWORD=smtp-password
```

## Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-feature`
3. **Make** changes with proper testing
4. **Run** tests: `pytest`
5. **Commit** changes: `git commit -m "Add new feature"`
6. **Push** to fork: `git push origin feature/new-feature`
7. **Create** Pull Request

### Code Review Guidelines

- Ensure all tests pass
- Follow code style guidelines
- Add documentation for new features
- Update API documentation
- Consider security implications
- Test performance impact

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] Security considerations addressed
```

### Release Process

1. **Update** version in `pyproject.toml`
2. **Update** CHANGELOG.md
3. **Create** Git tag: `git tag v1.0.0`
4. **Push** tag: `git push origin v1.0.0`
5. **Create** GitHub Release
6. **Deploy** to production

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connection
psql $DATABASE_URL

# Check database logs
docker logs saas-auth-api_db_1
```

#### Redis Connection Issues
```bash
# Check Redis connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT

# Check Redis logs
docker logs saas-auth-api_redis_1
```

#### Token Issues
```python
# Debug token validation
from app.core.jwt import TokenManager
token_manager = TokenManager()
try:
    payload = token_manager.validate_token(token)
    print("Token valid:", payload)
except Exception as e:
    print("Token invalid:", str(e))
```

### Performance Issues

#### Slow Queries
```python
# Enable query logging
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Analyze slow queries
from app.db.utils import analyze_query_performance
results = analyze_query_performance(db, query)
```

#### Memory Issues
```python
# Monitor memory usage
import psutil
memory_usage = psutil.virtual_memory()
print(f"Memory usage: {memory_usage.percent}%")
```

### Getting Help

- **Documentation**: Check this guide and API docs
- **Issues**: Create GitHub issue with details
- **Discussions**: Use GitHub Discussions for questions
- **Slack**: Join our development Slack channel

## Additional Resources

- [API Documentation](./API.md)
- [Database Schema](./DATABASE.md)
- [Security Guide](./SECURITY.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

For more information, visit our [GitHub repository](https://github.com/your-org/saas-auth-api) or contact the development team.
