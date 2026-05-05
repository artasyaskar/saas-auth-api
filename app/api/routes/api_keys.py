"""
API Key management endpoints for programmatic access.
Allows users to create and manage API keys for service-to-service authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import User, APIKey as ApiKey
from app.api.auth import get_current_active_user
from app.core.security import generate_secure_token, hash_token

router = APIRouter()


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")
    expires_days: Optional[int] = Field(90, ge=1, le=365, description="Days until expiration")
    scopes: List[str] = Field(default=["read"], description="Permission scopes")


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_preview: str
    scopes: List[str]
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_used_at: Optional[datetime]


class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    api_key: str  # Only shown once on creation
    scopes: List[str]
    expires_at: datetime
    message: str


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = Field(None, description="Permission scopes")


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for programmatic access.
    
    The full API key is only shown once during creation.
    Store it securely - it cannot be retrieved again.
    """
    # Generate secure API key
    raw_key = f"sk_{generate_secure_token(32)}"
    hashed_key = hash_token(raw_key)
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)
    
    # Create API key record
    api_key = ApiKey(
        user_id=current_user.id,
        name=key_data.name,
        key_hash=hashed_key,
        scopes=key_data.scopes,
        is_active=True,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at,
        "message": "Store this API key securely - it won't be shown again"
    }


@router.get("/", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    include_revoked: bool = False
):
    """List all API keys for the current user."""
    query = db.query(ApiKey).filter(ApiKey.user_id == current_user.id)
    
    if not include_revoked:
        query = query.filter(ApiKey.is_active == True)
    
    api_keys = query.order_by(ApiKey.created_at.desc()).all()
    
    return [
        {
            "id": key.id,
            "name": key.name,
            "key_preview": f"{key.key_hash[:8]}..." if key.key_hash else "...",
            "scopes": key.scopes or ["read"],
            "is_active": key.is_active,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "last_used_at": key.last_used_at
        }
        for key in api_keys
    ]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific API key."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_preview": f"{api_key.key_hash[:8]}..." if api_key.key_hash else "...",
        "scopes": api_key.scopes or ["read"],
        "is_active": api_key.is_active,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at
    }


@router.put("/{key_id}")
async def update_api_key(
    key_id: int,
    update_data: ApiKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update API key name or scopes."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    if update_data.name:
        api_key.name = update_data.name
    
    if update_data.scopes:
        api_key.scopes = update_data.scopes
    
    api_key.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "API key updated successfully"}


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    api_key.revoked_reason = "user_requested"
    db.commit()
    
    return {"message": "API key revoked successfully"}


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Permanently delete an API key."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted permanently"}
