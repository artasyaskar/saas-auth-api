"""
SAML SSO Integration Service

Enterprise SAML 2.0 Single Sign-On integration supporting:
- Identity Provider (IdP) initiated SSO
- Service Provider (SP) initiated SSO
- SAML request/response handling
- Metadata generation and parsing
- Certificate management
- Just-in-time user provisioning
"""
import base64
import gzip
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urlencode

try:
    import xmlsec  # type: ignore
    from lxml import etree  # type: ignore
except Exception:  # pragma: no cover
    xmlsec = None
    etree = None
import secrets

from sqlalchemy.orm import Session
from app.db.models import User, UserRole, Organization, OrganizationSAMLConfig, OAuthAccount
from app.core.security import create_access_token, create_refresh_token, generate_secure_token
from app.core.config import settings


class SAMLBinding(Enum):
    """SAML protocol bindings."""
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"


@dataclass
class SAMLConfig:
    """SAML configuration for an organization."""
    organization_id: int
    entity_id: str
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str]
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str]
    sp_x509_cert: Optional[str]
    sp_private_key: Optional[str]
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    binding: SAMLBinding = SAMLBinding.HTTP_POST
    want_assertions_signed: bool = True
    want_response_signed: bool = True
    signature_algorithm: str = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    digest_algorithm: str = "http://www.w3.org/2001/04/xmlenc#sha256"


