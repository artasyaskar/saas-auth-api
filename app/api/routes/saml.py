"""
SAML SSO API Routes

Enterprise SAML 2.0 Single Sign-On endpoints:
- Service Provider metadata
- SSO initiation (SP and IdP initiated)
- SAML assertion consumer service
- Single logout
- Certificate management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs
import base64
import gzip

from app.db.session import get_db
from app.db.models import User, Organization, OrganizationSAMLConfig
from app.api.auth import get_current_active_user
from app.services.saml_sso import SAMLService, SAMLBinding
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings


router = APIRouter(prefix="/saml", tags=["saml"])


class SAMLConfigRequest(BaseModel):
    """SAML configuration request."""
    idp_entity_id: str = Field(..., description="Identity Provider Entity ID")
    idp_sso_url: str = Field(..., description="Identity Provider SSO URL")
    idp_slo_url: Optional[str] = Field(None, description="Identity Provider SLO URL")
    idp_x509_cert: str = Field(..., description="Identity Provider X.509 Certificate")
    name_id_format: str = Field("urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", description="Name ID Format")
    want_assertions_signed: bool = Field(True, description="Require signed assertions")
    want_response_signed: bool = Field(True, description="Require signed response")


class SAMLConfigResponse(BaseModel):
    """SAML configuration response."""
    entity_id: str
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str]
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str]
    name_id_format: str
    want_assertions_signed: bool
    want_response_signed: bool
    is_active: bool
    created_at: str


class SAMLInitRequest(BaseModel):
    """SAML SSO initiation request."""
    organization_id: int
    relay_state: Optional[str] = None


def get_saml_service(db: Session) -> SAMLService:
    """Get SAML service instance."""
    return SAMLService(db)


@router.get("/metadata", response_class=HTMLResponse)
async def get_metadata(
    organization_id: int = Query(..., description="Organization ID"),
    db: Session = Depends(get_db)
):
    """
    Get Service Provider metadata.
    
    Returns SAML 2.0 SP metadata XML for the specified organization.
    This is provided to the Identity Provider for SP configuration.
    """
    saml_service = get_saml_service(db)
    
    # Get SAML configuration
    config = saml_service.get_saml_config(organization_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found for organization"
        )
    
    # Generate metadata
    metadata = saml_service.generate_metadata(config)
    
    return Response(
        content=metadata,
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=metadata.xml"}
    )


@router.get("/sso")
async def initiate_sso(
    organization_id: int,
    relay_state: Optional[str] = Query(None),
    binding: str = Query("HTTP-POST", regex="^(HTTP-POST|HTTP-Redirect)$"),
    db: Session = Depends(get_db)
):
    """
    Initiate SAML SSO (SP-initiated).
    
    Redirects user to Identity Provider for authentication.
    """
    saml_service = get_saml_service(db)
    
    # Get SAML configuration
    config = saml_service.get_saml_config(organization_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found for organization"
        )
    
    # Create SAML authentication request
    authn_request = saml_service.create_authn_request(config, relay_state)
    
    # Encode request
    saml_binding = SAMLBinding.HTTP_POST if binding == "HTTP-POST" else SAMLBinding.HTTP_REDIRECT
    encoded_request = saml_service.encode_saml_request(authn_request, saml_binding)
    
    if saml_binding == SAMLBinding.HTTP_REDIRECT:
        # Redirect binding
        params = {
            "SAMLRequest": encoded_request,
            "RelayState": relay_state or ""
        }
        
        redirect_url = f"{config.idp_sso_url}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)
    
    else:
        # POST binding - return HTML form
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SAML SSO</title>
</head>
<body onload="document.forms[0].submit()">
    <form method="post" action="{config.idp_sso_url}">
        <input type="hidden" name="SAMLRequest" value="{encoded_request}">
        <input type="hidden" name="RelayState" value="{relay_state or ''}">
        <p>Redirecting to Identity Provider...</p>
        <button type="submit">Continue</button>
    </form>
</body>
</html>'''
        
        return HTMLResponse(content=html)


@router.post("/acs")
async def assertion_consumer_service(
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    SAML Assertion Consumer Service.
    
    Processes SAML response from Identity Provider and authenticates user.
    """
    saml_service = get_saml_service(db)
    
    try:
        # Decode SAML response
        saml_response_xml = saml_service.decode_saml_response(SAMLResponse)
        
        # Find organization from response issuer
        # In production, you'd parse the issuer to find the organization
        # For now, we'll assume the organization ID is in RelayState
        
        organization_id = None
        if RelayState and RelayState.isdigit():
            organization_id = int(RelayState)
        else:
            # Parse issuer from response to find organization
            # This is simplified - in production you'd have a mapping
            import xml.etree.ElementTree as ET
            root = ET.fromstring(saml_response_xml)
            issuer = root.find('.//{urn:oasis:names:tc:SAML:2.0:assertion}Issuer')
            if issuer is not None:
                issuer_entity_id = issuer.text
                # Find organization by IdP entity ID
                saml_config = db.query(OrganizationSAMLConfig).filter(
                    OrganizationSAMLConfig.idp_entity_id == issuer_entity_id,
                    OrganizationSAMLConfig.is_active == True
                ).first()
                if saml_config:
                    organization_id = saml_config.organization_id
        
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to determine organization"
            )
        
        # Get SAML configuration
        config = saml_service.get_saml_config(organization_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML configuration not found"
            )
        
        # Validate SAML response
        saml_response = saml_service.validate_saml_response(saml_response_xml, config)
        
        # Parse user attributes
        user_attrs = saml_service.parse_user_attributes(saml_response)
        
        # Provision user
        user, is_new = await saml_service.provision_user(user_attrs, organization_id, config)
        
        # Create authentication tokens
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})
        
        # Store session info
        # In production, you'd store the SAML session index for logout
        
        # Redirect to frontend with tokens
        redirect_url = f"{settings.FRONTEND_URL}/auth/saml/callback?access_token={access_token}&refresh_token={refresh_token}"
        
        if RelayState and RelayState != str(organization_id):
            redirect_url += f"&state={RelayState}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SAML authentication failed: {str(e)}"
        )


