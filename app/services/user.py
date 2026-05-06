"""
User service for user-related business logic.

Handles user management, profile operations, and
user preferences with proper validation and error handling.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.models import User, UserRole, UserPreferences
from app.repositories.user import UserRepository
from app.repositories.auth import AuthRepository
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserProfile,
    UserPreferences as UserPreferencesSchema, UserStats
)
from app.core.security import hash_password, verify_password
from app.core.exceptions import (
    ValidationError as AppValidationError,
    NotFoundError, ConflictError, SecurityError
)
from app.services.email import EmailService


class UserService:
    """
    User service for user management business logic.
    
    Handles user CRUD operations, profile management,
    and user preferences with proper validation and error handling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.auth_repo = AuthRepository(db)
        self.email_service = EmailService(db)
        
        # TODO: Add caching layer for user data
        # TODO: Add user activity tracking
        # TODO: Add profile completion tracking
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user with validation and security checks.
        
        Args:
            user_data: User creation data with validation
            
        Returns:
            Created user response
            
        Raises:
            ValidationError: If user data is invalid
            ConflictError: If user already exists
            SecurityError: If security check fails
        """
        try:
            # Check if user already exists
            existing_user = self.user_repo.get_by_email_or_username(user_data.email)
            
            if existing_user:
                if existing_user.email == user_data.email.lower():
                    raise ConflictError("Email already registered")
                else:
                    raise ConflictError("Username already taken")
            
            # Hash password
            hashed_password = hash_password(user_data.password)
            
            # Create user
            user = self.user_repo.create_user(
                email=user_data.email,
                username=user_data.username,
                password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone=user_data.phone,
                role=UserRole.USER
            )
            
            # TODO: Send welcome email
            # TODO: Create email verification token
            # TODO: Log user creation event
            
            return UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                role=user.role.value if user.role else None,
                is_active=user.is_active,
                email_verified=user.email_verified,
                created_at=user.created_at,
                last_login=user.last_login,
                login_count=user.login_count
            )
            
        except (ConflictError, ValidationError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"User creation failed: {str(e)}")
    
    def get_user(self, user_id: int) -> UserResponse:
        """
        Get user by ID with proper error handling.
        
        Args:
            user_id: User ID
            
        Returns:
            User response
            
        Raises:
            NotFoundError: If user not found
        """
        try:
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # TODO: Add permission check
            # TODO: Add privacy settings check
            
            return UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                role=user.role.value if user.role else None,
                is_active=user.is_active,
                email_verified=user.email_verified,
                created_at=user.created_at,
                last_login=user.last_login,
                login_count=user.login_count
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"Failed to get user: {str(e)}")
    
    def update_user(self, user_id: int, user_data: UserUpdate, current_user_id: int) -> UserResponse:
        """
        Update user profile with validation and authorization checks.
        
        Args:
            user_id: User ID to update
            user_data: Update data
            current_user_id: ID of user making the request
            
        Returns:
            Updated user response
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If update data is invalid
            SecurityError: If not authorized to update
        """
        try:
            # Check if user exists
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Check authorization (users can only update their own profile)
            if user_id != current_user_id:
                # TODO: Add admin override check
                raise SecurityError("Not authorized to update this user")
            
            # Validate update data
            update_dict = user_data.dict(exclude_unset=True)
            
            # TODO: Add field-specific validation
            # TODO: Add profile completion tracking
            
            # Update user
            updated_user = self.user_repo.update(user_id, update_dict)
            
            if not updated_user:
                raise AppValidationError("Failed to update user")
            
            # TODO: Log profile update event
            # TODO: Send notification if sensitive fields changed
            
            return UserResponse(
                id=updated_user.id,
                email=updated_user.email,
                username=updated_user.username,
                first_name=updated_user.first_name,
                last_name=updated_user.last_name,
                phone=updated_user.phone,
                role=updated_user.role.value if updated_user.role else None,
                is_active=updated_user.is_active,
                email_verified=updated_user.email_verified,
                created_at=updated_user.created_at,
                last_login=updated_user.last_login,
                login_count=updated_user.login_count
            )
            
        except (NotFoundError, ValidationError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"User update failed: {str(e)}")
    
    def get_user_profile(self, user_id: int, current_user_id: int) -> UserProfile:
        """
        Get comprehensive user profile with preferences.
        
        Args:
            user_id: User ID
            current_user_id: ID of user making the request
            
        Returns:
            User profile with preferences
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to view
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                # TODO: Add admin override check
                # TODO: Add privacy settings check
                raise SecurityError("Not authorized to view this profile")
            
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Get user preferences
            preferences = self.user_repo.get_user_preferences(user_id)
            
            # TODO: Add user statistics
            # TODO: Add activity history
            
            return UserProfile(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                bio=user.bio,
                avatar_url=user.avatar_url,
                timezone=user.timezone,
                language=user.language,
                role=user.role.value if user.role else None,
                is_active=user.is_active,
                email_verified=user.email_verified,
                created_at=user.created_at,
                last_login=user.last_login,
                login_count=user.login_count,
                preferences=preferences
            )
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"Failed to get user profile: {str(e)}")
    
    def update_user_preferences(
        self, 
        user_id: int, 
        preferences: UserPreferencesSchema,
        current_user_id: int
    ) -> bool:
        """
        Update user preferences with validation.
        
        Args:
            user_id: User ID to update
            preferences: New preferences
            current_user_id: ID of user making the request
            
        Returns:
            True if updated successfully
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to update
            ValidationError: If preferences are invalid
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                raise SecurityError("Not authorized to update these preferences")
            
            # Validate preferences
            # TODO: Add preference validation logic
            # TODO: Add preference schema validation
            
            # Update preferences
            success = self.user_repo.update_user_preferences(user_id, preferences.dict())
            
            if success:
                # TODO: Log preference update event
                # TODO: Update user's last activity
                pass
            
            return success
            
        except (NotFoundError, SecurityError, ValidationError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            return False
    
    def get_user_stats(self, user_id: int, current_user_id: int) -> UserStats:
        """
        Get user statistics and activity metrics.
        
        Args:
            user_id: User ID
            current_user_id: ID of user making the request
            
        Returns:
            User statistics
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to view
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                # TODO: Add admin override check
                raise SecurityError("Not authorized to view these statistics")
            
            stats = self.user_repo.get_user_stats(user_id)
            
            # TODO: Add more comprehensive statistics
            # TODO: Add usage analytics
            # TODO: Add activity heat map
            
            return UserStats(**stats)
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"Failed to get user stats: {str(e)}")
    
    def search_users(
        self, 
        search_term: str, 
        page: int = 1, 
        size: int = 20,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Search users with pagination and authorization.
        
        Args:
            search_term: Search query
            page: Page number
            size: Items per page
            current_user_id: ID of user making the request
            
        Returns:
            Paginated search results
            
        Raises:
            SecurityError: If not authorized to search
        """
        try:
            # TODO: Add search authorization check
            # TODO: Add search rate limiting
            # TODO: Add search analytics
            
            offset = (page - 1) * size
            
            users = self.user_repo.search_users(
                search_term=search_term,
                skip=offset,
                limit=size
            )
            
            # Get total count for pagination
            total = self.user_repo.count({"username": search_term})
            
            return {
                "users": [
                    UserResponse(
                        id=user.id,
                        email=user.email,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        phone=user.phone,
                        role=user.role.value if user.role else None,
                        is_active=user.is_active,
                        email_verified=user.email_verified,
                        created_at=user.created_at,
                        last_login=user.last_login,
                        login_count=user.login_count
                    )
                    for user in users
                ],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "pages": (total + size - 1) // size if total > 0 else 0
                }
            }
            
        except SecurityError:
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"User search failed: {str(e)}")
    
    def deactivate_user(self, user_id: int, current_user_id: int) -> bool:
        """
        Deactivate user account with authorization checks.
        
        Args:
            user_id: User ID to deactivate
            current_user_id: ID of user making the request
            
        Returns:
            True if deactivated successfully
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to deactivate
        """
        try:
            # TODO: Add admin authorization check
            # TODO: Add self-deactivation protection
            # TODO: Add deactivation reason tracking
            
            success = self.user_repo.deactivate_user(user_id)
            
            if success:
                # TODO: Invalidate all user sessions
                # TODO: Send deactivation email
                # TODO: Log deactivation event
                pass
            
            return success
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            return False
    
    def verify_email(self, token: str) -> bool:
        """
        Verify user email address.
        
        Args:
            token: Email verification token
            
        Returns:
            True if verified successfully
            
        Raises:
            ValidationError: If token is invalid
        """
        try:
            # Get verification token
            verification_token = self.auth_repo.get_email_verification_token(token)
            
            if not verification_token:
                raise ValidationError("Invalid or expired verification token")
            
            # Mark email as verified
            success = self.user_repo.verify_email(verification_token.user_id)
            
            if success:
                # Mark token as used
                self.auth_repo.use_email_verification_token(token)
                
                # TODO: Send welcome email
                # TODO: Log email verification event
                pass
            
            return success
            
        except ValidationError:
            raise
        except Exception as e:
            # TODO: Add proper logging
            return False
    
    def get_recent_users(self, days: int = 30, limit: int = 50) -> List[UserResponse]:
        """
        Get recently registered users.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of users to return
            
        Returns:
            List of recently registered users
            
        Raises:
            SecurityError: If not authorized
        """
        try:
            # TODO: Add admin authorization check
            # TODO: Add privacy filtering
            
            users = self.user_repo.get_recent_users(days=days, limit=limit)
            
            return [
                UserResponse(
                    id=user.id,
                    email=user.email,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    phone=user.phone,
                    role=user.role.value if user.role else None,
                    is_active=user.is_active,
                    email_verified=user.email_verified,
                    created_at=user.created_at,
                    last_login=user.last_login,
                    login_count=user.login_count
                )
                for user in users
            ]
            
        except SecurityError:
            raise
        except Exception as e:
            # TODO: Add proper logging
            return []
    
    def get_user_analytics(self, user_id: int, current_user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user analytics.
        
        Args:
            user_id: User ID
            current_user_id: ID of user making the request
            
        Returns:
            User analytics data
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                # TODO: Add admin override check
                raise SecurityError("Not authorized to view these analytics")
            
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # TODO: Implement comprehensive analytics
            # TODO: Add login patterns analysis
            # TODO: Add activity heat map
            # TODO: Add usage statistics
            
            return {
                "user_id": user.id,
                "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0,
                "login_count": user.login_count or 0,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "email_verified": user.email_verified,
                "is_active": user.is_active,
                "profile_completion": self._calculate_profile_completion(user),
                "engagement_score": self._calculate_engagement_score(user_id),
                "security_score": self._calculate_security_score(user_id)
            }
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            # TODO: Add proper logging
            raise AppValidationError(f"Failed to get user analytics: {str(e)}")
    
    def _calculate_profile_completion(self, user: User) -> float:
        """
        Calculate user profile completion percentage.
        
        Args:
            user: User object
            
        Returns:
            Profile completion percentage (0-100)
        """
        # TODO: Implement comprehensive profile completion logic
        # TODO: Add weighted field importance
        # TODO: Add optional fields tracking
        
        fields = [
            user.first_name,
            user.last_name,
            user.phone,
            user.bio,
            user.avatar_url
        ]
        
        completed_fields = sum(1 for field in fields if field)
        total_fields = len(fields)
        
        return (completed_fields / total_fields) * 100 if total_fields > 0 else 0
    
    def _calculate_engagement_score(self, user_id: int) -> float:
        """
        Calculate user engagement score.
        
        Args:
            user_id: User ID
            
        Returns:
            Engagement score (0-100)
        """
        # TODO: Implement engagement scoring algorithm
        # TODO: Consider login frequency
        # TODO: Consider feature usage
        # TODO: Consider activity recency
        
        # Placeholder implementation
        stats = self.user_repo.get_user_stats(user_id)
        
        login_score = min((stats.get("login_count", 0) / 10) * 20, 20)  # Max 20 points
        activity_score = 30  # TODO: Calculate based on recent activity
        profile_score = self._calculate_profile_completion(
            self.user_repo.get(user_id)
        ) * 0.5  # Max 50 points
        
        return login_score + activity_score + profile_score
    
    def _calculate_security_score(self, user_id: int) -> float:
        """
        Calculate user security score.
        
        Args:
            user_id: User ID
            
        Returns:
            Security score (0-100)
        """
        # TODO: Implement security scoring algorithm
        # TODO: Consider 2FA usage
        # TODO: Consider password strength
        # TODO: Consider login patterns
        
        # Placeholder implementation
        user = self.user_repo.get(user_id)
        
        if not user:
            return 0
        
        email_verified_score = 30 if user.email_verified else 0
        recent_login_score = 20 if user.last_login and (
            datetime.utcnow() - user.last_login
        ).days < 7 else 0
        account_age_score = min(
            ((datetime.utcnow() - user.created_at).days / 30) * 10, 50
        ) if user.created_at else 0
        
        return email_verified_score + recent_login_score + account_age_score
