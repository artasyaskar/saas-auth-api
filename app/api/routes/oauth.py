"""
OAuth2/OIDC API Routes

Provides endpoints for social authentication with Google, GitHub, Microsoft,
and other OAuth2/OIDC providers. Includes authorization URL generation,
callback handling, token exchange, and account linking.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
import secrets
import json

from app.db.session import get_db
from app.db.models import User, UserRole, OAuthAccount, OAuthProvider
from app.core.security import create_access_token, create_refresh_token, generate_secure_token
from app.services.oauth import (
    OAuth2Service,
    OAuthProviderType,
    OAuthConfig,
    OAuthTokenResponse,
    OAuthUserInfo,
    get_oauth_config,
    generate_pkce_challenge,
    verify_state_token
)
from app.api.auth import get_current_active_user
from app.core.config import settings


router = APIRouter(prefix="/oauth", tags=["oauth"])


class OAuthProviderResponse(BaseModel):
    """OAuth provider information."""
    id: str
    name: str
    icon_url: Optional[str] = None
    enabled: bool


class OAuthAuthorizationRequest(BaseModel):
    """Request to initiate OAuth authorization."""
    provider: str
    redirect_uri: Optional[str] = None
    scopes: Optional[list] = None
    state: Optional[str] = None


class OAuthAuthorizationResponse(BaseModel):
    """OAuth authorization URL response."""
    authorization_url: str
    state: str
    code_verifier: Optional[str] = None
    provider: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""
    code: str
    state: str
    code_verifier: Optional[str] = None


class OAuthTokenExchangeRequest(BaseModel):
    """Token exchange request."""
    provider: str
    code: str
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = None


class OAuthLoginResponse(BaseModel):
    """OAuth login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    is_new_user: bool
    provider: str
    linked_accounts: list


class OAuthAccountInfo(BaseModel):
    """Linked OAuth account information."""
    id: int
    provider: str
    provider_user_id: str
    email: Optional[str]
    name: Optional[str]
    picture: Optional[str]
    linked_at: str
    last_used_at: Optional[str]


class LinkOAuthAccountRequest(BaseModel):
    """Request to link OAuth account to existing user."""
    provider: str
    code: str
    state: str
    code_verifier: Optional[str] = None


def get_enabled_providers() -> list:
    """Get list of enabled OAuth providers."""
    providers = []
    
    if settings.GOOGLE_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            id="google",
            name="Google",
            icon_url="/static/icons/google.svg",
            enabled=True
        ))
    
    if settings.GITHUB_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            id="github",
            name="GitHub",
            icon_url="/static/icons/github.svg",
            enabled=True
        ))
    
    if settings.MICROSOFT_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            id="microsoft",
            name="Microsoft",
            icon_url="/static/icons/microsoft.svg",
            enabled=True
        ))
    
    if settings.APPLE_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            id="apple",
            name="Apple",
            icon_url="/static/icons/apple.svg",
            enabled=True
        ))
    
    if settings.OKTA_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            id="okta",
            name="Okta",
            icon_url="/static/icons/okta.svg",
            enabled=True
        ))
    
    return providers


@router.get("/providers", response_model=list)
async def list_oauth_providers():
    """
    List all enabled OAuth providers.
    
    Returns providers configured in application settings.
    """
    return get_enabled_providers()


@router.get("/{provider}/url", response_model=OAuthAuthorizationResponse)
async def get_oauth_authorization_url(
    provider: str,
    redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    scopes: Optional[str] = Query(None)
):
    """
    Get OAuth authorization URL for a provider.
    
    - **provider**: OAuth provider (google, github, microsoft, apple, okta)
    - **redirect_uri**: Optional custom redirect URI
    - **state**: Optional state parameter for CSRF protection
    - **scopes**: Optional comma-separated list of scopes
    
    Returns authorization URL, state token, and PKCE code verifier.
    """
    try:
        provider_type = OAuthProviderType(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    # Check if provider is enabled
    enabled_providers = {p.id for p in get_enabled_providers()}
    if provider.lower() not in enabled_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not enabled"
        )
    
    # Generate state if not provided
    state_token = state or secrets.token_urlsafe(32)
    
    # Generate PKCE challenge
    code_verifier, code_challenge = generate_pkce_challenge()
    
    # Build authorization URL
    config = get_oauth_config(provider_type)
    
    # Override redirect URI if provided
    if redirect_uri:
        auth_url = config.authorization_url
    else:
        redirect_uri = f"{settings.FRONTEND_URL}/auth/callback"
    
    # Build authorization parameters
    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state_token,
    }
    
    # Add PKCE if enabled
    if config.pkce:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    
    # Build full URL
    from urllib.parse import urlencode
    authorization_url = f"{config.authorization_url}?{urlencode(params)}"
    
    return OAuthAuthorizationResponse(
        authorization_url=authorization_url,
        state=state_token,
        code_verifier=code_verifier if config.pkce else None,
        provider=provider
    )


