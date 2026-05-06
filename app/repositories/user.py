"""
User repository for user-related database operations.

Handles all user data access including authentication,
profile management, and user preferences.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import User, UserRole, UserPreferences
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository for user database operations.
    
    Provides methods for user CRUD operations, authentication,
    and user management functionality.
    """
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        return self.get_by_field("email", email.lower())
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User instance or None if not found
        """
        return self.get_by_field("username", username)
    
    def get_by_email_or_username(self, identifier: str) -> Optional[User]:
        """
        Get user by email or username.
        
        Args:
            identifier: Email or username
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(
            or_(
                User.email == identifier.lower(),
                User.username == identifier
            )
        ).first()
    
    def create_user(
        self, 
        email: str, 
        username: str, 
        password: str,
        role: UserRole = UserRole.USER,
        **kwargs
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email address
            username: Username
            password: Plain text password
            role: User role
            **kwargs: Additional user fields
            
        Returns:
            Created user instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        # TODO: Add email validation before creation
        # TODO: Add username availability check
        # TODO: Add password strength validation
        
        user_data = {
            "email": email.lower(),
            "username": username,
            "role": role,
            "is_active": True,
            "email_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
        
        # Password will be hashed at service layer
        if password:
            user_data["hashed_password"] = password
        
        return self.create(user_data)
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated, False if user not found
        """
        try:
            user = self.get(user_id)
            if user:
                user.last_login = datetime.utcnow()
                user.login_count = (user.login_count or 0) + 1
                self.db.commit()
                return True
            return False
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def update_password(self, user_id: int, hashed_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            hashed_password: New hashed password
            
        Returns:
            True if updated, False if user not found
        """
        try:
            user = self.get(user_id)
            if user:
                user.hashed_password = hashed_password
                user.password_changed_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def verify_email(self, user_id: int) -> bool:
        """
        Mark user email as verified.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated, False if user not found
        """
        try:
            user = self.get(user_id)
            if user:
                user.email_verified = True
                user.email_verified_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deactivated, False if user not found
        """
        try:
            user = self.get(user_id)
            if user:
                user.is_active = False
                user.deactivated_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def activate_user(self, user_id: int) -> bool:
        """
        Activate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if activated, False if user not found
        """
        try:
            user = self.get(user_id)
            if user:
                user.is_active = True
                user.deactivated_at = None
                self.db.commit()
                return True
            return False
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def get_active_users(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """
        Get list of active users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active user instances
        """
        return self.db.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_users_by_role(
        self, 
        role: UserRole, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """
        Get users by role.
        
        Args:
            role: User role to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user instances with specified role
        """
        return self.db.query(User).filter(
            and_(
                User.role == role,
                User.is_active == True
            )
        ).offset(skip).limit(limit).all()
    
    def search_users(
        self, 
        search_term: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """
        Search users by email or username.
        
        Args:
            search_term: Term to search for
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching user instances
        """
        return self.search(
            search_term=search_term,
            search_fields=["email", "username", "first_name", "last_name"],
            skip=skip,
            limit=limit
        )
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user statistics
        """
        user = self.get(user_id)
        if not user:
            return {}
        
        # TODO: Add more comprehensive user stats
        # TODO: Cache this data
        # TODO: Add activity tracking
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "login_count": user.login_count or 0,
            "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0
        }
    
    def update_user_preferences(
        self, 
        user_id: int, 
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            preferences: Dictionary of preference key-value pairs
            
        Returns:
            True if updated, False if user not found
        """
        try:
            # Check if user exists
            user = self.get(user_id)
            if not user:
                return False
            
            # Get existing preferences
            user_prefs = self.db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            
            if user_prefs:
                # Update existing preferences
                user_prefs.preferences = preferences
                user_prefs.updated_at = datetime.utcnow()
            else:
                # Create new preferences
                user_prefs = UserPreferences(
                    user_id=user_id,
                    preferences=preferences,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(user_prefs)
            
            self.db.commit()
            return True
            
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of user preferences or empty dict
        """
        user_prefs = self.db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        return user_prefs.preferences if user_prefs else {}
    
    def get_recent_users(
        self, 
        days: int = 30, 
        limit: int = 50
    ) -> List[User]:
        """
        Get recently created users.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of recently created user instances
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(User).filter(
            and_(
                User.created_at >= cutoff_date,
                User.is_active == True
            )
        ).order_by(desc(User.created_at)).limit(limit).all()
    
    def count_active_users(self) -> int:
        """
        Count total active users.
        
        Returns:
            Number of active users
        """
        return self.db.query(User).filter(
            User.is_active == True
        ).count()
    
    def count_users_by_role(self) -> Dict[str, int]:
        """
        Count users by role.
        
        Returns:
            Dictionary with role names as keys and counts as values
        """
        # TODO: Add caching for this expensive query
        # TODO: Consider materialized view for analytics
        
        result = {}
        for role in UserRole:
            count = self.db.query(User).filter(
                and_(
                    User.role == role,
                    User.is_active == True
                )
            ).count()
            result[role.value] = count
        
        return result
