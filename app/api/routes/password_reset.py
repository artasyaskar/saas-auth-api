"""
Password reset endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.services.password_reset import PasswordResetService, get_password_reset_service

router = APIRouter()


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=32, max_length=64, description="Reset token from email")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123...",
                "new_password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        }


@router.post("/reset-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    reset_service: PasswordResetService = Depends(get_password_reset_service)
):
    """
    Request a password reset email.
    
    - Always returns 202 to prevent email enumeration
    - Sends email with reset link if email exists
    - Token expires in 24 hours
    """
    client_ip = request.client.host if request.client else None
    
    # Request reset (always succeeds to prevent enumeration)
    reset_service.request_password_reset(
        email=request_data.email,
        ip_address=client_ip
    )
    
    return {
        "message": "If an account with that email exists, a password reset link has been sent.",
        "status": "accepted"
    }


@router.get("/validate-token/{token}")
async def validate_reset_token(
    token: str,
    db: Session = Depends(get_db),
    reset_service: PasswordResetService = Depends(get_password_reset_service)
):
    """Validate a password reset token without consuming it."""
    user = reset_service.validate_reset_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "email": user.email
    }


@router.post("/reset")
async def reset_password(
    reset_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
    reset_service: PasswordResetService = Depends(get_password_reset_service)
):
    """
    Reset password using a valid token.
    
    - Token must be valid and not expired
    - Passwords must match
    - All existing sessions will be invalidated
    """
    # Validate passwords match
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    client_ip = request.client.host if request.client else None
    
    # Reset password
    success, message = reset_service.reset_password(
        token=reset_data.token,
        new_password=reset_data.new_password,
        ip_address=client_ip
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "message": message,
        "status": "success"
    }


# TODO: Add email verification endpoints
# TODO: Add resend verification email endpoint
