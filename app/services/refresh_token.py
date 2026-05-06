"""
Refresh token service for secure token rotation.

Handles refresh token creation, rotation, validation,
and lifecycle management with proper security considerations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib

from sqlalchemy.orm import Session
from app.db.models import RefreshToken
from app.core.config import settings
from app.core.exceptions import SecurityError, AuthenticationError, DatabaseError


class RefreshTokenService:
    """
    Refresh token service with rotation support.
    
    Handles refresh token creation, rotation, validation,
    and lifecycle management with proper security considerations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # TODO: Add Redis caching for refresh tokens
        # TODO: Add device binding support
        # TODO: Add token usage tracking
        # TODO: Add rotation limits
    
    def create_refresh_token(
        self,
        user_id: int,
        device_id: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> Optional[RefreshToken]:
        """
        Create a new refresh token.
        
        Args:
            user_id: User ID
            device_id: Device identifier for binding
            expires_days: Custom expiration in days
            
        Returns:
            RefreshToken instance or None if failed
            
        Raises:
            SecurityError: If token creation fails
        """
        try:
            # Check user's existing refresh tokens
            existing_tokens = self._get_user_active_tokens(user_id)
            max_tokens = settings.security.max_sessions_per_user
            
            if len(existing_tokens) >= max_tokens:
                # Revoke oldest token
                self._revoke_oldest_token(user_id)
            
            # Generate secure token
            token = self._generate_secure_token()
            token_hash = self._hash_token(token)
            
            # Set expiration
            if not expires_days:
                expires_days = settings.security.refresh_token_expire_days
            
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # Create refresh token record
            refresh_token = RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                device_id=device_id,
                expires_at=expires_at,
                is_active=True,
                created_at=datetime.utcnow(),
                last_used_at=None,
                usage_count=0
            )
            
            self.db.add(refresh_token)
            self.db.commit()
            self.db.refresh(refresh_token)
            
            # Store the actual token temporarily for return
            refresh_token.token = token
            
            return refresh_token
            
        except Exception as e:
            self.db.rollback()
            raise SecurityError(f"Failed to create refresh token: {str(e)}")
    
    def validate_refresh_token(
        self,
        token: str,
        device_id: Optional[str] = None
    ) -> Optional[RefreshToken]:
        """
        Validate refresh token and return token record.
        
        Args:
            token: Refresh token to validate
            device_id: Expected device ID for binding
            
        Returns:
            RefreshToken instance or None if invalid
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Hash the token for comparison
            token_hash = self._hash_token(token)
            
            # Find token in database
            refresh_token = self.db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_active == True
            ).first()
            
            if not refresh_token:
                raise AuthenticationError("Invalid refresh token")
            
            # Check expiration
            if datetime.utcnow() > refresh_token.expires_at:
                self._revoke_token(refresh_token.id, "Token expired")
                raise AuthenticationError("Refresh token has expired")
            
            # Check device binding if provided
            if device_id and refresh_token.device_id and refresh_token.device_id != device_id:
                raise AuthenticationError("Token is bound to different device")
            
            # Check rotation requirements
            if self._should_rotate_token(refresh_token):
                # Mark for rotation
                refresh_token.needs_rotation = True
            
            return refresh_token
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise SecurityError(f"Token validation failed: {str(e)}")
    
    def rotate_refresh_token(
        self,
        old_token: str,
        device_id: Optional[str] = None
    ) -> Optional[RefreshToken]:
        """
        Rotate refresh token for security.
        
        Args:
            old_token: Current refresh token
            device_id: Device identifier
            
        Returns:
            New RefreshToken instance or None if failed
            
        Raises:
            AuthenticationError: If old token is invalid
            SecurityError: If rotation fails
        """
        try:
            # Validate old token
            old_refresh_token = self.validate_refresh_token(old_token, device_id)
            
            if not old_refresh_token:
                raise AuthenticationError("Invalid refresh token for rotation")
            
            # Revoke old token
            self._revoke_token(old_refresh_token.id, "Token rotation")
            
            # Create new token
            new_token = self.create_refresh_token(
                user_id=old_refresh_token.user_id,
                device_id=old_refresh_token.device_id,
                expires_days=settings.security.refresh_token_expire_days
            )
            
            # Update usage statistics
            old_refresh_token.last_used_at = datetime.utcnow()
            old_refresh_token.usage_count += 1
            self.db.commit()
            
            # TODO: Log rotation event
            # TODO: Add rotation tracking
            # TODO: Add rotation limits
            
            return new_token
            
        except (AuthenticationError, SecurityError):
            raise
        except Exception as e:
            raise SecurityError(f"Token rotation failed: {str(e)}")
    
    def revoke_refresh_token(
        self,
        token: str,
        reason: str = "User logout"
    ) -> bool:
        """
        Revoke a specific refresh token.
        
        Args:
            token: Refresh token to revoke
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
        """
        try:
            token_hash = self._hash_token(token)
            
            refresh_token = self.db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_active == True
            ).first()
            
            if not refresh_token:
                return False
            
            return self._revoke_token(refresh_token.id, reason)
            
        except Exception as e:
            raise SecurityError(f"Failed to revoke token: {str(e)}")
    
    def revoke_user_tokens(
        self,
        user_id: int,
        reason: str = "User request"
    ) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            
        Returns:
            Number of tokens revoked
        """
        try:
            tokens = self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_active == True
            ).all()
            
            revoked_count = 0
            for token in tokens:
                if self._revoke_token(token.id, reason):
                    revoked_count += 1
            
            return revoked_count
            
        except Exception as e:
            raise SecurityError(f"Failed to revoke user tokens: {str(e)}")
    
    def revoke_device_tokens(
        self,
        device_id: str,
        reason: str = "Device compromise"
    ) -> int:
        """
        Revoke all tokens for a specific device.
        
        Args:
            device_id: Device identifier
            reason: Reason for revocation
            
        Returns:
            Number of tokens revoked
        """
        try:
            tokens = self.db.query(RefreshToken).filter(
                RefreshToken.device_id == device_id,
                RefreshToken.is_active == True
            ).all()
            
            revoked_count = 0
            for token in tokens:
                if self._revoke_token(token.id, reason):
                    revoked_count += 1
            
            return revoked_count
            
        except Exception as e:
            raise SecurityError(f"Failed to revoke device tokens: {str(e)}")
    
    def get_user_tokens(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all refresh tokens for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active tokens
            
        Returns:
            List of token information
        """
        try:
            query = self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id
            )
            
            if active_only:
                query = query.filter(RefreshToken.is_active == True)
            
            tokens = query.order_by(desc(RefreshToken.created_at)).all()
            
            return [
                {
                    "id": token.id,
                    "device_id": token.device_id,
                    "created_at": token.created_at.isoformat() if token.created_at else None,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "usage_count": token.usage_count,
                    "is_active": token.is_active,
                    "is_expired": datetime.utcnow() > token.expires_at if token.expires_at else False
                }
                for token in tokens
            ]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user tokens: {str(e)}")
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired refresh tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            expired_tokens = self.db.query(RefreshToken).filter(
                RefreshToken.expires_at < datetime.utcnow(),
                RefreshToken.is_active == True
            ).all()
            
            cleaned_count = 0
            for token in expired_tokens:
                if self._revoke_token(token.id, "Token expired"):
                    cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to cleanup expired tokens: {str(e)}")
    
    def get_token_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get refresh token statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with token statistics
        """
        try:
            tokens = self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id
            ).all()
            
            active_tokens = [t for t in tokens if t.is_active and not self._is_expired(t)]
            expired_tokens = [t for t in tokens if self._is_expired(t)]
            revoked_tokens = [t for t in tokens if not t.is_active]
            
            total_usage = sum(t.usage_count for t in tokens)
            recent_usage = sum(
                1 for t in tokens 
                if t.last_used_at and (datetime.utcnow() - t.last_used_at).days <= 7
            )
            
            return {
                "total_tokens": len(tokens),
                "active_tokens": len(active_tokens),
                "expired_tokens": len(expired_tokens),
                "revoked_tokens": len(revoked_tokens),
                "total_usage": total_usage,
                "recent_usage": recent_usage,
                "max_tokens_allowed": settings.security.max_sessions_per_user,
                "tokens_at_limit": len(active_tokens) >= settings.security.max_sessions_per_user
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get token statistics: {str(e)}")
    
    def _get_user_active_tokens(self, user_id: int) -> List[RefreshToken]:
        """
        Get active refresh tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active refresh tokens
        """
        return self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_active == True,
            RefreshToken.expires_at > datetime.utcnow()
        ).all()
    
    def _revoke_oldest_token(self, user_id: int) -> bool:
        """
        Revoke the oldest active token for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if revoked successfully
        """
        try:
            oldest_token = self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_active == True
            ).order_by(RefreshToken.created_at).first()
            
            if oldest_token:
                return self._revoke_token(oldest_token.id, "Token limit exceeded")
            
            return False
            
        except Exception:
            return False
    
    def _revoke_token(self, token_id: int, reason: str) -> bool:
        """
        Revoke a specific refresh token by ID.
        
        Args:
            token_id: Token ID
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
        """
        try:
            token = self.db.query(RefreshToken).filter(
                RefreshToken.id == token_id
            ).first()
            
            if not token:
                return False
            
            token.is_active = False
            token.revoked_at = datetime.utcnow()
            token.revocation_reason = reason
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    def _should_rotate_token(self, token: RefreshToken) -> bool:
        """
        Check if token should be rotated based on usage and age.
        
        Args:
            token: Refresh token to check
            
        Returns:
            True if rotation is recommended
        """
        # Rotate based on usage count
        if token.usage_count >= 10:
            return True
        
        # Rotate based on age (30 days)
        if token.created_at:
            age_days = (datetime.utcnow() - token.created_at).days
            if age_days >= 30:
                return True
        
        # Rotate based on last usage (7 days)
        if token.last_used_at:
            days_since_use = (datetime.utcnow() - token.last_used_at).days
            if days_since_use >= 7:
                return True
        
        return False
    
    def _is_expired(self, token: RefreshToken) -> bool:
        """
        Check if token is expired.
        
        Args:
            token: Refresh token to check
            
        Returns:
            True if expired, False otherwise
        """
        if not token.expires_at:
            return False
        
        return datetime.utcnow() > token.expires_at
    
    def _generate_secure_token(self) -> str:
        """
        Generate a cryptographically secure random token.
        
        Returns:
            Secure random token
        """
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """
        Hash token for secure storage.
        
        Args:
            token: Token to hash
            
        Returns:
            Hashed token
        """
        return hashlib.sha256(token.encode()).hexdigest()


# Service factory function
def get_refresh_token_service(db: Session) -> RefreshTokenService:
    """
    Get refresh token service instance.
    
    Args:
        db: Database session
        
    Returns:
        RefreshTokenService instance
    """
    return RefreshTokenService(db)
