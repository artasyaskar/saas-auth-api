# API Examples and Usage Guide

This document provides comprehensive examples and usage guides for the SaaS Auth API.

## Table of Contents

- [Authentication](#authentication)
- [User Management](#user-management)
- [API Keys](#api-keys)
- [Webhooks](#webhooks)
- [Feature Flags](#feature-flags)
- [Consent Management](#consent-management)
- [Messaging](#messaging)
- [Workflows](#workflows)
- [File Storage](#file-storage)
- [GraphQL API](#graphql-api)
- [WebSocket](#websocket)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Authentication

### Register a New User

```bash
curl -X POST https://api.saas-auth-api.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "id": 123,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "USER",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Login

```bash
curl -X POST https://api.saas-auth-api.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Refresh Token

```bash
curl -X POST https://api.saas-auth-api.com/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### Logout

```bash
curl -X POST https://api.saas-auth-api.com/v1/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## User Management

### Get User Profile

```bash
curl -X GET https://api.saas-auth-api.com/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "id": 123,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "USER",
  "subscription_plan": "PRO",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T15:45:00Z"
}
```

### Update User Profile

```bash
curl -X PUT https://api.saas-auth-api.com/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe_updated",
    "email": "john.updated@example.com"
  }'
```

### Change Password

```bash
curl -X POST https://api.saas-auth-api.com/v1/auth/change-password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "SecurePassword123!",
    "new_password": "NewSecurePassword456!"
  }'
```

## API Keys

### Create API Key

```bash
curl -X POST https://api.saas-auth-api.com/v1/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "scopes": ["read", "write"],
    "rate_limit": 1000
  }'
```

**Response:**
```json
{
  "id": 456,
  "key": "sk_live_xxxxxxxxxxxxxxxxxxxx",
  "name": "Production API Key",
  "scopes": ["read", "write"],
  "rate_limit": 1000,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List API Keys

```bash
curl -X GET https://api.saas-auth-api.com/v1/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Delete API Key

```bash
curl -X DELETE https://api.saas-auth-api.com/v1/api-keys/456 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Webhooks

### Create Webhook

```bash
curl -X POST https://api.saas-auth-api.com/v1/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Created Webhook",
    "url": "https://your-app.com/webhooks/user-created",
    "events": ["user.created", "user.updated"],
    "secret": "webhook_secret_key",
    "retry_policy": {
      "max_retries": 3,
      "backoff": "exponential"
    }
  }'
```

### List Webhooks

```bash
curl -X GET https://api.saas-auth-api.com/v1/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Delete Webhook

```bash
curl -X DELETE https://api.saas-auth-api.com/v1/webhooks/789 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Feature Flags

### Create Feature Flag

```bash
curl -X POST https://api.saas-auth-api.com/v1/feature-flags \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_dashboard_ui",
    "description": "Enable new dashboard UI for beta users",
    "default_value": false,
    "strategy": "percentage",
    "rollout_percentage": 20,
    "target_users": [1, 2, 3, 4, 5]
  }'
```

### Check Feature Flag

```bash
curl -X POST https://api.saas-auth-api.com/v1/feature-flags/new_dashboard_ui/evaluate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123
  }'
```

**Response:**
```json
{
  "flag_name": "new_dashboard_ui",
  "enabled": true,
  "variant": "variant_a"
}
```

### List Feature Flags

```bash
curl -X GET https://api.saas-auth-api.com/v1/feature-flags \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Consent Management

### Grant Consent

```bash
curl -X POST https://api.saas-auth-api.com/v1/consent/grant \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "consent_type": "marketing",
    "granted_from": "https://your-app.com/settings"
  }'
```

### Withdraw Consent

```bash
curl -X POST https://api.saas-auth-api.com/v1/consent/withdraw/marketing \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "No longer interested in marketing emails"
  }'
```

### Request Data Export (GDPR)

```bash
curl -X POST https://api.saas-auth-api.com/v1/consent/data-export \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "include_deleted": false
  }'
```

**Response:**
```json
{
  "request_id": "export_1234567890",
  "status": "pending",
  "message": "Data export request initiated"
}
```

## Messaging

### Send Message

```bash
curl -X POST https://api.saas-auth-api.com/v1/messaging/messages \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_id": 456,
    "content": "Hello, how are you?",
    "message_type": "direct"
  }'
```

### Get Message Threads

```bash
curl -X GET https://api.saas-auth-api.com/v1/messaging/threads \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Notifications

```bash
curl -X GET https://api.saas-auth-api.com/v1/messaging/notifications?unread_only=true&limit=20 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Workflows

### Create Workflow

```bash
curl -X POST https://api.saas-auth-api.com/v1/workflows \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Onboarding",
    "description": "Automated user onboarding workflow",
    "definition": {
      "steps": [
        {
          "id": "send_welcome_email",
          "action": "send_email",
          "config": {
            "template": "welcome"
          }
        },
        {
          "id": "assign_tutorial",
          "action": "assign_task",
          "config": {
            "task": "complete_tutorial"
          }
        }
      ]
    }
  }'
```

### Execute Workflow

```bash
curl -X POST https://api.saas-auth-api.com/v1/workflows/1/execute \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "user_id": 123
    }
  }'
```

## File Storage

### Upload File

```bash
curl -X POST https://api.saas-auth-api.com/v1/files/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/file.pdf" \
  -F "access_level=private"
```

**Response:**
```json
{
  "file_id": "file_abc123",
  "url": "https://cdn.saas-auth-api.com/files/file_abc123.pdf",
  "filename": "document.pdf",
  "size": 1024000
}
```

### Download File

```bash
curl -X GET https://api.saas-auth-api.com/v1/files/file_abc123/download \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List Files

```bash
curl -X GET https://api.saas-auth-api.com/v1/files?limit=50&offset=0 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## GraphQL API

### Query Example

```bash
curl -X POST https://api.saas-auth-api.com/v1/graphql \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { me { id username email role } }"
  }'
```

**Response:**
```json
{
  "data": {
    "me": {
      "id": 123,
      "username": "john_doe",
      "email": "john@example.com",
      "role": "USER"
    }
  }
}
```

### Subscription Example (WebSocket)

```javascript
const ws = new WebSocket('wss://api.saas-auth-api.com/v1/graphql');

ws.onopen = () => {
  ws.send(JSON.stringify({
    query: `
      subscription {
        notification(user_id: 123) {
          id
          title
          body
          created_at
        }
      }
    `
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Notification:', data.data.notification);
};
```

## WebSocket

### Connect to WebSocket

```javascript
const ws = new WebSocket('wss://api.saas-auth-api.com/v1/ws');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'YOUR_ACCESS_TOKEN'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Message:', data);
};

// Subscribe to notifications
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'notifications'
}));
```

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {
      "field": "email"
    }
  }
}
```

### Common Error Codes

- `INVALID_CREDENTIALS` - Invalid login credentials
- `UNAUTHORIZED` - Missing or invalid authentication
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `VALIDATION_ERROR` - Request validation failed
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded
- `INTERNAL_ERROR` - Internal server error

## Rate Limiting

The API implements rate limiting based on your subscription plan:

- **Free**: 100 requests/minute
- **Pro**: 1,000 requests/minute
- **Enterprise**: Custom limits

Rate limit headers are included in every response:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642238400
```

## SDK Usage

### JavaScript SDK

```javascript
import { AuthClient } from '@saas-auth-api/sdk';

const client = new AuthClient({
  baseURL: 'https://api.saas-auth-api.com/v1',
  apiKey: 'YOUR_API_KEY'
});

// Login
const result = await client.login('john@example.com', 'password');
console.log(result.access_token);

// Get profile
const profile = await client.getProfile();
console.log(profile);
```

### Python SDK

```python
from saas_auth_api import AuthClient

client = AuthClient(
    base_url='https://api.saas-auth-api.com/v1',
    api_key='YOUR_API_KEY'
)

# Login
result = client.login('john@example.com', 'password')
print(result['access_token'])

# Get profile
profile = client.get_profile()
print(profile)
```

## Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** (use httpOnly cookies for web apps)
3. **Implement token refresh** to avoid frequent logins
4. **Handle rate limits** gracefully with exponential backoff
5. **Validate webhook signatures** to verify authenticity
6. **Use feature flags** for gradual rollouts
7. **Monitor API usage** through the dashboard
8. **Keep SDKs updated** for latest features and security patches

## Support

- Documentation: https://docs.saas-auth-api.com
- Support Email: support@saas-auth-api.com
- Status Page: https://status.saas-auth-api.com
- GitHub Issues: https://github.com/saas-auth-api/issues
