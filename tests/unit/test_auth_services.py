"""
Unit tests for authentication services.

Tests the refactored authentication services with proper
separation of concerns and comprehensive coverage.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.auth.credential_service import CredentialService
from app.services.auth.token_service import TokenService
from app.services.auth.session_service import SessionService
from app.services.auth.auth_orchestrator import AuthOrchestrator
from app.db.models import User, UserRole, LoginAttempt
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.exceptions import (
    AuthenticationError, SecurityError, RateLimitError,
    TokenError, SessionError
)


class TestCredentialService:
    """Test cases for CredentialService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def credential_service(self, mock_db):
        """Create credential service instance."""
        return CredentialService(mock_db)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.hashed_password = "hashed_password"
        user.is_active = True
        user.is_locked = False
        user.email_verified = True
        user.two_factor_enabled = False
        user.password_expires_at = None
        user.force_password_reset = False
        return user
    
    @pytest.fixture
    def login_request(self):
        """Create login request."""
        return LoginRequest(
            identifier="test@example.com",
            password="password123",
            user_agent="Mozilla/5.0"
        )
    
    def test_validate_credentials_success(self, credential_service, mock_user, login_request):
        """Test successful credential validation."""
        # Mock repository methods
        credential_service.user_repo.get_by_email_or_username.return_value = mock_user
        credential_service.auth_repo.get_recent_attempts.return_value = []
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with patch('app.services.auth.credential_service.verify_password', return_value=True):
            result = credential_service.validate_credentials(login_request, "192.168.1.1")
        
        assert result == mock_user
        credential_service.user_repo.get_by_email_or_username.assert_called_once_with("test@example.com")
        credential_service.auth_repo.record_login_attempt.assert_called()
    
    def test_validate_credentials_user_not_found(self, credential_service, login_request):
        """Test credential validation with user not found."""
        credential_service.user_repo.get_by_email_or_username.return_value = None
        credential_service.auth_repo.get_recent_attempts.return_value = []
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            credential_service.validate_credentials(login_request, "192.168.1.1")
    
    def test_validate_credentials_rate_limited(self, credential_service, login_request):
        """Test credential validation with rate limit exceeded."""
        credential_service.auth_repo.get_recent_attempts.return_value = [Mock()] * 5
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with pytest.raises(RateLimitError, match="Too many login attempts"):
            credential_service.validate_credentials(login_request, "192.168.1.1")
    
    def test_validate_credentials_inactive_user(self, credential_service, mock_user, login_request):
        """Test credential validation with inactive user."""
        mock_user.is_active = False
        credential_service.user_repo.get_by_email_or_username.return_value = mock_user
        credential_service.auth_repo.get_recent_attempts.return_value = []
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with patch('app.services.auth.credential_service.verify_password', return_value=True):
            with pytest.raises(AuthenticationError, match="Account is not active"):
                credential_service.validate_credentials(login_request, "192.168.1.1")
    
    def test_validate_credentials_locked_user(self, credential_service, mock_user, login_request):
        """Test credential validation with locked user."""
        mock_user.is_locked = True
        credential_service.user_repo.get_by_email_or_username.return_value = mock_user
        credential_service.auth_repo.get_recent_attempts.return_value = []
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with patch('app.services.auth.credential_service.verify_password', return_value=True):
            with pytest.raises(SecurityError, match="Account is locked"):
                credential_service.validate_credentials(login_request, "192.168.1.1")
    
    def test_validate_credentials_invalid_password(self, credential_service, mock_user, login_request):
        """Test credential validation with invalid password."""
        credential_service.user_repo.get_by_email_or_username.return_value = mock_user
        credential_service.auth_repo.get_recent_attempts.return_value = []
        credential_service.auth_repo.get_recent_attempts_by_ip.return_value = []
        
        with patch('app.services.auth.credential_service.verify_password', return_value=False):
            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                credential_service.validate_credentials(login_request, "192.168.1.1")
    
    def test_check_2fa_requirement_no_2fa(self, credential_service, mock_user):
        """Test 2FA requirement check when 2FA is not enabled."""
        mock_user.two_factor_enabled = False
        
        result = credential_service.check_2fa_requirement(mock_user)
        
        assert result["required"] is False
    
    def test_check_2fa_requirement_with_2fa_enabled(self, credential_service, mock_user):
        """Test 2FA requirement check when 2FA is enabled."""
        mock_user.two_factor_enabled = True
        credential_service.auth_repo.get_recent_failed_attempts.return_value = []
        
        result = credential_service.check_2fa_requirement(mock_user)
        
        assert result["required"] is True
        assert "totp" in result["methods"]
    
    def test_assess_login_risk_high_risk_multiple_failures(self, credential_service, mock_user):
        """Test risk assessment with multiple failed attempts."""
        mock_user.created_at = datetime.utcnow() - timedelta(days=30)
        mock_user.last_login_at = datetime.utcnow() - timedelta(days=1)
        
        # Mock 6 failed attempts
        credential_service.auth_repo.get_recent_failed_attempts.return_value = [Mock()] * 6
        
        result = credential_service._assess_login_risk(mock_user)
        
        assert result["high_risk"] is True
        assert "multiple_failed_attempts" in result["factors"]


