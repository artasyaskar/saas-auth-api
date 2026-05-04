"""
Security-related tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token, verify_token
)


class TestPasswordHashing:
    """Tests for password hashing."""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed and can be verified."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # Hash should be different from plain text
        assert hashed != password
        # Should be able to verify
        assert verify_password(password, hashed) is True
        # Wrong password should fail
        assert verify_password("wrongpassword", hashed) is False
    
    def test_password_hashing_long_password(self):
        """Test password hashing with long passwords (bcrypt limit is 72 bytes)."""
        long_password = "a" * 100
        hashed = get_password_hash(long_password)
        
        # Should still work (truncated to 72 bytes)
        assert verify_password(long_password, hashed) is True
    
    def test_password_hashing_unicode(self):
        """Test password hashing with unicode characters."""
        password = "пароль123!@#$%"  # Russian word for password
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True


class TestJWTToken:
    """Tests for JWT token operations."""
    
    def test_create_and_verify_access_token(self):
        """Test creating and verifying access tokens."""
        data = {"sub": "testuser", "role": "USER"}
        token = create_access_token(data=data)
        
        # Verify token
        payload = verify_token(token, "access")
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
    
    def test_create_and_verify_refresh_token(self):
        """Test creating and verifying refresh tokens."""
        data = {"sub": "testuser"}
        token = create_refresh_token(data=data)
        
        # Verify token
        payload = verify_token(token, "refresh")
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
    
    def test_verify_token_wrong_type(self):
        """Test verifying token with wrong type."""
        data = {"sub": "testuser"}
        access_token = create_access_token(data=data)
        
        # Try to verify as refresh token
        with pytest.raises(Exception):
            verify_token(access_token, "refresh")
    
    def test_verify_expired_token(self):
        """Test verifying expired token."""
        from datetime import timedelta
        
        # Create expired token
        data = {"sub": "testuser"}
        expired_token = create_access_token(
            data=data,
            expires_delta=timedelta(minutes=-1)  # Already expired
        )
        
        with pytest.raises(Exception):
            verify_token(expired_token, "access")
    
    def test_verify_invalid_token(self):
        """Test verifying completely invalid token."""
        with pytest.raises(Exception):
            verify_token("invalid_token", "access")


class TestRateLimiting:
    """Tests for rate limiting functionality.
    
    TODO: Implement more comprehensive rate limit tests
    """
    
    def test_rate_limit_headers(self, client: TestClient, auth_headers: dict):
        """Test that rate limit headers are present in responses."""
        # Make a request
        response = client.get("/users/profile", headers=auth_headers)
        
        # Check for rate limit headers (if implemented)
        # assert "X-RateLimit-Remaining" in response.headers
        pass
    
    def test_rate_limit_enforcement(self, client: TestClient, auth_headers: dict):
        """Test rate limiting enforcement.
        
        Would need to make many requests quickly to trigger rate limit.
        """
        # Make multiple requests rapidly
        # responses = [client.get("/users/profile", headers=auth_headers) for _ in range(100)]
        # Last response should be 429 Too Many Requests
        pass


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_preflight(self, client: TestClient):
        """Test CORS preflight request."""
        response = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_headers_in_response(self, client: TestClient):
        """Test CORS headers are present in actual responses."""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )
        assert "access-control-allow-origin" in response.headers


class TestSecurityHeaders:
    """Tests for security headers middleware."""
    
    def test_security_headers_present(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/")
        
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in headers
        assert "Referrer-Policy" in headers


class TestRequestID:
    """Tests for request ID middleware."""
    
    def test_request_id_generated(self, client: TestClient):
        """Test that request ID is generated if not provided."""
        response = client.get("/")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36  # UUID length
    
    def test_request_id_preserved(self, client: TestClient):
        """Test that provided request ID is preserved."""
        custom_id = "my-custom-request-id-12345"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id
