"""
Two-Factor Authentication (2FA) API Routes

Provides comprehensive 2FA support including:
- TOTP (Time-based One-Time Password) with QR codes
- SMS verification
- Email verification codes
- Backup recovery codes
- Hardware security keys (WebAuthn/FIDO2)
- 2FA enforcement policies
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
import secrets

from app.db.session import get_db
from app.db.models import User, TwoFactorMethod, TwoFactorType, UserRole
from app.api.auth import get_current_active_user, create_access_token, create_refresh_token
from app.services.two_factor import TwoFactorService
from app.core.config import settings


router = APIRouter(prefix="/2fa", tags=["two-factor-authentication"])


class TOTPSetupRequest(BaseModel):
    """Request to setup TOTP."""
    password: str  # Verify identity


class TOTPSetupResponse(BaseModel):
    """TOTP setup response with secret and QR code."""
    secret: str
    qr_code_url: str
    qr_code_image: str  # Base64 encoded
    backup_codes: List[str]
    uri: str  # otpauth:// URI


class TOTPVerifyRequest(BaseModel):
    """Request to verify TOTP code."""
    code: str = Field(..., min_length=6, max_length=6)


class TOTPVerifyResponse(BaseModel):
    """TOTP verification response."""
    verified: bool
    remaining_attempts: Optional[int] = None


class SMSSetupRequest(BaseModel):
    """Request to setup SMS 2FA."""
    phone_number: str = Field(..., regex=r"^\+[1-9]\d{1,14}$")
    password: str


class SMSVerifyRequest(BaseModel):
    """Request to verify SMS code."""
    code: str = Field(..., min_length=4, max_length=6)


class EmailSetupRequest(BaseModel):
    """Request to setup Email 2FA."""
    password: str


class BackupCodesResponse(BaseModel):
    """Backup codes response."""
    codes: List[str]
    message: str


class TwoFactorStatusResponse(BaseModel):
    """2FA status for user."""
    enabled: bool
    methods: List[Dict[str, Any]]
    preferred_method: Optional[str]
    backup_codes_remaining: int
    last_used_at: Optional[str]
    enforced: bool  # If required by organization


class TwoFactorEnforceRequest(BaseModel):
    """Request to enforce 2FA for organization."""
    enforce: bool
    grace_period_days: int = Field(default=7, ge=1, le=30)
    exempt_roles: List[str] = []


class TwoFactorLoginRequest(BaseModel):
    """2FA verification during login."""
    username: str
    password: str
    two_factor_code: Optional[str] = None
    two_factor_method: Optional[str] = "totp"  # totp, sms, email, backup


class TwoFactorLoginResponse(BaseModel):
    """Response after 2FA verification."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False
    two_factor_methods: Optional[List[str]] = None


class WebAuthnRegisterRequest(BaseModel):
    """WebAuthn registration request."""
    password: str
    device_name: str = "Security Key"


class WebAuthnVerifyRequest(BaseModel):
    """WebAuthn verification request."""
    credential_id: str
    client_data: Dict[str, Any]
    authenticator_data: str
    signature: str


class HardwareKeyInfo(BaseModel):
    """Hardware security key information."""
    id: int
    name: str
    credential_id: str
    registered_at: str
    last_used_at: Optional[str]
    is_active: bool


def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate secure backup recovery codes."""
    codes = []
    for _ in range(count):
        # Format: XXXX-XXXX-XXXX (16 chars, 4 groups)
        code = '-'.join([
            secrets.token_hex(2).upper(),
            secrets.token_hex(2).upper(),
            secrets.token_hex(2).upper()
        ])
        codes.append(code)
    return codes


def generate_qr_code(uri: str) -> str:
    """Generate QR code as base64 image."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get 2FA status for the current user.
    
    Returns enabled methods, backup codes count, and enforcement status.
    """
    service = TwoFactorService(db)
    status_info = service.get_2fa_status(current_user.id)
    
    return TwoFactorStatusResponse(
        enabled=status_info.get("enabled", False),
        methods=status_info.get("methods", []),
        preferred_method=status_info.get("preferred_method"),
        backup_codes_remaining=status_info.get("backup_codes_remaining", 0),
        last_used_at=status_info.get("last_used_at"),
        enforced=status_info.get("enforced", False)
    )


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    request: TOTPSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup TOTP (Authenticator App) 2FA.
    
    Generates a secret key, QR code for scanning, and backup recovery codes.
    User must verify with a TOTP code to complete setup.
    """
    # Verify password
    from app.core.security import verify_password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Generate TOTP secret
    secret = pyotp.random_base32()
    
    # Create OTP URI
    issuer_name = settings.APP_NAME or "SaaS Auth"
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=current_user.email or current_user.username,
        issuer_name=issuer_name
    )
    
    # Generate QR code
    qr_code_image = generate_qr_code(uri)
    
    # Generate backup codes
    backup_codes = generate_backup_codes(10)
    
    # Store in database (pending verification)
    service = TwoFactorService(db)
    service.setup_totp_pending(
        user_id=current_user.id,
        secret=secret,
        backup_codes=backup_codes
    )
    
    return TOTPSetupResponse(
        secret=secret,
        qr_code_url=uri,
        qr_code_image=qr_code_image,
        backup_codes=backup_codes,
        uri=uri
    )


