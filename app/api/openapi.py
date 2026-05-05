"""
OpenAPI/Swagger Documentation Configuration

Comprehensive API documentation using OpenAPI 3.0 specification.
"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Custom OpenAPI schema with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="SaaS Auth API",
        version="1.0.0",
        description="""
        ## SaaS Auth API - Enterprise Authentication & Authorization Service
        
        A comprehensive authentication and authorization API for SaaS applications.
        
        ### Features
        - User authentication (JWT, OAuth2/OIDC, Social Login)
        - Two-Factor Authentication (TOTP, SMS, Email)
        - Role-based access control
        - API key management
        - Webhook management
        - Feature flags
        - Rate limiting
        - Audit logging
        - GDPR/CCPA compliance
        - Real-time notifications via WebSocket
        - GraphQL API
        - File storage
        - Messaging
        - Workflow automation
        - Machine learning for fraud detection
        
        ### Authentication
        Most endpoints require authentication via JWT bearer token or API key.
        
        ### Rate Limits
        - Free tier: 100 requests/minute
        - Pro tier: 1000 requests/minute
        - Enterprise: Custom limits
        
        ### Support
        - Documentation: https://docs.saas-auth-api.com
        - Support: support@saas-auth-api.com
        - Status: https://status.saas-auth-api.com
        """,
        routes=app.routes,
    )
    
    # Add custom tags
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "Users",
            "description": "User profile and account management"
        },
        {
            "name": "API Keys",
            "description": "API key management for programmatic access"
        },
        {
            "name": "Webhooks",
            "description": "Webhook configuration and management"
        },
        {
            "name": "Feature Flags",
            "description": "Feature flag management for gradual rollouts"
        },
        {
            "name": "Consent",
            "description": "GDPR/CCPA consent management"
        },
        {
            "name": "Messaging",
            "description": "In-app messaging and notifications"
        },
        {
            "name": "Workflows",
            "description": "Workflow automation"
        },
        {
            "name": "Files",
            "description": "File storage and management"
        },
        {
            "name": "Analytics",
            "description": "Usage analytics and reporting"
        },
        {
            "name": "Audit",
            "description": "Security audit logs"
        },
        {
            "name": "GraphQL",
            "description": "GraphQL API endpoint"
        },
        {
            "name": "WebSocket",
            "description": "Real-time WebSocket connections"
        }
    ]
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT bearer token authentication"
        },
        "APIKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication"
        },
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://auth.saas-auth-api.com/oauth/authorize",
                    "tokenUrl": "https://auth.saas-auth-api.com/oauth/token",
                    "scopes": {
                        "read": "Read access",
                        "write": "Write access",
                        "admin": "Admin access"
                    }
                }
            }
        }
    }
    
    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.saas-auth-api.com/v1",
            "description": "Production server"
        },
        {
            "url": "https://staging.saas-auth-api.com/v1",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000/v1",
            "description": "Local development server"
        }
    ]
    
    # Add contact info
    openapi_schema["info"]["contact"] = {
        "name": "SaaS Auth API Support",
        "email": "support@saas-auth-api.com",
        "url": "https://saas-auth-api.com"
    }
    
    # Add license
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Add external docs
    openapi_schema["externalDocs"] = {
        "description": "Full documentation",
        "url": "https://docs.saas-auth-api.com"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """Setup custom OpenAPI schema for the FastAPI app"""
    app.openapi = lambda: custom_openapi(app)
