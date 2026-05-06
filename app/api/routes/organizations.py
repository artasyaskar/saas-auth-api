"""
Multi-Tenant Organization API Routes

Comprehensive organization management for enterprise multi-tenant support:
- Organization CRUD
- Member management with roles
- Invitation system
- Domain verification
- Organization-level settings
- Billing and subscription management
- Data isolation enforcement
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum

from app.db.session import get_db
from app.db.models import (
    User, UserRole, Organization, OrganizationMember,
    OrganizationRole, OrganizationInvitation, SubscriptionPlan
)
from app.api.auth import get_current_active_user, get_current_admin_user
from app.services.email import EmailService


router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationRole(str, Enum):
    """Organization member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationBase(BaseModel):
    """Base organization data."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)


class OrganizationCreate(OrganizationBase):
    """Create organization request."""
    plan: SubscriptionPlan = SubscriptionPlan.FREE


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: int
    name: str
    slug: str
    description: Optional[str]
    website: Optional[str]
    plan: str
    member_count: int
    is_verified: bool
    created_at: str
    updated_at: str
    settings: Dict[str, Any]
    
    class Config:
        from_attributes = True


class OrganizationMemberBase(BaseModel):
    """Organization member data."""
    user_id: int
    organization_id: int
    role: str
    email: str
    name: Optional[str]
    joined_at: str
    last_active_at: Optional[str]


class OrganizationMemberResponse(BaseModel):
    """Organization member response."""
    id: int
    user_id: int
    email: str
    name: str
    role: str
    joined_at: str
    last_active_at: Optional[str]
    is_active: bool


class InviteMemberRequest(BaseModel):
    """Invite member request."""
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER
    message: Optional[str] = Field(None, max_length=500)


class InvitationResponse(BaseModel):
    """Invitation response."""
    id: int
    email: str
    role: str
    invited_by: str
    status: str
    created_at: str
    expires_at: str
    invite_url: Optional[str]


class UpdateMemberRoleRequest(BaseModel):
    """Update member role request."""
    role: OrganizationRole


class DomainVerificationRequest(BaseModel):
    """Domain verification request."""
    domain: str = Field(..., pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$")


class DomainVerificationResponse(BaseModel):
    """Domain verification response."""
    domain: str
    status: str  # pending, verified, failed
    verification_method: str  # dns, file, meta
    dns_record: Optional[Dict[str, str]]
    verification_code: str


class OrganizationSettings(BaseModel):
    """Organization settings."""
    enforce_sso: bool = False
    allowed_domains: List[str] = []
    require_2fa: bool = False
    session_timeout_minutes: int = 60
    password_policy: Dict[str, Any] = {}
    branding: Dict[str, Optional[str]] = {
        "logo_url": None,
        "favicon_url": None,
        "primary_color": None
    }
    features: Dict[str, bool] = {
        "api_access": True,
        "webhooks": False,
        "advanced_analytics": False,
        "custom_integrations": False
    }


class BillingInfo(BaseModel):
    """Organization billing information."""
    plan: str
    status: str
    current_period_start: str
    current_period_end: str
    seats_used: int
    seats_limit: int
    usage: Dict[str, Any]


def check_organization_permission(
    current_user: User,
    organization_id: int,
    required_role: OrganizationRole,
    db: Session
) -> bool:
    """
    Check if user has required permission in organization.
    
    Role hierarchy: owner > admin > member > viewer
    """
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        return False
    
    role_hierarchy = {
        OrganizationRole.OWNER: 4,
        OrganizationRole.ADMIN: 3,
        OrganizationRole.MEMBER: 2,
        OrganizationRole.VIEWER: 1
    }
    
    user_level = role_hierarchy.get(member.role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new organization.
    
    The current user becomes the organization owner.
    """
    # Check if slug is available
    existing = db.query(Organization).filter(Organization.slug == request.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists"
        )
    
    # Create organization
    organization = Organization(
        name=request.name,
        slug=request.slug,
        description=request.description,
        website=request.website,
        plan=request.plan,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(organization)
    db.flush()  # Get organization ID
    
    # Add creator as owner
    member = OrganizationMember(
        user_id=current_user.id,
        organization_id=organization.id,
        role=OrganizationRole.OWNER,
        joined_at=datetime.utcnow(),
        is_active=True
    )
    
    db.add(member)
    db.commit()
    db.refresh(organization)
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        website=organization.website,
        plan=organization.plan.value,
        member_count=1,
        is_verified=False,
        created_at=organization.created_at.isoformat(),
        updated_at=organization.updated_at.isoformat(),
        settings=organization.settings or {}
    )


