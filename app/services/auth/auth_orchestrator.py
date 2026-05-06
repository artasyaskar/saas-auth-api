"""
Authentication orchestrator for coordinating auth services.

Coordinates between credential validation, token management,
and session services to provide a unified authentication interface.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from sqlalchemy.orm import Session
from app.db.models import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.exceptions import AuthenticationError, SecurityError, RateLimitError
from .credential_service import CredentialService
from .token_service import TokenService
from .session_service import SessionService

logger = structlog.get_logger()


class AuthOrchestrator:
    """
    Orchestrator for authentication operations.
    
    Coordinates between specialized auth services to provide
    a unified authentication interface while maintaining
    proper separation of concerns.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credential_service = CredentialService(db)
        self.token_service = TokenService(db)
        self.session_service = SessionService(db)
    
    def authenticate_user(self, request: LoginRequest, ip_address: str = None, user_agent: str = None) -> LoginResponse:
        """
        Authenticate user and return login response.
        
        Args:
            request: Login request with credentials
            ip_address: Client IP address
            user_agent: User agent string
            
        Returns:
            Login response with tokens and user info
            
        Raises:
            AuthenticationError: If authentication fails
            SecurityError: If security issues detected
            RateLimitError: If rate limit exceeded
        """
        try:
            # Step 1: Validate credentials
            user = self.credential_service.validate_credentials(request, ip_address)
            
            # Step 2: Check 2FA requirements
            two_fa_requirements = self.credential_service.check_2fa_requirement(user)
            
            if two_fa_requirements.get("required", False):
                return LoginResponse(
                    requires_2fa=True,
                    two_factor_methods=two_fa_requirements["methods"],
                    message=two_fa_requirements.get("reason", "Two-factor authentication required"),
                    user=self._prepare_user_response(user)
                )
            
            # Step 3: Create tokens
            device_id = self._extract_device_id(user_agent)
            tokens = self.token_service.create_user_tokens(user, device_id)
            
            # Step 4: Create session
            session = self.session_service.create_user_session(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id
            )
            
            # Step 5: Update user login info
            self._update_user_login_info(user)
            
            # Step 6: Log successful authentication
            logger.info(f"User authenticated successfully", user_id=user.id, ip_address=ip_address)
            
            return LoginResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_type=tokens["token_type"],
                expires_in=tokens["expires_in"],
                user=tokens["user"],
                session_id=session.id,
                requires_2fa=False
            )
            
        except (AuthenticationError, SecurityError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"Authentication orchestration failed: {str(e)}")
            raise AuthenticationError("Authentication failed")
    
    def refresh_authentication(self, refresh_token: str, ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """
        Refresh user authentication using refresh token.
        
        Args:
            refresh_token: Refresh token to use
            ip_address: Client IP address
            user_agent: User agent string
            
        Returns:
            Dictionary with new tokens and session info
            
        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            # Step 1: Refresh access token
            device_id = self._extract_device_id(user_agent)
            tokens = self.token_service.refresh_access_token(refresh_token, device_id)
            
            # Step 2: Update session if exists
            # Note: Session update would require session token from original login
            # This is a simplified implementation
            
            logger.info("Authentication refreshed successfully")
            return tokens
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication refresh failed: {str(e)}")
            raise AuthenticationError("Token refresh failed")
    
    def logout_user(self, access_token: str, refresh_token: str = None, session_token: str = None) -> bool:
        """
        Logout user by revoking tokens and sessions.
        
        Args:
            access_token: Access token to revoke
            refresh_token: Refresh token to revoke (optional)
            session_token: Session token to revoke (optional)
            
        Returns:
            True if logout was successful
        """
        try:
            # Extract user ID from access token
            payload = self.token_service.validate_access_token(access_token)
            user_id = payload.get("user_id")
            
            if not user_id:
                logger.warning("Could not extract user ID from access token during logout")
                return False
            
            success_count = 0
            
            # Revoke access token
            if self.token_service.revoke_token(access_token, "access", "logout"):
                success_count += 1
            
            # Revoke refresh token if provided
            if refresh_token:
                if self.token_service.revoke_token(refresh_token, "refresh", "logout"):
                    success_count += 1
            
            # Revoke session if provided
            if session_token:
                if self.session_service.revoke_session(session_token, "logout"):
                    success_count += 1
            
            # Revoke all other sessions for the user (optional - can be configurable)
            # This ensures complete logout from all devices
            all_sessions_revoked = self.session_service.revoke_user_sessions(
                user_id, "logout_all", exclude_session=session_token
            )
            
            logger.info(f"User logged out successfully", user_id=user_id, revoked_items=success_count + all_sessions_revoked)
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False
    
    def logout_all_devices(self, access_token: str) -> bool:
        """
        Logout user from all devices.
        
        Args:
            access_token: Current access token
            
        Returns:
            True if logout was successful
        """
        try:
            # Extract user ID from access token
            payload = self.token_service.validate_access_token(access_token)
            user_id = payload.get("user_id")
            
            if not user_id:
                return False
            
            # Revoke all tokens for the user
            tokens_revoked = self.token_service.revoke_user_tokens(user_id, "logout_all_devices")
            
            # Revoke all sessions for the user
            sessions_revoked = self.session_service.revoke_user_sessions(user_id, "logout_all_devices")
            
            logger.info(f"User logged out from all devices", user_id=user_id, tokens_revoked=tokens_revoked, sessions_revoked=sessions_revoked)
            return True
            
        except Exception as e:
            logger.error(f"Logout all devices failed: {str(e)}")
            return False
    
    def get_user_sessions(self, access_token: str) -> Dict[str, Any]:
        """
        Get user's active sessions.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dictionary with session information
        """
        try:
            # Extract user ID from access token
            payload = self.token_service.validate_access_token(access_token)
            user_id = payload.get("user_id")
            
            if not user_id:
                raise AuthenticationError("Invalid access token")
            
            # Get user sessions
            sessions = self.session_service.get_user_sessions(user_id, active_only=True)
            
            # Get session statistics
            stats = self.session_service.get_session_statistics(user_id)
            
            return {
                "sessions": sessions,
                "statistics": stats,
                "max_sessions_per_user": stats.get("max_sessions_per_user", 5)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            raise AuthenticationError("Failed to get sessions")
    
    def _prepare_user_response(self, user: User) -> Dict[str, Any]:
        """Prepare user data for response."""
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "two_factor_enabled": user.two_factor_enabled
        }
    
    def _extract_device_id(self, user_agent: str) -> Optional[str]:
        """Extract device identifier from user agent."""
        # Simplified device ID extraction
        # In production, this would use more sophisticated fingerprinting
        if not user_agent:
            return None
        
        # Create a simple hash of user agent for device identification
        import hashlib
        return hashlib.md5(user_agent.encode()).hexdigest()[:16]
    
    def _update_user_login_info(self, user: User) -> None:
        """Update user's login information."""
        try:
            user.last_login_at = datetime.utcnow()
            user.login_count = (user.login_count or 0) + 1
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update user login info: {str(e)}")
            self.db.rollback()


# Backward compatibility wrapper
class AuthService(AuthOrchestrator):
    """
    Backward compatibility wrapper for the original AuthService.
    
    Maintains the same interface while using the new orchestrator
    internally for better separation of concerns.
    """
    pass
