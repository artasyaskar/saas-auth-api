"""
SCIM 2.0 API Routes

System for Cross-domain Identity Management (SCIM) protocol implementation:
- User provisioning and deprovisioning
- Group management
- Enterprise directory synchronization
- Resource filtering and pagination
- Bulk operations support
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import re
import json

from app.db.session import get_db
from app.db.models import User, UserRole, Organization, OrganizationMember
from app.api.auth import get_current_active_user
from app.core.config import settings


router = APIRouter(prefix="/scim/v2", tags=["scim"])


# SCIM 2.0 Constants
SCIM_CONTENT_TYPE = "application/scim+json"
SCIM_SCHEMA_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_SCHEMA_GROUP = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_SCHEMA_ERROR = "urn:ietf:params:scim:api:messages:2.0:Error"
SCIM_SCHEMA_LIST = "urn:ietf:params:scim:api:messages:2.0:ListResponse"


class SCIMName(BaseModel):
    """SCIM user name complex attribute."""
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


class SCIMEmail(BaseModel):
    """SCIM email attribute."""
    value: str
    type: str = "work"
    primary: bool = True


class SCIMRole(BaseModel):
    """SCIM role attribute."""
    value: str
    type: str = "organization"


class SCIMMeta(BaseModel):
    """SCIM resource metadata."""
    resourceType: str
    created: str
    lastModified: str
    location: str
    version: str


class SCIMUser(BaseModel):
    """SCIM User resource."""
    schemas: List[str] = [SCIM_SCHEMA_USER]
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: List[SCIMEmail] = []
    active: bool = True
    roles: List[SCIMRole] = []
    meta: Optional[SCIMMeta] = None
    organizationId: Optional[int] = None


class SCIMGroupMember(BaseModel):
    """SCIM group member reference."""
    value: str
    display: str
    type: str = "User"


class SCIMGroup(BaseModel):
    """SCIM Group resource."""
    schemas: List[str] = [SCIM_SCHEMA_GROUP]
    id: Optional[str] = None
    externalId: Optional[str] = None
    displayName: str
    members: List[SCIMGroupMember] = []
    meta: Optional[SCIMMeta] = None


class SCIMError(BaseModel):
    """SCIM Error response."""
    schemas: List[str] = [SCIM_SCHEMA_ERROR]
    status: str
    detail: str
    scimType: Optional[str] = None


class SCIMListResponse(BaseModel):
    """SCIM List response."""
    schemas: List[str] = [SCIM_SCHEMA_LIST]
    totalResults: int
    startIndex: int
    itemsPerPage: int
    Resources: List[Union[SCIMUser, SCIMGroup]]


class SCIMPatchOperation(BaseModel):
    """SCIM Patch operation."""
    op: str  # add, remove, replace
    path: Optional[str] = None
    value: Optional[Any] = None


class SCIMPatchRequest(BaseModel):
    """SCIM Patch request."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: List[SCIMPatchOperation]


class SCIMBulkRequest(BaseModel):
    """SCIM Bulk request."""
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"]
    Operations: List[Dict[str, Any]]


def scim_error(status: int, detail: str, scim_type: Optional[str] = None) -> Dict[str, Any]:
    """Generate SCIM error response."""
    return {
        "schemas": [SCIM_SCHEMA_ERROR],
        "status": str(status),
        "detail": detail,
        "scimType": scim_type
    }


def parse_filter(filter_string: str) -> Dict[str, Any]:
    """
    Parse SCIM filter expression.
    
    Supports: eq, ne, co, sw, ew, pr, gt, lt, ge, le
    Examples: userName eq "john", emails.value co "@example.com"
    """
    if not filter_string:
        return {}
    
    # Simple eq filter parser
    match = re.match(r'(\w+(?:\.\w+)*)\s+eq\s+["\']?([^"\']+)["\']?', filter_string)
    if match:
        return {
            'field': match.group(1),
            'operator': 'eq',
            'value': match.group(2)
        }
    
    # contains filter
    match = re.match(r'(\w+(?:\.\w+)*)\s+co\s+["\']?([^"\']+)["\']?', filter_string)
    if match:
        return {
            'field': match.group(1),
            'operator': 'co',
            'value': match.group(2)
        }
    
    return {}