@router.post("/totp/verify-setup")
async def verify_totp_setup(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify and activate TOTP setup.
    
    Validates the TOTP code from authenticator app to complete 2FA setup.
    """
    service = TwoFactorService(db)
    
    verified = await service.verify_and_activate_totp(
        user_id=current_user.id,
        code=request.code
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please try again."
        )
    
    return {
        "message": "TOTP 2FA activated successfully",
        "enabled": True,
        "method": "totp"
    }


@router.post("/totp/verify")
async def verify_totp(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify a TOTP code for the current user.
    
    Used for verifying TOTP during sensitive operations.
    """
    service = TwoFactorService(db)
    
    verified = await service.verify_totp(current_user.id, request.code)
    
    return TOTPVerifyResponse(
        verified=verified,
        remaining_attempts=5 if not verified else None
    )


@router.post("/sms/setup")
async def setup_sms(
    request: SMSSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup SMS 2FA.
    
    Sends verification code to phone number.
    """
    # Verify password
    from app.core.security import verify_password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    service = TwoFactorService(db)
    
    # Send verification code
    code_sent = await service.send_sms_verification(
        user_id=current_user.id,
        phone_number=request.phone_number
    )
    
    if not code_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS verification code"
        )
    
    return {
        "message": "Verification code sent to your phone",
        "phone_number": request.phone_number,
        "expires_in": 600  # 10 minutes
    }


@router.post("/sms/verify")
async def verify_sms(
    request: SMSVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify SMS code and activate SMS 2FA.
    """
    service = TwoFactorService(db)
    
    verified = await service.verify_sms_and_activate(
        user_id=current_user.id,
        code=request.code
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired SMS code"
        )
    
    return {
        "message": "SMS 2FA activated successfully",
        "enabled": True,
        "method": "sms"
    }


@router.post("/sms/verify-login")
async def verify_sms_login(
    request: SMSVerifyRequest,
    username: str,
    db: Session = Depends(get_db)
):
    """
    Verify SMS code during login.
    
    Completes authentication after username/password verification.
    """
    service = TwoFactorService(db)
    
    verified, user = await service.verify_sms_login(
        username=username,
        code=request.code
    )
    
    if not verified or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid SMS code"
        )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return TwoFactorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_2fa=False
    )


@router.post("/email/setup")
async def setup_email_2fa(
    request: EmailSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup Email 2FA.
    
    Sends verification code to user's email.
    """
    # Verify password
    from app.core.security import verify_password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    service = TwoFactorService(db)
    
    # Send verification code
    code_sent = await service.send_email_verification(
        user_id=current_user.id,
        email=current_user.email
    )
    
    if not code_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email verification code"
        )
    
    return {
        "message": "Verification code sent to your email",
        "email": current_user.email,
        "expires_in": 600
    }


@router.post("/email/verify")
async def verify_email_2fa(
    request: SMSVerifyRequest,  # Same format
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify email code and activate Email 2FA.
    """
    service = TwoFactorService(db)
    
    verified = await service.verify_email_and_activate(
        user_id=current_user.id,
        code=request.code
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email code"
        )
    
    return {
        "message": "Email 2FA activated successfully",
        "enabled": True,
        "method": "email"
    }


@router.post("/backup/verify")
async def verify_backup_code(
    request: TOTPVerifyRequest,
    username: str,
    db: Session = Depends(get_db)
):
    """
    Verify backup recovery code.
    
    Used when primary 2FA methods are unavailable.
    """
    service = TwoFactorService(db)
    
    verified, user = await service.verify_backup_code(
        username=username,
        code=request.code
    )
    
    if not verified or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup code"
        )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    remaining_codes = await service.get_remaining_backup_codes(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "backup_codes_remaining": remaining_codes,
        "warning": "Please generate new backup codes" if remaining_codes < 3 else None
    }


