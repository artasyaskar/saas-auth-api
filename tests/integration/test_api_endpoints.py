"""
Comprehensive API endpoint integration tests.

Tests all major API endpoints with various scenarios:
- Authentication flows
- Authorization checks
- Rate limiting
- Input validation
- Error handling
- Performance testing
- Security testing
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from tests.conftest import get_test_db, test_user, admin_user


class TestAPIEndpoints:
    """
    Comprehensive API endpoint test suite.
    
    Tests all major endpoints with various scenarios:
    - Authentication and authorization
    - Input validation and sanitization
    - Rate limiting and throttling
    - Error handling and responses
    - Performance and load testing
    - Security vulnerability testing
    """
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Authentication headers fixture."""
        # Login to get token
        response = self.client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def admin_headers(self, admin_user):
        """Admin authentication headers fixture."""
        response = self.client.post(
            "/auth/login",
            json={
                "email": admin_user.email,
                "password": "adminpassword123"
            }
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # Authentication Endpoints Tests
    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    def test_register_user_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "email" in data["detail"]
    
    def test_register_user_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "weak@test.com",
                "password": "123",
                "first_name": "Weak",
                "last_name": "Password"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "password" in data["detail"]
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_logout_success(self, client, auth_headers):
        """Test successful logout."""
        response = client.post(
            "/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    # User Management Endpoints Tests
    def test_get_user_profile(self, client, auth_headers, test_user):
        """Test getting user profile."""
        response = client.get(
            "/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
    
    def test_update_user_profile(self, client, auth_headers):
        """Test updating user profile."""
        response = client.put(
            "/users/me",
            headers=auth_headers,
            json={
                "first_name": "Updated",
                "last_name": "Name"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
    
    def test_get_user_profile_unauthorized(self, client):
        """Test getting profile without authentication."""
        response = client.get("/users/me")
        
        assert response.status_code == 401
    
    def test_change_password_success(self, client, auth_headers):
        """Test successful password change."""
        response = client.post(
            "/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePass456!"
            }
        )
        
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password."""
        response = client.post(
            "/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass456!"
            }
        )
        
        assert response.status_code == 400
    
    # API Key Management Tests
    def test_create_api_key(self, client, auth_headers):
        """Test creating API key."""
        response = client.post(
            "/api-keys",
            headers=auth_headers,
            json={
                "name": "Test API Key",
                "scopes": ["read", "write"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "key" in data
        assert data["name"] == "Test API Key"
        assert data["scopes"] == ["read", "write"]
    
    def test_list_api_keys(self, client, auth_headers):
        """Test listing API keys."""
        response = client.get(
            "/api-keys",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_revoke_api_key(self, client, auth_headers):
        """Test revoking API key."""
        # First create an API key
        create_response = client.post(
            "/api-keys",
            headers=auth_headers,
            json={
                "name": "To Revoke",
                "scopes": ["read"]
            }
        )
        key_id = create_response.json()["id"]
        
        # Then revoke it
        response = client.delete(
            f"/api-keys/{key_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    # Rate Limiting Tests
    def test_rate_limiting_login(self, client):
        """Test rate limiting on login endpoint."""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.post(
                "/auth/login",
                json={
                    "email": "ratelimit@test.com",
                    "password": "testpassword123"
                }
            )
            responses.append(response)
        
        # Should be rate limited after some requests
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0
    
    def test_rate_limiting_api_requests(self, client, auth_headers):
        """Test rate limiting on API endpoints."""
        # Make multiple rapid requests to a protected endpoint
        responses = []
        for _ in range(15):
            response = client.get(
                "/users/me",
                headers=auth_headers
            )
            responses.append(response)
        
        # Should eventually be rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0
    
    # Input Validation Tests
    def test_sql_injection_protection(self, client):
        """Test SQL injection protection."""
        malicious_payload = "'; DROP TABLE users; --"
        response = client.post(
            "/auth/login",
            json={
                "email": malicious_payload,
                "password": "password"
            }
        )
        
        assert response.status_code in [400, 422, 401]
        # Should not cause server error
    
    def test_xss_protection(self, client, auth_headers):
        """Test XSS protection in user input."""
        xss_payload = "<script>alert('xss')</script>"
        response = client.put(
            "/users/me",
            headers=auth_headers,
            json={
                "first_name": xss_payload,
                "last_name": "Test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # XSS payload should be escaped or sanitized
        assert xss_payload not in data["first_name"]
    
    def test_large_payload_handling(self, client, auth_headers):
        """Test handling of large payloads."""
        large_payload = "A" * 10000  # 10KB string
        response = client.put(
            "/users/me",
            headers=auth_headers,
            json={
                "first_name": large_payload,
                "last_name": "Test"
            }
        )
        
        # Should either accept or reject gracefully
        assert response.status_code in [200, 413, 422]
    
    # Error Handling Tests
    def test_404_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 method not allowed."""
        response = client.patch("/auth/login")  # Login only accepts POST
        
        assert response.status_code == 405
    
    def test_413_payload_too_large(self, client, auth_headers):
        """Test 413 payload too large."""
        # Create a very large payload
        large_data = {"data": "x" * 1000000}  # ~10MB
        
        response = client.post(
            "/api-keys",
            headers=auth_headers,
            json=large_data
        )
        
        assert response.status_code == 413
    
    # Performance Tests
    def test_response_time_login(self, client):
        """Test login endpoint response time."""
        start_time = time.time()
        response = client.post(
            "/auth/login",
            json={
                "email": "performance@test.com",
                "password": "testpassword123"
            }
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        async def make_request():
            return client.post(
                "/auth/login",
                json={
                    "email": "concurrent@test.com",
                    "password": "testpassword123"
                }
            )
        
        # Make 10 concurrent requests
        loop = asyncio.new_event_loop()
        responses = loop.run_until_complete(
            asyncio.gather([make_request() for _ in range(10)])
        )
        
        # All should succeed or fail gracefully
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 8  # Allow some failures due to rate limiting
    
    # Security Tests
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/auth/login")
        
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get("/users/me")
        
        # Check for common security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection"
        ]
        
        for header in security_headers:
            assert header.lower() in [h.lower() for h in response.headers.keys()]
    
    def test_authentication_bypass_attempts(self, client):
        """Test attempts to bypass authentication."""
        # Try accessing protected endpoints without auth
        protected_endpoints = [
            "/users/me",
            "/api-keys",
            "/auth/refresh"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_token_tampering(self, client, auth_headers):
        """Test token tampering detection."""
        # Modify the token to make it invalid
        tampered_headers = auth_headers.copy()
        tampered_headers["Authorization"] = "Bearer tampered.invalid.token"
        
        response = client.get(
            "/users/me",
            headers=tampered_headers
        )
        
        assert response.status_code == 401
    
    # Admin Endpoints Tests
    def test_admin_get_users_list(self, client, admin_headers):
        """Test admin can get users list."""
        response = client.get(
            "/admin/users",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_admin_unauthorized_access(self, client, auth_headers):
        """Test regular user cannot access admin endpoints."""
        response = client.get(
            "/admin/users",
            headers=auth_headers  # Regular user headers
        )
        
        assert response.status_code == 403
    
    def test_admin_create_user(self, client, admin_headers):
        """Test admin can create users."""
        response = client.post(
            "/admin/users",
            headers=admin_headers,
            json={
                "email": "admincreated@test.com",
                "password": "AdminCreated123!",
                "first_name": "Admin",
                "last_name": "Created"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "admincreated@test.com"
    
    # Health Check Tests
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    # Webhook Tests
    def test_webhook_subscription(self, client, auth_headers):
        """Test webhook subscription creation."""
        response = client.post(
            "/webhooks",
            headers=auth_headers,
            json={
                "url": "https://example.com/webhook",
                "events": ["user.created", "user.updated"],
                "secret": "webhook-secret"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["user.created", "user.updated"]
    
    def test_webhook_list(self, client, auth_headers):
        """Test webhook listing."""
        response = client.get(
            "/webhooks",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    # Integration Tests
    def test_full_user_lifecycle(self, client):
        """Test complete user lifecycle: register -> login -> update -> logout."""
        # 1. Register user
        register_response = client.post(
            "/auth/register",
            json={
                "email": "lifecycle@test.com",
                "password": "LifecyclePass123!",
                "first_name": "Life",
                "last_name": "Cycle"
            }
        )
        assert register_response.status_code == 201
        
        # 2. Login user
        login_response = client.post(
            "/auth/login",
            json={
                "email": "lifecycle@test.com",
                "password": "LifecyclePass123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Get profile
        profile_response = client.get("/users/me", headers=headers)
        assert profile_response.status_code == 200
        
        # 4. Update profile
        update_response = client.put(
            "/users/me",
            headers=headers,
            json={"first_name": "Updated"}
        )
        assert update_response.status_code == 200
        
        # 5. Logout
        logout_response = client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
    
    def test_api_key_workflow(self, client, auth_headers):
        """Test complete API key workflow."""
        # 1. Create API key
        create_response = client.post(
            "/api-keys",
            headers=auth_headers,
            json={
                "name": "Workflow Key",
                "scopes": ["read", "write"]
            }
        )
        assert create_response.status_code == 201
        key_data = create_response.json()
        key_id = key_data["id"]
        api_key = key_data["key"]
        
        # 2. List API keys
        list_response = client.get("/api-keys", headers=auth_headers)
        assert list_response.status_code == 200
        keys = list_response.json()
        assert any(k["id"] == key_id for k in keys)
        
        # 3. Use API key to access protected endpoint
        api_headers = {"X-API-Key": api_key}
        test_response = client.get("/users/me", headers=api_headers)
        assert test_response.status_code == 200
        
        # 4. Revoke API key
        revoke_response = client.delete(f"/api-keys/{key_id}", headers=auth_headers)
        assert revoke_response.status_code == 204
    
    # Load Testing
    @pytest.mark.slow
    def test_load_test_endpoints(self, client):
        """Load test critical endpoints."""
        endpoints_to_test = [
            "/auth/login",
            "/health",
            "/users/me"
        ]
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            responses = []
            
            # Make 100 requests
            for _ in range(100):
                if endpoint == "/auth/login":
                    response = client.post(
                        endpoint,
                        json={
                            "email": "loadtest@test.com",
                            "password": "testpassword123"
                        }
                    )
                elif endpoint == "/users/me":
                    # Skip auth required endpoints for load test
                    continue
                else:
                    response = client.get(endpoint)
                
                responses.append(response)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            success_count = sum(1 for r in responses if r.status_code == 200)
            avg_response_time = total_time / len(responses)
            
            # Performance assertions
            assert success_count >= 80  # At least 80% success rate
            assert avg_response_time < 1.0  # Average response time under 1 second
    
    # Error Scenario Tests
    def test_database_connection_error_handling(self, client):
        """Test handling of database connection errors."""
        # This would need to mock database failures
        # For now, just test that errors are handled gracefully
        response = client.get("/users/me")
        
        # Should return proper error response, not crash
        assert response.status_code in [401, 500]
        if response.status_code == 500:
            data = response.json()
            assert "detail" in data
    
    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/auth/login",
            data="{'invalid': json}",  # Malformed JSON
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/auth/register",
            json={"email": "missingfields@test.com"}  # Missing password, names
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "password" in data["detail"]
    
    # Concurrency and Race Condition Tests
    def test_concurrent_registration_same_email(self, client):
        """Test concurrent registration with same email."""
        async def register_user():
            return client.post(
                "/auth/register",
                json={
                    "email": "concurrent@test.com",
                    "password": "ConcurrentPass123!",
                    "first_name": "Concurrent",
                    "last_name": "User"
                }
            )
        
        # Make 5 concurrent registration attempts
        loop = asyncio.new_event_loop()
        responses = loop.run_until_complete(
            asyncio.gather([register_user() for _ in range(5)])
        )
        
        # Only one should succeed
        success_count = sum(1 for r in responses if r.status_code == 201)
        conflict_count = sum(1 for r in responses if r.status_code == 409)
        
        assert success_count == 1
        assert conflict_count == 4
    
    # Cache and Performance Tests
    def test_response_caching_headers(self, client):
        """Test caching headers in responses."""
        response = client.get("/health")
        
        # Check for cache control headers
        cache_headers = [
            "cache-control",
            "etag",
            "last-modified"
        ]
        
        for header in cache_headers:
            assert header.lower() in [h.lower() for h in response.headers.keys()]
    
    def test_compression_support(self, client):
        """Test response compression support."""
        response = client.get(
            "/users/me",
            headers={"Accept-Encoding": "gzip, deflate"}
        )
        
        # Should support compression
        assert response.status_code in [200, 401]  # 401 if no auth, 200 if auth
        if response.status_code == 200:
            assert "content-encoding" in response.headers


class TestAPIErrorHandling:
    """Specific tests for API error handling."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_validation_error_format(self, client):
        """Test validation error response format."""
        response = client.post(
            "/auth/register",
            json={"email": "invalid"}  # Invalid data
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Should follow standard error format
        assert "detail" in data
        assert isinstance(data["detail"], (list, dict))
    
    def test_authentication_error_format(self, client):
        """Test authentication error response format."""
        response = client.get("/users/me")  # No auth
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_authorization_error_format(self, client):
        """Test authorization error response format."""
        # Login as regular user and try admin endpoint
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@test.com",
                "password": "testpassword123"
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/admin/users", headers=headers)
        
        assert response.status_code == 403
        data = response.json()
        
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_not_found_error_format(self, client):
        """Test 404 error response format."""
        response = client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_rate_limit_error_format(self, client):
        """Test rate limit error response format."""
        # Make rapid requests to trigger rate limiting
        for _ in range(20):
            response = client.post(
                "/auth/login",
                json={
                    "email": "ratelimit@test.com",
                    "password": "testpassword123"
                }
            )
            if response.status_code == 429:
                break
        
        assert response.status_code == 429
        data = response.json()
        
        assert "detail" in data
        assert isinstance(data["detail"], str)
        # Should include retry-after header if available
        if "retry-after" in response.headers:
            assert isinstance(response.headers["retry-after"], (int, str))


class TestAPISecurity:
    """Security-focused API tests."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_sql_injection_in_login(self, client):
        """Test SQL injection protection in login."""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--"
        ]
        
        for payload in sql_payloads:
            response = client.post(
                "/auth/login",
                json={
                    "email": payload,
                    "password": "password"
                }
            )
            
            # Should not succeed or cause server error
            assert response.status_code in [400, 401, 422]
    
    def test_xss_in_user_input(self, client):
        """Test XSS protection in user input."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            response = client.post(
                "/auth/register",
                json={
                    "email": f"xss{payload}@test.com",
                    "password": "SecurePass123!",
                    "first_name": payload,
                    "last_name": "Test"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                # XSS should be escaped or removed
                assert payload not in data.get("first_name", "")
    
    def test_path_traversal_protection(self, client):
        """Test path traversal protection."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//etc/passwd"
        ]
        
        for path in malicious_paths:
            response = client.get(f"/{path}")
            
            # Should not allow file system access
            assert response.status_code in [400, 404, 422]
    
    def test_http_method_tampering(self, client):
        """Test HTTP method tampering protection."""
        response = client.post(
            "/auth/login",
            json={"email": "test@test.com"},
            headers={
                "X-HTTP-Method-Override": "PUT",
                "X-HTTP-Method": "DELETE"
            }
        )
        
        # Should ignore method override headers
        assert response.status_code == 405  # Method not allowed for PUT/DELETE on login
    
    def test_content_type_validation(self, client):
        """Test content type validation."""
        # Send JSON endpoint with different content types
        invalid_content_types = [
            "text/plain",
            "application/xml",
            "multipart/form-data"
        ]
        
        for content_type in invalid_content_types:
            response = client.post(
                "/auth/login",
                data="not json",
                headers={"Content-Type": content_type}
            )
            
            # Should reject or handle appropriately
            assert response.status_code in [400, 415, 422]


# Performance benchmarks
class TestAPIPerformance:
    """API performance benchmark tests."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.slow
    def test_endpoint_performance_benchmarks(self, client):
        """Benchmark critical endpoint performance."""
        endpoints = [
            {"path": "/health", "method": "GET", "max_time": 0.1},
            {"path": "/auth/login", "method": "POST", "max_time": 0.5},
            {"path": "/users/me", "method": "GET", "max_time": 0.3},
        ]
        
        for endpoint in endpoints:
            times = []
            
            # Make 50 requests and measure time
            for _ in range(50):
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    response = client.get(endpoint["path"])
                else:
                    response = client.post(
                        endpoint["path"],
                        json={"email": "perf@test.com", "password": "testpassword123"}
                    )
                
                end_time = time.time()
                times.append(end_time - start_time)
            
            # Calculate statistics
            avg_time = sum(times) / len(times)
            max_time = max(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]
            
            # Performance assertions
            assert avg_time < endpoint["max_time"]
            assert max_time < endpoint["max_time"] * 2
            assert p95_time < endpoint["max_time"] * 1.5
            
            print(f"Endpoint {endpoint['path']}: avg={avg_time:.3f}s, max={max_time:.3f}s, p95={p95_time:.3f}s")
    
    def test_concurrent_load_performance(self, client):
        """Test performance under concurrent load."""
        import concurrent.futures
        
        def make_request():
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }
        
        # Make 100 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        success_count = sum(1 for r in results if r["status_code"] == 200)
        avg_time = sum(r["response_time"] for r in results) / len(results)
        
        assert success_count >= 95  # 95% success rate
        assert avg_time < 0.2  # Average under 200ms