@router.post("/callback", response_model=OAuthLoginResponse)
async def handle_oauth_callback(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and exchange code for tokens.
    
    Exchanges authorization code for access token, creates or links user,
    and returns JWT tokens for application authentication.
    """
    # Verify state token (in production, validate against stored state)
    if not verify_state_token(request.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )
    
    # Get provider from state or request
    # In production, store provider in state/session
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use provider-specific callback endpoints"
    )


@router.post("/{provider}/callback", response_model=OAuthLoginResponse)
async def handle_provider_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    code_verifier: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback for a specific provider.
    
    This endpoint receives the authorization code from the OAuth provider
    after user consent. It exchanges the code for tokens and creates/links
    the user account.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}"
        )
    
    try:
        provider_type = OAuthProviderType(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    # Initialize OAuth service
    oauth_service = OAuth2Service(db)
    
    # Get redirect URI
    redirect_uri = f"{settings.FRONTEND_URL}/auth/callback"
    
    try:
        # Exchange code for tokens and user info
        oauth_user, is_new_user = await oauth_service.authenticate_with_provider(
            provider=provider_type,
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )
        
        # Get or create user
        user = await oauth_service.get_or_create_user(oauth_user, provider_type)
        
        # Generate JWT tokens
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        # Get linked accounts
        linked_accounts = db.query(OAuthAccount).filter(
            OAuthAccount.user_id == user.id
        ).all()
        
        account_list = []
        for account in linked_accounts:
            account_list.append({
                "provider": account.provider.value,
                "email": account.email,
                "linked_at": account.created_at.isoformat() if account.created_at else None
            })
        
        return OAuthLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active
            },
            is_new_user=is_new_user,
            provider=provider,
            linked_accounts=account_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


@router.post("/token/exchange", response_model=OAuthLoginResponse)
async def exchange_oauth_token(
    request: OAuthTokenExchangeRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange OAuth authorization code for application tokens.
    
    Server-side token exchange for enhanced security.
    """
    try:
        provider_type = OAuthProviderType(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {request.provider}"
        )
    
    oauth_service = OAuth2Service(db)
    
    try:
        oauth_user, is_new_user = await oauth_service.authenticate_with_provider(
            provider=provider_type,
            code=request.code,
            redirect_uri=request.redirect_uri or f"{settings.FRONTEND_URL}/auth/callback",
            code_verifier=request.code_verifier
        )
        
        user = await oauth_service.get_or_create_user(oauth_user, provider_type)
        
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        return OAuthLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active
            },
            is_new_user=is_new_user,
            provider=request.provider,
            linked_accounts=[]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {str(e)}"
        )


@router.get("/accounts", response_model=list)
async def list_linked_oauth_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all OAuth accounts linked to the current user.
    
    Returns information about connected social login providers.
    """
    accounts = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == current_user.id
    ).all()
    
    result = []
    for account in accounts:
        result.append(OAuthAccountInfo(
            id=account.id,
            provider=account.provider.value,
            provider_user_id=account.provider_user_id,
            email=account.email,
            name=account.name,
            picture=account.picture,
            linked_at=account.created_at.isoformat() if account.created_at else None,
            last_used_at=account.updated_at.isoformat() if account.updated_at else None
        ))
    
    return result


@router.post("/accounts/link", response_model=OAuthAccountInfo)
async def link_oauth_account(
    request: LinkOAuthAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Link an OAuth account to the current user.
    
    Allows users to connect additional social login providers to their account.
    """
    try:
        provider_type = OAuthProviderType(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {request.provider}"
        )
    
    oauth_service = OAuth2Service(db)
    
    try:
        oauth_user, _ = await oauth_service.authenticate_with_provider(
            provider=provider_type,
            code=request.code,
            redirect_uri=f"{settings.FRONTEND_URL}/auth/callback",
            code_verifier=request.code_verifier
        )
        
        # Link account to user
        account = await oauth_service.link_oauth_account(
            user=current_user,
            oauth_user=oauth_user,
            provider=provider_type
        )
        
        return OAuthAccountInfo(
            id=account.id,
            provider=account.provider.value,
            provider_user_id=account.provider_user_id,
            email=account.email,
            name=account.name,
            picture=account.picture,
            linked_at=account.created_at.isoformat() if account.created_at else None,
            last_used_at=account.updated_at.isoformat() if account.updated_at else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to link account: {str(e)}"
        )


@router.delete("/accounts/{account_id}")
async def unlink_oauth_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Unlink an OAuth account from the current user.
    
    Removes the connection to a social login provider.
    """
    # Find account
    account = db.query(OAuthAccount).filter(
        OAuthAccount.id == account_id,
        OAuthAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth account not found"
        )
    
    # Check if this is the last login method
    other_accounts = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.id != account_id
    ).count()
    
    # If no other OAuth accounts and user has no password, prevent unlinking
    if other_accounts == 0 and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink last login method. Set a password first."
        )
    
    # Delete account
    db.delete(account)
    db.commit()
    
    return {"message": "OAuth account unlinked successfully"}


@router.post("/refresh/{provider}")
async def refresh_oauth_token(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Refresh OAuth access token for a provider.
    
    Used when the OAuth access token expires and needs refreshing.
    """
    try:
        provider_type = OAuthProviderType(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    # Find account
    account = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.provider == provider_type
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No linked {provider} account found"
        )
    
    if not account.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available"
        )
    
    oauth_service = OAuth2Service(db)
    
    try:
        new_tokens = await oauth_service.refresh_access_token(
            provider=provider_type,
            refresh_token=account.refresh_token
        )
        
        # Update stored tokens
        account.access_token = new_tokens.access_token
        if new_tokens.refresh_token:
            account.refresh_token = new_tokens.refresh_token
        account.token_expires_at = datetime.utcnow() + timedelta(seconds=new_tokens.expires_in) if new_tokens.expires_in else None
        account.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Token refreshed successfully",
            "expires_in": new_tokens.expires_in
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh token: {str(e)}"
        )


from datetime import datetime, timedelta