@router.get("/slo")
async def initiate_logout(
    organization_id: int,
    name_id: str,
    session_index: Optional[str] = None,
    relay_state: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Initiate SAML Single Logout.
    
    Sends logout request to Identity Provider.
    """
    saml_service = get_saml_service(db)
    
    # Get SAML configuration
    config = saml_service.get_saml_config(organization_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found"
        )
    
    if not config.idp_slo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Single Logout not configured"
        )
    
    # Create logout request
    logout_request = saml_service.create_logout_request(config, name_id, session_index)
    
    # Encode request
    encoded_request = base64.b64encode(logout_request.encode()).decode()
    
    # Redirect to IdP
    params = {
        "SAMLRequest": encoded_request,
        "RelayState": relay_state or ""
    }
    
    redirect_url = f"{config.idp_slo_url}?{urlencode(params)}"
    return RedirectResponse(url=redirect_url)


@router.post("/slo")
async def logout_response(
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Process SAML Logout Response.
    
    Handles logout response from Identity Provider.
    """
    saml_service = get_saml_service(db)
    
    try:
        # Decode SAML response
        saml_response_xml = saml_service.decode_saml_response(SAMLResponse)
        
        # Parse logout response
        logout_response = saml_service.parse_logout_response(saml_response_xml)
        
        if logout_response['success']:
            # Logout successful - redirect to frontend
            redirect_url = f"{settings.FRONTEND_URL}/logout?success=true"
        else:
            # Logout failed
            redirect_url = f"{settings.FRONTEND_URL}/logout?success=false&error={logout_response.get('status', 'unknown')}"
        
        if RelayState:
            redirect_url += f"&state={RelayState}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SAML logout failed: {str(e)}"
        )


