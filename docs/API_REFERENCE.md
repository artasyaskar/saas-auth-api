# API Reference

## SaaS Auth API - Complete Endpoint Documentation

### Base URL
- Development: `http://localhost:8000`
- Production: `https://api.yourdomain.com`

### Authentication
All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

---

## Authentication Endpoints

### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "string (3-32 chars, alphanumeric)",
  "email": "string (valid email)",
  "password": "string (min 8 chars, must include uppercase, lowercase, number, special char)"
}
```

**Response (201):**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400`: Username already taken
- `400`: Email already registered
- `422`: Validation error

### POST /auth/login
Authenticate and receive access tokens.

**Request Body (form-data):**
- `username`: string
- `password`: string

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401`: Invalid credentials
- `401`: Account suspended

### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET /auth/me
Get current authenticated user profile.

**Response (200):**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "subscription_plan": "free",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### POST /auth/logout
Logout and invalidate current token.

**Request Body (optional):**
```json
{
  "refresh_token": "string"
}
```

**Response (200):**
```json
{
  "message": "Successfully logged out",
  "status": "success"
}
```

### POST /auth/logout-all
Logout from all devices.

**Response (200):**
```json
{
  "message": "Logged out from all devices",
  "status": "success",
  "sessions_invalidated": 5
}
```

---

## User Management Endpoints

### GET /users/profile
Get detailed user profile.

**Response (200):**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "subscription_plan": "free"
}
```

### GET /users/usage
Get API usage statistics.

**Response (200):**
```json
{
  "total_requests": 1523,
  "requests_this_month": 342,
  "most_used_endpoint": "/api/data",
  "average_response_time": 45.2
}
```

---

## Admin Endpoints

### GET /admin/users
List all users (admin only).

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100, max: 1000)

**Response (200):**
```json
[
  {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "subscription_plan": "free",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### GET /admin/users/{user_id}
Get specific user details.

**Response (200):** User object

**Errors:**
- `404`: User not found

### PUT /admin/users/{user_id}/suspend
Toggle user suspension status.

**Response (200):**
```json
{
  "message": "User john_doe suspended successfully"
}
```

### PUT /admin/users/{user_id}/role
Update user role.

**Query Parameters:**
- `new_role`: string (user, admin, moderator)

**Response (200):**
```json
{
  "message": "User john_doe role updated to admin"
}
```

### GET /admin/usage
Get system-wide usage statistics.

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)

**Response (200):**
```json
[
  {
    "user_id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "total_requests": 1523,
    "requests_this_month": 342,
    "subscription_plan": "free",
    "last_request": "2024-01-20T15:30:00Z"
  }
]
```

### GET /admin/stats
Get system statistics.

**Response (200):**
```json
{
  "total_users": 1250,
  "active_users": 890,
  "total_requests_today": 15420,
  "total_requests_this_month": 385420,
  "free_plan_users": 980,
  "pro_plan_users": 270
}
```

---

## Password Reset Endpoints

### POST /auth/password/reset-request
Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (202):**
```json
{
  "message": "If an account with that email exists, a password reset link has been sent.",
  "status": "accepted"
}
```

### GET /auth/password/validate-token/{token}
Validate a password reset token.

**Response (200):**
```json
{
  "valid": true,
  "email": "user@example.com"
}
```

### POST /auth/password/reset
Reset password using token.

**Request Body:**
```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123!",
  "confirm_password": "NewSecurePass123!"
}
```

**Response (200):**
```json
{
  "message": "Password reset successfully. Please login with your new password.",
  "status": "success"
}
```

---

## API Key Management Endpoints

### POST /api-keys
Create a new API key.

**Request Body:**
```json
{
  "name": "Production Integration",
  "expires_days": 90,
  "scopes": ["read", "write"]
}
```

**Response (201):**
```json
{
  "id": 1,
  "name": "Production Integration",
  "api_key": "sk_abc123xyz789...",
  "scopes": ["read", "write"],
  "expires_at": "2024-04-20T10:30:00Z",
  "message": "Store this API key securely - it won't be shown again"
}
```

### GET /api-keys
List all API keys.

**Query Parameters:**
- `include_revoked`: bool (default: false)

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Production Integration",
    "key_preview": "sk_abc12...",
    "scopes": ["read", "write"],
    "is_active": true,
    "created_at": "2024-01-20T10:30:00Z",
    "expires_at": "2024-04-20T10:30:00Z",
    "last_used_at": "2024-01-20T15:45:00Z"
  }
]
```

### POST /api-keys/{key_id}/revoke
Revoke an API key.

