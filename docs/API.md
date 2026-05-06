# SaaS Auth API Documentation

## Overview

The SaaS Auth API provides comprehensive authentication and authorization services for SaaS applications. Built with FastAPI, it offers RESTful endpoints with automatic OpenAPI/Swagger documentation.

## Base URL

```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## API Endpoints

### Authentication Endpoints

#### Register User

Register a new user account.

```http
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": false,
  "created_at": "2023-01-01T00:00:00Z"
}
```

**Status Codes:**
- `201` - User created successfully
- `400` - Invalid input data
- `409` - User already exists
- `422` - Validation error

#### Login User

Authenticate user and receive tokens.

```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Status Codes:**
- `200` - Login successful
- `401` - Invalid credentials
- `422` - Validation error

#### Refresh Token

Refresh access token using refresh token.

```http
POST /api/v1/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 1800
}
```

**Status Codes:**
- `200` - Token refreshed successfully
- `401` - Invalid refresh token
- `422` - Validation error

#### Logout User

Invalidate user session and tokens.

```http
POST /api/v1/auth/logout
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

**Status Codes:**
- `200` - Logout successful
- `401` - Invalid token

#### Password Reset Request

Request password reset email.

```http
POST /api/v1/auth/password-reset-request
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset email sent"
}
```

**Status Codes:**
- `200` - Email sent successfully
- `404` - User not found
- `422` - Validation error

#### Reset Password

Reset password with token.

```http
POST /api/v1/auth/reset-password
```

**Request Body:**
```json
{
  "token": "reset-token-string",
  "new_password": "NewSecurePass123!"
}
```

**Response:**
```json
{
  "message": "Password reset successful"
}
```

**Status Codes:**
- `200` - Password reset successful
- `400` - Invalid token
- `422` - Validation error

### User Management Endpoints

#### Get User Profile

Get current user profile.

```http
GET /api/v1/users/me
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "email_verified": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z",
  "last_login": "2023-01-01T12:00:00Z",
  "roles": ["user"],
  "permissions": ["read", "write"]
}
```

**Status Codes:**
- `200` - Profile retrieved successfully
- `401` - Unauthorized

#### Update User Profile

Update current user profile.

```http
PUT /api/v1/users/me
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890",
  "updated_at": "2023-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200` - Profile updated successfully
- `401` - Unauthorized
- `422` - Validation error

#### Change Password

Change user password.

```http
POST /api/v1/users/me/change-password
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Request Body:**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass123!"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

**Status Codes:**
- `200` - Password changed successfully
- `400` - Invalid current password
- `401` - Unauthorized
- `422` - Validation error

#### Delete User Account

Delete user account.

```http
DELETE /api/v1/users/me
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "message": "Account deleted successfully"
}
```

**Status Codes:**
- `200` - Account deleted successfully
- `401` - Unauthorized

### API Key Management

#### Create API Key

Create new API key for user.

```http
POST /api/v1/api-keys
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Request Body:**
```json
{
  "name": "My API Key",
  "scopes": ["read", "write"],
  "expires_at": "2024-01-01T00:00:00Z"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "name": "My API Key",
  "key": "sk_live_1234567890abcdef",
  "scopes": ["read", "write"],
  "created_at": "2023-01-01T00:00:00Z",
  "expires_at": "2024-01-01T00:00:00Z",
  "last_used": null
}
```

**Status Codes:**
- `201` - API key created successfully
- `401` - Unauthorized
- `422` - Validation error

#### List API Keys

List user's API keys.

```http
GET /api/v1/api-keys
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "api_keys": [
    {
      "id": "uuid-string",
      "name": "My API Key",
      "scopes": ["read", "write"],
      "created_at": "2023-01-01T00:00:00Z",
      "expires_at": "2024-01-01T00:00:00Z",
      "last_used": "2023-01-01T12:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `200` - API keys retrieved successfully
- `401` - Unauthorized

#### Delete API Key

Delete API key.

```http
DELETE /api/v1/api-keys/{key_id}
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "message": "API key deleted successfully"
}
```

**Status Codes:**
- `204` - API key deleted successfully
- `401` - Unauthorized
- `404` - API key not found

### OAuth2 Endpoints

#### Get OAuth2 Authorization URL

Get authorization URL for OAuth2 provider.

```http
GET /api/v1/oauth/{provider}/authorize
```

**Query Parameters:**
- `redirect_uri` (required): URL to redirect after authorization
- `state` (optional): CSRF protection state

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-state-string"
}
```

**Status Codes:**
- `200` - Authorization URL generated successfully
- `400` - Invalid provider
- `422` - Validation error

#### OAuth2 Callback

Handle OAuth2 callback.

```http
GET /api/v1/oauth/{provider}/callback
```

**Query Parameters:**
- `code` (required): Authorization code from provider
- `state` (optional): State parameter from authorization request

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Status Codes:**
- `200` - OAuth2 login successful
- `400` - Invalid OAuth2 callback
- `422` - Validation error

