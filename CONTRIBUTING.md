# Contributing to SaaS Auth API

Thank you for your interest in contributing to the SaaS Auth API! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for example apps)

### Setup Development Environment

1. **Fork and clone the repository**
```bash
git clone https://github.com/your-username/saas-auth-api.git
cd saas-auth-api
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your local configuration
```

5. **Start services with Docker Compose**
```bash
docker-compose up -d
```

6. **Run database migrations**
```bash
alembic upgrade head
```

7. **Run the application**
```bash
uvicorn app.main:app --reload
```

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Critical production fixes

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Making Changes

1. Write code following the [Coding Standards](#coding-standards)
2. Add tests for your changes
3. Update documentation if needed
4. Run linting and tests locally
5. Commit with a clear message

### Commit Message Format

Follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(auth): add OAuth2 provider support for LinkedIn

- Add LinkedIn OAuth2 provider configuration
- Implement token exchange logic
- Add tests for LinkedIn OAuth flow

Closes #123
```

## Coding Standards

### Python Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Use isort for import sorting
- Use type hints where appropriate
- Maximum line length: 100 characters

### Code Organization

- Keep functions focused and small
- Use descriptive variable and function names
- Add docstrings to all public functions and classes
- Separate concerns into appropriate modules

### Security Best Practices

- Never commit secrets or API keys
- Validate all user inputs
- Use parameterized queries for database operations
- Sanitize data before logging
- Follow OWASP security guidelines

### Example Code Structure

```python
"""
Module docstring describing the purpose of this module.
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ExampleData:
    """Dataclass for example data."""
    id: int
    name: str


def process_data(data: ExampleData) -> bool:
    """
    Process example data.
    
    Args:
        data: The data to process
        
    Returns:
        True if successful, False otherwise
    """
    # Implementation
    return True
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_feature_flags.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/
```

### Writing Tests

- Write tests for all new features
- Aim for high code coverage (>80%)
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies

### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from app.services.feature_flags import FeatureFlagService


def test_create_feature_flag():
    """Test creating a new feature flag."""
    service = FeatureFlagService(db=Mock())
    
    result = service.create_flag(
        name="test_flag",
        description="Test flag",
        default_value=False
    )
    
    assert result.name == "test_flag"
    assert result.default_value is False
```

### Test Coverage

Check coverage report:
```bash
pytest --cov=app --cov-report=term-missing
```

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include parameter and return type descriptions
- Add examples for complex functions

### API Documentation

- Update OpenAPI/Swagger specs for new endpoints
- Add examples to API documentation
- Document error responses
- Include authentication requirements

### README Updates

- Update README.md for significant changes
- Add new features to the features list
- Update installation instructions if needed
- Update environment variable documentation

## Submitting Changes

### Pull Request Process

1. **Update your branch**
```bash
git checkout develop
git pull origin develop
git checkout feature/your-feature-name
git rebase develop
```

2. **Run full test suite**
```bash
pytest
black app tests
flake8 app tests
mypy app
```

3. **Push to your fork**
```bash
git push origin feature/your-feature-name
```

4. **Create Pull Request**
- Go to the repository on GitHub
- Click "New Pull Request"
- Select your branch
- Fill in the PR template
- Link related issues

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts
- [ ] PR description clearly describes changes

### Review Process

- Maintainers will review your PR
- Address feedback in a timely manner
- Keep PRs focused and small
- Respond to review comments

## Reporting Issues

### Bug Reports

When reporting a bug, include:

- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version)
- Relevant logs or error messages

### Feature Requests

When requesting a feature, include:

- Description of the feature
- Use case or problem it solves
- Possible implementation approach
- Alternative solutions considered

### Security Issues

For security vulnerabilities, do not open a public issue. Instead:

- Email security@saas-auth-api.com
- Include "Security" in the subject line
- Provide details about the vulnerability
- Wait for confirmation before disclosing

## Additional Resources

- [Project Documentation](docs/)
- [API Examples](docs/API_EXAMPLES.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)

## Questions?

- Open an issue for questions
- Join our community chat
- Contact maintainers via email

Thank you for contributing to SaaS Auth API!