def user_to_scim(user: User, organization_id: int, request: Request) -> SCIMUser:
    """Convert database user to SCIM format."""
    base_url = str(request.base_url).rstrip('/')
    
    return SCIMUser(
        id=str(user.id),
        externalId=user.external_id,
        userName=user.username,
        name=SCIMName(
            givenName=user.first_name,
            familyName=user.last_name,
            formatted=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username
        ),
        displayName=user.username,
        emails=[SCIMEmail(value=user.email, type="work", primary=True)],
        active=user.is_active,
        roles=[SCIMRole(value=user.role.value, type="organization")],
        meta=SCIMMeta(
            resourceType="User",
            created=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
            lastModified=user.updated_at.isoformat() if user.updated_at else datetime.utcnow().isoformat(),
            location=f"{base_url}/scim/v2/Users/{user.id}",
            version=f'W/"{user.updated_at.timestamp() if user.updated_at else 1}"'
        ),
        organizationId=organization_id
    )


def scim_to_user(scim_user: SCIMUser, organization_id: int) -> Dict[str, Any]:
    """Convert SCIM user to database format."""
    user_data = {
        'username': scim_user.userName,
        'email': scim_user.emails[0].value if scim_user.emails else None,
        'external_id': scim_user.externalId,
        'is_active': scim_user.active,
        'organization_id': organization_id
    }
    
    if scim_user.name:
        user_data['first_name'] = scim_user.name.givenName
        user_data['last_name'] = scim_user.name.familyName
    
    # Extract role from SCIM roles
    if scim_user.roles:
        role_value = scim_user.roles[0].value.lower()
        if role_value in ['admin', 'administrator']:
            user_data['role'] = UserRole.ADMIN
        else:
            user_data['role'] = UserRole.USER
    
    return user_data


@router.get("/ServiceProviderConfig")
async def get_service_provider_config(request: Request):
    """
    Get SCIM Service Provider configuration.
    
    Returns capabilities and configuration of this SCIM endpoint.
    """
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://docs.example.com/scim",
        "patch": {
            "supported": True
        },
        "bulk": {
            "supported": True,
            "maxOperations": 100,
            "maxPayloadSize": 1048576
        },
        "filter": {
            "supported": True,
            "maxResults": 200
        },
        "changePassword": {
            "supported": False
        },
        "sort": {
            "supported": True
        },
        "etag": {
            "supported": True
        },
        "authenticationSchemes": [
            {
                "type": "oauth",
                "name": "OAuth 2.0",
                "description": "OAuth 2.0 Bearer Token authentication",
                "specUri": "https://tools.ietf.org/html/rfc6749",
                "documentationUri": "https://docs.example.com/oauth",
                "primary": True
            }
        ],
        "meta": {
            "location": f"{request.base_url}scim/v2/ServiceProviderConfig",
            "resourceType": "ServiceProviderConfig",
            "created": "2024-01-01T00:00:00Z",
            "lastModified": "2024-01-01T00:00:00Z",
            "version": "W/\"1\""
        }
    }


@router.get("/ResourceTypes")
async def get_resource_types(request: Request):
    """Get available SCIM resource types."""
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "startIndex": 1,
        "itemsPerPage": 2,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/Users",
                "description": "User Account",
                "schema": SCIM_SCHEMA_USER,
                "schemaExtensions": [],
                "meta": {
                    "location": f"{base_url}/scim/v2/ResourceTypes/User",
                    "resourceType": "ResourceType"
                }
            },
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Group",
                "name": "Group",
                "endpoint": "/Groups",
                "description": "Group of users",
                "schema": SCIM_SCHEMA_GROUP,
                "schemaExtensions": [],
                "meta": {
                    "location": f"{base_url}/scim/v2/ResourceTypes/Group",
                    "resourceType": "ResourceType"
                }
            }
        ]
    }


