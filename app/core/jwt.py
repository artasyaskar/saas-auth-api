"""
JWT token management for secure authentication.

Handles JWT token creation, validation, refresh, and
blacklist management with proper security considerations.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac
from jose import JWTError, jwt, ExpiredSignatureError
from jose.exceptions import JWTClaimsError

from app.core.config import settings
from app.core.exceptions import SecurityError, AuthenticationError


class TokenManager:
    """
    JWT token management with security best practices.
    
    Handles token creation, validation, refresh, and
    blacklist management with proper security considerations.
    """
    
    def __init__(self):
        self.secret_key = settings.security.secret_key
        self.jwt_secret = settings.security.jwt_secret
        self.algorithm = settings.security.jwt_algorithm
        self.access_token_expire_minutes = settings.security.access_token_expire_minutes
        self.refresh_token_expire_days = settings.security.refresh_token_expire_days
        
        # Token blacklist (in production, use Redis)
        self._token_blacklist = set()
        
        # TODO: Add Redis-based blacklist
        # TODO: Add token rotation support
        # TODO: Add device binding
        # TODO: Add token metadata tracking
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Create JWT access token with proper claims.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            scopes: Token permissions/scopes
            
        Returns:
            JWT access token
        """
        try:
            to_encode = data.copy()
            
            # Add standard claims
            now = datetime.utcnow()
            if expires_delta:
                expire = now + expires_delta
            else:
                expire = now + timedelta(minutes=self.access_token_expire_minutes)
            
            to_encode.update({
                "exp": expire,
                "iat": now,
                "nbf": now,
                "iss": settings.app.name,
                "aud": settings.app.name,
                "type": "access",
                "jti": self._generate_jti()
            })
            
            # Add scopes if provided
            if scopes:
                to_encode["scopes"] = scopes
            
            # Create token
            token = jwt.encode(to_encode, self.jwt_secret, algorithm=self.algorithm)
            
            return token
            
        except Exception as e:
            raise SecurityError(f"Failed to create access token: {str(e)}")
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token with proper claims.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            
        Returns:
            JWT refresh token
        """
        try:
            to_encode = data.copy()
            
            # Add standard claims
            now = datetime.utcnow()
            if expires_delta:
                expire = now + expires_delta
            else:
                expire = now + timedelta(days=self.refresh_token_expire_days)
            
            to_encode.update({
                "exp": expire,
                "iat": now,
                "nbf": now,
                "iss": settings.app.name,
                "aud": settings.app.name,
                "type": "refresh",
                "jti": self._generate_jti()
            })
            
            # Create token
            token = jwt.encode(to_encode, self.jwt_secret, algorithm=self.algorithm)
            
            return token
            
        except Exception as e:
            raise SecurityError(f"Failed to create refresh token: {str(e)}")
    
    def verify_token(
        self, 
        token: str, 
        token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access/refresh)
            
        Returns:
            Token payload or None if invalid
            
        Raises:
            AuthenticationError: If token is invalid
            SecurityError: If token is blacklisted
        """
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                raise SecurityError("Token has been revoked")
            
            # Decode token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.algorithm],
                audience=settings.app.name,
                issuer=settings.app.name
            )
            
            # Validate token type
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type. Expected {token_type}")
            
            # Validate expiration (though JWT library does this)
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except JWTClaimsError as e:
            raise AuthenticationError(f"Invalid token claims: {str(e)}")
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except SecurityError:
            raise
        except Exception as e:
            raise SecurityError(f"Token verification failed: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Create new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary with new access token and refresh token
            
        Raises:
            AuthenticationError: If refresh token is invalid
            SecurityError: If security check fails
        """
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token, "refresh")
            
            # Extract user data
            user_data = {
                "sub": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "role": payload.get("role")
            }
            
            # Create new access token
            access_token = self.create_access_token(user_data)
            
            # TODO: Implement token rotation
            # TODO: Revoke old refresh token
            # TODO: Add device binding validation
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,  # Keep same refresh token for now
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }
            
        except (AuthenticationError, SecurityError):
            raise
        except Exception as e:
            raise SecurityError(f"Token refresh failed: {str(e)}")
    
    def blacklist_token(self, token: str, reason: str = "User logout") -> bool:
        """
        Add token to blacklist.
        
        Args:
            token: Token to blacklist
            reason: Reason for blacklisting
            
        Returns:
            True if blacklisted successfully
        """
        try:
            # Get token payload to extract JTI
            payload = self._decode_token_without_validation(token)
            
            if payload and "jti" in payload:
                # Add JTI to blacklist
                self._token_blacklist.add(payload["jti"])
                
                # TODO: Add to Redis with expiration
                # TODO: Log blacklisting event
                # TODO: Add reason tracking
                
                return True
            
            return False
            
        except Exception as e:
            raise SecurityError(f"Failed to blacklist token: {str(e)}")
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            token: Token to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        try:
            # Get token payload to extract JTI
            payload = self._decode_token_without_validation(token)
            
            if payload and "jti" in payload:
                return payload["jti"] in self._token_blacklist
            
            return False
            
        except Exception:
            # If we can't decode, consider it not blacklisted
            return False
    
    def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        # TODO: Implement user-specific token revocation
        # TODO: Add database tracking of active tokens
        # TODO: Add WebSocket notification for token revocation
        
        # For now, this is a placeholder
        return 0
    
    def cleanup_expired_blacklist(self) -> int:
        """
        Clean up expired blacklist entries.
        
        Returns:
            Number of entries cleaned up
        """
        # TODO: Implement cleanup logic
        # TODO: Add automatic cleanup scheduling
        # TODO: Add blacklist size monitoring
        
        # For now, this is a placeholder
        return 0
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Get token information without full validation.
        
        Args:
            token: JWT token
            
        Returns:
            Token information
        """
        try:
            payload = self._decode_token_without_validation(token)
            
            if not payload:
                return {}
            
            return {
                "jti": payload.get("jti"),
                "type": payload.get("type"),
                "sub": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "scopes": payload.get("scopes", []),
                "iat": payload.get("iat"),
                "exp": payload.get("exp"),
                "nbf": payload.get("nbf"),
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "is_expired": datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)),
                "is_blacklisted": self.is_token_blacklisted(token)
            }
            
        except Exception:
            return {}
    
    def validate_token_claims(self, payload: Dict[str, Any]) -> bool:
        """
        Validate token claims for security.
        
        Args:
            payload: Token payload
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required claims
            required_claims = ["exp", "iat", "nbf", "iss", "aud", "type", "jti"]
            
            for claim in required_claims:
                if claim not in payload:
                    return False
            
            # Validate issuer and audience
            if payload.get("iss") != settings.app.name:
                return False
            
            if payload.get("aud") != settings.app.name:
                return False
            
            # Validate token type
            if payload.get("type") not in ["access", "refresh"]:
                return False
            
            # Validate timestamps
            now = datetime.utcnow()
            
            # Not before
            if datetime.fromtimestamp(payload["nbf"]) > now:
                return False
            
            # Expiration
            if datetime.fromtimestamp(payload["exp"]) <= now:
                return False
            
            # TODO: Add additional claim validation
            # TODO: Add scope validation
            # TODO: Add user status validation
            
            return True
            
        except Exception:
            return False
    
    def _generate_jti(self) -> str:
        """
        Generate JWT ID (JTI) for token identification.
        
        Returns:
            Unique JTI string
        """
        return secrets.token_urlsafe(32)
    
    def _decode_token_without_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without signature verification.
        
        Used for extracting JTI and other metadata.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload or None if invalid
        """
        try:
            # Decode without verification
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "verify_aud": False,
                    "verify_iss": False
                }
            )
            
            return payload
            
        except Exception:
            return None
    
    def create_token_pair(
        self, 
        user_data: Dict[str, Any], 
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create access and refresh token pair.
        
        Args:
            user_data: User data for tokens
            scopes: Token permissions/scopes
            
        Returns:
            Dictionary with access and refresh tokens
        """
        try:
            # Create access token
            access_token = self.create_access_token(user_data, scopes=scopes)
            
            # Create refresh token
            refresh_token = self.create_refresh_token(user_data)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "refresh_expires_in": self.refresh_token_expire_days * 24 * 60 * 60
            }
            
        except Exception as e:
            raise SecurityError(f"Failed to create token pair: {str(e)}")
    
    def rotate_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Rotate refresh token for security.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            Dictionary with new refresh token
            
        Raises:
            AuthenticationError: If refresh token is invalid
            SecurityError: If security check fails
        """
        try:
            # Verify current refresh token
            payload = self.verify_token(refresh_token, "refresh")
            
            # Blacklist old refresh token
            self.blacklist_token(refresh_token, "Token rotation")
            
            # Create new refresh token
            user_data = {
                "sub": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "role": payload.get("role")
            }
            
            new_refresh_token = self.create_refresh_token(user_data)
            
            # TODO: Add rotation tracking
            # TODO: Add rotation limits
            # TODO: Add device binding validation
            
            return {
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.refresh_token_expire_days * 24 * 60 * 60
            }
            
        except (AuthenticationError, SecurityError):
            raise
        except Exception as e:
            raise SecurityError(f"Token rotation failed: {str(e)}")


# Global token manager instance
token_manager = TokenManager()


# Convenience functions
def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[List[str]] = None
) -> str:
    """Create JWT access token."""
    return token_manager.create_access_token(data, expires_delta, scopes)


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    return token_manager.create_refresh_token(data, expires_delta)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify JWT token."""
    return token_manager.verify_token(token, token_type)


def blacklist_token(token: str, reason: str = "User logout") -> bool:
    """Add token to blacklist."""
    return token_manager.blacklist_token(token, reason)


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    return token_manager.is_token_blacklisted(token)


def create_token_pair(
    user_data: Dict[str, Any], 
    scopes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create access and refresh token pair."""
    return token_manager.create_token_pair(user_data, scopes)


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Create new access token from refresh token."""
    return token_manager.refresh_access_token(refresh_token)


def get_token_info(token: str) -> Dict[str, Any]:
    """Get token information."""
    return token_manager.get_token_info(token)
