# SaaS Auth API

Enterprise-grade authentication and authorization service with comprehensive security features.

## 🚀 Features

### Core Authentication
- **Multi-provider OAuth2/OIDC**: Google, GitHub, Microsoft, Apple, Okta
- **Two-Factor Authentication**: TOTP, SMS, Email, Backup codes, WebAuthn/FIDO2
- **Traditional Auth**: Email/password with secure password policies
- **Session Management**: JWT tokens with refresh tokens, session timeout

### Enterprise Features
- **Multi-tenant Organizations**: Role-based access control, member management
- **SAML SSO**: SP/IdP initiated flows, metadata generation, certificate management
- **SCIM 2.0**: User provisioning, bulk operations, filtering and pagination
- **Advanced RBAC**: Role hierarchy, permission evaluation, ABAC, policy-based access

### Security & Compliance
- **Audit Logging**: Comprehensive request/response logging with PII redaction
- **Rate Limiting**: Configurable limits per endpoint and user
- **Webhook Security**: Signature verification, retry logic, dead letter queue
- **Data Protection**: Encryption at rest and in transit, GDPR compliance

### Developer Experience
- **RESTful API**: OpenAPI 3.0 specification, interactive documentation
- **Webhooks**: Real-time event notifications with retry mechanisms
- **SDKs**: Python, JavaScript, Go, Java client libraries
- **Monitoring**: Prometheus metrics, Grafana dashboards, alerting

## 📋 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/saas-auth-api.git
cd saas-auth-api

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python scripts/db_migrate.py upgrade

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Basic Usage

```python
import requests

# Register a new user
response = requests.post('http://localhost:8000/auth/register', json={
    'email': 'user@example.com',
    'password': 'SecurePassword123!',
    'username': 'testuser'
})

# Login
response = requests.post('http://localhost:8000/auth/login', data={
    'username': 'user@example.com',
    'password': 'SecurePassword123!'
})

tokens = response.json()
access_token = tokens['access_token']

# Use the API
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get('http://localhost:8000/users/me', headers=headers)
```

### 3. OAuth2 Integration

```python
# Get OAuth providers
response = requests.get('http://localhost:8000/auth/oauth/providers')
providers = response.json()

# Start OAuth flow with Google
response = requests.get('http://localhost:8000/auth/oauth/google/url', params={
    'redirect_uri': 'https://your-app.com/callback'
})

auth_url = response.json()['authorization_url']
# Redirect user to auth_url
```

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend App  │    │   Mobile App    │    │   Third Party   │
│                 │    │                 │    │   Services      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     API Gateway/LB        │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     SaaS Auth API         │
                    │  (FastAPI + SQLAlchemy)   │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────┴───────┐    ┌─────────┴───────┐    ┌─────────┴───────┐
│   PostgreSQL    │    │      Redis      │    │   External      │
│   (Primary DB)  │    │   (Cache/Sess)  │    │   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Service Components

- **API Layer**: FastAPI with middleware for logging, rate limiting, security
- **Business Logic**: Authentication, authorization, user management services
- **Data Layer**: PostgreSQL with SQLAlchemy ORM, Redis for caching
- **Integration Layer**: OAuth providers, email services, webhook delivery
- **Monitoring**: Prometheus metrics, structured logging, distributed tracing

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/saas_auth
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
TOKEN_EXPIRE_MINUTES=30

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key

# OAuth Providers
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Frontend
FRONTEND_URL=https://your-app.com
BASE_URL=https://api.your-app.com
```

### Advanced Configuration

See [Configuration Guide](docs/configuration.md) for detailed configuration options including:
- Database connection pooling
- Rate limiting strategies
- OAuth provider setup
- Email service configuration
- Security settings
- Monitoring and logging

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`

### Key Endpoints

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh access token

#### OAuth2
- `GET /auth/oauth/providers` - List OAuth providers
- `GET /auth/oauth/{provider}/url` - Get authorization URL
- `POST /auth/oauth/{provider}/callback` - OAuth callback

#### Two-Factor Auth
- `POST /auth/2fa/totp/setup` - Setup TOTP
- `POST /auth/2fa/totp/verify` - Verify TOTP
- `POST /auth/2fa/sms/send` - Send SMS code
- `POST /auth/2fa/sms/verify` - Verify SMS code

#### Organizations
- `POST /organizations` - Create organization
- `GET /organizations` - List user organizations
- `GET /organizations/{id}/members` - List organization members
- `POST /organizations/{id}/invitations` - Invite member

