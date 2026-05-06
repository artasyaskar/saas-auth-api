"""
Token service for JWT token management.

Handles token creation, validation, refresh, and lifecycle
management with proper security considerations.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import structlog

from sqlalchemy.orm import Session
from app.db.models import User
from app.core.jwt import (
    create_access_token, create_refresh_token, verify_token,
    create_token_pair, refresh_access_token
)
from app.core.config import settings
from app.core.exceptions import AuthenticationError, TokenError, SecurityError
from app.services.refresh_token import RefreshTokenService
from app.services.token_blacklist import TokenBlacklistService

logger = structlog.get_logger()


class TokenService:
    """
    Service for handling JWT token operations.
    
    Separated from main auth service to focus specifically on
    token creation, validation, and lifecycle management.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.refresh_token_service = RefreshTokenService(db)
        self.blacklist_service = TokenBlacklistService(db)
    
    def create_user_tokens(self, user: User, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user: User to create tokens for
            device_id: Device identifier for token binding
            
        Returns:
            Dictionary with token information
            
        Raises:
            TokenError: If token creation fails
        """
        try:
            # Prepare user data for token payload
            user_data = self._prepare_user_data(user)
            
            # Create JWT token pair
            token_pair = create_token_pair(user_data)
            
            # Create refresh token record
            refresh_token_record = self.refresh_token_service.create_refresh_token(
                user_id=user.id,
                device_id=device_id,
                expires_days=settings.security.refresh_token_expire_days
            )
            
            if not refresh_token_record:
                raise TokenError("Failed to create refresh token record")
            
            return {
                "access_token": token_pair["access_token"],
                "refresh_token": refresh_token_record.token,  # Use the actual token
                "token_type": "bearer",
                "expires_in": settings.security.access_token_expire_minutes * 60,
                "refresh_token_expires_in": settings.security.refresh_token_expire_days * 24 * 3600,
                "user": self._sanitize_user_data(user)
            }
            
        except Exception as e:
            logger.error(f"Token creation failed for user {user.id}: {str(e)}")
            raise TokenError(f"Failed to create tokens: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token to use
            device_id: Device identifier for validation
            
        Returns:
            Dictionary with new access token
            
        Raises:
            AuthenticationError: If refresh token is invalid
            TokenError: If token refresh fails
        """
        try:
            # Validate refresh token
            validated_token, rotated_token = self.refresh_token_service.validate_refresh_token_with_rotation_check(
                refresh_token, device_id, auto_rotate=True
            )
            
            if not validated_token:
                raise AuthenticationError("Invalid refresh token")
            
            # Get user information
            user = self._get_user_by_id(validated_token.user_id)
            if not user:
                raise AuthenticationError("User not found")
            
            # Validate user status
            self._validate_user_for_token(user)
            
            # Prepare user data
            user_data = self._prepare_user_data(user)
            
            # Create new access token
            new_access_token = create_access_token(user_data)
            
            result = {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": settings.security.access_token_expire_minutes * 60
            }
            
            # Include new refresh token if rotation occurred
            if rotated_token:
                result["refresh_token"] = rotated_token.token
                result["refresh_token_rotated"] = True
            
            return result
            
        except (AuthenticationError, TokenError):
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise TokenError(f"Failed to refresh token: {str(e)}")
    
    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """
        Validate access token and return payload.
        
        Args:
            token: Access token to validate
            
        Returns:
            Token payload
            
        Raises:
            AuthenticationError: If token is invalid
            TokenError: If token validation fails
        """
        try:
            # Check if token is blacklisted
            if self.blacklist_service.is_token_blacklisted(token):
                raise AuthenticationError("Token has been revoked")
            
            # Verify JWT token
            payload = verify_token(token)
            
            # Validate token structure
            self._validate_token_payload(payload)
            
            return payload
            
        except (AuthenticationError, TokenError):
            raise
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            raise TokenError(f"Failed to validate token: {str(e)}")
    
    def revoke_token(self, token: str, token_type: str = "access", reason: str = "logout") -> bool:
        """
        Revoke a token by adding it to the blacklist.
        
        Args:
            token: Token to revoke
            token_type: Type of token (access/refresh)
            reason: Reason for revocation
            
        Returns:
            True if token was revoked successfully
        """
        try:
            if token_type == "refresh":
                # Revoke refresh token record
                return self.refresh_token_service.revoke_refresh_token(token, reason)
            else:
                # Blacklist access token
                payload = self.validate_access_token(token)
                expires_at = datetime.utcnow() + timedelta(minutes=15)  # Short TTL for blacklisted access tokens
                
                return self.blacklist_service.blacklist_token(
                    token=token,
                    expires_at=expires_at,
                    user_id=payload.get("user_id"),
                    token_type=token_type,
                    reason=reason
                )
                
        except Exception as e:
            logger.error(f"Token revocation failed: {str(e)}")
            return False
    
    def revoke_user_tokens(self, user_id: int, reason: str = "logout") -> int:
        """
        Revoke all tokens for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            
        Returns:
            Number of tokens revoked
        """
        try:
            # Revoke refresh tokens
            refresh_revoked = self.refresh_token_service.revoke_user_tokens(user_id, reason)
            
            # Mark all user tokens for revocation
            blacklist_revoked = self.blacklist_service.revoke_user_tokens_by_reason(
                user_id, reason
            )
            
            total_revoked = refresh_revoked + blacklist_revoked
            logger.info(f"Revoked {total_revoked} tokens for user {user_id}, reason: {reason}")
            
            return total_revoked
            
        except Exception as e:
            logger.error(f"User token revocation failed: {str(e)}")
            return 0
    
    def _prepare_user_data(self, user: User) -> Dict[str, Any]:
        """Prepare user data for token payload."""
        return {
            "sub": user.email,
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value if user.role else None,
            "iat": datetime.utcnow().timestamp()
        }
    
    def _sanitize_user_data(self, user: User) -> Dict[str, Any]:
        """Sanitize user data for response."""
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "email_verified": user.email_verified
        }
    
    def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None
    
    def _validate_user_for_token(self, user: User) -> None:
        """Validate user status for token issuance."""
        if not user.is_active:
            raise AuthenticationError("User account is not active")
        
        if user.is_locked:
            raise AuthenticationError("User account is locked")
    
    def _validate_token_payload(self, payload: Dict[str, Any]) -> None:
        """Validate token payload structure."""
        required_fields = ["sub", "user_id", "email"]
        
        for field in required_fields:
            if field not in payload:
                raise TokenError(f"Token missing required field: {field}")
        
        # Validate token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthenticationError("Token has expired")
