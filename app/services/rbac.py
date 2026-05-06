"""
Role-Based Access Control (RBAC) Service

Enterprise-grade RBAC system for fine-grained permission management:
- Role hierarchy and inheritance
- Permission-based access control
- Dynamic permission evaluation
- Resource-level permissions
- Organization-scoped permissions
- Policy-based access control (PBAC)
- Attribute-based access control (ABAC)
"""
from typing import Dict, List, Set, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends

from app.db.models import (
    User, Organization, OrganizationMember, Role, Permission,
    RolePermission, UserRole, ResourcePolicy
)
from app.api.auth import get_current_active_user


class PermissionType(Enum):
    """Permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    CREATE = "create"
    UPDATE = "update"
    EXECUTE = "execute"


class ResourceType(Enum):
    """Resource types for permissions."""
    USER = "user"
    ORGANIZATION = "organization"
    BILLING = "billing"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    AUDIT_LOG = "audit_log"
    INTEGRATION = "integration"
    REPORT = "report"
    SETTING = "setting"
    SAML_CONFIG = "saml_config"
    SCIM_CONFIG = "scim_config"


class AccessDecision(Enum):
    """Access control decisions."""
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class Permission:
    """Permission definition."""
    name: str
    resource_type: ResourceType
    action: PermissionType
    description: str = ""
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class Role:
    """Role definition."""
    name: str
    display_name: str
    description: str = ""
    permissions: Set[str] = field(default_factory=set)
    inherits: Set[str] = field(default_factory=set)
    is_system: bool = False
    organization_id: Optional[int] = None


@dataclass
class AccessRequest:
    """Access control request."""
    user_id: int
    resource_type: ResourceType
    action: PermissionType
    resource_id: Optional[str] = None
    organization_id: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessResult:
    """Access control result."""
    decision: AccessDecision
    reason: str
    evaluated_policies: List[str] = field(default_factory=list)
    missing_permissions: List[str] = field(default_factory=list)


class RBACService:
    """
    Enterprise Role-Based Access Control service.
    
    Provides comprehensive permission management and access control:
    - Role hierarchy and inheritance
    - Permission evaluation
    - Resource-level access control
    - Policy-based access control
    - Attribute-based access control
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._permission_cache = {}
        self._role_cache = {}
    
    def create_role(
        self,
        name: str,
        display_name: str,
        description: str = "",
        permissions: List[str] = None,
        inherits: List[str] = None,
        organization_id: Optional[int] = None
    ) -> Role:
        """Create a new role."""
        # Check if role already exists
        existing = self.db.query(Role).filter(
            Role.name == name,
            Role.organization_id == organization_id
        ).first()
        
        if existing:
            raise ValueError(f"Role '{name}' already exists")
        
        # Create role
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            organization_id=organization_id,
            is_system=False,
            created_at=datetime.utcnow()
        )
        
        self.db.add(role)
        self.db.flush()
        
        # Add permissions
        if permissions:
            for perm_name in permissions:
                permission = self.db.query(Permission).filter(
                    Permission.name == perm_name
                ).first()
                
                if permission:
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    self.db.add(role_permission)
        
        # Set inheritance
        if inherits:
            for parent_name in inherits:
                parent_role = self.db.query(Role).filter(
                    Role.name == parent_name,
                    Role.organization_id == organization_id
                ).first()
                
                if parent_role:
                    role.inherits_from = parent_role.id
        
        self.db.commit()
        self.db.refresh(role)
        
        # Clear cache
        self._role_cache.clear()
        
        return role
    
    def assign_role(
        self,
        user_id: int,
        role_name: str,
        organization_id: Optional[int] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """Assign role to user."""
        role = self.db.query(Role).filter(
            Role.name == role_name,
            Role.organization_id == organization_id
        ).first()
        
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        # Check existing assignment
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.organization_id == organization_id,
            UserRole.resource_id == resource_id
        ).first()
        
        if existing:
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
        else:
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                organization_id=organization_id,
                resource_id=resource_id,
                is_active=True,
                assigned_at=datetime.utcnow()
            )
            self.db.add(user_role)
        
        self.db.commit()
        return True
    
    def revoke_role(
        self,
        user_id: int,
        role_name: str,
        organization_id: Optional[int] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """Revoke role from user."""
        role = self.db.query(Role).filter(
            Role.name == role_name,
            Role.organization_id == organization_id
        ).first()
        
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        user_role = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.organization_id == organization_id,
            UserRole.resource_id == resource_id
        ).first()
        
        if user_role:
            user_role.is_active = False
            user_role.revoked_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def check_permission(
        self,
        request: AccessRequest
    ) -> AccessResult:
        """
        Check if user has permission for action on resource.
        
        Evaluates:
        1. Direct user permissions
        2. Role-based permissions
        3. Resource policies
        4. Attribute-based conditions
        """
        # Get user roles
        user_roles = self._get_user_roles(request.user_id, request.organization_id)
        
        # Get effective permissions (including inheritance)
        effective_permissions = self._get_effective_permissions(user_roles)
        
        # Build permission name
        permission_name = f"{request.resource_type.value}.{request.action.value}"
        
        # Check direct permission
        if permission_name in effective_permissions:
            return AccessResult(
                decision=AccessDecision.ALLOW,
                reason="Permission granted via role"
            )
        
        # Check resource policies
        policy_result = self._evaluate_policies(request)
        if policy_result.decision != AccessDecision.ABSTAIN:
            return policy_result
        
        # Check attribute-based access control
        abac_result = self._evaluate_abac(request)
        if abac_result.decision != AccessDecision.ABSTAIN:
            return abac_result
        
        return AccessResult(
            decision=AccessDecision.DENY,
            reason="No sufficient permissions found",
            missing_permissions=[permission_name]
        )
    
    def _get_user_roles(
        self,
        user_id: int,
        organization_id: Optional[int] = None
    ) -> List[Role]:
        """Get user's active roles."""
        user_roles = self.db.query(UserRole).join(Role).filter(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            Role.organization_id == organization_id
        ).all()
        
        return [ur.role for ur in user_roles]
    
    def _get_effective_permissions(self, roles: List[Role]) -> Set[str]:
        """Get effective permissions including role inheritance."""
        permissions = set()
        processed_roles = set()
        
        def process_role(role: Role):
            if role.name in processed_roles:
                return
            
            processed_roles.add(role.name)
            
            # Add role permissions
            for rp in role.role_permissions:
                permissions.add(rp.permission.name)
            
            # Process inherited roles
            if role.inherits_from:
                parent_role = self.db.query(Role).filter(Role.id == role.inherits_from).first()
                if parent_role:
                    process_role(parent_role)
        
        for role in roles:
            process_role(role)
        
        return permissions
    
    def _evaluate_policies(self, request: AccessRequest) -> AccessResult:
        """Evaluate resource-based policies."""
        policies = self.db.query(ResourcePolicy).filter(
            ResourcePolicy.resource_type == request.resource_type.value,
            ResourcePolicy.is_active == True
        ).all()
        
        for policy in policies:
            # Check if policy applies
            if self._policy_applies(policy, request):
                if policy.effect == "allow":
                    return AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason=f"Allowed by policy: {policy.name}",
                        evaluated_policies=[policy.name]
                    )
                else:
                    return AccessResult(
                        decision=AccessDecision.DENY,
                        reason=f"Denied by policy: {policy.name}",
                        evaluated_policies=[policy.name]
                    )
        
        return AccessResult(decision=AccessDecision.ABSTAIN, reason="No applicable policies")
    
    def _policy_applies(self, policy: ResourcePolicy, request: AccessRequest) -> bool:
        """Check if policy applies to request."""
        try:
            conditions = json.loads(policy.conditions) if policy.conditions else {}
            
            # Check user conditions
            if "users" in conditions:
                if str(request.user_id) not in conditions["users"]:
                    return False
            
            # Check organization conditions
            if "organizations" in conditions:
                if request.organization_id and str(request.organization_id) not in conditions["organizations"]:
                    return False
            
            # Check custom conditions
            if "custom" in conditions:
                for condition in conditions["custom"]:
                    if not self._evaluate_condition(condition, request):
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _evaluate_condition(self, condition: Dict[str, Any], request: AccessRequest) -> bool:
        """Evaluate individual condition."""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if not field or not operator:
            return False
        
        # Get field value from request context
        field_value = request.context.get(field)
        if field_value is None:
            return False
        
        # Evaluate condition
        if operator == "equals":
            return field_value == value
        elif operator == "not_equals":
            return field_value != value
        elif operator == "in":
            return field_value in value
        elif operator == "not_in":
            return field_value not in value
        elif operator == "contains":
            return value in field_value
        elif operator == "greater_than":
            return field_value > value
        elif operator == "less_than":
            return field_value < value
        
        return False
    
    def _evaluate_abac(self, request: AccessRequest) -> AccessResult:
        """Evaluate attribute-based access control."""
        # Get user attributes
        user = self.db.query(User).filter(User.id == request.user_id).first()
        if not user:
            return AccessResult(decision=AccessDecision.ABSTAIN, reason="User not found")
        
        # Get organization member info if applicable
        member = None
        if request.organization_id:
            member = self.db.query(OrganizationMember).filter(
                OrganizationMember.user_id == request.user_id,
                OrganizationMember.organization_id == request.organization_id
            ).first()
        
        # Build ABAC context
        context = {
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
        
        if member:
            context["member"] = {
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "is_active": member.is_active
            }
        
        # Add request context
        context.update(request.context)
        
        # Evaluate ABAC rules
        # This is a simplified example - in production, you'd have more sophisticated rules
        if request.resource_type == ResourceType.USER:
            # Users can only read their own profile unless they're admin
            if request.action == PermissionType.READ:
                if request.resource_id == str(request.user_id):
                    return AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason="User can read own profile"
                    )
            
            # Admins can manage users in their organization
            if user.role == UserRole.ADMIN:
                if request.organization_id and member:
                    return AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason="Admin can manage organization users"
                    )
        
        elif request.resource_type == ResourceType.ORGANIZATION:
            # Organization members can read their organization
            if request.action == PermissionType.READ:
                if member and member.is_active:
                    return AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason="Organization member can read organization"
                    )
            
            # Admins and owners can manage organization
            if request.action in [PermissionType.WRITE, PermissionType.UPDATE]:
                if member and member.role in ['admin', 'owner']:
                    return AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason=f"Organization {member.role} can manage organization"
                    )
        
        return AccessResult(decision=AccessDecision.ABSTAIN, reason="No ABAC rules matched")
    
    def get_user_permissions(
        self,
        user_id: int,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all permissions for a user."""
        user_roles = self._get_user_roles(user_id, organization_id)
        effective_permissions = self._get_effective_permissions(user_roles)
        
        return {
            "user_id": user_id,
            "organization_id": organization_id,
            "roles": [role.name for role in user_roles],
            "permissions": list(effective_permissions)
        }
    
    def create_permission(
        self,
        name: str,
        resource_type: ResourceType,
        action: PermissionType,
        description: str = "",
        conditions: Optional[Dict[str, Any]] = None
    ) -> Permission:
        """Create a new permission."""
        # Check if permission already exists
        existing = self.db.query(Permission).filter(
            Permission.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(
            name=name,
            resource_type=resource_type.value,
            action=action.value,
            description=description,
            conditions=json.dumps(conditions) if conditions else None,
            created_at=datetime.utcnow()
        )
        
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        
        return permission
    
    def create_policy(
        self,
        name: str,
        resource_type: ResourceType,
        effect: str,  # allow or deny
        conditions: Dict[str, Any],
        description: str = ""
    ) -> ResourcePolicy:
        """Create a resource policy."""
        policy = ResourcePolicy(
            name=name,
            resource_type=resource_type.value,
            effect=effect,
            conditions=json.dumps(conditions),
            description=description,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        
        return policy


# Decorator for permission checking
def require_permission(
    resource_type: ResourceType,
    action: PermissionType,
    get_resource_id: Optional[Callable] = None
):
    """
    Decorator for requiring permission to access endpoint.
    
    Usage:
        @require_permission(ResourceType.USER, PermissionType.READ)
        async def get_user(user_id: str):
            ...
    
    The decorator will check if the current user has the required permission
    and raise HTTPException if not.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from dependencies
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get organization_id from kwargs or user context
            organization_id = kwargs.get('organization_id')
            
            # Get resource_id
            resource_id = None
            if get_resource_id:
                resource_id = get_resource_id(*args, **kwargs)
            else:
                # Try to get from kwargs
                for key, value in kwargs.items():
                    if key.endswith('_id') and value:
                        resource_id = str(value)
                        break
            
            # Get database session
            db = None
            for arg in args:
                if hasattr(arg, 'query'):  # SQLAlchemy Session
                    db = arg
                    break
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )
            
            # Check permission
            rbac = RBACService(db)
            request = AccessRequest(
                user_id=current_user.id,
                resource_type=resource_type,
                action=action,
                resource_id=resource_id,
                organization_id=organization_id
            )
            
            result = rbac.check_permission(request)
            
            if result.decision != AccessDecision.ALLOW:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: {result.reason}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Dependency for getting RBAC service