class TestTokenService:
    """Test cases for TokenService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def token_service(self, mock_db):
        """Create token service instance."""
        return TokenService(mock_db)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.role = UserRole.USER
        user.is_active = True
        user.is_locked = False
        return user
    
    def test_create_user_tokens_success(self, token_service, mock_user):
        """Test successful token creation."""
        # Mock dependencies
        mock_refresh_token = Mock()
        mock_refresh_token.token = "refresh_token_123"
        token_service.refresh_token_service.create_refresh_token.return_value = mock_refresh_token
        
        with patch('app.services.auth.token_service.create_token_pair') as mock_create_pair:
            mock_create_pair.return_value = {
                "access_token": "access_token_123",
                "refresh_token": "refresh_token_456"
            }
            
            result = token_service.create_user_tokens(mock_user, "device_123")
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert "expires_in" in result
        assert "user" in result
        
        token_service.refresh_token_service.create_refresh_token.assert_called_once()
    
    def test_create_user_tokens_refresh_token_failure(self, token_service, mock_user):
        """Test token creation when refresh token creation fails."""
        token_service.refresh_token_service.create_refresh_token.return_value = None
        
        with patch('app.services.auth.token_service.create_token_pair'):
            with pytest.raises(TokenError, match="Failed to create refresh token record"):
                token_service.create_user_tokens(mock_user)
    
    def test_refresh_access_token_success(self, token_service):
        """Test successful access token refresh."""
        # Mock validated token
        mock_validated_token = Mock()
        mock_validated_token.user_id = 1
        mock_validated_token.device_id = "device_123"
        
        # Mock rotated token
        mock_rotated_token = Mock()
        mock_rotated_token.token = "new_refresh_token"
        
        token_service.refresh_token_service.validate_refresh_token_with_rotation_check.return_value = (
            mock_validated_token, mock_rotated_token
        )
        
        # Mock user
        mock_user = Mock(spec=User)
        mock_user.is_active = True
        mock_user.is_locked = False
        token_service._get_user_by_id = Mock(return_value=mock_user)
        
        with patch('app.services.auth.token_service.create_access_token', return_value="new_access_token"):
            result = token_service.refresh_access_token("refresh_token_123", "device_123")
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token_rotated"] is True
        assert result["refresh_token"] == "new_refresh_token"
    
    def test_refresh_access_token_invalid_token(self, token_service):
        """Test access token refresh with invalid token."""
        token_service.refresh_token_service.validate_refresh_token_with_rotation_check.return_value = (None, None)
        
        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            token_service.refresh_access_token("invalid_token")
    
    def test_validate_access_token_success(self, token_service):
        """Test successful access token validation."""
        mock_payload = {"sub": "test@example.com", "user_id": 1, "email": "test@example.com"}
        
        with patch('app.services.auth.token_service.verify_token', return_value=mock_payload):
            token_service.blacklist_service.is_token_blacklisted.return_value = False
            
            result = token_service.validate_access_token("valid_token")
        
        assert result == mock_payload
        token_service.blacklist_service.is_token_blacklisted.assert_called_once_with("valid_token")
    
    def test_validate_access_token_blacklisted(self, token_service):
        """Test access token validation with blacklisted token."""
        token_service.blacklist_service.is_token_blacklisted.return_value = True
        
        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            token_service.validate_access_token("blacklisted_token")
    
    def test_revoke_token_access_token(self, token_service):
        """Test revoking access token."""
        mock_payload = {"user_id": 1}
        
        with patch('app.services.auth.token_service.verify_token', return_value=mock_payload):
            token_service.blacklist_service.blacklist_token.return_value = True
            
            result = token_service.revoke_token("access_token", "access", "logout")
        
        assert result is True
        token_service.blacklist_service.blacklist_token.assert_called_once()
    
    def test_revoke_token_refresh_token(self, token_service):
        """Test revoking refresh token."""
        token_service.refresh_token_service.revoke_refresh_token.return_value = True
        
        result = token_service.revoke_token("refresh_token", "refresh", "logout")
        
        assert result is True
        token_service.refresh_token_service.revoke_refresh_token.assert_called_once_with("refresh_token", "logout")


class TestSessionService:
    """Test cases for SessionService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def session_service(self, mock_db):
        """Create session service instance."""
        return SessionService(mock_db)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = Mock()
        session.id = 1
        session.session_token = "session_token_123"
        session.user_id = 1
        session.ip_address = "192.168.1.1"
        session.user_agent = "Mozilla/5.0"
        session.device_id = "device_123"
        session.is_active = True
        session.expires_at = datetime.utcnow() + timedelta(days=1)
        return session
    
    def test_create_user_session_success(self, session_service, mock_session):
        """Test successful session creation."""
        session_service._get_active_sessions.return_value = []
        
        with patch('app.services.auth.session_service.secrets.token_urlsafe', return_value="session_token_123"):
            with patch.object(session_service.db, 'add') as mock_add:
                with patch.object(session_service.db, 'commit') as mock_commit:
                    with patch.object(session_service.db, 'refresh') as mock_refresh:
                        mock_refresh.return_value = mock_session
                        
                        result = session_service.create_user_session(
                            user_id=1,
                            ip_address="192.168.1.1",
                            user_agent="Mozilla/5.0",
                            device_id="device_123"
                        )
        
        assert result == mock_session
        mock_add.assert_called_once()
        mock_commit.assert_called_once()
    
    def test_create_user_session_enforce_limit(self, session_service, mock_session):
        """Test session creation with limit enforcement."""
        # Mock existing sessions at limit
        existing_sessions = [Mock()] * 5  # Assuming max_sessions_per_user = 5
        session_service._get_active_sessions.return_value = existing_sessions
        
        # Mock oldest session
        oldest_session = Mock()
        oldest_session.id = 1
        session_service._deactivate_session.return_value = True
        
        with patch('app.services.auth.session_service.secrets.token_urlsafe', return_value="new_session_token"):
            with patch.object(session_service.db, 'add'):
                with patch.object(session_service.db, 'commit'):
                    with patch.object(session_service.db, 'refresh', return_value=mock_session):
                        result = session_service.create_user_session(user_id=1)
        
        assert result == mock_session
        session_service._deactivate_session.assert_called_once()
    
    def test_validate_session_success(self, session_service, mock_session):
        """Test successful session validation."""
        session_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_session
        
        result = session_service.validate_session("session_token_123", "192.168.1.1")
        
        assert result == mock_session
        assert mock_session.last_accessed_at is not None
    
    def test_validate_session_invalid_token(self, session_service):
        """Test session validation with invalid token."""
        session_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(SessionError, match="Invalid session token"):
            session_service.validate_session("invalid_token")
    
    def test_validate_session_expired(self, session_service, mock_session):
        """Test session validation with expired session."""
        mock_session.expires_at = datetime.utcnow() - timedelta(days=1)
        session_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_session
        session_service._deactivate_session.return_value = True
        
        with pytest.raises(SessionError, match="Session has expired"):
            session_service.validate_session("expired_token")
    
    def test_revoke_session_success(self, session_service, mock_session):
        """Test successful session revocation."""
        session_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_session
        session_service._deactivate_session.return_value = True
        
        result = session_service.revoke_session("session_token_123", "logout")
        
        assert result is True
        session_service._deactivate_session.assert_called_once_with(mock_session.id, "logout")
    
    def test_revoke_session_not_found(self, session_service):
        """Test session revocation with session not found."""
        session_service.db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        result = session_service.revoke_session("nonexistent_token")
        
        assert result is False


