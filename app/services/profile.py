"""
User profile service for comprehensive profile management.

Handles user profiles, preferences, activity tracking,
and profile completion with proper validation and security.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.db.models import User, UserProfile, UserPreferences, UserActivity
from app.repositories.user import UserRepository
from app.schemas.user import UserPreferences as UserPreferencesSchema
from app.core.config import settings
from app.core.exceptions import (
    ValidationError, NotFoundError, SecurityError,
    DatabaseError
)


class ProfileService:
    """
    User profile service for comprehensive profile management.
    
    Handles user profiles, preferences, activity tracking,
    and profile completion with proper validation and security.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        
        # TODO: Add profile caching
        # TODO: Add profile image handling
        # TODO: Add profile completion tracking
        # TODO: Add social profile integration
    
    def get_user_profile(
        self, 
        user_id: int, 
        include_private: bool = False,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive user profile.
        
        Args:
            user_id: User ID to get profile for
            include_private: Whether to include private fields
            current_user_id: ID of user making request
            
        Returns:
            User profile data
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to view profile
        """
        try:
            # Check authorization for private fields
            if include_private and user_id != current_user_id:
                # TODO: Add admin override check
                include_private = False
            
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Get profile data
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            # Get preferences
            preferences = self.user_repo.get_user_preferences(user_id)
            
            # Build profile response
            profile_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone if include_private else None,
                "bio": profile.bio if profile else None,
                "avatar_url": profile.avatar_url if profile else None,
                "timezone": profile.timezone if profile else None,
                "language": profile.language if profile else None,
                "website": profile.website if profile else None,
                "location": profile.location if profile else None,
                "company": profile.company if profile else None,
                "job_title": profile.job_title if profile else None,
                "social_links": profile.social_links if profile else {},
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "email_verified": user.email_verified,
                "is_active": user.is_active,
                "preferences": preferences if include_private else self._sanitize_preferences(preferences),
                "profile_completion": self._calculate_profile_completion(user, profile),
                "privacy_settings": self._get_privacy_settings(user_id) if include_private else {}
            }
            
            # Add public-only fields for non-owners
            if not include_private:
                profile_data = self._sanitize_profile_data(profile_data)
            
            return profile_data
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get user profile: {str(e)}")
    
    def update_user_profile(
        self, 
        user_id: int, 
        profile_data: Dict[str, Any],
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Update user profile with validation.
        
        Args:
            user_id: User ID to update
            profile_data: Profile data to update
            current_user_id: ID of user making request
            
        Returns:
            Updated profile data
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If profile data is invalid
            SecurityError: If not authorized to update
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                # TODO: Add admin override check
                raise SecurityError("Not authorized to update this profile")
            
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Validate profile data
            self._validate_profile_data(profile_data)
            
            # Get or create profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                self.db.add(profile)
            
            # Update profile fields
            updatable_fields = [
                'bio', 'avatar_url', 'timezone', 'language',
                'website', 'location', 'company', 'job_title',
                'social_links'
            ]
            
            for field in updatable_fields:
                if field in profile_data:
                    setattr(profile, field, profile_data[field])
            
            profile.updated_at = datetime.utcnow()
            
            # Update user fields
            user_updatable_fields = ['first_name', 'last_name', 'phone']
            
            for field in user_updatable_fields:
                if field in profile_data:
                    setattr(user, field, profile_data[field])
            
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(profile)
            
            # Log activity
            self._log_user_activity(user_id, "profile_updated", {
                "fields_updated": list(profile_data.keys())
            })
            
            return self.get_user_profile(user_id, include_private=True, current_user_id=current_user_id)
            
        except (NotFoundError, ValidationError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to update user profile: {str(e)}")
    
    def update_user_preferences(
        self, 
        user_id: int, 
        preferences: Dict[str, Any],
        current_user_id: int
    ) -> bool:
        """
        Update user preferences with validation.
        
        Args:
            user_id: User ID to update
            preferences: Preferences to update
            current_user_id: ID of user making request
            
        Returns:
            True if updated successfully
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If preferences are invalid
            SecurityError: If not authorized to update
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                raise SecurityError("Not authorized to update these preferences")
            
            # Validate preferences
            self._validate_preferences(preferences)
            
            # Update preferences
            success = self.user_repo.update_user_preferences(user_id, preferences)
            
            if success:
                # Log activity
                self._log_user_activity(user_id, "preferences_updated", {
                    "preferences_updated": list(preferences.keys())
                })
            
            return success
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update user preferences: {str(e)}")
    
    def update_privacy_settings(
        self, 
        user_id: int, 
        privacy_settings: Dict[str, Any],
        current_user_id: int
    ) -> bool:
        """
        Update user privacy settings.
        
        Args:
            user_id: User ID to update
            privacy_settings: Privacy settings to update
            current_user_id: ID of user making request
            
        Returns:
            True if updated successfully
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If privacy settings are invalid
            SecurityError: If not authorized to update
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                raise SecurityError("Not authorized to update privacy settings")
            
            # Validate privacy settings
            self._validate_privacy_settings(privacy_settings)
            
            # Get or create privacy settings record
            # TODO: Add privacy settings model
            # TODO: Store privacy settings in database
            # TODO: Add privacy settings validation
            
            # Log activity
            self._log_user_activity(user_id, "privacy_updated", {
                "settings_updated": list(privacy_settings.keys())
            })
            
            return True
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update privacy settings: {str(e)}")
    
    def upload_avatar(
        self, 
        user_id: int, 
        avatar_data: bytes,
        content_type: str,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Upload user avatar with validation and processing.
        
        Args:
            user_id: User ID to upload avatar for
            avatar_data: Avatar image data
            content_type: Image content type
            current_user_id: ID of user making request
            
        Returns:
            Avatar upload result
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If avatar is invalid
            SecurityError: If not authorized to upload
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                raise SecurityError("Not authorized to upload avatar for this user")
            
            # Validate avatar data
            self._validate_avatar_data(avatar_data, content_type)
            
            # TODO: Implement image processing
            # TODO: Add image storage (S3, local, etc.)
            # TODO: Add image optimization
            # TODO: Add image format conversion
            
            # Generate avatar URL
            avatar_url = f"/avatars/{user_id}_{datetime.utcnow().timestamp()}.{content_type.split('/')[-1]}"
            
            # Update profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                self.db.add(profile)
            
            profile.avatar_url = avatar_url
            profile.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log activity
            self._log_user_activity(user_id, "avatar_uploaded", {
                "content_type": content_type,
                "size": len(avatar_data)
            })
            
            return {
                "avatar_url": avatar_url,
                "size": len(avatar_data),
                "content_type": content_type
            }
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to upload avatar: {str(e)}")
    
    def get_user_activity(
        self, 
        user_id: int, 
        limit: int = 50,
        offset: int = 0,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Get user activity history.
        
        Args:
            user_id: User ID to get activity for
            limit: Maximum number of activities
            offset: Number of activities to skip
            current_user_id: ID of user making request
            
        Returns:
            User activity data
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to view activity
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                # TODO: Add admin override check
                raise SecurityError("Not authorized to view this user's activity")
            
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Get activities
            activities = self.db.query(UserActivity).filter(
                UserActivity.user_id == user_id
            ).order_by(desc(UserActivity.created_at)).offset(offset).limit(limit).all()
            
            # Get total count
            total = self.db.query(UserActivity).filter(
                UserActivity.user_id == user_id
            ).count()
            
            return {
                "activities": [
                    {
                        "id": activity.id,
                        "action": activity.action,
                        "resource_type": activity.resource_type,
                        "resource_id": activity.resource_id,
                        "ip_address": activity.ip_address,
                        "user_agent": activity.user_agent,
                        "metadata": activity.metadata,
                        "created_at": activity.created_at.isoformat() if activity.created_at else None
                    }
                    for activity in activities
                ],
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total
                }
            }
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get user activity: {str(e)}")
    
    def get_profile_analytics(
        self, 
        user_id: int, 
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Get user profile analytics and insights.
        
        Args:
            user_id: User ID to get analytics for
            current_user_id: ID of user making request
            
        Returns:
            Profile analytics data
            
        Raises:
            NotFoundError: If user not found
            SecurityError: If not authorized to view analytics
        """
        try:
            # Check authorization
            if user_id != current_user_id:
                raise SecurityError("Not authorized to view profile analytics")
            
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Get profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            # Calculate analytics
            analytics = {
                "profile_completion": self._calculate_profile_completion(user, profile),
                "engagement_score": self._calculate_engagement_score(user_id),
                "activity_summary": self._get_activity_summary(user_id),
                "profile_strength": self._calculate_profile_strength(user, profile),
                "recommendations": self._get_profile_recommendations(user, profile)
            }
            
            return analytics
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get profile analytics: {str(e)}")
    
    def _validate_profile_data(self, profile_data: Dict[str, Any]):
        """
        Validate profile data.
        
        Args:
            profile_data: Profile data to validate
            
        Raises:
            ValidationError: If data is invalid
        """
        errors = []
        
        # Validate bio
        if 'bio' in profile_data:
            bio = profile_data['bio']
            if bio and len(bio) > 500:
                errors.append("Bio must be less than 500 characters")
        
        # Validate website
        if 'website' in profile_data:
            website = profile_data['website']
            if website and not self._is_valid_url(website):
                errors.append("Invalid website URL")
        
        # Validate timezone
        if 'timezone' in profile_data:
            timezone = profile_data['timezone']
            if timezone and not self._is_valid_timezone(timezone):
                errors.append("Invalid timezone")
        
        # Validate language
        if 'language' in profile_data:
            language = profile_data['language']
            if language and len(language) > 10:
                errors.append("Language code must be less than 10 characters")
        
        if errors:
            raise ValidationError("Profile validation failed", errors=errors)
    
    def _validate_preferences(self, preferences: Dict[str, Any]):
        """
        Validate user preferences.
        
        Args:
            preferences: Preferences to validate
            
        Raises:
            ValidationError: If preferences are invalid
        """
        errors = []
        
        # Validate theme
        if 'theme' in preferences:
            theme = preferences['theme']
            if theme not in ['light', 'dark', 'auto']:
                errors.append("Invalid theme preference")
        
        # Validate language
        if 'language' in preferences:
            language = preferences['language']
            if language and len(language) > 10:
                errors.append("Language code must be less than 10 characters")
        
        # Validate timezone
        if 'timezone' in preferences:
            timezone = preferences['timezone']
            if timezone and not self._is_valid_timezone(timezone):
                errors.append("Invalid timezone")
        
        if errors:
            raise ValidationError("Preferences validation failed", errors=errors)
    
    def _validate_privacy_settings(self, privacy_settings: Dict[str, Any]):
        """
        Validate privacy settings.
        
        Args:
            privacy_settings: Privacy settings to validate
            
        Raises:
            ValidationError: If privacy settings are invalid
        """
        errors = []
        
        # Validate profile visibility
        if 'profile_visibility' in privacy_settings:
            visibility = privacy_settings['profile_visibility']
            if visibility not in ['public', 'private', 'friends']:
                errors.append("Invalid profile visibility setting")
        
        if errors:
            raise ValidationError("Privacy settings validation failed", errors=errors)
    
    def _validate_avatar_data(self, avatar_data: bytes, content_type: str):
        """
        Validate avatar image data.
        
        Args:
            avatar_data: Avatar image data
            content_type: Image content type
            
        Raises:
            ValidationError: If avatar data is invalid
        """
        errors = []
        
        # Check file size
        max_size = 5 * 1024 * 1024  # 5MB
        if len(avatar_data) > max_size:
            errors.append("Avatar must be less than 5MB")
        
        # Check content type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in allowed_types:
            errors.append("Avatar must be a valid image format")
        
        if errors:
            raise ValidationError("Avatar validation failed", errors=errors)
    
    def _calculate_profile_completion(self, user: User, profile: Optional[UserProfile]) -> float:
        """
        Calculate profile completion percentage.
        
        Args:
            user: User object
            profile: User profile object
            
        Returns:
            Profile completion percentage (0-100)
        """
        fields = []
        
        # User fields
        if user.first_name:
            fields.append('first_name')
        if user.last_name:
            fields.append('last_name')
        if user.phone:
            fields.append('phone')
        
        # Profile fields
        if profile:
            if profile.bio:
                fields.append('bio')
            if profile.avatar_url:
                fields.append('avatar_url')
            if profile.timezone:
                fields.append('timezone')
            if profile.language:
                fields.append('language')
            if profile.website:
                fields.append('website')
            if profile.location:
                fields.append('location')
        
        total_fields = 10  # Expected total fields
        completed_fields = len(fields)
        
        return (completed_fields / total_fields) * 100
    
    def _calculate_engagement_score(self, user_id: int) -> float:
        """
        Calculate user engagement score.
        
        Args:
            user_id: User ID
            
        Returns:
            Engagement score (0-100)
        """
        # TODO: Implement comprehensive engagement scoring
        # TODO: Consider login frequency
        # TODO: Consider activity patterns
        # TODO: Consider feature usage
        
        # Placeholder implementation
        return 75.0
    
    def _get_activity_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get user activity summary.
        
        Args:
            user_id: User ID
            
        Returns:
            Activity summary
        """
        # TODO: Implement activity summary calculation
        # TODO: Add activity heat map
        # TODO: Add activity patterns
        
        return {
            "total_activities": 0,
            "recent_activities": 0,
            "most_active_day": None,
            "activity_streak": 0
        }
    
    def _calculate_profile_strength(self, user: User, profile: Optional[UserProfile]) -> float:
        """
        Calculate profile strength score.
        
        Args:
            user: User object
            profile: User profile object
            
        Returns:
            Profile strength score (0-100)
        """
        # TODO: Implement profile strength calculation
        # TODO: Consider verification status
        # TODO: Consider profile completeness
        # TODO: Consider account age
        
        return 80.0
    
    def _get_profile_recommendations(self, user: User, profile: Optional[UserProfile]) -> List[str]:
        """
        Get profile improvement recommendations.
        
        Args:
            user: User object
            profile: User profile object
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check profile completion
        completion = self._calculate_profile_completion(user, profile)
        if completion < 80:
            recommendations.append("Complete your profile to increase visibility")
        
        # Check email verification
        if not user.email_verified:
            recommendations.append("Verify your email address")
        
        # Check avatar
        if not profile or not profile.avatar_url:
            recommendations.append("Add a profile picture")
        
        # Check bio
        if not profile or not profile.bio:
            recommendations.append("Add a bio to your profile")
        
        return recommendations
    
    def _sanitize_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize profile data for public viewing.
        
        Args:
            profile_data: Profile data to sanitize
            
        Returns:
            Sanitized profile data
        """
        # Remove private fields
        private_fields = ['phone', 'email', 'preferences', 'privacy_settings']
        
        sanitized = profile_data.copy()
        for field in private_fields:
            if field in sanitized:
                del sanitized[field]
        
        return sanitized
    
    def _sanitize_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize preferences for public viewing.
        
        Args:
            preferences: Preferences to sanitize
            
        Returns:
            Sanitized preferences
        """
        # Remove sensitive preferences
        sensitive_fields = ['email_notifications', 'push_notifications', 'marketing_emails']
        
        sanitized = preferences.copy()
        for field in sensitive_fields:
            if field in sanitized:
                del sanitized[field]
        
        return sanitized
    
    def _get_privacy_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Get user privacy settings.
        
        Args:
            user_id: User ID
            
        Returns:
            Privacy settings
        """
        # TODO: Implement privacy settings retrieval
        # TODO: Add privacy settings model
        # TODO: Add default privacy settings
        
        return {
            "profile_visibility": "public",
            "show_email": False,
            "show_phone": False,
            "allow_messages": True
        }
    
    def _log_user_activity(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """
        Log user activity.
        
        Args:
            user_id: User ID
            action: Activity action
            metadata: Activity metadata
        """
        try:
            activity = UserActivity(
                user_id=user_id,
                action=action,
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            
            self.db.add(activity)
            self.db.commit()
            
        except Exception:
            # Don't fail the main operation if activity logging fails
            pass
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
    
    def _is_valid_timezone(self, timezone: str) -> bool:
        """
        Validate timezone string.
        
        Args:
            timezone: Timezone to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            import pytz
            pytz.timezone(timezone)
            return True
        except:
            return False


# Service factory function
def get_profile_service(db: Session) -> ProfileService:
    """
    Get profile service instance.
    
    Args:
        db: Database session
        
    Returns:
        ProfileService instance
    """
    return ProfileService(db)