@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    include_invited: bool = Query(False)
):
    """
    List organizations the user is a member of.
    """
    # Get user's organizations
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.is_active == True
    ).all()
    
    org_ids = [m.organization_id for m in memberships]
    
    organizations = db.query(Organization).filter(
        Organization.id.in_(org_ids),
        Organization.is_active == True
    ).all()
    
    result = []
    for org in organizations:
        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True
        ).count()
        
        result.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            website=org.website,
            plan=org.plan.value,
            member_count=member_count,
            is_verified=org.is_verified,
            created_at=org.created_at.isoformat() if org.created_at else None,
            updated_at=org.updated_at.isoformat() if org.updated_at else None,
            settings=org.settings or {}
        ))
    
    return result


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get organization details.
    """
    # Check permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.VIEWER, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.is_active == True
    ).count()
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        website=organization.website,
        plan=organization.plan.value,
        member_count=member_count,
        is_verified=organization.is_verified,
        created_at=organization.created_at.isoformat() if organization.created_at else None,
        updated_at=organization.updated_at.isoformat() if organization.updated_at else None,
        settings=organization.settings or {}
    )


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    request: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update organization details.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    if request.name is not None:
        organization.name = request.name
    if request.description is not None:
        organization.description = request.description
    if request.website is not None:
        organization.website = request.website
    if request.settings is not None:
        current_settings = organization.settings or {}
        current_settings.update(request.settings)
        organization.settings = current_settings
    
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(organization)
    
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.is_active == True
    ).count()
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        website=organization.website,
        plan=organization.plan.value,
        member_count=member_count,
        is_verified=organization.is_verified,
        created_at=organization.created_at.isoformat() if organization.created_at else None,
        updated_at=organization.updated_at.isoformat() if organization.updated_at else None,
        settings=organization.settings or {}
    )


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete organization (owner only).
    """
    # Check owner permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.OWNER, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Soft delete
    organization.is_active = False
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Organization deleted successfully"}


@router.get("/{organization_id}/members", response_model=List[OrganizationMemberResponse])
async def list_members(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    role: Optional[str] = None
):
    """
    List organization members.
    """
    # Check permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.VIEWER, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    query = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.is_active == True
    )
    
    if role:
        query = query.filter(OrganizationMember.role == role)
    
    members = query.all()
    
    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            result.append(OrganizationMemberResponse(
                id=member.id,
                user_id=member.user_id,
                email=user.email,
                name=user.username,
                role=member.role.value if hasattr(member.role, 'value') else str(member.role),
                joined_at=member.joined_at.isoformat() if member.joined_at else None,
                last_active_at=member.last_active_at.isoformat() if member.last_active_at else None,
                is_active=member.is_active
            ))
    
    return result


