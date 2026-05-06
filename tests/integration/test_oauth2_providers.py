"""
Integration tests for OAuth2 providers.

Tests the complete OAuth2 flow with different providers
including Google, GitHub, and other OAuth2 implementations.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from httpx import AsyncClient

from app.main import app
from app.db.models import User, UserRole, OAuthAccount
from app.services.oauth2 import OAuth2Service
from app.core.exceptions import AuthenticationError, OAuth2Error


class TestOAuth2Integration:
    """Integration tests for OAuth2 providers."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def oauth2_service(self, mock_db):
        """Create OAuth2 service instance."""
        return OAuth2Service(mock_db)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.role = UserRole.USER
        user.is_active = True
        user.email_verified = True
        return user
    
    @pytest.fixture
    def sample_oauth_state(self):
        """Sample OAuth state parameter."""
        return "oauth_state_123456"
    
    @pytest.fixture
    def sample_oauth_code(self):
        """Sample OAuth authorization code."""
        return "auth_code_789012"


class TestGoogleOAuth2Integration(TestOAuth2Integration):
    """Integration tests for Google OAuth2."""
    
    def test_google_oauth_authorization_url(self, oauth2_service, sample_oauth_state):
        """Test Google OAuth2 authorization URL generation."""
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.authorization_url.return_value = (
                "https://accounts.google.com/oauth/authorize?"
                "response_type=code&client_id=test_client_id&"
                "redirect_uri=http://localhost:8000/auth/google/callback&"
                "scope=openid%20email%20profile&"
                f"state={sample_oauth_state}"
            )
            
            url = oauth2_service.get_authorization_url("google", sample_oauth_state)
            
            assert "accounts.google.com" in url
            assert sample_oauth_state in url
            assert "response_type=code" in url
    
    def test_google_oauth_callback_success(self, oauth2_service, mock_user, sample_oauth_state, sample_oauth_code):
        """Test successful Google OAuth2 callback."""
        # Mock OAuth token exchange
        mock_token = {
            "access_token": "google_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "google_refresh_token",
            "scope": "openid email profile"
        }
        
        # Mock user info from Google
        mock_user_info = {
            "id": "google_user_id_123",
            "email": "test@example.com",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg",
            "verified_email": True
        }
        
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.return_value = mock_token
            mock_google_oauth.parse_id_token.return_value = {
                "sub": "google_user_id_123",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/photo.jpg",
                "email_verified": True
            }
            mock_google_oauth.get_user_info.return_value = mock_user_info
            
            # Mock existing OAuth account
            mock_oauth_account = Mock(spec=OAuthAccount)
            mock_oauth_account.user = mock_user
            
            oauth2_service._get_or_create_oauth_account = Mock(return_value=mock_oauth_account)
            oauth2_service._create_or_update_user_from_oauth = Mock(return_value=mock_user)
            
            result = oauth2_service.handle_oauth_callback(
                "google", sample_oauth_code, sample_oauth_state
            )
        
        assert result["user"] == mock_user
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["provider"] == "google"
    
    def test_google_oauth_callback_invalid_state(self, oauth2_service, sample_oauth_code):
        """Test Google OAuth2 callback with invalid state."""
        with pytest.raises(OAuth2Error, match="Invalid state parameter"):
            oauth2_service.handle_oauth_callback(
                "google", sample_oauth_code, "invalid_state"
            )
    
    def test_google_oauth_callback_token_exchange_failure(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test Google OAuth2 callback with token exchange failure."""
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.side_effect = Exception("Token exchange failed")
            
            with pytest.raises(OAuth2Error, match="OAuth2 token exchange failed"):
                oauth2_service.handle_oauth_callback(
                    "google", sample_oauth_code, sample_oauth_state
                )
    
    def test_google_oauth_callback_invalid_user_info(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test Google OAuth2 callback with invalid user info."""
        mock_token = {"access_token": "valid_token"}
        
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.return_value = mock_token
            mock_google_oauth.parse_id_token.side_effect = Exception("Invalid ID token")
            
            with pytest.raises(OAuth2Error, match="Failed to retrieve user information"):
                oauth2_service.handle_oauth_callback(
                    "google", sample_oauth_code, sample_oauth_state
                )


class TestGitHubOAuth2Integration(TestOAuth2Integration):
    """Integration tests for GitHub OAuth2."""
    
    def test_github_oauth_authorization_url(self, oauth2_service, sample_oauth_state):
        """Test GitHub OAuth2 authorization URL generation."""
        with patch('app.services.oauth2.github_oauth') as mock_github_oauth:
            mock_github_oauth.authorization_url.return_value = (
                "https://github.com/login/oauth/authorize?"
                "response_type=code&client_id=test_client_id&"
                "redirect_uri=http://localhost:8000/auth/github/callback&"
                "scope=user:email&"
                f"state={sample_oauth_state}"
            )
            
            url = oauth2_service.get_authorization_url("github", sample_oauth_state)
            
            assert "github.com" in url
            assert sample_oauth_state in url
            assert "response_type=code" in url
    
    def test_github_oauth_callback_success(self, oauth2_service, mock_user, sample_oauth_state, sample_oauth_code):
        """Test successful GitHub OAuth2 callback."""
        # Mock OAuth token exchange
        mock_token = {
            "access_token": "github_access_token",
            "token_type": "Bearer",
            "scope": "user:email"
        }
        
        # Mock user info from GitHub
        mock_user_info = {
            "id": 12345,
            "login": "testuser",
            "email": "test@example.com",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg"
        }
        
        with patch('app.services.oauth2.github_oauth') as mock_github_oauth:
            mock_github_oauth.fetch_token.return_value = mock_token
            mock_github_oauth.get.return_value.json.return_value = mock_user_info
            
            # Mock existing OAuth account
            mock_oauth_account = Mock(spec=OAuthAccount)
            mock_oauth_account.user = mock_user
            
            oauth2_service._get_or_create_oauth_account = Mock(return_value=mock_oauth_account)
            oauth2_service._create_or_update_user_from_oauth = Mock(return_value=mock_user)
            
            result = oauth2_service.handle_oauth_callback(
                "github", sample_oauth_code, sample_oauth_state
            )
        
        assert result["user"] == mock_user
        assert "access_token" in result
        assert result["provider"] == "github"
    
    def test_github_oauth_callback_no_email(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test GitHub OAuth2 callback when user has no public email."""
        mock_token = {"access_token": "valid_token"}
        mock_user_info = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": None  # No public email
        }
        
        with patch('app.services.oauth2.github_oauth') as mock_github_oauth:
            mock_github_oauth.fetch_token.return_value = mock_token
            mock_github_oauth.get.return_value.json.return_value = mock_user_info
            
            with pytest.raises(OAuth2Error, match="Email address is required"):
                oauth2_service.handle_oauth_callback(
                    "github", sample_oauth_code, sample_oauth_state
                )


class TestOAuth2AccountLinking(TestOAuth2Integration):
    """Integration tests for OAuth2 account linking."""
    
    def test_link_oauth_account_to_existing_user(self, oauth2_service, mock_user):
        """Test linking OAuth account to existing user."""
        provider = "google"
        provider_user_id = "google_user_id_123"
        access_token = "access_token_123"
        
        # Mock OAuth account creation
        mock_oauth_account = Mock(spec=OAuthAccount)
        oauth2_service._create_oauth_account = Mock(return_value=mock_oauth_account)
        
        result = oauth2_service.link_oauth_account(
            mock_user.id, provider, provider_user_id, access_token
        )
        
        assert result == mock_oauth_account
        oauth2_service._create_oauth_account.assert_called_once()
    
    def test_unlink_oauth_account(self, oauth2_service, mock_user):
        """Test unlinking OAuth account."""
        provider = "google"
        
        # Mock OAuth account lookup and deletion
        mock_oauth_account = Mock(spec=OAuthAccount)
        oauth2_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_oauth_account
        oauth2_service.db.delete.return_value = None
        oauth2_service.db.commit.return_value = None
        
        result = oauth2_service.unlink_oauth_account(mock_user.id, provider)
        
        assert result is True
    
    def test_get_linked_oauth_accounts(self, oauth2_service, mock_user):
        """Test getting linked OAuth accounts for a user."""
        # Mock OAuth accounts
        mock_oauth_accounts = [
            Mock(spec=OAuthAccount, provider="google", provider_user_id="google_123"),
            Mock(spec=OAuthAccount, provider="github", provider_user_id="github_456")
        ]
        
        oauth2_service.db.query.return_value.filter.return_value.all.return_value = mock_oauth_accounts
        
        result = oauth2_service.get_linked_oauth_accounts(mock_user.id)
        
        assert len(result) == 2
        assert result[0].provider == "google"
        assert result[1].provider == "github"


class TestOAuth2Security(TestOAuth2Integration):
    """Integration tests for OAuth2 security features."""
    
    def test_oauth_state_validation(self, oauth2_service):
        """Test OAuth state parameter validation."""
        # Generate state
        state = oauth2_service.generate_oauth_state()
        
        # Validate state
        assert oauth2_service.validate_oauth_state(state) is True
        
        # Test invalid state
        assert oauth2_service.validate_oauth_state("invalid_state") is False
    
    def test_oauth_state_expiration(self, oauth2_service):
        """Test OAuth state parameter expiration."""
        # Generate state
        state = oauth2_service.generate_oauth_state()
        
        # Mock expired state
        with patch('app.services.oauth2.time.time', return_value=time.time() + 600):  # 10 minutes later
            assert oauth2_service.validate_oauth_state(state) is False
    
    def test_oauth_token_revocation(self, oauth2_service, mock_user):
        """Test OAuth token revocation."""
        provider = "google"
        access_token = "access_token_123"
        
        # Mock token revocation
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.revoke_token.return_value = True
            
            result = oauth2_service.revoke_oauth_token(mock_user.id, provider, access_token)
            
            assert result is True
    
    def test_oauth_account_cleanup(self, oauth2_service, mock_user):
        """Test cleanup of unused OAuth accounts."""
        # Mock OAuth accounts
        mock_oauth_accounts = [Mock(spec=OAuthAccount) for _ in range(3)]
        
        oauth2_service.db.query.return_value.filter.return_value.all.return_value = mock_oauth_accounts
        oauth2_service.db.delete.return_value = None
        oauth2_service.db.commit.return_value = None
        
        result = oauth2_service.cleanup_unused_oauth_accounts(days_unused=30)
        
        assert result == 3


class TestOAuth2Endpoints(TestOAuth2Integration):
    """Integration tests for OAuth2 API endpoints."""
    
    def test_oauth_authorization_endpoint(self, client):
        """Test OAuth authorization endpoint."""
        response = client.get("/auth/oauth/google/authorize")
        
        assert response.status_code == 302  # Redirect to OAuth provider
        assert "location" in response.headers
    
    def test_oauth_callback_endpoint_invalid_provider(self, client):
        """Test OAuth callback endpoint with invalid provider."""
        response = client.get("/auth/oauth/invalid/callback?code=test&state=test")
        
        assert response.status_code == 400
        assert "Invalid OAuth provider" in response.json()["detail"]
    
    def test_oauth_callback_endpoint_missing_params(self, client):
        """Test OAuth callback endpoint with missing parameters."""
        response = client.get("/auth/oauth/google/callback")
        
        assert response.status_code == 400
        assert "Missing required parameters" in response.json()["detail"]
    
    def test_oauth_link_endpoint_unauthorized(self, client):
        """Test OAuth link endpoint without authentication."""
        response = client.post("/auth/oauth/link", json={
            "provider": "google",
            "access_token": "test_token"
        })
        
        assert response.status_code == 401
    
    def test_oauth_unlink_endpoint_unauthorized(self, client):
        """Test OAuth unlink endpoint without authentication."""
        response = client.delete("/auth/oauth/unlink/google")
        
        assert response.status_code == 401
    
    def test_oauth_linked_accounts_endpoint_unauthorized(self, client):
        """Test linked accounts endpoint without authentication."""
        response = client.get("/auth/oauth/linked")
        
        assert response.status_code == 401


class TestOAuth2ErrorHandling(TestOAuth2Integration):
    """Integration tests for OAuth2 error handling."""
    
    def test_oauth_provider_unavailable(self, oauth2_service, sample_oauth_state):
        """Test handling when OAuth provider is unavailable."""
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.authorization_url.side_effect = Exception("Provider unavailable")
            
            with pytest.raises(OAuth2Error, match="OAuth provider unavailable"):
                oauth2_service.get_authorization_url("google", sample_oauth_state)
    
    def test_oauth_invalid_client_credentials(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test handling invalid client credentials."""
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.side_effect = Exception("Invalid client credentials")
            
            with pytest.raises(OAuth2Error, match="OAuth2 token exchange failed"):
                oauth2_service.handle_oauth_callback(
                    "google", sample_oauth_code, sample_oauth_state
                )
    
    def test_oauth_user_denied_access(self, oauth2_service, sample_oauth_state):
        """Test handling when user denies access."""
        # Simulate user denial with error parameter
        error_response = {
            "error": "access_denied",
            "error_description": "The user denied the request"
        }
        
        with pytest.raises(OAuth2Error, match="User denied access"):
            oauth2_service.handle_oauth_error("google", error_response)
    
    def test_oauth_invalid_redirect_uri(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test handling invalid redirect URI."""
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.side_effect = Exception("Invalid redirect URI")
            
            with pytest.raises(OAuth2Error, match="OAuth2 token exchange failed"):
                oauth2_service.handle_oauth_callback(
                    "google", sample_oauth_code, sample_oauth_state
                )


class TestOAuth2Performance(TestOAuth2Integration):
    """Integration tests for OAuth2 performance."""
    
    def test_oauth_callback_performance(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test OAuth callback performance."""
        import time
        
        # Mock successful callback
        mock_token = {"access_token": "test_token"}
        mock_user_info = {"id": "123", "email": "test@example.com"}
        
        with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
            mock_google_oauth.fetch_token.return_value = mock_token
            mock_google_oauth.parse_id_token.return_value = {"sub": "123", "email": "test@example.com"}
            mock_google_oauth.get_user_info.return_value = mock_user_info
            
            mock_user = Mock(spec=User)
            mock_oauth_account = Mock(spec=OAuthAccount)
            mock_oauth_account.user = mock_user
            
            oauth2_service._get_or_create_oauth_account = Mock(return_value=mock_oauth_account)
            oauth2_service._create_or_update_user_from_oauth = Mock(return_value=mock_user)
            
            # Measure performance
            start_time = time.time()
            result = oauth2_service.handle_oauth_callback(
                "google", sample_oauth_code, sample_oauth_state
            )
            end_time = time.time()
            
            # Should complete within reasonable time (5 seconds)
            assert (end_time - start_time) < 5.0
            assert result["user"] == mock_user
    
    def test_concurrent_oauth_callbacks(self, oauth2_service, sample_oauth_state, sample_oauth_code):
        """Test handling concurrent OAuth callbacks."""
        import threading
        import time
        
        results = []
        errors = []
        
        def oauth_callback():
            try:
                mock_token = {"access_token": f"token_{threading.get_ident()}"}
                mock_user_info = {"id": str(threading.get_ident()), "email": f"test{threading.get_ident()}@example.com"}
                
                with patch('app.services.oauth2.google_oauth') as mock_google_oauth:
                    mock_google_oauth.fetch_token.return_value = mock_token
                    mock_google_oauth.parse_id_token.return_value = {"sub": str(threading.get_ident()), "email": f"test{threading.get_ident()}@example.com"}
                    mock_google_oauth.get_user_info.return_value = mock_user_info
                    
                    mock_user = Mock(spec=User)
                    mock_oauth_account = Mock(spec=OAuthAccount)
                    mock_oauth_account.user = mock_user
                    
                    oauth2_service._get_or_create_oauth_account = Mock(return_value=mock_oauth_account)
                    oauth2_service._create_or_update_user_from_oauth = Mock(return_value=mock_user)
                    
                    result = oauth2_service.handle_oauth_callback(
                        "google", sample_oauth_code, sample_oauth_state
                    )
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=oauth_callback)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__])
