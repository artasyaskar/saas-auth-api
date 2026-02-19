# SaaS Auth API

A production-ready backend service that demonstrates secure authentication, role-based access control, rate limiting, usage tracking, and billing simulation.

##  Project Vision

This project answers the critical hiring question: **"Can this person build and operate a secure, paid backend system?"**

Most developers can build APIs that return JSON. Very few can:
- Handle authentication correctly
- Enforce permissions  
- Protect APIs from abuse
- Track usage
- Simulate billing

This proves you understand how software actually makes money.

##  What This System Does

This is a backend service that:
-  Authenticates users using JWT (access + refresh tokens)
-  Enforces role-based access (USER, ADMIN)
-  Limits API calls per minute and per month
-  Tracks usage per user and endpoint
-  Simulates subscription plans (FREE vs PRO)
-  Blocks users when they exceed limits
-  Provides admin dashboard APIs

## 🛠 Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Auth & Security**: JWT, bcrypt password hashing
- **Database**: PostgreSQL (with SQLite fallback)
- **ORM**: SQLAlchemy
- **Rate Limiting**: Redis + in-memory fallback
- **Billing**: Stripe test mode (simulation)
- **Infrastructure**: Docker, docker-compose

##  Project Structure

```
saas-auth-api/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── users.py         # User profile and usage
│   │   └── admin.py         # Admin dashboard APIs
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   ├── security.py      # JWT and password hashing
│   │   └── rate_limit.py    # Rate limiting logic
│   ├── db/
│   │   ├── models.py        # Database models
│   │   └── session.py       # Database session
│   └── services/
│       ├── billing.py       # Billing simulation
│       └── usage.py         # Usage tracking
├── docker/
│   └── Dockerfile
├── tests/                   # Comprehensive test suite
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🏗 Installation & Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis (optional, for rate limiting)
- PostgreSQL (optional, defaults to SQLite)

### Quick Start

1. **Clone and setup**
```bash
git clone <repository-url>
cd saas-auth-api
```

2. **Environment configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Using Docker (Recommended)**
```bash
docker-compose up -d
```

4. **Manual setup (Development)**
```bash
# Install dependencies
pip install -r requirements.txt

# Run with SQLite (default)
uvicorn app.main:app --reload

# Or with PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost/saas_auth_db"
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

### Authentication Endpoints

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com", 
  "password": "secure_password"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=secure_password
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>
```

### User Endpoints

#### Get Profile
```http
GET /users/profile
Authorization: Bearer <access_token>
```

#### Get Usage Stats
```http
GET /users/usage
Authorization: Bearer <access_token>
```

### Admin Endpoints (Admin access required)

#### Get All Users
```http
GET /admin/users
Authorization: Bearer <admin_token>
```

#### Get System Stats
```http
GET /admin/stats
Authorization: Bearer <admin_token>
```

#### Suspend User
```http
PUT /admin/users/{user_id}/suspend
Authorization: Bearer <admin_token>
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app tests/
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./saas_auth.db` |
| `SECRET_KEY` | JWT signing key | Change in production! |
| `REDIS_URL` | Redis connection for rate limiting | `redis://localhost:6379` |
| `STRIPE_API_KEY` | Stripe test API key | Optional |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |

### Rate Limits by Plan

| Plan | Requests/Minute | Monthly Quota |
|------|----------------|---------------|
| FREE | 60 | 1,000 |
| PRO | 300 | 10,000 |

## 🚦 Rate Limiting

The system implements two-tier rate limiting:

1. **Per-minute limits**: Enforced via Redis (fallback to in-memory)
2. **Monthly quotas**: Tracked in database, resets monthly

When limits are exceeded:
- **429 Too Many Requests**: Per-minute limit exceeded
- **403 Forbidden**: Monthly quota exceeded

##  Billing Simulation

The system simulates SaaS billing with:

- **Free Plan**: 60 requests/minute, 1,000 requests/month
- **Pro Plan**: 300 requests/minute, 10,000 requests/month

Stripe integration is in test mode - no real charges are made.

##  Security Features

- **JWT Authentication**: Access + refresh token pattern
- **Password Hashing**: bcrypt with salt
- **Role-Based Access**: USER vs ADMIN permissions
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Pydantic models for all inputs
- **CORS Configurable**: Secure cross-origin requests

##  Usage Tracking

Every API call is logged with:
- User ID
- Endpoint and method
- Response status code
- Response time
- Timestamp

Admins can view:
- Per-user usage statistics
- System-wide metrics
- Most-used endpoints
- Response time analytics

## 🐳 Docker Deployment

### Production Dockerfile
Optimized multi-stage build with:
- Non-root user execution
- Minimal attack surface
- Efficient layer caching

### Docker Compose
Complete stack with:
- Application container
- PostgreSQL database
- Redis for rate limiting
- Persistent volumes


##  Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

##  License

This project is licensed under the MIT License.

##  Default Admin Account

For testing, a default admin account is created:
- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@example.com`

 **Change this in production!**

---

**Built to demonstrate production-ready backend engineering skills**