**Response (200):**
```json
{
  "message": "API key revoked successfully"
}
```

---

## Webhook Management Endpoints

### POST /webhooks/subscriptions
Create webhook subscription.

**Request Body:**
```json
{
  "url": "https://yourapp.com/webhook",
  "events": ["user.created", "payment.succeeded"],
  "description": "Production webhook"
}
```

**Response (201):**
```json
{
  "id": 1,
  "url": "https://yourapp.com/webhook",
  "events": ["user.created", "payment.succeeded"],
  "secret": "whsec_...",
  "is_active": true,
  "created_at": "2024-01-20T10:30:00Z",
  "message": "Store the secret securely - it won't be shown again"
}
```

### GET /webhooks/events
List available webhook events.

**Response (200):**
```json
{
  "events": [
    {
      "event": "user.created",
      "description": "Triggered when a new user registers"
    },
    {
      "event": "payment.succeeded",
      "description": "Triggered when payment is successful"
    }
  ]
}
```

---

## Analytics Endpoints (Admin Only)

### GET /admin/analytics/dashboard
Get comprehensive dashboard metrics.

**Query Parameters:**
- `days`: int (default: 30)

**Response (200):**
```json
{
  "user_metrics": {...},
  "revenue_metrics": {...},
  "popular_endpoints": [...],
  "security_summary": {...},
  "generated_at": "2024-01-20T10:30:00Z"
}
```

### GET /admin/analytics/users/cohorts
Get cohort retention analysis.

**Response (200):**
```json
{
  "cohorts": [
    {
      "cohort_id": "2024-01-01_to_2024-01-07",
      "cohort_size": 150,
      "retention_by_period": [
        {"period": 1, "retention_pct": 85.5},
        {"period": 2, "retention_pct": 72.3}
      ]
    }
  ]
}
```

### GET /admin/analytics/revenue
Get revenue metrics.

**Response (200):**
```json
{
  "mrr": 8750,
  "arr": 105000,
  "plan_distribution": {"free": 980, "pro": 270},
  "upgrades_last_30d": 15,
  "downgrades_last_30d": 3
}
```

---

## System Endpoints

### GET /
Root endpoint - API information.

**Response (200):**
```json
{
  "message": "SaaS Auth API",
  "version": "1.1.0",
  "docs": "/docs"
}
```

### GET /health
Health check endpoint.

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "environment": "production"
}
```

### GET /protected
Example protected endpoint.

**Response (200):**
```json
{
  "message": "This is a protected endpoint"
}
```

**Errors:**
- `401`: Not authenticated

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message here",
  "request_id": "uuid-for-tracing"
}
```

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `202`: Accepted (async processing)
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Too Many Requests
- `500`: Internal Server Error

### Rate Limiting Headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642681200
Retry-After: 30
```

---

## Rate Limits

| Endpoint Group | Requests/Minute | Monthly Quota (Free) | Monthly Quota (Pro) |
|----------------|-----------------|----------------------|---------------------|
| Auth | 60 | 1000 | 10000 |
| Users | 60 | 1000 | 10000 |
| Admin | 30 | 500 | 5000 |
| Analytics | 30 | 300 | 3000 |

---

## Webhook Events

### Event Payload Format
```json
{
  "event_id": "uuid",
  "event_type": "user.created",
  "timestamp": "2024-01-20T10:30:00Z",
  "data": {...},
  "subscription_id": 1
}
```

### Signature Verification
```python
import hmac
import hashlib

signature = hmac.new(
    secret.encode(),
    payload_json.encode(),
    hashlib.sha256
).hexdigest()
```

---

## SDK Examples

### JavaScript/TypeScript
```typescript
const client = new SaasAuthClient({
  baseURL: 'https://api.yourdomain.com',
  apiKey: 'sk_...'
});

// Login
const { access_token } = await client.auth.login({
  username: 'john',
  password: 'secret'
});

// Use token
client.setToken(access_token);
const profile = await client.users.getProfile();
```

### Python
```python
from saas_auth import SaasAuthClient

client = SaasAuthClient(
    base_url="https://api.yourdomain.com",
    api_key="sk_..."
)

# Login
response = client.auth.login("john", "secret")
client.set_token(response.access_token)

# Get profile
profile = client.users.get_profile()
```

---

## Changelog

### v1.1.0 (2024-01-20)
- Added webhook management
- Added API key authentication
- Added analytics dashboard
- Improved rate limiting

### v1.0.0 (2024-01-15)
- Initial release
- Authentication system
- User management
- Admin controls