@router.post("/config", response_model=SAMLConfigResponse)
async def create_saml_config(
    request: SAMLConfigRequest,
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create SAML configuration for organization.
    
    Sets up SAML SSO integration for an organization.
    """
    # Check admin permissions
    from app.db.models import OrganizationMember, OrganizationRole
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Check if config already exists
    existing = db.query(OrganizationSAMLConfig).filter(
        OrganizationSAMLConfig.organization_id == organization_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SAML configuration already exists"
        )
    
    # Generate SP entity ID and URLs
    sp_entity_id = f"{settings.BASE_URL}/saml/metadata?organization_id={organization_id}"
    sp_acs_url = f"{settings.BASE_URL}/saml/acs"
    sp_slo_url = f"{settings.BASE_URL}/saml/slo"
    
    # Create SAML configuration
    saml_config = OrganizationSAMLConfig(
        organization_id=organization_id,
        entity_id=sp_entity_id,
        idp_entity_id=request.idp_entity_id,
        idp_sso_url=request.idp_sso_url,
        idp_slo_url=request.idp_slo_url,
        idp_x509_cert=request.idp_x509_cert,
        sp_entity_id=sp_entity_id,
        sp_acs_url=sp_acs_url,
        sp_slo_url=sp_slo_url,
        name_id_format=request.name_id_format,
        want_assertions_signed=request.want_assertions_signed,
        want_response_signed=request.want_response_signed,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(saml_config)
    db.commit()
    db.refresh(saml_config)
    
    return SAMLConfigResponse(
        entity_id=saml_config.entity_id,
        idp_entity_id=saml_config.idp_entity_id,
        idp_sso_url=saml_config.idp_sso_url,
        idp_slo_url=saml_config.idp_slo_url,
        sp_entity_id=saml_config.sp_entity_id,
        sp_acs_url=saml_config.sp_acs_url,
        sp_slo_url=saml_config.sp_slo_url,
        name_id_format=saml_config.name_id_format,
        want_assertions_signed=saml_config.want_assertions_signed,
        want_response_signed=saml_config.want_response_signed,
        is_active=saml_config.is_active,
        created_at=saml_config.created_at.isoformat()
    )


@router.get("/config", response_model=SAMLConfigResponse)
async def get_saml_config(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get SAML configuration for organization."""
    from app.db.models import OrganizationMember
    
    # Check member access
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    config = db.query(OrganizationSAMLConfig).filter(
        OrganizationSAMLConfig.organization_id == organization_id,
        OrganizationSAMLConfig.is_active == True
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found"
        )
    
    return SAMLConfigResponse(
        entity_id=config.entity_id,
        idp_entity_id=config.idp_entity_id,
        idp_sso_url=config.idp_sso_url,
        idp_slo_url=config.idp_slo_url,
        sp_entity_id=config.sp_entity_id,
        sp_acs_url=config.sp_acs_url,
        sp_slo_url=config.sp_slo_url,
        name_id_format=config.name_id_format,
        want_assertions_signed=config.want_assertions_signed,
        want_response_signed=config.want_response_signed,
        is_active=config.is_active,
        created_at=config.created_at.isoformat()
    )


@router.patch("/config")
async def update_saml_config(
    organization_id: int,
    request: SAMLConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update SAML configuration."""
    from app.db.models import OrganizationMember, OrganizationRole
    
    # Check admin permissions
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    config = db.query(OrganizationSAMLConfig).filter(
        OrganizationSAMLConfig.organization_id == organization_id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found"
        )
    
    # Update fields
    config.idp_entity_id = request.idp_entity_id
    config.idp_sso_url = request.idp_sso_url
    config.idp_slo_url = request.idp_slo_url
    config.idp_x509_cert = request.idp_x509_cert
    config.name_id_format = request.name_id_format
    config.want_assertions_signed = request.want_assertions_signed
    config.want_response_signed = request.want_response_signed
    config.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "SAML configuration updated successfully"}


@router.delete("/config")
async def delete_saml_config(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete SAML configuration."""
    from app.db.models import OrganizationMember, OrganizationRole
    
    # Check owner permissions
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == 'owner'
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required"
        )
    
    config = db.query(OrganizationSAMLConfig).filter(
        OrganizationSAMLConfig.organization_id == organization_id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found"
        )
    
    # Soft delete
    config.is_active = False
    config.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "SAML configuration deleted successfully"}


@router.post("/test")
async def test_saml_connection(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Test SAML configuration.
    
    Validates IdP connectivity and certificate.
    """
    from app.db.models import OrganizationMember, OrganizationRole
    
    # Check admin permissions
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    saml_service = get_saml_service(db)
    
    # Get SAML configuration
    config = saml_service.get_saml_config(organization_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML configuration not found"
        )
    
    # Test IdP connectivity
    try:
        import requests
        response = requests.get(config.idp_sso_url, timeout=10)
        idp_reachable = response.status_code == 200
    except:
        idp_reachable = False
    
    # Test certificate validation
    cert_valid = True
    try:
        # Basic certificate validation
        import ssl
        import base64
        cert_der = base64.b64decode(config.idp_x509_cert)
        cert = ssl.DER_cert_to_PEM_cert(cert_der)
        # In production, do more thorough validation
    except:
        cert_valid = False
    
    return {
        "idp_reachable": idp_reachable,
        "certificate_valid": cert_valid,
        "configuration_complete": idp_reachable and cert_valid
    }


from fastapi import Form
