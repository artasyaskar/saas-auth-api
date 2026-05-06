"""
Authorization service for RBAC and permissions management.

Handles role-based access control, permission evaluation,
and comprehensive authorization with proper security considerations.
"""

from typing import Optional, Dict, Any, List, Set, Union
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import User, UserRole, Permission, Role, RolePermission, UserRoleAssignment
from app.repositories.user import UserRepository
from app.core.config import settings
from app.core.exceptions import (
    ValidationError, NotFoundError, SecurityError,
    DatabaseError, AuthorizationError
)


class PermissionType(str, Enum):
    """Permission type enumeration."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_PERMISSIONS = "manage_permissions"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_BILLING = "manage_billing"
    MANAGE_ORGANIZATIONS = "manage_organizations"
    SYSTEM_ADMIN = "system_admin"


class ResourceType(str, Enum):
    """Resource type enumeration."""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    ORGANIZATION = "organization"
    BILLING = "billing"
    ANALYTICS = "analytics"
    SYSTEM = "system"


class AuthorizationService:
    """
    Authorization service for RBAC and permissions management.
    
    Handles role-based access control, permission evaluation,
    and comprehensive authorization with proper security considerations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        
        # TODO: Add permission caching
        # TODO: Add role hierarchy support
        # TODO: Add attribute-based access control (ABAC)
        # TODO: Add permission inheritance
    
    def check_permission(
        self, 
        user_id: int, 
        permission: Union[str, PermissionType],
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user_id: User ID to check
            permission: Permission to check
            resource_type: Type of resource
            resource_id: Specific resource ID
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user or not user.is_active:
                return False
            
            # System admin has all permissions
            if self._is_system_admin(user):
                return True
            
            # Get user's roles
            user_roles = self._get_user_roles(user_id)
            
            if not user_roles:
                return False
            
            # Check permission for each role
            for role in user_roles:
                if self._role_has_permission(role, permission, resource_type, resource_id):
                    return True
            
            return False
            
        except Exception:
            # Default to deny on error
            return False
    
    def check_permissions(
        self, 
        user_id: int, 
        permissions: List[Union[str, PermissionType]],
        require_all: bool = True,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has multiple permissions.
        
        Args:
            user_id: User ID to check
            permissions: List of permissions to check
            require_all: Whether all permissions are required (AND) or any (OR)
            resource_type: Type of resource
            resource_id: Specific resource ID
            
        Returns:
            True if user has required permissions, False otherwise
        """
        try:
            if require_all:
                # User must have all permissions
                return all(
                    self.check_permission(user_id, perm, resource_type, resource_id)
                    for perm in permissions
                )
            else:
                # User must have at least one permission
                return any(
                    self.check_permission(user_id, perm, resource_type, resource_id)
                    for perm in permissions
                )
                
        except Exception:
            # Default to deny on error
            return False
    
    def get_user_permissions(
        self, 
        user_id: int,
        resource_type: Optional[ResourceType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            resource_type: Filter by resource type
            
        Returns:
            List of user permissions
        """
        try:
            # Get user
            user = self.user_repo.get(user_id)
            
            if not user or not user.is_active:
                return []
            
            # System admin has all permissions
            if self._is_system_admin(user):
                return self._get_all_permissions(resource_type)
            
            # Get user's roles and permissions
            user_roles = self._get_user_roles(user_id)
            permissions = set()
            
            for role in user_roles:
                role_permissions = self._get_role_permissions(role.id)
                for perm in role_permissions:
                    if not resource_type or perm.resource_type == resource_type:
                        permissions.add(perm)
            
            return [
                {
                    "id": perm.id,
                    "name": perm.name,
                    "resource_type": perm.resource_type,
                    "resource_id": perm.resource_id,
                    "description": perm.description,
                    "created_at": perm.created_at.isoformat() if perm.created_at else None
                }
                for perm in permissions
            ]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user permissions: {str(e)}")
    
    def get_user_roles(
        self, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user roles
        """
        try:
            user_roles = self._get_user_roles(user_id)
            
            return [
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_system": role.is_system,
                    "created_at": role.created_at.isoformat() if role.created_at else None,
                    "assigned_at": role.assigned_at.isoformat() if role.assigned_at else None,
                    "assigned_by": role.assigned_by
                }
                for role in user_roles
            ]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user roles: {str(e)}")
    
    def assign_role(
        self, 
        user_id: int, 
        role_id: int,
        assigned_by: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Assign role to user.
        
        Args:
            user_id: User ID to assign role to
            role_id: Role ID to assign
            assigned_by: User ID making the assignment
            expires_at: Optional expiration time
            
        Returns:
            True if assigned successfully
            
        Raises:
            NotFoundError: If user or role not found
            SecurityError: If not authorized to assign role
            ValidationError: If assignment is invalid
        """
        try:
            # Check authorization
            if not self._can_manage_roles(assigned_by):
                raise SecurityError("Not authorized to assign roles")
            
            # Get user and role
            user = self.user_repo.get(user_id)
            role = self.db.query(Role).filter(Role.id == role_id).first()
            
            if not user:
                raise NotFoundError("User not found")
            
            if not role:
                raise NotFoundError("Role not found")
            
            # Check if already assigned
            existing_assignment = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.expires_at > datetime.utcnow() if UserRoleAssignment.expires_at else True
            ).first()
            
            if existing_assignment:
                raise ValidationError("User already has this role")
            
            # Create role assignment
            assignment = UserRoleAssignment(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                expires_at=expires_at
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            # Log assignment
            self._log_authorization_event("role_assigned", {
                "user_id": user_id,
                "role_id": role_id,
                "assigned_by": assigned_by,
                "expires_at": expires_at.isoformat() if expires_at else None
            })
            
            return True
            
        except (NotFoundError, SecurityError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to assign role: {str(e)}")
    
    def revoke_role(
        self, 
        user_id: int, 
        role_id: int,
        revoked_by: int,
        reason: str = "Role revocation"
    ) -> bool:
        """
        Revoke role from user.
        
        Args:
            user_id: User ID to revoke role from
            role_id: Role ID to revoke
            revoked_by: User ID making the revocation
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
            
        Raises:
            NotFoundError: If assignment not found
            SecurityError: If not authorized to revoke role
        """
        try:
            # Check authorization
            if not self._can_manage_roles(revoked_by):
                raise SecurityError("Not authorized to revoke roles")
            
            # Get role assignment
            assignment = self.db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.expires_at > datetime.utcnow() if UserRoleAssignment.expires_at else True
            ).first()
            
            if not assignment:
                raise NotFoundError("Role assignment not found")
            
            # Revoke assignment
            assignment.revoked_at = datetime.utcnow()
            assignment.revoked_by = revoked_by
            assignment.revocation_reason = reason
            
            self.db.commit()
            
            # Log revocation
            self._log_authorization_event("role_revoked", {
                "user_id": user_id,
                "role_id": role_id,
                "revoked_by": revoked_by,
                "reason": reason
            })
            
            return True
            
        except (NotFoundError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to revoke role: {str(e)}")
    
    def create_role(
        self, 
        name: str,
        description: str,
        permissions: List[int],
        created_by: int,
        is_system: bool = False
    ) -> Dict[str, Any]:
        """
        Create new role with permissions.
        
        Args:
            name: Role name
            description: Role description
            permissions: List of permission IDs
            created_by: User ID creating the role
            is_system: Whether this is a system role
            
        Returns:
            Created role data
            
        Raises:
            ValidationError: If role data is invalid
            SecurityError: If not authorized to create role
        """
        try:
            # Check authorization
            if not self._can_manage_roles(created_by):
                raise SecurityError("Not authorized to create roles")
            
            # Validate role data
            self._validate_role_data(name, description, permissions)
            
            # Create role
            role = Role(
                name=name,
                description=description,
                is_system=is_system,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            self.db.add(role)
            self.db.flush()  # Get role ID
            
            # Assign permissions to role
            for permission_id in permissions:
                role_permission = RolePermission(
                    role_id=role.id,
                    permission_id=permission_id
                )
                self.db.add(role_permission)
            
            self.db.commit()
            
            # Log creation
            self._log_authorization_event("role_created", {
                "role_id": role.id,
                "name": name,
                "created_by": created_by,
                "permission_count": len(permissions)
            })
            
            return {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "permission_count": len(permissions),
                "created_at": role.created_at.isoformat()
            }
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create role: {str(e)}")
    
    def update_role(
        self, 
        role_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[int]] = None,
        updated_by: int = None
    ) -> Dict[str, Any]:
        """
        Update existing role.
        
        Args:
            role_id: Role ID to update
            name: New role name
            description: New role description
            permissions: New list of permission IDs
            updated_by: User ID updating the role
            
        Returns:
            Updated role data
            
        Raises:
            NotFoundError: If role not found
            ValidationError: If role data is invalid
            SecurityError: If not authorized to update role
        """
        try:
            # Check authorization
            if updated_by and not self._can_manage_roles(updated_by):
                raise SecurityError("Not authorized to update roles")
            
            # Get role
            role = self.db.query(Role).filter(Role.id == role_id).first()
            
            if not role:
                raise NotFoundError("Role not found")
            
            # Don't allow updating system roles
            if role.is_system:
                raise SecurityError("Cannot modify system roles")
            
            # Update role fields
            if name is not None:
                role.name = name
            if description is not None:
                role.description = description
            
            role.updated_at = datetime.utcnow()
            role.updated_by = updated_by
            
            # Update permissions if provided
            if permissions is not None:
                # Remove existing permissions
                self.db.query(RolePermission).filter(
                    RolePermission.role_id == role_id
                ).delete()
                
                # Add new permissions
                for permission_id in permissions:
                    role_permission = RolePermission(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    self.db.add(role_permission)
            
            self.db.commit()
            
            # Log update
            self._log_authorization_event("role_updated", {
                "role_id": role_id,
                "updated_by": updated_by,
                "fields_updated": list(filter(None, [name, description, permissions]))
            })
            
            return {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "permission_count": len(permissions) if permissions is not None else 0,
                "updated_at": role.updated_at.isoformat() if role.updated_at else None
            }
            
        except (NotFoundError, ValidationError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to update role: {str(e)}")
    
    def create_permission(
        self, 
        name: str,
        description: str,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create new permission.
        
        Args:
            name: Permission name
            description: Permission description
            resource_type: Type of resource
            resource_id: Specific resource ID
            created_by: User ID creating the permission
            
        Returns:
            Created permission data
            
        Raises:
            ValidationError: If permission data is invalid
            SecurityError: If not authorized to create permission
        """
        try:
            # Check authorization
            if not self._can_manage_permissions(created_by):
                raise SecurityError("Not authorized to create permissions")
            
            # Validate permission data
            self._validate_permission_data(name, description, resource_type, resource_id)
            
            # Create permission
            permission = Permission(
                name=name,
                description=description,
                resource_type=resource_type.value,
                resource_id=resource_id,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            self.db.add(permission)
            self.db.commit()
            
            # Log creation
            self._log_authorization_event("permission_created", {
                "permission_id": permission.id,
                "name": name,
                "resource_type": resource_type.value,
                "created_by": created_by
            })
            
            return {
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
                "resource_type": permission.resource_type,
                "resource_id": permission.resource_id,
                "created_at": permission.created_at.isoformat()
            }
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create permission: {str(e)}")
    
    def get_role_hierarchy(self) -> List[Dict[str, Any]]:
        """
        Get role hierarchy and relationships.
        
        Returns:
            Role hierarchy data
        """
        try:
            # TODO: Implement role hierarchy
            # TODO: Add role inheritance
            # TODO: Add role dependencies
            
            # Placeholder implementation
            roles = self.db.query(Role).all()
            
            return [
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_system": role.is_system,
                    "parent_id": None,  # TODO: Implement parent/child relationships
                    "children": [],  # TODO: Implement child roles
                    "permission_count": len(role.permissions) if hasattr(role, 'permissions') else 0,
                    "user_count": self._count_role_users(role.id)
                }
                for role in roles
            ]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get role hierarchy: {str(e)}")
    
    def get_authorization_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive authorization summary for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Authorization summary
        """
        try:
            user = self.user_repo.get(user_id)
            
            if not user:
                raise NotFoundError("User not found")
            
            # Get user roles and permissions
            roles = self.get_user_roles(user_id)
            permissions = self.get_user_permissions(user_id)
            
            # Calculate authorization metrics
            return {
                "user_id": user_id,
                "is_active": user.is_active,
                "is_system_admin": self._is_system_admin(user),
                "role_count": len(roles),
                "permission_count": len(permissions),
                "roles": roles,
                "permissions": permissions,
                "can_manage_users": self.check_permission(user_id, PermissionType.MANAGE_USERS),
                "can_manage_roles": self.check_permission(user_id, PermissionType.MANAGE_ROLES),
                "can_manage_permissions": self.check_permission(user_id, PermissionType.MANAGE_PERMISSIONS),
                "can_view_analytics": self.check_permission(user_id, PermissionType.VIEW_ANALYTICS),
                "can_manage_billing": self.check_permission(user_id, PermissionType.MANAGE_BILLING),
                "can_manage_organizations": self.check_permission(user_id, PermissionType.MANAGE_ORGANIZATIONS),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get authorization summary: {str(e)}")
    
    def _get_user_roles(self, user_id: int) -> List[Role]:
        """
        Get user's active roles.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user roles
        """
        return self.db.query(Role).join(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.expires_at > datetime.utcnow() if UserRoleAssignment.expires_at else True,
            UserRoleAssignment.revoked_at.is_(None)
        ).all()
    
    def _get_role_permissions(self, role_id: int) -> List[Permission]:
        """
        Get permissions for a role.
        
        Args:
            role_id: Role ID
            
        Returns:
            List of role permissions
        """
        return self.db.query(Permission).join(RolePermission).filter(
            RolePermission.role_id == role_id
        ).all()
    
    def _role_has_permission(
        self, 
        role: Role, 
        permission: Union[str, PermissionType],
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if role has specific permission.
        
        Args:
            role: Role object
            permission: Permission to check
            resource_type: Type of resource
            resource_id: Specific resource ID
            
        Returns:
            True if role has permission, False otherwise
        """
        # Get role permissions
        role_permissions = self._get_role_permissions(role.id)
        
        permission_str = permission.value if isinstance(permission, PermissionType) else permission
        
        for perm in role_permissions:
            if perm.name == permission_str:
                # Check resource type match
                if resource_type and perm.resource_type != resource_type.value:
                    continue
                
                # Check resource ID match
                if resource_id and perm.resource_id != resource_id:
                    continue
                
                return True
        
        return False
    
    def _is_system_admin(self, user: User) -> bool:
        """
        Check if user is system administrator.
        
        Args:
            user: User object
            
        Returns:
            True if system admin, False otherwise
        """
        return user.role == UserRole.ADMIN
    
    def _can_manage_roles(self, user_id: int) -> bool:
        """
        Check if user can manage roles.
        
        Args:
            user_id: User ID
            
        Returns:
            True if can manage roles, False otherwise
        """
        return self.check_permission(user_id, PermissionType.MANAGE_ROLES)
    
    def _can_manage_permissions(self, user_id: int) -> bool:
        """
        Check if user can manage permissions.
        
        Args:
            user_id: User ID
            
        Returns:
            True if can manage permissions, False otherwise
        """
        return self.check_permission(user_id, PermissionType.MANAGE_PERMISSIONS)
    
    def _get_all_permissions(self, resource_type: Optional[ResourceType] = None) -> List[Permission]:
        """
        Get all permissions, optionally filtered by resource type.
        
        Args:
            resource_type: Filter by resource type
            
        Returns:
            List of all permissions
        """
        query = self.db.query(Permission)
        
        if resource_type:
            query = query.filter(Permission.resource_type == resource_type.value)
        
        return query.all()
    
    def _validate_role_data(self, name: str, description: str, permissions: List[int]):
        """
        Validate role data.
        
        Args:
            name: Role name
            description: Role description
            permissions: List of permission IDs
            
        Raises:
            ValidationError: If data is invalid
        """
        errors = []
        
        if not name or len(name.strip()) < 2:
            errors.append("Role name must be at least 2 characters long")
        
        if len(name) > 100:
            errors.append("Role name must be less than 100 characters")
        
        if not description or len(description.strip()) < 5:
            errors.append("Role description must be at least 5 characters long")
        
        if len(description) > 500:
            errors.append("Role description must be less than 500 characters")
        
        if not permissions or len(permissions) == 0:
            errors.append("Role must have at least one permission")
        
        # Check if role name already exists
        existing_role = self.db.query(Role).filter(Role.name == name).first()
        if existing_role:
            errors.append("Role name already exists")
        
        if errors:
            raise ValidationError("Role validation failed", errors=errors)
    
    def _validate_permission_data(self, name: str, description: str, resource_type: ResourceType, resource_id: Optional[str]):
        """
        Validate permission data.
        
        Args:
            name: Permission name
            description: Permission description
            resource_type: Type of resource
            resource_id: Specific resource ID
            
        Raises:
            ValidationError: If data is invalid
        """
        errors = []
        
        if not name or len(name.strip()) < 2:
            errors.append("Permission name must be at least 2 characters long")
        
        if len(name) > 100:
            errors.append("Permission name must be less than 100 characters")
        
        if not description or len(description.strip()) < 5:
            errors.append("Permission description must be at least 5 characters long")
        
        if len(description) > 500:
            errors.append("Permission description must be less than 500 characters")
        
        # Check if permission name already exists for this resource
        existing_permission = self.db.query(Permission).filter(
            Permission.name == name,
            Permission.resource_type == resource_type.value,
            Permission.resource_id == resource_id
        ).first()
        
        if existing_permission:
            errors.append("Permission already exists for this resource")
        
        if errors:
            raise ValidationError("Permission validation failed", errors=errors)
    
    def _count_role_users(self, role_id: int) -> int:
        """
        Count users with specific role.
        
        Args:
            role_id: Role ID
            
        Returns:
            Number of users with role
        """
        return self.db.query(UserRoleAssignment).filter(
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.expires_at > datetime.utcnow() if UserRoleAssignment.expires_at else True,
            UserRoleAssignment.revoked_at.is_(None)
        ).count()
    
    def _log_authorization_event(self, event_type: str, metadata: Dict[str, Any]):
        """
        Log authorization event for auditing.
        
        Args:
            event_type: Type of authorization event
            metadata: Event metadata
        """
        try:
            # TODO: Implement authorization event logging
            # TODO: Add audit trail
            # TODO: Add security monitoring
            
            pass
        except Exception:
            pass


# Service factory function
def get_authorization_service(db: Session) -> AuthorizationService:
    """
    Get authorization service instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthorizationService instance
    """
    return AuthorizationService(db)
