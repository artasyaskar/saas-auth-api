# SaaS Auth API

An enterprise-grade authentication and authorization service for SaaS applications with comprehensive features including OAuth2/OIDC, two-factor authentication, webhooks, feature flags, real-time notifications, GraphQL API, and more.

## Project Vision

This project demonstrates the ability to build and operate a secure, scalable, and feature-rich backend system that powers real-world SaaS applications. It showcases:

- **Enterprise Authentication**: JWT, OAuth2/OIDC, social login, 2FA
- **Advanced Security**: Rate limiting, audit logging, fraud detection
- **Developer Experience**: SDKs, GraphQL, comprehensive documentation
- **Operational Excellence**: Monitoring, alerting, CI/CD, infrastructure as code
- **Compliance**: GDPR/CCPA consent management, data export
- **Scalability**: Redis Cluster, Elasticsearch, Kubernetes deployment

## Features

### Core Authentication
- JWT-based authentication with access and refresh tokens
- OAuth2/OIDC integration (Google, GitHub, Apple)
- Social login providers
- Two-Factor Authentication (TOTP, SMS, Email)
- API key management
- Session management with multi-device support

### Security & Compliance
- Role-based access control (RBAC)
- Advanced rate limiting with Redis Cluster
- Comprehensive audit logging
- GDPR/CCPA consent management
- Data export and deletion requests
- Security event tracking
- Fraud detection and risk scoring (ML)

### Developer Tools
- RESTful API with OpenAPI/Swagger documentation
- GraphQL API with subscriptions for real-time updates
- Multi-language SDKs (JavaScript, Python, React Native, Flutter)
- Webhook management with retry logic
- Feature flag management with A/B testing
- API versioning and deprecation

### Business Features
- Subscription and billing management (Stripe integration)
- Usage-based billing
- Usage analytics and reporting
- Funnel analysis and predictive analytics
- Geolocation and IP intelligence

### Communication
- Real-time notifications via WebSocket
- In-app messaging system
- Multi-channel notifications (email, SMS, push)
- Email service with multi-provider support (SMTP, SendGrid, Mailgun)

### Infrastructure & Operations
- File storage with multi-provider support (S3, local)
- Search service with Elasticsearch integration
- Workflow automation engine
- Cache invalidation service
- Comprehensive monitoring (Prometheus, Grafana)
- CI/CD pipeline with GitHub Actions
- Docker Compose for local development
- Kubernetes deployment manifests
- Terraform infrastructure as code

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL 15
- **Cache**: Redis 7, Redis Cluster
- **Search**: Elasticsearch 8.11
- **GraphQL**: Strawberry

### Security
- **Authentication**: JWT, OAuth2/OIDC (Authlib)
- **Password Hashing**: bcrypt
- **Rate Limiting**: Redis Cluster with multiple algorithms
- **Audit Logging**: Custom service with compliance tracking

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes
- **IaC**: Terraform (AWS)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana
- **Reverse Proxy**: Nginx

### Billing & Payments
- **Payment Provider**: Stripe
- **Webhooks**: Custom service with retry logic

### Development Tools
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Linting**: Black, Flake8, MyPy
- **Security**: Safety, Bandit
- **Load Testing**: Locust-style benchmarks

## Project Structure