### Admin Endpoints

#### Get All Users

Get all users (admin only).

```http
GET /api/v1/admin/users
```

**Headers:**
```
Authorization: Bearer <admin-access-token>
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `search` (optional): Search term
- `active` (optional): Filter by active status
- `verified` (optional): Filter by email verification status

**Response:**
```json
{
  "users": [
    {
      "id": "uuid-string",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "email_verified": true,
      "created_at": "2023-01-01T00:00:00Z",
      "last_login": "2023-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

**Status Codes:**
- `200` - Users retrieved successfully
- `401` - Unauthorized
- `403` - Forbidden (admin required)

#### Create User (Admin)

Create user account (admin only).

```http
POST /api/v1/admin/users
```

**Headers:**
```
Authorization: Bearer <admin-access-token>
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "first_name": "Jane",
  "last_name": "Doe",
  "roles": ["user"],
  "is_active": true
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "is_active": true,
  "roles": ["user"],
  "created_at": "2023-01-01T00:00:00Z"
}
```

**Status Codes:**
- `201` - User created successfully
- `401` - Unauthorized
- `403` - Forbidden (admin required)
- `422` - Validation error

#### Update User (Admin)

Update user account (admin only).

```http
PUT /api/v1/admin/users/{user_id}
```

**Headers:**
```
Authorization: Bearer <admin-access-token>
```

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "is_active": true,
  "roles": ["user", "admin"]
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "is_active": true,
  "roles": ["user", "admin"],
  "updated_at": "2023-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200` - User updated successfully
- `401` - Unauthorized
- `403` - Forbidden (admin required)
- `404` - User not found
- `422` - Validation error

#### Delete User (Admin)

Delete user account (admin only).

```http
DELETE /api/v1/admin/users/{user_id}
```

**Headers:**
```
Authorization: Bearer <admin-access-token>
```

**Response:**
```json
{
  "message": "User deleted successfully"
}
```

**Status Codes:**
- `200` - User deleted successfully
- `401` - Unauthorized
- `403` - Forbidden (admin required)
- `404` - User not found

### Webhook Endpoints

#### Create Webhook

Create webhook subscription.

```http
POST /api/v1/webhooks
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Request Body:**
```json
{
  "url": "https://yourapp.com/webhooks/auth",
  "events": ["user.created", "user.login", "user.logout"],
  "secret": "webhook-secret-key",
  "active": true
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "url": "https://yourapp.com/webhooks/auth",
  "events": ["user.created", "user.login", "user.logout"],
  "active": true,
  "created_at": "2023-01-01T00:00:00Z"
}
```

**Status Codes:**
- `201` - Webhook created successfully
- `401` - Unauthorized
- `422` - Validation error

#### List Webhooks

List webhook subscriptions.

```http
GET /api/v1/webhooks
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "webhooks": [
    {
      "id": "uuid-string",
      "url": "https://yourapp.com/webhooks/auth",
      "events": ["user.created", "user.login"],
      "active": true,
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `200` - Webhooks retrieved successfully
- `401` - Unauthorized

#### Delete Webhook

Delete webhook subscription.

```http
DELETE /api/v1/webhooks/{webhook_id}
```

**Headers:**
```
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "message": "Webhook deleted successfully"
}
```

**Status Codes:**
- `200` - Webhook deleted successfully
- `401` - Unauthorized
- `404` - Webhook not found

### Health Check Endpoints

#### Health Check

Comprehensive health check.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T12:00:00Z",
  "uptime": 86400,
  "version": "1.0.0",
  "environment": "production",
  "checks": [
    {
      "component": "database",
      "status": "healthy",
      "message": "Database is healthy",
      "response_time": 0.05
    },
    {
      "component": "redis",
      "status": "healthy",
      "message": "Redis is healthy",
      "response_time": 0.02
    }
  ]
}
```

**Status Codes:**
- `200` - Health check completed

#### Liveness Probe

Kubernetes liveness probe.

```http
GET /health/liveness
```

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2023-01-01T12:00:00Z",
  "uptime": 86400
}
```

**Status Codes:**
- `200` - Application is alive

#### Readiness Probe

Kubernetes readiness probe.

```http
GET /health/readiness
```

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2023-01-01T12:00:00Z",
  "checks": [
    {
      "component": "database",
      "status": "healthy"
    },
    {
      "component": "redis",
      "status": "healthy"
    }
  ]
}
```

**Status Codes:**
- `200` - Application is ready
- `503` - Application is not ready

## Error Responses

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": {
    "type": "validation",
    "severity": "medium",
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "timestamp": "2023-01-01T12:00:00Z",
    "correlation_id": "abc123",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "metadata": {
    "request_id": "abc123",
    "category": "validation"
  }
}
```

### Common Error Types

- `validation` - Input validation errors
- `authentication` - Authentication failures
- `authorization` - Permission errors
- `not_found` - Resource not found
- `permission` - Insufficient permissions
- `rate_limit` - Rate limiting errors
- `business_logic` - Business logic violations
- `external_service` - External service errors
- `system` - System-level errors
- `security` - Security violations

## Rate Limiting

The API implements rate limiting to prevent abuse:

### Rate Limit Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1672531200
X-RateLimit-Retry-After: 60
```

### Rate Limit Response

When rate limited:

```json
{
  "success": false,
  "error": {
    "type": "rate_limit",
    "severity": "medium",
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

**Status Code:** `429 Too Many Requests`

## Pagination

List endpoints support pagination:

### Query Parameters

- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `sort` (optional): Sort field
- `order` (optional): Sort order (`asc` or `desc`)

### Pagination Response

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

## Filtering and Searching

Many endpoints support filtering and searching:

### Query Parameters

- `search` (optional): Search term
- `filter[field]` (optional): Filter by specific field
- `date_from` (optional): Filter by date range (start)
- `date_to` (optional): Filter by date range (end)

### Example

```http
GET /api/v1/admin/users?search=john&active=true&date_from=2023-01-01
```

## SDKs

### Python SDK

```python
from saas_auth_sdk import SaaSAuthClient

# Initialize client
client = SaaSAuthClient(
    base_url="https://api.yourdomain.com",
    api_key="your-api-key"
)

# Register user
user = client.auth.register(
    email="user@example.com",
    password="SecurePass123!",
    first_name="John",
    last_name="Doe"
)

# Login
tokens = client.auth.login(
    email="user@example.com",
    password="SecurePass123!"
)

# Use access token
client.set_access_token(tokens.access_token)

# Get user profile
profile = client.users.get_profile()
```

### JavaScript SDK

```javascript
import { SaaSAuthClient } from 'saas-auth-sdk';

// Initialize client
const client = new SaaSAuthClient({
  baseURL: 'https://api.yourdomain.com',
  apiKey: 'your-api-key'
});

// Register user
const user = await client.auth.register({
  email: 'user@example.com',
  password: 'SecurePass123!',
  firstName: 'John',
  lastName: 'Doe'
});

// Login
const tokens = await client.auth.login({
  email: 'user@example.com',
  password: 'SecurePass123!'
});

// Set access token
client.setAccessToken(tokens.accessToken);

// Get user profile
const profile = await client.users.getProfile();
```

## Webhooks

### Webhook Events

The API sends webhook notifications for various events:

#### User Events
- `user.created` - User account created
- `user.updated` - User profile updated
- `user.deleted` - User account deleted
- `user.login` - User logged in
- `user.logout` - User logged out
- `user.password_changed` - User password changed
- `user.email_verified` - User email verified

#### Authentication Events
- `auth.login_failed` - Failed login attempt
- `auth.token_refreshed` - Token refreshed
- `auth.session_expired` - Session expired
- `auth.account_locked` - Account locked

#### Security Events
- `security.suspicious_login` - Suspicious login detected
- `security.brute_force_detected` - Brute force attack detected
- `security.ip_blocked` - IP address blocked

### Webhook Payload

```json
{
  "event": "user.created",
  "timestamp": "2023-01-01T12:00:00Z",
  "data": {
    "user_id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "signature": "sha256=abc123..."
}
```

### Webhook Security

Webhooks are signed using HMAC-SHA256:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(
        f"sha256={expected_signature}",
        signature
    )
```

## OpenAPI/Swagger

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Testing

### Test Environment

A test environment is available at:

```
https://test-api.yourdomain.com
```

### Test Credentials

```json
{
  "email": "test@example.com",
  "password": "TestPassword123!"
}
```

## Support

### Documentation

- [Development Guide](./DEVELOPMENT_GUIDE.md)
- [Database Schema](./DATABASE.md)
- [Security Guide](./SECURITY.md)
- [Deployment Guide](./DEPLOYMENT.md)

### Contact

- **Email**: support@yourdomain.com
- **Documentation**: https://docs.yourdomain.com
- **Status Page**: https://status.yourdomain.com
- **GitHub Issues**: https://github.com/your-org/saas-auth-api/issues

## Changelog

### Version 1.0.0 (2023-01-01)

#### Features
- User registration and authentication
- JWT token management
- OAuth2 integration
- API key management
- Admin endpoints
- Webhook support
- Rate limiting
- Health checks
- Comprehensive API documentation

#### Security
- Password hashing with bcrypt
- JWT token security
- Rate limiting protection
- Input validation and sanitization
- CORS protection
- Security headers

#### Performance
- Database connection pooling
- Redis caching
- Background job processing
- Optimized queries
- Response compression

---

For more information, visit our [documentation portal](https://docs.yourdomain.com) or contact our support team.