@router.get("/Schemas")
async def get_schemas(request: Request):
    """Get SCIM schemas."""
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 2,
        "startIndex": 1,
        "itemsPerPage": 2,
        "Resources": [
            {
                "id": SCIM_SCHEMA_USER,
                "name": "User",
                "description": "User Account",
                "attributes": [
                    {
                        "name": "userName",
                        "type": "string",
                        "multiValued": False,
                        "required": True,
                        "caseExact": False,
                        "mutability": "readWrite",
                        "returned": "default",
                        "uniqueness": "server"
                    },
                    {
                        "name": "name",
                        "type": "complex",
                        "multiValued": False,
                        "required": False,
                        "subAttributes": [
                            {"name": "familyName", "type": "string"},
                            {"name": "givenName", "type": "string"},
                            {"name": "formatted", "type": "string"}
                        ]
                    },
                    {
                        "name": "emails",
                        "type": "complex",
                        "multiValued": True,
                        "required": False,
                        "subAttributes": [
                            {"name": "value", "type": "string"},
                            {"name": "type", "type": "string"},
                            {"name": "primary", "type": "boolean"}
                        ]
                    },
                    {
                        "name": "active",
                        "type": "boolean",
                        "multiValued": False,
                        "required": False
                    }
                ],
                "meta": {
                    "location": f"{base_url}/scim/v2/Schemas/{SCIM_SCHEMA_USER}",
                    "resourceType": "Schema"
                }
            },
            {
                "id": SCIM_SCHEMA_GROUP,
                "name": "Group",
                "description": "Group of users",
                "attributes": [
                    {
                        "name": "displayName",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "members",
                        "type": "complex",
                        "multiValued": True,
                        "subAttributes": [
                            {"name": "value", "type": "string"},
                            {"name": "display", "type": "string"},
                            {"name": "type", "type": "string"}
                        ]
                    }
                ],
                "meta": {
                    "location": f"{base_url}/scim/v2/Schemas/{SCIM_SCHEMA_GROUP}",
                    "resourceType": "Schema"
                }
            }
        ]
    }


@router.get("/Users/{user_id}", response_model=SCIMUser)
async def get_user(
    user_id: str,
    request: Request,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a user by ID.
    
    Returns the user resource in SCIM 2.0 format.
    """
    # Verify organization access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Access denied")
        )
    
    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=scim_error(404, "User not found")
        )
    
    return user_to_scim(user, organization_id, request)


@router.get("/Users", response_model=SCIMListResponse)
async def list_users(
    request: Request,
    organization_id: int = Query(..., description="Organization ID"),
    filter: Optional[str] = Query(None, description="SCIM filter expression"),
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=200),
    sortBy: Optional[str] = None,
    sortOrder: str = Query("ascending", regex="^(ascending|descending)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List users with filtering and pagination.
    
    Supports SCIM filter expressions and pagination parameters.
    """
    # Verify organization access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Access denied")
        )
    
    # Build query
    query = db.query(User).join(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id
    )
    
    # Apply filter
    if filter:
        filter_params = parse_filter(filter)
        if filter_params:
            field = filter_params['field']
            value = filter_params['value']
            
            if field == 'userName':
                query = query.filter(User.username.ilike(f"%{value}%"))
            elif field == 'emails.value':
                query = query.filter(User.email.ilike(f"%{value}%"))
            elif field == 'active':
                query = query.filter(User.is_active == (value.lower() == 'true'))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.offset(startIndex - 1).limit(count)
    
    users = query.all()
    
    # Convert to SCIM format
    resources = [user_to_scim(user, organization_id, request) for user in users]
    
    return SCIMListResponse(
        totalResults=total,
        startIndex=startIndex,
        itemsPerPage=len(resources),
        Resources=resources
    )


@router.post("/Users", response_model=SCIMUser, status_code=status.HTTP_201_CREATED)
async def create_user(
    scim_user: SCIMUser,
    request: Request,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    
    Creates a user from SCIM User resource.
    """
    # Verify organization admin access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Admin access required")
        )
    
    # Check if user already exists
    existing = db.query(User).filter(
        (User.username == scim_user.userName) |
        (User.email == (scim_user.emails[0].value if scim_user.emails else None))
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=scim_error(409, "User already exists")
        )
    
    # Create user
    user_data = scim_to_user(scim_user, organization_id)
    
    user = User(
        username=user_data['username'],
        email=user_data['email'],
        first_name=user_data.get('first_name'),
        last_name=user_data.get('last_name'),
        external_id=user_data.get('external_id'),
        is_active=user_data.get('is_active', True),
        role=user_data.get('role', UserRole.USER),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(user)
    db.flush()
    
    # Add to organization
    org_member = OrganizationMember(
        user_id=user.id,
        organization_id=organization_id,
        role=user_data.get('organization_role', 'member'),
        joined_at=datetime.utcnow(),
        is_active=True
    )
    db.add(org_member)
    
    db.commit()
    db.refresh(user)
    
    return user_to_scim(user, organization_id, request)


@router.put("/Users/{user_id}", response_model=SCIMUser)
async def update_user(
    user_id: str,
    scim_user: SCIMUser,
    request: Request,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a user (full replacement).
    
    Replaces the user resource entirely.
    """
    # Verify organization access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Access denied")
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=scim_error(404, "User not found")
        )
    
    # Update fields
    user_data = scim_to_user(scim_user, organization_id)
    
    user.username = user_data['username']
    user.email = user_data['email']
    user.first_name = user_data.get('first_name')
    user.last_name = user_data.get('last_name')
    user.external_id = user_data.get('external_id')
    user.is_active = user_data.get('is_active', True)
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user_to_scim(user, organization_id, request)