```
saas-auth-api/
├── app/
│   ├── main.py                      # FastAPI application entry point
│   ├── api/
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── users.py                 # User profile and usage
│   │   ├── admin.py                 # Admin dashboard APIs
│   │   ├── routes/
│   │   │   ├── consent.py           # Consent management
│   │   │   ├── messaging.py         # Messaging service
│   │   │   ├── workflows.py         # Workflow automation
│   │   │   ├── files.py             # File storage
│   │   │   └── feature_flags.py     # Feature flags
│   │   ├── openapi.py               # OpenAPI/Swagger config
│   │   └── graphql/
│   │       └── schema.py            # GraphQL schema
│   ├── core/
│   │   ├── config.py                # Configuration management
│   │   ├── security.py              # JWT and password hashing
│   │   └── rate_limit.py            # Rate limiting logic
│   ├── db/
│   │   ├── models.py                # Database models
│   │   └── session.py               # Database session
│   ├── services/
│   │   ├── billing.py               # Billing service
│   │   ├── usage.py                 # Usage tracking
│   │   ├── oauth2.py                # OAuth2/OIDC service
│   │   ├── two_factor.py            # 2FA service
│   │   ├── social_login.py          # Social login
│   │   ├── websocket.py             # WebSocket service
│   │   ├── audit.py                 # Audit logging
│   │   ├── rate_limit_cluster.py    # Redis Cluster rate limiting
│   │   ├── monitoring.py            # Monitoring service
│   │   ├── geolocation.py           # Geolocation service
│   │   ├── email.py                 # Email service
│   │   ├── webhook.py               # Webhook service
│   │   ├── analytics.py             # Analytics service
│   │   ├── consent.py               # Consent management
│   │   ├── api_gateway.py           # API gateway
│   │   ├── file_storage.py          # File storage
│   │   ├── search.py                # Search service
│   │   ├── workflow.py              # Workflow automation
│   │   ├── messaging.py             # Messaging service
│   │   ├── ml_service.py            # ML service
│   │   ├── api_versioning.py        # API versioning
│   │   ├── feature_flags.py         # Feature flags
│   │   ├── cache_invalidation.py    # Cache invalidation
│   │   └── rate_limiter_config.py   # Rate limiter config
│   └── graphql/
│       └── schema.py                # GraphQL schema
├── alembic/
│   └── versions/                    # Database migrations
├── benchmarks/
│   └── load_test.py                 # Load testing
├── cli/
│   └── main.py                      # CLI tool
├── dashboard/
│   └── index.html                   # Performance dashboard
├── docker/
│   └── Dockerfile
├── docs/
│   ├── ARCHITECTURE.md              # Architecture documentation
│   ├── DEVELOPMENT.md               # Development guide
│   └── API_EXAMPLES.md              # API examples
├── examples/
│   └── react-app/                   # React example
├── grafana/
│   └── provisioning/                # Grafana dashboards
├── kubernetes/
│   └── deployment.yaml              # K8s manifests
├── nginx/
│   └── nginx.conf                   # Nginx config
├── prometheus/
│   ├── prometheus.yml               # Prometheus config
│   └── alerts.yml                   # Alert rules
├── scripts/
│   └── security_scan.py            # Security scanning
├── sdk/
│   ├── javascript/                  # JavaScript SDK
│   ├── react-native/                # React Native SDK
│   └── flutter/                     # Flutter SDK
├── terraform/
│   ├── main.tf                      # Terraform config
│   └── variables.tf                # Terraform variables
├── tests/
│   ├── integration/                 # Integration tests
│   └── unit/                        # Unit tests
├── .github/
│   └── workflows/
│       └── ci-cd.yml                # CI/CD pipeline
├── requirements.txt
├── docker-compose.yml
├── alembic.ini
└── README.md
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Elasticsearch 8.11+ (optional, for search)
- Node.js 18+ (for example apps)

### Quick Start with Docker Compose

1. **Clone the repository**
```bash
git clone https://github.com/artasyaskar/saas-auth-api
cd saas-auth-api
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start all services**
```bash
docker-compose up -d
```

This will start:
- API application (FastAPI)
- PostgreSQL database
- Redis cache
- Redis Cluster
- Elasticsearch
- Prometheus (monitoring)
- Grafana (dashboards)
- Nginx (reverse proxy)
- Celery worker
- Flower (Celery monitoring)
- Mailhog (email testing)

4. **Run database migrations**
```bash
docker-compose exec app alembic upgrade head
```

5. **Access the services**
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090
- Flower: http://localhost:5555
- Mailhog: http://localhost:8025

### Manual Setup (Development)

1. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up PostgreSQL**
```bash
# Create database
createdb saas_auth_db

# Run migrations
alembic upgrade head
```

3. **Start Redis**
```bash
redis-server
```

4. **Start the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### CLI Tool

The project includes a CLI tool for management tasks:

```bash
# Initialize database
python -m cli.main db init

# Create a user
python -m cli.main user create --email user@example.com --password secret123

# List users
python -m cli.main user list

# Create feature flag
python -m cli.main feature-flag create --name new_feature --percentage 50

# View monitoring stats
python -m cli.main monitoring stats

# Run security audit
python -m cli.main security audit
```

## API Documentation

### REST API

The REST API is documented with OpenAPI/Swagger and available at:
- Interactive docs: http://localhost:8000/docs
- JSON schema: http://localhost:8000/openapi.json

### GraphQL API

The GraphQL endpoint is available at `/v1/graphql` with support for:
- Queries: Fetch data
- Mutations: Modify data
- Subscriptions: Real-time updates via WebSocket

Example GraphQL query:
```graphql
query {
  me {
    id
    username
    email
    role
  }
}
```

