# Development Guide

## SaaS Auth API - Development Guide

This guide covers everything you need to know about developing the SaaS Auth API.

## Table of Contents
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Database Migrations](#database-migrations)
- [API Design](#api-design)
- [Security](#security)
- [Performance](#performance)
- [Debugging](#debugging)

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git
- Make (optional)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-org/saas-auth-api.git
cd saas-auth-api
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your local settings
```

5. **Initialize database**
```bash
alembic upgrade head
```

6. **Run development server**
```bash
make dev
# Or: uvicorn app.main:app --reload --port 8000
```

---

## Project Structure

```
saas-auth-api/
├── app/                    # Main application code
│   ├── api/               # API routes
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── users.py       # User management
│   │   ├── admin.py       # Admin endpoints
│   │   └── routes/        # Additional routes
│   │       ├── password_reset.py
│   │       ├── api_keys.py
│   │       ├── analytics.py
│   │       └── webhooks.py
│   ├── core/              # Core utilities
│   │   ├── config.py      # Configuration
│   │   ├── security.py    # Security utilities
│   │   └── rate_limit.py  # Rate limiting
│   ├── db/                # Database
│   │   ├── models.py      # SQLAlchemy models
│   │   └── session.py     # Database sessions
│   ├── middleware/        # FastAPI middleware
│   │   ├── logging.py
│   │   ├── security.py
│   │   └── request_id.py
│   ├── services/          # Business logic
│   │   ├── analytics.py
│   │   ├── billing.py
│   │   ├── cache.py
│   │   ├── email.py
│   │   ├── export.py
│   │   ├── notifications.py
│   │   ├── password_reset.py
│   │   ├── token_blacklist.py
│   │   ├── usage.py
│   │   └── webhooks.py
│   └── utils/             # Utility functions
│       ├── validators.py
│       └── helpers.py
├── tests/                 # Test suite
├── docs/                  # Documentation
├── docker/                # Docker configurations
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── .github/              # GitHub workflows
├── Makefile              # Development commands
├── pyproject.toml        # Project configuration
└── README.md
```

---

## Development Workflow

### Branch Naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates
- `test/description` - Test additions/updates

### Commit Message Format
```
type: subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

Example:
```
feat: add password reset functionality

- Add token generation
- Add email template
- Add reset validation

Closes #123
```

### Pull Request Process
1. Create feature branch
2. Make changes with tests
3. Run full test suite
4. Update documentation
5. Submit PR with description
6. Code review
7. Merge to main

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v

# Run failed tests only
pytest --lf

# Run tests matching pattern
pytest -k "test_login"
```

### Test Structure

```python
# tests/test_feature.py
import pytest
from fastapi.testclient import TestClient

class TestFeatureName:
    """Group related tests in a class."""
    
    def test_specific_behavior(self, client, auth_headers):
        """Test docstring explains what is tested."""
        response = client.get("/endpoint", headers=auth_headers)
        assert response.status_code == 200
        assert "expected_key" in response.json()
    
    def test_error_condition(self, client):
        """Test error handling."""
        response = client.post("/endpoint", json={"invalid": "data"})
        assert response.status_code == 422
```

### Test Fixtures

Key fixtures in `conftest.py`:
- `db` - Database session
- `client` - Test client
- `test_user` - Regular user
- `admin_user` - Admin user
- `auth_headers` - Authentication headers

### Writing Tests

1. **Unit Tests**
```python
def test_service_function(db):
    service = MyService(db)
    result = service.do_something()
    assert result == expected_value
```

2. **Integration Tests**
```python
def test_endpoint_integration(client, auth_headers):
    response = client.get("/api/resource", headers=auth_headers)
    assert response.status_code == 200
```

3. **Async Tests**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

---

## Code Quality

### Linting

```bash
# Run all linters
make lint

# Run specific linter
flake8 app/
mypy app/
black --check app/
isort --check-only app/
```

### Formatting

```bash
# Auto-format code
make format

# Or individually
black app/ tests/
isort app/ tests/
```

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict, Any

def get_user(user_id: int, db: Session) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()
```

### Code Style

- Follow PEP 8
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all functions
- Comment complex logic

---

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration
alembic revision --autogenerate -m "add user profile fields"

# Create empty migration
alembic revision -m "manual migration"
```

### Migration Structure

```python
def upgrade():
    # Migration operations
    op.add_column('users', sa.Column('profile', sa.JSON(), nullable=True))
    
def downgrade():
    # Rollback operations
    op.drop_column('users', 'profile')
```

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade specific version
alembic upgrade +1

# Downgrade
alembic downgrade -1

# Current version
alembic current

# History
alembic history
```

### Migration Best Practices

1. Always test migrations on copy of production data
2. Make migrations reversible when possible
3. Avoid deleting data in migrations
4. Use batch operations for large datasets

---

## API Design

### RESTful Endpoints

```python
# Standard CRUD pattern
@router.get("/users")              # List
@router.post("/users")             # Create
@router.get("/users/{id}")        # Read
@router.put("/users/{id}")        # Update
@router.delete("/users/{id}")     # Delete
```

### Response Format

```python
# Success response
{
    "id": 1,
    "username": "john",
    "email": "john@example.com"
}

# Error response
{
    "detail": "Error message",
    "request_id": "uuid"
}

# List response
{
    "items": [...],
    "total": 100,
    "page": 1,
    "pages": 10
}
```

### Status Codes

- `200` - Success
- `201` - Created
- `202` - Accepted (async)
- `204` - No content
- `400` - Bad request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not found
- `422` - Validation error
- `429` - Rate limited
- `500` - Server error

### Validation

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123!"
            }
        }
```

---

## Security

### Authentication

```python
# Require authentication
async def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.username}

# Require admin
def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user
```

### Input Validation

```python
from app.utils.validators import validate_password_strength

@router.post("/register")
async def register(user: UserCreate):
    is_valid, error = validate_password_strength(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    # ...
```

### Rate Limiting

```python
from app.core.rate_limit import rate_limiter

@router.get("/endpoint")
async def endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    rate_limiter.check_rate_limit(current_user.id, db)
    # ...
```

---

## Performance

### Database Optimization

1. **Use Indexes**
```python
# In migration
op.create_index('ix_users_email', 'users', ['email'])
```

2. **Select Only Needed Columns**
```python
# Good
db.query(User.id, User.username).filter(...)

# Avoid
db.query(User).filter(...)  # Selects all columns
```

3. **Eager Loading**
```python
from sqlalchemy.orm import joinedload

db.query(User).options(joinedload(User.subscriptions)).all()
```

### Caching

```python
from app.services.cache import CacheService

cache = CacheService()

# Cache query result
def get_user_cached(user_id: int):
    return cache.remember(
        f"user:{user_id}",
        lambda: db.query(User).get(user_id),
        ttl=300
    )
```

### Async Operations

```python
# Use background tasks for heavy operations
from fastapi import BackgroundTasks

@router.post("/report")
async def generate_report(
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(generate_large_report)
    return {"message": "Report generation started"}
```

---

## Debugging

### Logging

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "user_action",
    user_id=user.id,
    action="login",
    ip_address=request.client.host
)

logger.error(
    "operation_failed",
    error=str(e),
    context={"user_id": user_id}
)
```

### Debugging Tools

```bash
# Interactive debugger
import pdb; pdb.set_trace()

# IPython debugger
import ipdb; ipdb.set_trace()

# FastAPI debug mode
uvicorn app.main:app --reload --log-level debug
```

### Common Issues

1. **Database Connection Issues**
```bash
# Check PostgreSQL
psql -U postgres -d saas_auth -c "SELECT 1;"

# Check connection pool
alembic current
```

2. **Redis Connection**
```bash
redis-cli ping
```

3. **Import Errors**
```python
# Check Python path
import sys
print(sys.path)

# Check module location
import app
print(app.__file__)
```

---

## Best Practices

### Do's
- ✓ Write tests for new features
- ✓ Add type hints
- ✓ Use dependency injection
- ✓ Handle errors gracefully
- ✓ Log important events
- ✓ Document complex logic
- ✓ Use transactions for DB operations
- ✓ Validate all inputs

### Don'ts
- ✗ Commit secrets to git
- ✗ Use print() for logging
- ✗ Ignore type hints
- ✗ Skip error handling
- ✗ Write long functions
- ✗ Bypass rate limiting
- ✗ Trust user input
- ✗ Forget database indexing

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- Slack: #dev-saas-auth
- Email: dev-team@example.com
- Issues: GitHub Issues