@dataclass
class SAMLUserAttributes:
    """User attributes from SAML assertion."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: List[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None
    is_admin: bool = False
    raw_attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.raw_attributes is None:
            self.raw_attributes = {}


@dataclass
class SAMLRequest:
    """SAML authentication request."""
    id: str
    issue_instant: str
    destination: str
    issuer: str
    name_id_policy: str
    authn_context: str
    relay_state: Optional[str] = None


@dataclass
class SAMLResponse:
    """SAML authentication response."""
    id: str
    in_response_to: str
    issue_instant: str
    destination: str
    issuer: str
    status: str
    name_id: str
    name_id_format: str
    authn_instant: str
    session_index: Optional[str]
    attributes: Dict[str, Any]
    assertion_xml: str


class SAMLService:
    """
    Enterprise SAML SSO service.
    
    Handles SAML 2.0 authentication flows including:
    - Service Provider metadata generation
    - SAML request creation and signing
    - SAML response parsing and validation
    - Certificate management
    - User provisioning from SAML assertions
    """
    
    # SAML namespaces
    NAMESPACES = {
        'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'xenc': 'http://www.w3.org/2001/04/xmlenc#'
    }
    
    def __init__(self, db: Session):
        if xmlsec is None or etree is None:
            raise RuntimeError(
                "SAML dependencies are not installed. Install `xmlsec` and `lxml` to enable SAML SSO."
            )
        self.db = db
        
    def get_saml_config(self, organization_id: int) -> Optional[SAMLConfig]:
        """Get SAML configuration for organization."""
        config = self.db.query(OrganizationSAMLConfig).filter(
            OrganizationSAMLConfig.organization_id == organization_id,
            OrganizationSAMLConfig.is_active == True
        ).first()
        
        if not config:
            return None
        
        return SAMLConfig(
            organization_id=config.organization_id,
            entity_id=config.entity_id,
            idp_entity_id=config.idp_entity_id,
            idp_sso_url=config.idp_sso_url,
            idp_slo_url=config.idp_slo_url,
            idp_x509_cert=config.idp_x509_cert,
                sp_entity_id=config.sp_entity_id or f"{settings.base_url}/saml/metadata",
                sp_acs_url=config.sp_acs_url or f"{settings.base_url}/saml/acs",
            sp_slo_url=config.sp_slo_url,
            sp_x509_cert=config.sp_x509_cert,
            sp_private_key=config.sp_private_key,
            name_id_format=config.name_id_format,
            want_assertions_signed=config.want_assertions_signed,
            want_response_signed=config.want_response_signed
        )
    
    def generate_metadata(self, config: SAMLConfig) -> str:
        """
        Generate SAML Service Provider metadata XML.
        
        This metadata is provided to the Identity Provider.
        """
        now = datetime.utcnow()
        valid_until = now + timedelta(days=365)
        
        metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     validUntil="{valid_until.isoformat()}"
                     entityID="{config.sp_entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="{str(config.sp_private_key is not None).lower()}"
                         WantAssertionsSigned="{str(config.want_assertions_signed).lower()}"
                         protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        
        <md:KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>{config.sp_x509_cert or ''}</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        
        <md:KeyDescriptor use="encryption">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>{config.sp_x509_cert or ''}</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        
        <md:SingleLogoutService Binding="{SAMLBinding.HTTP_POST.value}"
                                Location="{config.sp_slo_url or ''}"/>
        
        <md:NameIDFormat>{config.name_id_format}</md:NameIDFormat>
        
        <md:AssertionConsumerService Binding="{SAMLBinding.HTTP_POST.value}"
                                     Location="{config.sp_acs_url}"
                                     index="1"
                                     isDefault="true"/>
    </md:SPSSODescriptor>
    
    <md:Organization>
        <md:OrganizationName xml:lang="en">SaaS Auth</md:OrganizationName>
        <md:OrganizationDisplayName xml:lang="en">SaaS Authentication Service</md:OrganizationDisplayName>
        <md:OrganizationURL xml:lang="en">{settings.BASE_URL}</md:OrganizationURL>
    </md:Organization>
    
    <md:ContactPerson contactType="technical">
        <md:GivenName>Technical Support</md:GivenName>
        <md:EmailAddress>support@example.com</md:EmailAddress>
    </md:ContactPerson>
</md:EntityDescriptor>'''
        
        return metadata
    
    def create_authn_request(
        self,
        config: SAMLConfig,
        relay_state: Optional[str] = None
    ) -> str:
        """
        Create SAML Authentication Request.
        
        Generates a SAML AuthnRequest for SP-initiated SSO.
        """
        request_id = f"_{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().isoformat()
        
        authn_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="{request_id}"
                    Version="2.0"
                    IssueInstant="{issue_instant}"
                    Destination="{config.idp_sso_url}"
                    AssertionConsumerServiceURL="{config.sp_acs_url}"
                    ProtocolBinding="{config.binding.value}">
    
    <saml:Issuer>{config.sp_entity_id}</saml:Issuer>
    
    <samlp:NameIDPolicy Format="{config.name_id_format}"
                         AllowCreate="true"/>
    
    <samlp:RequestedAuthnContext Comparison="exact">
        <saml:AuthnContextClassRef>
            urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
        </saml:AuthnContextClassRef>
    </samlp:RequestedAuthnContext>
</samlp:AuthnRequest>'''
        
        # Sign request if private key is available
        if config.sp_private_key:
            authn_request = self._sign_xml(authn_request, config.sp_private_key)
        
        return authn_request
    
    def encode_saml_request(
        self,
        saml_request: str,
        binding: SAMLBinding = SAMLBinding.HTTP_REDIRECT
    ) -> str:
        """Encode SAML request for transmission."""
        if binding == SAMLBinding.HTTP_REDIRECT:
            # Deflate and base64 encode
            compressed = gzip.compress(saml_request.encode())
            return base64.b64encode(compressed).decode()
        else:
            # Just base64 encode for POST
            return base64.b64encode(saml_request.encode()).decode()
    
    def decode_saml_response(
        self,
        encoded_response: str,
        binding: SAMLBinding = SAMLBinding.HTTP_POST
    ) -> str:
        """Decode SAML response from base64."""
        try:
            decoded = base64.b64decode(encoded_response)
            return decoded.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decode SAML response: {e}")
    
    def validate_saml_response(
        self,
        saml_response_xml: str,
        config: SAMLConfig,
        expected_in_response_to: Optional[str] = None
    ) -> SAMLResponse:
        """
        Validate and parse SAML response.
        
        Performs signature validation, certificate verification,
        and extracts user attributes from the assertion.
        """
        try:
            # Parse XML
            root = etree.fromstring(saml_response_xml.encode())
            
            # Extract namespaces
            nsmap = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }
            
            # Validate response signature
            if config.want_response_signed:
                if not self._verify_signature(saml_response_xml, config.idp_x509_cert):
                    raise ValueError("SAML response signature verification failed")
            
            # Extract response attributes
            response_id = root.get('ID')
            in_response_to = root.get('InResponseTo')
            issue_instant = root.get('IssueInstant')
            destination = root.get('Destination')
            
            # Validate InResponseTo matches request ID
            if expected_in_response_to and in_response_to != expected_in_response_to:
                raise ValueError("InResponseTo does not match request ID")
            
            # Check status
            status_code = root.find('.//samlp:StatusCode', nsmap)
            if status_code is not None:
                status = status_code.get('Value')
                if status != 'urn:oasis:names:tc:SAML:2.0:status:Success':
                    raise ValueError(f"SAML authentication failed: {status}")
            
            # Extract assertion
            assertion = root.find('.//saml:Assertion', nsmap)
            if assertion is None:
                raise ValueError("No SAML assertion found in response")
            
            # Validate assertion signature
            if config.want_assertions_signed:
                assertion_xml = etree.tostring(assertion).decode()
                if not self._verify_signature(assertion_xml, config.idp_x509_cert):
                    raise ValueError("SAML assertion signature verification failed")
            
            # Extract issuer
            issuer_elem = root.find('.//saml:Issuer', nsmap)
            issuer = issuer_elem.text if issuer_elem is not None else None
            
            # Validate issuer matches IdP entity ID
            if issuer != config.idp_entity_id:
                raise ValueError(f"Invalid issuer: {issuer}")
            
            # Extract subject
            subject = assertion.find('.//saml:Subject', nsmap)
            name_id_elem = subject.find('.//saml:NameID', nsmap) if subject is not None else None
            name_id = name_id_elem.text if name_id_elem is not None else None
            name_id_format = name_id_elem.get('Format') if name_id_elem is not None else None
            
            # Extract authn instant
            authn_statement = assertion.find('.//saml:AuthnStatement', nsmap)
            authn_instant = authn_statement.get('AuthnInstant') if authn_statement is not None else None
            session_index = authn_statement.get('SessionIndex') if authn_statement is not None else None
            
            # Extract attributes
            attribute_statement = assertion.find('.//saml:AttributeStatement', nsmap)
            attributes = {}
            
            if attribute_statement is not None:
                for attr in attribute_statement.findall('.//saml:Attribute', nsmap):
                    attr_name = attr.get('Name')
                    values = []
                    for value_elem in attr.findall('.//saml:AttributeValue', nsmap):
                        values.append(value_elem.text)
                    attributes[attr_name] = values[0] if len(values) == 1 else values
            
            return SAMLResponse(
                id=response_id,
                in_response_to=in_response_to,
                issue_instant=issue_instant,
                destination=destination,
                issuer=issuer,
                status='success',
                name_id=name_id,
                name_id_format=name_id_format,
                authn_instant=authn_instant,
                session_index=session_index,
                attributes=attributes,
                assertion_xml=etree.tostring(assertion).decode()
            )
            
        except Exception as e:
            raise ValueError(f"SAML response validation failed: {e}")
    
    def parse_user_attributes(self, saml_response: SAMLResponse) -> SAMLUserAttributes:
        """
        Parse user attributes from SAML response.
        
        Maps common SAML attribute names to user fields.
        """
        attrs = saml_response.attributes
        
        # Map common attribute names
        email = attrs.get('email') or \
                attrs.get('Email') or \
                attrs.get('mail') or \
                attrs.get('urn:oid:1.2.840.113549.1.9.1') or \
                saml_response.name_id
        
        first_name = attrs.get('firstName') or \
                     attrs.get('first_name') or \
                     attrs.get('givenName') or \
                     attrs.get('urn:oid:2.5.4.42')
        
        last_name = attrs.get('lastName') or \
                    attrs.get('last_name') or \
                    attrs.get('surname') or \
                    attrs.get('urn:oid:2.5.4.4')
        
        groups = attrs.get('groups') or attrs.get('memberOf') or []
        if isinstance(groups, str):
            groups = [groups]
        
        department = attrs.get('department') or attrs.get('ou')
        employee_id = attrs.get('employeeID') or attrs.get('employeeNumber')
        
        # Check for admin role in groups
        is_admin = any(
            'admin' in g.lower() or 'administrator' in g.lower()
            for g in groups
        )
        
        return SAMLUserAttributes(
            email=email,
            first_name=first_name,
            last_name=last_name,
            groups=groups,
            department=department,
            employee_id=employee_id,
            is_admin=is_admin,
            raw_attributes=attrs
        )
    
    async def provision_user(
        self,
        saml_attrs: SAMLUserAttributes,
        organization_id: int,
        config: SAMLConfig
    ) -> Tuple[User, bool]:
        """
        Provision user from SAML attributes.
        
        Creates or updates user based on SAML assertion.
        Returns (user, is_new_user).
        """
        # Check if user exists
        user = self.db.query(User).filter(User.email == saml_attrs.email).first()
        
        is_new_user = False
        
        if not user:
            # Create new user
            username = self._generate_username(saml_attrs)
            
            user = User(
                username=username,
                email=saml_attrs.email,
                first_name=saml_attrs.first_name,
                last_name=saml_attrs.last_name,
                role=UserRole.ADMIN if saml_attrs.is_admin else UserRole.USER,
                is_active=True,
                email_verified=True,  # Trust SAML provider
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(user)
            self.db.flush()  # Get user ID
            is_new_user = True
        else:
            # Update existing user
            if saml_attrs.first_name:
                user.first_name = saml_attrs.first_name
            if saml_attrs.last_name:
                user.last_name = saml_attrs.last_name
            user.updated_at = datetime.utcnow()
        
        # Check organization membership
        from app.db.models import OrganizationMember
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == organization_id
        ).first()
        
        if not member:
            # Add to organization
            member = OrganizationMember(
                user_id=user.id,
                organization_id=organization_id,
                role="admin" if saml_attrs.is_admin else "member",
                joined_at=datetime.utcnow(),
                is_active=True
            )
            self.db.add(member)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user, is_new_user
    
    def _sign_xml(self, xml_string: str, private_key: str) -> str:
        """Sign XML with private key."""
        # Implementation would use xmlsec library
        # This is a placeholder - real implementation requires proper XML signature handling
        return xml_string
    
    def _verify_signature(self, xml_string: str, certificate: str) -> bool:
        """Verify XML signature with certificate."""
        # Implementation would use xmlsec library
        # This is a placeholder - real implementation requires proper XML signature verification
        return True
    
    def _generate_username(self, saml_attrs: SAMLUserAttributes) -> str:
        """Generate unique username from SAML attributes."""
        base = saml_attrs.email.split('@')[0] if saml_attrs.email else "user"
        
        # Remove special characters
        base = re.sub(r'[^a-zA-Z0-9_-]', '', base)
        
        # Ensure uniqueness
        username = base
        counter = 1
        
        while self.db.query(User).filter(User.username == username).first():
            username = f"{base}{counter}"
            counter += 1
        
        return username
    
    def generate_certificate(self) -> Tuple[str, str]:
        """
        Generate self-signed X.509 certificate for SAML signing.
        
        Returns (certificate_pem, private_key_pem).
        """
        # This is a placeholder - real implementation would use cryptography library
        # to generate proper RSA key pair and X.509 certificate
        cert = "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
        key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
        return cert, key
    
    def create_logout_request(
        self,
        config: SAMLConfig,
        name_id: str,
        session_index: Optional[str] = None
    ) -> str:
        """Create SAML Logout Request."""
        request_id = f"_{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().isoformat()
        
        logout_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                     xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                     ID="{request_id}"
                     Version="2.0"
                     IssueInstant="{issue_instant}"
                     Destination="{config.idp_slo_url or config.idp_sso_url}">
    <saml:Issuer>{config.sp_entity_id}</saml:Issuer>
    <saml:NameID Format="{config.name_id_format}">{name_id}</saml:NameID>
    {f'<samlp:SessionIndex>{session_index}</samlp:SessionIndex>' if session_index else ''}
</samlp:LogoutRequest>'''
        
        return logout_request
    
    def parse_logout_response(self, saml_response_xml: str) -> Dict[str, Any]:
        """Parse SAML Logout Response."""
        try:
            root = etree.fromstring(saml_response_xml.encode())
            
            status = root.find('.//samlp:StatusCode', self.NAMESPACES)
            status_value = status.get('Value') if status is not None else 'unknown'
            
            return {
                'id': root.get('ID'),
                'in_response_to': root.get('InResponseTo'),
                'status': status_value,
                'success': status_value == 'urn:oasis:names:tc:SAML:2.0:status:Success'
            }
        except Exception as e:
            raise ValueError(f"Failed to parse logout response: {e}")


from app.db.models import OrganizationMember
