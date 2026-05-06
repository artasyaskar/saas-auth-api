"""
Integration tests for authentication endpoints.

Tests authentication API endpoints including
login, logout, token refresh, and password reset.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.security import SecurityService
from .conftest import (
    test_client, test_db, security_service,
    sample_user_data, sample_admin_user_data,
    sample_jwt_token, auth_headers
)


class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_login_success(self, test_client: TestClient, test_db):
        """Test successful login endpoint."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Mock user repository
        with patch('app.services.auth.UserService') as mock_user_service:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.username = "testuser"
            mock_user.is_active = True
            mock_user.role = "USER"
            mock_user_service.return_value.get_by_email_or_username.return_value = mock_user
            
            # Mock authentication service
            with patch('app.services.auth.AuthService') as mock_auth_service:
                mock_auth_service.return_value.authenticate_user.return_value = {
                    "access_token": "test_access_token",
                    "refresh_token": "test_refresh_token",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "user": {
                        "id": 1,
                        "email": "test@example.com",
                        "username": "testuser",
                        "role": "USER"
                    }
                }
                
                # Act
                response = test_client.post("/api/v1/auth/login", json=login_data)
                
                # Assert
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
                assert data["user"]["email"] == "test@example.com"
    
    def test_login_invalid_credentials(self, test_client: TestClient, test_db):
        """Test login with invalid credentials."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "wrongpassword"
        }
        
        # Mock authentication service failure
        with patch('app.services.auth.AuthService') as mock_auth_service:
            from app.core.exceptions import AuthenticationError
            mock_auth_service.return_value.authenticate_user.side_effect = AuthenticationError("Invalid credentials")
            
            # Act
            response = test_client.post("/api/v1/auth/login", json=login_data)
            
            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "error" in data
            assert data["error"] == "authentication_error"
    
    def test_login_missing_fields(self, test_client: TestClient, test_db):
        """Test login with missing required fields."""
        # Arrange
        login_data = {
            "identifier": "test@example.com"
            # Missing password
        }
        
        # Act
        response = test_client.post("/api/v1/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_login_rate_limited(self, test_client: TestClient, test_db):
        """Test login when rate limited."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Mock rate limiting
        with patch('app.services.auth.AuthService') as mock_auth_service:
            from app.core.exceptions import RateLimitError
            mock_auth_service.return_value.authenticate_user.side_effect = RateLimitError("Too many attempts")
            
            # Act
            response = test_client.post("/api/v1/auth/login", json=login_data)
            
            # Assert
            assert response.status_code == 429
            data = response.json()
            assert "error" in data
            assert data["error"] == "rate_limit_error"
    
    def test_refresh_token_success(self, test_client: TestClient, test_db):
        """Test successful token refresh."""
        # Arrange
        refresh_data = {
            "refresh_token": "valid_refresh_token"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.refresh_token.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "test@example.com",
                    "username": "testuser",
                    "role": "USER"
                }
            }
            
            # Act
            response = test_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["access_token"] == "new_access_token"
    
    def test_refresh_token_invalid(self, test_client: TestClient, test_db):
        """Test refresh token with invalid token."""
        # Arrange
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }
        
        # Mock authentication service failure
        with patch('app.services.auth.AuthService') as mock_auth_service:
            from app.core.exceptions import AuthenticationError
            mock_auth_service.return_value.refresh_token.side_effect = AuthenticationError("Invalid refresh token")
            
            # Act
            response = test_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "error" in data
    
    def test_logout_success(self, test_client: TestClient, test_db):
        """Test successful logout."""
        # Arrange
        logout_data = {
            "refresh_token": "valid_refresh_token"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.logout_user.return_value = True
            
            # Act
            response = test_client.post("/api/v1/auth/logout", json=logout_data, headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_logout_invalid_token(self, test_client: TestClient, test_db):
        """Test logout with invalid token."""
        # Arrange
        logout_data = {
            "refresh_token": "invalid_refresh_token"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.logout_user.return_value = False
            
            # Act
            response = test_client.post("/api/v1/auth/logout", json=logout_data, headers=auth_headers)
            
            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_password_reset_initiation(self, test_client: TestClient, test_db):
        """Test password reset initiation."""
        # Arrange
        reset_data = {
            "email": "test@example.com"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.initiate_password_reset.return_value = True
            
            # Act
            response = test_client.post("/api/v1/auth/password-reset", json=reset_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_password_reset_confirmation(self, test_client: TestClient, test_db):
        """Test password reset confirmation."""
        # Arrange
        reset_data = {
            "token": "valid_reset_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.reset_password.return_value = {
                "success": True,
                "message": "Password reset successfully"
            }
            
            # Act
            response = test_client.post("/api/v1/auth/password-reset/confirm", json=reset_data)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_password_reset_invalid_token(self, test_client: TestClient, test_db):
        """Test password reset with invalid token."""
        # Arrange
        reset_data = {
            "token": "invalid_reset_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            from app.core.exceptions import AuthenticationError
            mock_auth_service.return_value.reset_password.side_effect = AuthenticationError("Invalid token")
            
            # Act
            response = test_client.post("/api/v1/auth/password-reset/confirm", json=reset_data)
            
            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "error" in data
    
    def test_password_reset_password_mismatch(self, test_client: TestClient, test_db):
        """Test password reset with password mismatch."""
        # Arrange
        reset_data = {
            "token": "valid_reset_token",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        # Act
        response = test_client.post("/api/v1/auth/password-reset/confirm", json=reset_data)
            
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_current_user(self, test_client: TestClient, test_db):
        """Test getting current user information."""
        # Mock user repository
        with patch('app.services.auth.UserService') as mock_user_service:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.username = "testuser"
            mock_user.is_active = True
            mock_user.role = "USER"
            mock_user_service.return_value.get.return_value = mock_user
            
            # Act
            response = test_client.get("/api/v1/auth/me", headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["username"] == "testuser"
    
    def test_get_current_user_unauthorized(self, test_client: TestClient, test_db):
        """Test getting current user without authentication."""
        # Act
        response = test_client.get("/api/v1/auth/me")
            
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
    
    def test_get_user_sessions(self, test_client: TestClient, test_db):
        """Test getting user sessions."""
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.get_user_sessions.return_value = [
                {
                    "session_id": "session_1",
                    "user_agent": "Mozilla/5.0",
                    "ip_address": "127.0.0.1",
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                }
            ]
            
            # Act
            response = test_client.get("/api/v1/auth/sessions", headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["session_id"] == "session_1"
    
    def test_revoke_session(self, test_client: TestClient, test_db):
        """Test revoking user session."""
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.revoke_user_session.return_value = True
            
            # Act
            response = test_client.delete("/api/v1/auth/sessions/session_1", headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_get_security_events(self, test_client: TestClient, test_db):
        """Test getting security events."""
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.get_security_events.return_value = [
                {
                    "action": "login_attempt",
                    "success": True,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            # Act
            response = test_client.get("/api/v1/auth/security-events", headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["action"] == "login_attempt"
    
    def test_change_password(self, test_client: TestClient, test_db):
        """Test changing password."""
        # Arrange
        password_data = {
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        # Mock user service
        with patch('app.services.auth.UserService') as mock_user_service:
            mock_user_service.return_value.change_password.return_value = True
            
            # Act
            response = test_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_change_password_wrong_current(self, test_client: TestClient, test_db):
        """Test changing password with wrong current password."""
        # Arrange
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        # Mock user service
        with patch('app.services.auth.UserService') as mock_user_service:
            from app.core.exceptions import ValidationError
            mock_user_service.return_value.change_password.side_effect = ValidationError("Current password is incorrect")
            
            # Act
            response = test_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
            
            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_change_password_mismatch(self, test_client: TestClient, test_db):
        """Test changing password with password mismatch."""
        # Arrange
        password_data = {
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        # Act
        response = test_client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
            
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.slow
    def test_concurrent_login_requests(self, test_client: TestClient, test_db):
        """Test concurrent login requests."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.authenticate_user.return_value = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "test@example.com",
                    "username": "testuser",
                    "role": "USER"
                }
            }
            
            # Act - send multiple concurrent requests
            import asyncio
            import aiohttp
            
            async def make_request():
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://testserver/api/v1/auth/login",
                        json=login_data
                    ) as response:
                        return await response.json()
            
            # Run concurrent requests
            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(
                asyncio.gather(*[make_request() for _ in range(5)], return_exceptions=True)
            )
            loop.close()
            
            # Assert
            assert len(results) == 5
            for result in results:
                if not isinstance(result, Exception):
                    assert "access_token" in result
    
    @pytest.mark.external
    def test_external_service_integration(self, test_client: TestClient, test_db):
        """Test integration with external services."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Mock external service failure
        with patch('app.services.auth.AuthService') as mock_auth_service:
            from app.core.exceptions import ExternalServiceError
            mock_auth_service.return_value.authenticate_user.side_effect = ExternalServiceError("Email service unavailable")
            
            # Act
            response = test_client.post("/api/v1/auth/login", json=login_data)
            
            # Assert
            assert response.status_code == 503
            data = response.json()
            assert "error" in data
            assert data["error"] == "external_service_error"
    
    def test_cors_headers(self, test_client: TestClient, test_db):
        """Test CORS headers on authentication endpoints."""
        # Act
        response = test_client.options("/api/v1/auth/login")
        
        # Assert
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    def test_rate_limiting_headers(self, test_client: TestClient, test_db):
        """Test rate limiting headers on authentication endpoints."""
        # Arrange
        login_data = {
            "identifier": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Mock authentication service
        with patch('app.services.auth.AuthService') as mock_auth_service:
            mock_auth_service.return_value.authenticate_user.return_value = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "test@example.com",
                    "username": "testuser",
                    "role": "USER"
                }
            }
            
            # Act
            response = test_client.post("/api/v1/auth/login", json=login_data)
            
            # Assert
            assert response.status_code == 200
            # Rate limiting headers should be present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