def get_rbac_service(db: Session = Depends(get_db)) -> RBACService:
    """Get RBAC service instance."""
    return RBACService(db)


# Initialize default permissions and roles
def initialize_rbac(db: Session):
    """Initialize default RBAC permissions and roles."""
    rbac = RBACService(db)
    
    # Create default permissions
    default_permissions = [
        ("user.read", ResourceType.USER, PermissionType.READ, "Read user information"),
        ("user.write", ResourceType.USER, PermissionType.WRITE, "Update user information"),
        ("user.delete", ResourceType.USER, PermissionType.DELETE, "Delete user"),
        ("organization.read", ResourceType.ORGANIZATION, PermissionType.READ, "Read organization information"),
        ("organization.write", ResourceType.ORGANIZATION, PermissionType.WRITE, "Update organization"),
        ("organization.admin", ResourceType.ORGANIZATION, PermissionType.ADMIN, "Administer organization"),
        ("billing.read", ResourceType.BILLING, PermissionType.READ, "Read billing information"),
        ("billing.write", ResourceType.BILLING, PermissionType.WRITE, "Update billing"),
        ("api_key.read", ResourceType.API_KEY, PermissionType.READ, "Read API keys"),
        ("api_key.write", ResourceType.API_KEY, PermissionType.WRITE, "Manage API keys"),
        ("webhook.read", ResourceType.WEBHOOK, PermissionType.READ, "Read webhooks"),
        ("webhook.write", ResourceType.WEBHOOK, PermissionType.WRITE, "Manage webhooks"),
        ("audit_log.read", ResourceType.AUDIT_LOG, PermissionType.READ, "Read audit logs"),
        ("integration.read", ResourceType.INTEGRATION, PermissionType.READ, "Read integrations"),
        ("integration.write", ResourceType.INTEGRATION, PermissionType.WRITE, "Manage integrations"),
    ]
    
    for name, resource_type, action, description in default_permissions:
        try:
            rbac.create_permission(name, resource_type, action, description)
        except ValueError:
            pass  # Permission already exists
    
    # Create default system roles
    system_roles = [
        ("super_admin", "Super Administrator", "Full system access", ["*"]),
        ("admin", "Administrator", "Organization administrator", ["organization.admin", "user.*", "billing.*"]),
        ("member", "Member", "Regular organization member", ["organization.read", "user.read"]),
        ("viewer", "Viewer", "Read-only access", ["organization.read", "user.read", "billing.read"]),
    ]
    
    for name, display_name, description, permissions in system_roles:
        try:
            rbac.create_role(name, display_name, description, permissions, is_system=True)
        except ValueError:
            pass  # Role already exists