#### SAML SSO
- `GET /saml/metadata` - SP metadata
- `GET /saml/sso` - Initiate SSO
- `POST /saml/acs` - Assertion consumer service

#### SCIM
- `GET /scim/v2/Users` - List users
- `POST /scim/v2/Users` - Create user
- `PATCH /scim/v2/Users/{id}` - Update user
- `POST /scim/v2/Bulk` - Bulk operations

## 🔐 Security

### Authentication Methods

1. **Email/Password**: Traditional authentication with secure password policies
2. **OAuth2/OIDC**: Social login with major providers
3. **SAML SSO**: Enterprise single sign-on
4. **Two-Factor Auth**: Multiple 2FA methods for enhanced security

### Security Features

- **Password Security**: Bcrypt hashing, minimum requirements, breach detection
- **Token Security**: JWT with RS256 signing, refresh tokens, revocation
- **Rate Limiting**: Configurable limits per endpoint and user
- **Audit Logging**: Comprehensive logging with PII redaction
- **Data Encryption**: TLS 1.3, database encryption, secret management

### Compliance

- **GDPR**: Data portability, right to be forgotten, consent management
- **SOC 2**: Security controls, audit trails, access controls
- **HIPAA**: Healthcare data protection (optional module)
- **ISO 27001**: Information security management

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t saas-auth/api .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### Terraform

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan and apply
terraform plan
terraform apply
```

## 📊 Monitoring

### Metrics

The API exposes Prometheus metrics at `/metrics`:

- **HTTP Metrics**: Request count, duration, status codes
- **Business Metrics**: User registrations, logins, errors
- **System Metrics**: Memory, CPU, database connections
- **Custom Metrics**: OAuth flows, 2FA usage, webhook delivery

### Dashboards

Pre-built Grafana dashboards available:
- API Performance
- Authentication Metrics
- Business KPIs
- Infrastructure Health

### Alerting

Configurable alerts for:
- Service downtime
- High error rates
- Security events
- Performance degradation

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/

# Run with specific environment
ENVIRONMENT=testing pytest tests/integration/
```

### Performance Tests

```bash
# Run load tests
k6 run tests/performance/load-test.js

# Run stress tests
k6 run tests/performance/stress-test.js
```

## 📖 Examples

### Python SDK

```python
from saas_auth import SaaSAuthClient

client = SaaSAuthClient(
    base_url='https://api.saas-auth.com',
    api_key='your-api-key'
)

# Register user
user = client.auth.register(
    email='user@example.com',
    password='SecurePassword123!',
    username='testuser'
)

# Login
tokens = client.auth.login(
    username='user@example.com',
    password='SecurePassword123!'
)

# Get user info
user = client.users.me()
```

### JavaScript SDK

```javascript
import { SaaSAuthClient } from 'saas-auth-js';

const client = new SaaSAuthClient({
  baseURL: 'https://api.saas-auth.com',
  apiKey: 'your-api-key'
});

// Register user
const user = await client.auth.register({
  email: 'user@example.com',
  password: 'SecurePassword123!',
  username: 'testuser'
});

// Login
const tokens = await client.auth.login({
  username: 'user@example.com',
  password: 'SecurePassword123!'
});
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/saas-auth-api.git
cd saas-auth-api

# Set up development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# Run pre-commit setup
pre-commit install

# Run tests
pytest
```

### Code Style

- **Python**: Black, isort, flake8, mypy
- **JavaScript**: ESLint, Prettier
- **Go**: gofmt, golint
- **Java**: Checkstyle, SpotBugs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.saas-auth.com](https://docs.saas-auth.com)
- **API Reference**: [api.saas-auth.com/docs](https://api.saas-auth.com/docs)
- **Support Email**: support@saas-auth.com
- **Discord Community**: [discord.gg/saas-auth](https://discord.gg/saas-auth)
- **GitHub Issues**: [github.com/your-org/saas-auth-api/issues](https://github.com/your-org/saas-auth-api/issues)

## 🗺️ Roadmap

### v1.2 (Q2 2024)
- [ ] Biometric authentication
- [ ] Advanced threat detection
- [ ] GraphQL API
- [ ] Mobile SDKs

### v1.3 (Q3 2024)
- [ ] Machine learning fraud detection
- [ ] Advanced analytics dashboard
- [ ] Multi-region deployment
- [ ] Enterprise SSO enhancements

### v2.0 (Q4 2024)
- [ ] Microservices architecture
- [ ] Event-driven architecture
- [ ] Advanced RBAC system
- [ ] Custom authentication providers

---

**Built with ❤️ by the SaaS Auth Team**