class TestAuthOrchestrator:
    """Test cases for AuthOrchestrator."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def auth_orchestrator(self, mock_db):
        """Create auth orchestrator instance."""
        return AuthOrchestrator(mock_db)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.role = UserRole.USER
        user.is_active = True
        user.two_factor_enabled = False
        return user
    
    @pytest.fixture
    def login_request(self):
        """Create login request."""
        return LoginRequest(
            identifier="test@example.com",
            password="password123",
            user_agent="Mozilla/5.0"
        )
    
    def test_authenticate_user_success(self, auth_orchestrator, mock_user, login_request):
        """Test successful user authentication."""
        # Mock credential service
        auth_orchestrator.credential_service.validate_credentials.return_value = mock_user
        auth_orchestrator.credential_service.check_2fa_requirement.return_value = {"required": False}
        
        # Mock token service
        tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {"id": 1, "email": "test@example.com"}
        }
        auth_orchestrator.token_service.create_user_tokens.return_value = tokens
        
        # Mock session service
        mock_session = Mock()
        mock_session.id = 1
        auth_orchestrator.session_service.create_user_session.return_value = mock_session
        
        # Mock user update
        auth_orchestrator._update_user_login_info = Mock()
        
        result = auth_orchestrator.authenticate_user(login_request, "192.168.1.1", "Mozilla/5.0")
        
        assert isinstance(result, LoginResponse)
        assert result.access_token == "access_token_123"
        assert result.refresh_token == "refresh_token_123"
        assert result.requires_2fa is False
        assert result.session_id == 1
    
    def test_authenticate_user_requires_2fa(self, auth_orchestrator, mock_user, login_request):
        """Test user authentication when 2FA is required."""
        # Mock credential service
        auth_orchestrator.credential_service.validate_credentials.return_value = mock_user
        auth_orchestrator.credential_service.check_2fa_requirement.return_value = {
            "required": True,
            "methods": ["totp", "sms"],
            "reason": "2FA enabled"
        }
        
        result = auth_orchestrator.authenticate_user(login_request, "192.168.1.1", "Mozilla/5.0")
        
        assert isinstance(result, LoginResponse)
        assert result.requires_2fa is True
        assert result.two_factor_methods == ["totp", "sms"]
        assert "user" in result
    
    def test_refresh_authentication_success(self, auth_orchestrator):
        """Test successful authentication refresh."""
        tokens = {
            "access_token": "new_access_token",
            "token_type": "bearer",
            "expires_in": 3600
        }
        auth_orchestrator.token_service.refresh_access_token.return_value = tokens
        
        result = auth_orchestrator.refresh_authentication("refresh_token_123", "192.168.1.1", "Mozilla/5.0")
        
        assert result["access_token"] == "new_access_token"
        assert result["token_type"] == "bearer"
    
    def test_logout_user_success(self, auth_orchestrator):
        """Test successful user logout."""
        # Mock token validation
        mock_payload = {"user_id": 1}
        auth_orchestrator.token_service.validate_access_token.return_value = mock_payload
        
        # Mock token revocation
        auth_orchestrator.token_service.revoke_token.return_value = True
        auth_orchestrator.session_service.revoke_session.return_value = True
        auth_orchestrator.session_service.revoke_user_sessions.return_value = 2
        
        result = auth_orchestrator.logout_user("access_token", "refresh_token", "session_token")
        
        assert result is True
    
    def test_logout_all_devices_success(self, auth_orchestrator):
        """Test successful logout from all devices."""
        # Mock token validation
        mock_payload = {"user_id": 1}
        auth_orchestrator.token_service.validate_access_token.return_value = mock_payload
        
        # Mock token and session revocation
        auth_orchestrator.token_service.revoke_user_tokens.return_value = 5
        auth_orchestrator.session_service.revoke_user_sessions.return_value = 3
        
        result = auth_orchestrator.logout_all_devices("access_token")
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