@router.post("/{organization_id}/invitations", response_model=InvitationResponse)
async def invite_member(
    organization_id: int,
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Invite a user to the organization.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if already member
    existing = db.query(OrganizationMember).join(User).filter(
        OrganizationMember.organization_id == organization_id,
        User.email == request.email
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )
    
    # Check pending invitation
    pending = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == organization_id,
        OrganizationInvitation.email == request.email,
        OrganizationInvitation.status == "pending"
    ).first()
    
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists"
        )
    
    # Create invitation
    from app.core.security import generate_secure_token
    token = generate_secure_token(32)
    
    invitation = OrganizationInvitation(
        organization_id=organization_id,
        email=request.email,
        role=request.role,
        invited_by=current_user.id,
        token=token,
        status="pending",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # Send invitation email
    # TODO: Integrate with email service
    
    invite_url = f"{settings.FRONTEND_URL}/invite?token={token}"
    
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value if hasattr(invitation.role, 'value') else str(invitation.role),
        invited_by=current_user.username,
        status=invitation.status,
        created_at=invitation.created_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
        invite_url=invite_url
    )


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Accept organization invitation.
    """
    invitation = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.token == token,
        OrganizationInvitation.status == "pending"
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed"
        )
    
    # Check expiration
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check email matches
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation email does not match your account"
        )
    
    # Add member
    member = OrganizationMember(
        user_id=current_user.id,
        organization_id=invitation.organization_id,
        role=invitation.role,
        joined_at=datetime.utcnow(),
        is_active=True
    )
    
    db.add(member)
    
    # Update invitation
    invitation.status = "accepted"
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Invitation accepted successfully"}


@router.patch("/{organization_id}/members/{member_id}")
async def update_member_role(
    organization_id: int,
    member_id: int,
    request: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update member role.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Can't change owner role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )
    
    # Only owner can assign admin
    if request.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign owner role"
        )
    
    if request.role == OrganizationRole.ADMIN:
        if not check_organization_permission(current_user, organization_id, OrganizationRole.OWNER, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner can assign admin role"
            )
    
    member.role = request.role
    member.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Member role updated successfully"}


@router.delete("/{organization_id}/members/{member_id}")
async def remove_member(
    organization_id: int,
    member_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove member from organization.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Can't remove owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove owner"
        )
    
    # Can only remove members with lower or equal role
    current_member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    role_hierarchy = {
        OrganizationRole.OWNER: 4,
        OrganizationRole.ADMIN: 3,
        OrganizationRole.MEMBER: 2,
        OrganizationRole.VIEWER: 1
    }
    
    if role_hierarchy.get(member.role, 0) >= role_hierarchy.get(current_member.role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove member with equal or higher role"
        )
    
    # Soft delete
    member.is_active = False
    member.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Member removed successfully"}


@router.post("/{organization_id}/domains/verify", response_model=DomainVerificationResponse)
async def verify_domain(
    organization_id: int,
    request: DomainVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate domain verification for SSO.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    
    # Generate verification code
    import secrets
    verification_code = f"saas-auth-verify-{secrets.token_hex(16)}"
    
    # Store in organization settings
    settings_data = organization.settings or {}
    settings_data['domain_verification'] = {
        'domain': request.domain,
        'code': verification_code,
        'status': 'pending',
        'requested_at': datetime.utcnow().isoformat()
    }
    organization.settings = settings_data
    
    db.commit()
    
    return DomainVerificationResponse(
        domain=request.domain,
        status="pending",
        verification_method="dns",
        dns_record={
            "type": "TXT",
            "name": "_saas-auth-verify",
            "value": verification_code
        },
        verification_code=verification_code
    )


@router.get("/{organization_id}/billing", response_model=BillingInfo)
async def get_billing_info(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get organization billing information.
    """
    # Check admin permission
    if not check_organization_permission(current_user, organization_id, OrganizationRole.ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.is_active == True
    ).count()
    
    # Plan limits
    limits = {
        SubscriptionPlan.FREE: {"members": 5, "storage": "1GB"},
        SubscriptionPlan.PRO: {"members": 25, "storage": "10GB"},
        SubscriptionPlan.ENTERPRISE: {"members": 100, "storage": "100GB"}
    }
    
    plan_limit = limits.get(organization.plan, limits[SubscriptionPlan.FREE])
    
    return BillingInfo(
        plan=organization.plan.value,
        status="active",
        current_period_start=datetime.utcnow().isoformat(),
        current_period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
        seats_used=member_count,
        seats_limit=plan_limit["members"],
        usage={
            "storage_used": "500MB",
            "storage_limit": plan_limit["storage"],
            "api_calls": 15000,
            "api_limit": 100000
        }
    )


from app.core.config import settings
from datetime import timedelta
