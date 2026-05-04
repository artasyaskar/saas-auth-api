from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.db.session import get_db
from app.db.models import User, UserRole
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
from app.core.config import settings
from app.services.token_blacklist import get_token_blacklist_service, TokenBlacklistService
from app.middleware.logging import audit_logger

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    subscription_plan: str
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is blacklisted (user logged out or token revoked)
    if blacklist_service.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(token, "access")
    username: str = payload.get("sub")
    
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=UserRole.USER
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = verify_token(refresh_token, "refresh")
        username: str = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = db.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    logout_data: LogoutRequest = None,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
):
    """
    Logout user and revoke tokens.
    
    - Blacklists the current access token
    - Optionally blacklist the refresh token
    - Logs the logout event
    """
    client_ip = request.client.host if request.client else None
    
    # Get token expiration from payload
    try:
        payload = verify_token(token, "access")
        exp_timestamp = payload.get("exp")
        expires_at = datetime.utcfromtimestamp(exp_timestamp) if exp_timestamp else datetime.utcnow() + timedelta(minutes=30)
    except Exception:
        expires_at = datetime.utcnow() + timedelta(minutes=30)
    
    # Blacklist access token
    blacklist_service.blacklist_token(
        token=token,
        expires_at=expires_at,
        user_id=current_user.id,
        token_type="access",
        reason="logout"
    )
    
    # Blacklist refresh token if provided
    if logout_data and logout_data.refresh_token:
        try:
            refresh_payload = verify_token(logout_data.refresh_token, "refresh")
            refresh_exp = refresh_payload.get("exp")
            refresh_expires = datetime.utcfromtimestamp(refresh_exp) if refresh_exp else datetime.utcnow() + timedelta(days=7)
            
            blacklist_service.blacklist_token(
                token=logout_data.refresh_token,
                expires_at=refresh_expires,
                user_id=current_user.id,
                token_type="refresh",
                reason="logout"
            )
        except Exception:
            pass  # Ignore invalid refresh token
    
    # Log the logout
    audit_logger.log_token_action(
        user_id=current_user.id,
        username=current_user.username,
        action="logout",
        token_type="access",
        ip_address=client_ip
    )
    
    return {"message": "Successfully logged out", "status": "success"}


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all_devices(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service)
):
    """
    Logout from all devices.
    
    - Invalidates all tokens for the user
    - Forces re-authentication on all devices
    """
    client_ip = request.client.host if request.client else None
    
    # Blacklist all tokens for this user
    invalidated_count = blacklist_service.blacklist_all_user_tokens(
        user_id=current_user.id,
        reason="logout_all"
    )
    
    # Log the action
    audit_logger.log_token_action(
        user_id=current_user.id,
        username=current_user.username,
        action="logout_all",
        token_type="all",
        ip_address=client_ip
    )
    
    return {
        "message": "Logged out from all devices",
        "status": "success",
        "sessions_invalidated": invalidated_count
    }