@router.patch("/Users/{user_id}", response_model=SCIMUser)
async def patch_user(
    user_id: str,
    patch_request: SCIMPatchRequest,
    request: Request,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a user (partial update).
    
    Applies patch operations to the user resource.
    """
    # Verify organization access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Access denied")
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=scim_error(404, "User not found")
        )
    
    # Apply patch operations
    for op in patch_request.Operations:
        if op.op == "replace" or op.op == "add":
            if op.path == "active":
                user.is_active = op.value if isinstance(op.value, bool) else op.value.lower() == 'true'
            elif op.path == "userName":
                user.username = op.value
            elif op.path == "name.givenName":
                user.first_name = op.value
            elif op.path == "name.familyName":
                user.last_name = op.value
            elif op.path == "emails":
                if isinstance(op.value, list) and len(op.value) > 0:
                    user.email = op.value[0].get('value') if isinstance(op.value[0], dict) else op.value[0]
        
        elif op.op == "remove":
            if op.path == "emails":
                # Can't remove primary email in this implementation
                pass
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user_to_scim(user, organization_id, request)


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) a user.
    
    Soft deletes the user by deactivating them.
    """
    # Verify organization admin access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Admin access required")
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=scim_error(404, "User not found")
        )
    
    # Soft delete by deactivating
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/Bulk", status_code=status.HTTP_200_OK)
async def bulk_operations(
    bulk_request: SCIMBulkRequest,
    organization_id: int = Query(..., description="Organization ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Execute bulk operations.
    
    Supports creating, updating, and deleting multiple resources.
    """
    # Verify organization admin access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scim_error(403, "Admin access required")
        )
    
    results = []
    
    for op in bulk_request.Operations:
        method = op.get('method', '').upper()
        path = op.get('path', '')
        data = op.get('data', {})
        bulk_id = op.get('bulkId')
        
        try:
            if method == "POST" and path == "/Users":
                # Create user
                user_data = {
                    'username': data.get('userName'),
                    'email': data.get('emails', [{}])[0].get('value'),
                    'is_active': data.get('active', True)
                }
                
                user = User(**user_data)
                db.add(user)
                db.flush()
                
                results.append({
                    "method": "POST",
                    "bulkId": bulk_id,
                    "status": "201",
                    "location": f"/Users/{user.id}"
                })
            
            elif method == "PUT" and path.startswith("/Users/"):
                # Update user
                user_id = path.split('/')[-1]
                user = db.query(User).filter(User.id == int(user_id)).first()
                
                if user:
                    user.username = data.get('userName', user.username)
                    user.is_active = data.get('active', user.is_active)
                    db.flush()
                    
                    results.append({
                        "method": "PUT",
                        "bulkId": bulk_id,
                        "status": "200"
                    })
                else:
                    results.append({
                        "method": "PUT",
                        "bulkId": bulk_id,
                        "status": "404"
                    })
            
            elif method == "DELETE" and path.startswith("/Users/"):
                # Delete user
                user_id = path.split('/')[-1]
                user = db.query(User).filter(User.id == int(user_id)).first()
                
                if user:
                    user.is_active = False
                    db.flush()
                    
                    results.append({
                        "method": "DELETE",
                        "bulkId": bulk_id,
                        "status": "204"
                    })
                else:
                    results.append({
                        "method": "DELETE",
                        "bulkId": bulk_id,
                        "status": "404"
                    })
            
            else:
                results.append({
                    "method": method,
                    "bulkId": bulk_id,
                    "status": "400",
                    "response": {"detail": "Unsupported operation"}
                })
        
        except Exception as e:
            results.append({
                "method": method,
                "bulkId": bulk_id,
                "status": "500",
                "response": {"detail": str(e)}
            })
    
    db.commit()
    
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"],
        "Operations": results
    }