### Key Endpoints

#### Authentication
- `POST /v1/auth/register` - Register new user
- `POST /v1/auth/login` - Login user
- `POST /v1/auth/refresh` - Refresh access token
- `POST /v1/auth/logout` - Logout user
- `POST /v1/auth/2fa/enable` - Enable 2FA
- `POST /v1/auth/oauth/{provider}` - OAuth login

#### User Management
- `GET /v1/users/me` - Get current user profile
- `PUT /v1/users/me` - Update profile
- `GET /v1/users/usage` - Get usage statistics

#### API Keys
- `POST /v1/api-keys` - Create API key
- `GET /v1/api-keys` - List API keys
- `DELETE /v1/api-keys/{id}` - Delete API key

#### Webhooks
- `POST /v1/webhooks` - Create webhook
- `GET /v1/webhooks` - List webhooks
- `DELETE /v1/webhooks/{id}` - Delete webhook

#### Feature Flags
- `POST /v1/feature-flags` - Create feature flag
- `GET /v1/feature-flags` - List feature flags
- `POST /v1/feature-flags/{name}/evaluate` - Evaluate flag

See [API_EXAMPLES.md](docs/API_EXAMPLES.md) for comprehensive examples.

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_feature_flags.py

# Run integration tests
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Load Testing

```bash
# Run load tests
python benchmarks/load_test.py --users 100 --duration 60
```

### Security Scanning

```bash
# Run security scan
python scripts/security_scan.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `ELASTICSEARCH_HOST` | Elasticsearch host | `http://localhost:9200` |
| `SECRET_KEY` | JWT signing key | Change in production! |
| `STRIPE_API_KEY` | Stripe API key | Optional |
| `AWS_ACCESS_KEY_ID` | AWS access key | Optional |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Optional |
| `SMTP_HOST` | SMTP server | Optional |
| `SENDGRID_API_KEY` | SendGrid API key | Optional |
| `MAILGUN_API_KEY` | Mailgun API key | Optional |

### Rate Limits by Plan

| Plan | Requests/Minute | Monthly Quota |
|------|----------------|---------------|
| FREE | 100 | 10,000 |
| PRO | 1,000 | 100,000 |
| ENTERPRISE | Custom | Custom |

## Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at `/metrics`:
- Request rate and latency
- Error rates
- Database connection pool
- Redis operations
- Custom business metrics

### Grafana Dashboards

Pre-configured dashboards include:
- API Overview
- Database Performance
- Redis Performance
- System Resources
- Security Events

### Alerting

Prometheus alert rules are configured in `prometheus/alerts.yml`:
- High API latency
- High error rates
- Database connection issues
- Redis memory usage
- Security events

## Deployment

### Kubernetes

Deploy to Kubernetes using the provided manifests:

```bash
kubectl apply -f kubernetes/deployment.yaml
```

### Terraform

Provision AWS infrastructure:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### CI/CD

The GitHub Actions workflow automatically:
- Runs linting and security scans
- Executes tests
- Builds Docker images
- Deploys to staging/production

## SDKs

### JavaScript

```bash
npm install @saas-auth-api/sdk
```

```javascript
import { AuthClient } from '@saas-auth-api/sdk';

const client = new AuthClient({
  baseURL: 'https://api.saas-auth-api.com/v1'
});

await client.login('user@example.com', 'password');
```

### Python

```bash
pip install saas-auth-api
```

```python
from saas_auth_api import AuthClient

client = AuthClient(base_url='https://api.saas-auth-api.com/v1')
client.login('user@example.com', 'password')
```

### React Native

See `sdk/react-native/AuthClient.ts`

### Flutter

See `sdk/flutter/auth_client.dart`

## Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [API Examples](docs/API_EXAMPLES.md)

## Security Features

- **JWT Authentication**: Access + refresh token pattern
- **Password Hashing**: bcrypt with salt
- **Role-Based Access**: USER, ADMIN, MODERATOR roles
- **Rate Limiting**: Multi-tier protection
- **Audit Logging**: Comprehensive security event tracking
- **Fraud Detection**: ML-based risk scoring
- **GDPR/CCPA**: Consent management and data export

## License

This project is licensed under the MIT License.

## Support

- Documentation: https://docs.saas-auth-api.com
- Support Email: support@saas-auth-api.com
- Status Page: https://status.saas-auth-api.com
- GitHub Issues: https://github.com/saas-auth-api/issues

---

**Built to demonstrate enterprise-grade backend engineering skills**