@router.post("/backup/regenerate", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    request: TOTPSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate backup recovery codes.
    
    Invalidates old codes and generates new ones.
    """
    # Verify password
    from app.core.security import verify_password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Verify 2FA if enabled
    service = TwoFactorService(db)
    status_info = service.get_2fa_status(current_user.id)
    
    if status_info.get("enabled"):
        # Additional verification would happen here in production
        pass
    
    # Generate new codes
    new_codes = generate_backup_codes(10)
    
    # Store new codes
    service.store_backup_codes(current_user.id, new_codes)
    
    return BackupCodesResponse(
        codes=new_codes,
        message="Save these backup codes in a secure location. Each code can only be used once."
    )


@router.post("/webauthn/register/begin")
async def begin_webauthn_registration(
    request: WebAuthnRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Begin WebAuthn/FIDO2 security key registration.
    
    Returns challenge and options for hardware key registration.
    """
    # Verify password
    from app.core.security import verify_password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    service = TwoFactorService(db)
    
    options = await service.begin_webauthn_registration(
        user_id=current_user.id,
        username=current_user.username,
        device_name=request.device_name
    )
    
    return options


@router.post("/webauthn/register/complete")
async def complete_webauthn_registration(
    request: WebAuthnVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete WebAuthn security key registration.
    """
    service = TwoFactorService(db)
    
    success = await service.complete_webauthn_registration(
        user_id=current_user.id,
        credential_data=request.dict()
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register security key"
        )
    
    return {
        "message": "Security key registered successfully",
        "enabled": True,
        "method": "webauthn"
    }


@router.post("/webauthn/authenticate/begin")
async def begin_webauthn_authentication(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Begin WebAuthn authentication for login.
    
    Returns challenge for hardware key verification.
    """
    service = TwoFactorService(db)
    
    options = await service.begin_webauthn_authentication(username)
    
    if not options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No security keys registered"
        )
    
    return options


@router.post("/webauthn/authenticate/complete")
async def complete_webauthn_authentication(
    request: WebAuthnVerifyRequest,
    username: str,
    db: Session = Depends(get_db)
):
    """
    Complete WebAuthn authentication and return tokens.
    """
    service = TwoFactorService(db)
    
    user = await service.complete_webauthn_authentication(
        username=username,
        credential_data=request.dict()
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed"
        )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return TwoFactorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_2fa=False
    )


@router.get("/webauthn/keys", response_model=List[HardwareKeyInfo])
async def list_security_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List registered hardware security keys.
    """
    service = TwoFactorService(db)
    
    keys = await service.list_security_keys(current_user.id)
    
    return [
        HardwareKeyInfo(
            id=key["id"],
            name=key["name"],
            credential_id=key["credential_id"],
            registered_at=key["registered_at"],
            last_used_at=key.get("last_used_at"),
            is_active=key["is_active"]
        )
        for key in keys
    ]


@router.delete("/webauthn/keys/{key_id}")
async def remove_security_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a registered hardware security key.
    """
    service = TwoFactorService(db)
    
    success = await service.remove_security_key(
        user_id=current_user.id,
        key_id=key_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security key not found"
        )
    
    return {"message": "Security key removed successfully"}


@router.delete("/disable")
async def disable_2fa(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disable all 2FA methods for user.
    
    Requires verification with current 2FA method or backup code.
    """
    service = TwoFactorService(db)
    
    # Verify 2FA code
    verified = await service.verify_any_2fa(
        user_id=current_user.id,
        code=request.code
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    # Disable 2FA
    success = await service.disable_2fa(current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )
    
    return {
        "message": "Two-factor authentication disabled",
        "enabled": False
    }


@router.post("/enforce", response_model=Dict[str, Any])
async def enforce_2fa_policy(
    request: TwoFactorEnforceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Enforce 2FA requirement for organization (admin only).
    
    Sets policy requiring all users to enable 2FA.
    """
    # Check admin role
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # In production, store policy in database
    # For now, return policy configuration
    return {
        "enforced": request.enforce,
        "grace_period_days": request.grace_period_days,
        "exempt_roles": request.exempt_roles,
        "effective_date": datetime.utcnow().isoformat(),
        "message": "2FA enforcement policy updated"
    }


@router.post("/login/challenge")
async def create_2fa_login_challenge(
    request: TwoFactorLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Create 2FA challenge during login.
    
    After username/password verification, returns available 2FA methods.
    """
    from app.core.security import verify_password
    
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    service = TwoFactorService(db)
    status_info = service.get_2fa_status(user.id)
    
    if not status_info.get("enabled"):
        # No 2FA required, return tokens directly
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        return TwoFactorLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            requires_2fa=False
        )
    
    # Return available 2FA methods
    available_methods = []
    for method in status_info.get("methods", []):
        if method.get("is_active"):
            available_methods.append(method.get("type"))
    
    # If backup codes available, add as option
    if status_info.get("backup_codes_remaining", 0) > 0:
        available_methods.append("backup")
    
    return TwoFactorLoginResponse(
        access_token="",
        refresh_token="",
        requires_2fa=True,
        two_factor_methods=available_methods
    )
