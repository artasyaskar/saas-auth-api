"""
Unit tests for authentication service.

Tests authentication service functionality including
login, token management, and security features.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.services.auth import AuthService
from app.schemas.auth import LoginRequest, RefreshTokenRequest
from app.core.exceptions import AuthenticationError, SecurityError, RateLimitError
from .conftest import (
    test_db, test_client, security_service,
    sample_user_data, sample_admin_user_data,
    sample_jwt_token, auth_headers
)


class TestAuthService:
    """Test authentication service functionality."""
    
    def test_login_success(self, test_db, security_service):
        """Test successful user login."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock user repository
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.username = "testuser"
            mock_user.hashed_password = security_service.hash_password("TestPassword123!")
            mock_user.is_active = True
            mock_user.role = "USER"
            mock_get_user.return_value = mock_user
            
            # Mock password verification
            with patch.object(security_service, 'verify_password') as mock_verify:
                mock_verify.return_value = True
                
                # Act
                result = auth_service.authenticate_user(login_request, "127.0.0.1")
                
                # Assert
                assert result is not None
                assert "access_token" in result
                assert "refresh_token" in result
                assert result["requires_2fa"] is False
                assert result["user"]["email"] == "test@example.com"
                assert result["user"]["username"] == "testuser"
    
    def test_login_invalid_credentials(self, test_db, security_service):
        """Test login with invalid credentials."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="wrongpassword"
        )
        
        # Mock user repository
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.hashed_password = security_service.hash_password("TestPassword123!")
            mock_get_user.return_value = mock_user
            
            # Act & Assert
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user(login_request, "127.0.0.1")
    
    def test_login_inactive_user(self, test_db, security_service):
        """Test login with inactive user."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock user repository
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.is_active = False
            mock_get_user.return_value = mock_user
            
            # Act & Assert
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user(login_request, "127.0.0.1")
    
    def test_login_rate_limit_exceeded(self, test_db, security_service):
        """Test login when rate limit is exceeded."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock rate limiting
        with patch.object(auth_service, '_is_rate_limited') as mock_rate_limit:
            mock_rate_limit.return_value = True
            
            # Act & Assert
            with pytest.raises(RateLimitError):
                auth_service.authenticate_user(login_request, "127.0.0.1")
    
    def test_login_requires_2fa(self, test_db, security_service):
        """Test login that requires 2FA."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="admin@example.com",
            password="AdminPassword123!"
        )
        
        # Mock admin user
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "admin@example.com"
            mock_user.hashed_password = security_service.hash_password("AdminPassword123!")
            mock_user.is_active = True
            mock_user.role = "ADMIN"
            mock_get_user.return_value = mock_user
            
            # Mock 2FA requirement
            with patch.object(auth_service, '_is_2fa_required') as mock_2fa:
                mock_2fa.return_value = True
                
                # Act
                result = auth_service.authenticate_user(login_request, "127.0.0.1")
                
                # Assert
                assert result is not None
                assert result["requires_2fa"] is True
                assert result["two_factor_methods"] == ["totp", "sms", "email"]
                assert "access_token" not in result
                assert "refresh_token" not in result
    
    def test_refresh_token_success(self, test_db, security_service):
        """Test successful token refresh."""
        # Arrange
        auth_service = AuthService(test_db)
        refresh_request = RefreshTokenRequest(
            refresh_token="valid_refresh_token"
        )
        
        # Mock token verification
        with patch.object(auth_service, 'refresh_access_token') as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "valid_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "test@example.com",
                    "username": "testuser"
                }
            }
            
            # Act
            result = auth_service.refresh_token(refresh_request)
            
            # Assert
            assert result is not None
            assert result["access_token"] == "new_access_token"
            assert result["refresh_token"] == "valid_refresh_token"
            assert result["user"]["email"] == "test@example.com"
    
    def test_refresh_token_invalid(self, test_db, security_service):
        """Test refresh token with invalid token."""
        # Arrange
        auth_service = AuthService(test_db)
        refresh_request = RefreshTokenRequest(
            refresh_token="invalid_refresh_token"
        )
        
        # Mock token verification failure
        with patch.object(auth_service, 'refresh_access_token') as mock_refresh:
            mock_refresh.side_effect = AuthenticationError("Invalid refresh token")
            
            # Act & Assert
            with pytest.raises(AuthenticationError):
                auth_service.refresh_token(refresh_request)
    
    def test_logout_success(self, test_db, security_service):
        """Test successful logout."""
        # Arrange
        auth_service = AuthService(test_db)
        token = sample_jwt_token()
        
        # Mock token blacklisting
        with patch.object(auth_service, 'blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = True
            
            # Act
            result = auth_service.logout_user(token)
            
            # Assert
            assert result is True
            mock_blacklist.assert_called_once_with(token, "User logout")
    
    def test_logout_invalid_token(self, test_db, security_service):
        """Test logout with invalid token."""
        # Arrange
        auth_service = AuthService(test_db)
        token = "invalid_token"
        
        # Mock token blacklisting
        with patch.object(auth_service, 'blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = False
            
            # Act
            result = auth_service.logout_user(token)
            
            # Assert
            assert result is False
    
    def test_password_reset_initiation(self, test_db, security_service):
        """Test password reset initiation."""
        # Arrange
        auth_service = AuthService(test_db)
        
        # Mock user repository
        with patch.object(auth_service.user_repo, 'get_by_email') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_get_user.return_value = mock_user
            
            # Mock password reset token creation
            with patch.object(auth_service.auth_repo, 'create_password_reset_token') as mock_create:
                mock_create.return_value = True
                
                # Mock email sending
                with patch.object(auth_service, 'generate_secure_token') as mock_token:
                    mock_token.return_value = "reset_token_123"
                    
                    # Act
                    result = auth_service.initiate_password_reset("test@example.com")
                    
                    # Assert
                    assert result is True
                    mock_create.assert_called_once()
                    mock_token.assert_called_once()
    
    def test_password_reset_user_not_found(self, test_db, security_service):
        """Test password reset for non-existent user."""
        # Arrange
        auth_service = AuthService(test_db)
        
        # Mock user repository
        with patch.object(auth_service.user_repo, 'get_by_email') as mock_get_user:
            mock_get_user.return_value = None
            
            # Act
            result = auth_service.initiate_password_reset("nonexistent@example.com")
            
            # Assert
            assert result is True  # Don't reveal if user exists
    
    def test_password_reset_confirmation(self, test_db, security_service):
        """Test password reset confirmation."""
        # Arrange
        auth_service = AuthService(test_db)
        
        # Mock password reset token
        with patch.object(auth_service.auth_repo, 'get_password_reset_token') as mock_get_token:
            mock_token = Mock()
            mock_token.user_id = 1
            mock_get_token.return_value = mock_token
            
            # Mock user repository
            with patch.object(auth_service.user_repo, 'get') as mock_get_user:
                mock_user = Mock()
                mock_user.id = 1
                mock_user.email = "test@example.com"
                mock_get_user.return_value = mock_user
                
                # Mock password update
                with patch.object(auth_service.user_repo, 'update_password') as mock_update:
                    mock_update.return_value = True
                    
                    # Mock token usage
                    with patch.object(auth_service.auth_repo, 'use_password_reset_token') as mock_use:
                        mock_use.return_value = True
                        
                        # Act
                        result = auth_service.reset_password("reset_token_123", "NewPassword123!", "NewPassword123!")
                        
                        # Assert
                        assert result is True
                        mock_update.assert_called_once()
                        mock_use.assert_called_once()
    
    def test_password_reset_invalid_token(self, test_db, security_service):
        """Test password reset with invalid token."""
        # Arrange
        auth_service = AuthService(test_db)
        
        # Mock password reset token
        with patch.object(auth_service.auth_repo, 'get_password_reset_token') as mock_get_token:
            mock_get_token.return_value = None
            
            # Act & Assert
            with pytest.raises(AuthenticationError):
                auth_service.reset_password("invalid_token", "NewPassword123!", "NewPassword123!")
    
    def test_get_user_sessions(self, test_db, security_service):
        """Test getting user sessions."""
        # Arrange
        auth_service = AuthService(test_db)
        user_id = 1
        
        # Mock session repository
        with patch.object(auth_service.auth_repo, 'get_user_sessions') as mock_sessions:
            mock_sessions.return_value = [
                {
                    "session_id": "session_1",
                    "user_agent": "Mozilla/5.0",
                    "ip_address": "127.0.0.1",
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                }
            ]
            
            # Act
            result = auth_service.get_user_sessions(user_id)
            
            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["session_id"] == "session_1"
    
    def test_revoke_session(self, test_db, security_service):
        """Test revoking user session."""
        # Arrange
        auth_service = AuthService(test_db)
        user_id = 1
        session_id = "session_1"
        
        # Mock session invalidation
        with patch.object(auth_service.auth_repo, 'invalidate_user_session') as mock_invalidate:
            mock_invalidate.return_value = True
            
            # Act
            result = auth_service.revoke_user_session(user_id, session_id)
            
            # Assert
            assert result is True
            mock_invalidate.assert_called_once_with(session_id)
    
    def test_get_security_events(self, test_db, security_service):
        """Test getting security events."""
        # Arrange
        auth_service = AuthService(test_db)
        user_id = 1
        
        # Mock login attempts
        with patch.object(auth_service.auth_repo, 'get_recent_login_attempts') as mock_attempts:
            mock_attempts.return_value = [
                {
                    "action": "login_attempt",
                    "success": True,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            # Act
            result = auth_service.get_security_events(user_id)
            
            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["action"] == "login_attempt"
            assert result[0]["success"] is True
    
    def test_cleanup_expired_data(self, test_db, security_service):
        """Test cleanup of expired authentication data."""
        # Arrange
        auth_service = AuthService(test_db)
        
        # Mock cleanup methods
        with patch.object(auth_service.auth_repo, 'cleanup_expired_blacklist') as mock_blacklist:
            mock_blacklist.return_value = 5
            
        with patch.object(auth_service.auth_repo, 'cleanup_expired_reset_tokens') as mock_reset:
            mock_reset.return_value = 3
            
        with patch.object(auth_service.auth_repo, 'cleanup_old_login_attempts') as mock_attempts:
            mock_attempts.return_value = 10
            
            # Act
            result = auth_service.cleanup_expired_data()
            
            # Assert
            assert result["blacklist_entries"] == 5
            assert result["reset_tokens"] == 3
            assert result["login_attempts"] == 10
    
    @pytest.mark.slow
    def test_concurrent_login_attempts(self, test_db, security_service):
        """Test concurrent login attempts."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock user
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.hashed_password = security_service.hash_password("TestPassword123!")
            mock_user.is_active = True
            mock_user.role = "USER"
            mock_get_user.return_value = mock_user
            
            # Act - simulate concurrent requests
            import asyncio
            async def login_attempt():
                return auth_service.authenticate_user(login_request, "127.0.0.1")
            
            # Run multiple concurrent attempts
            results = asyncio.run(login_attempt() for _ in range(5))
            
            # Assert
            assert len(results) == 5
            # All should succeed (no rate limiting in test)
            for result in results:
                assert result is not None
                assert "access_token" in result
    
    @pytest.mark.external
    def test_external_service_failure(self, test_db, security_service):
        """Test handling of external service failures."""
        # Arrange
        auth_service = AuthService(test_db)
        login_request = LoginRequest(
            identifier="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock external service failure
        with patch.object(auth_service.user_repo, 'get_by_email_or_username') as mock_get_user:
            mock_get_user.side_effect = Exception("Database connection failed")
            
            # Act & Assert
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user(login_request, "127.0.0.1")
    
    def test_edge_cases(self, test_db, security_service):
        """Test edge cases and boundary conditions."""
        # Test empty identifier
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(LoginRequest(identifier="", password="test"), "127.0.0.1")
        
        # Test empty password
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(LoginRequest(identifier="test@example.com", password=""), "127.0.0.1")
        
        # Test None values
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(LoginRequest(identifier=None, password="test"), "127.0.0.1")
        
        # Test very long identifier
        long_identifier = "a" * 1000
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(LoginRequest(identifier=long_identifier, password="test"), "127.0.0.1")
        
        # Test very long password
        long_password = "a" * 1000
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(LoginRequest(identifier="test@example.com", password=long_password), "127.0.0.1")
