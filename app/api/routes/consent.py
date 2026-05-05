"""
Consent Management API Routes

API endpoints for managing user consent, GDPR compliance,
and data export requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, ConsentRecord, DataExportRequest
from app.services.consent import (
    ConsentService,
    ConsentType,
    ConsentStatus,
    AccessLevel
)
from app.core.security import get_current_user

router = APIRouter(prefix="/consent", tags=["consent"])


@router.post("/grant")
async def grant_consent(
    consent_type: ConsentType,
    granted_from: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant consent for a specific type."""
    service = ConsentService(db)
    record = service.grant_consent(
        user_id=current_user.id,
        consent_type=consent_type,
        granted_from=granted_from
    )
    return {
        "consent_type": record.consent_type.value,
        "status": record.status.value,
        "granted_at": record.granted_at.isoformat()
    }


@router.post("/withdraw/{consent_type}")
async def withdraw_consent(
    consent_type: ConsentType,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Withdraw previously granted consent."""
    service = ConsentService(db)
    success = service.withdraw_consent(
        user_id=current_user.id,
        consent_type=consent_type,
        reason=reason
    )
    if not success:
        raise HTTPException(status_code=404, detail="Consent not found")
    return {"message": "Consent withdrawn successfully"}


@router.get("/my-consents")
async def get_my_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all consent records for the current user."""
    service = ConsentService(db)
    consents = service.get_user_consents(current_user.id)
    return consents


@router.get("/templates")
async def get_consent_templates(
    db: Session = Depends(get_db)
):
    """Get all consent templates for UI display."""
    service = ConsentService(db)
    return service.get_consent_templates()


@router.post("/batch-grant")
async def batch_grant_consents(
    consent_types: List[ConsentType],
    granted_from: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant multiple consents at once."""
    service = ConsentService(db)
    records = service.batch_grant_consents(
        user_id=current_user.id,
        consent_types=consent_types,
        granted_from=granted_from
    )
    return {
        "granted": len(records),
        "consents": [
            {"type": r.consent_type.value, "status": r.status.value}
            for r in records
        ]
    }


@router.post("/data-export")
async def request_data_export(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request data export (GDPR Article 15)."""
    service = ConsentService(db)
    request_id = service.request_data_export(
        user_id=current_user.id,
        include_deleted=include_deleted
    )
    return {"request_id": request_id, "status": "pending"}


@router.get("/data-export/{request_id}")
async def get_export_status(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get status of data export request."""
    service = ConsentService(db)
    status = service.get_export_status(request_id)
    if not status:
        raise HTTPException(status_code=404, detail="Export request not found")
    return status


@router.get("/audit-trail")
async def get_consent_audit_trail(
    consent_type: Optional[ConsentType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit trail of consent changes."""
    service = ConsentService(db)
    trail = service.get_consent_audit_trail(
        user_id=current_user.id,
        consent_type=consent_type
    )
    return trail


@router.post("/data-deletion")
async def request_data_deletion(
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request data deletion (GDPR Right to be Forgotten)."""
    service = ConsentService(db)
    request_id = service.request_data_deletion(
        user_id=current_user.id,
        reason=reason
    )
    return {"request_id": request_id, "message": "Deletion request initiated"}


@router.get("/check/{consent_type}")
async def check_consent(
    consent_type: ConsentType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if user has granted specific consent."""
    service = ConsentService(db)
    has_consent = service.check_consent(
        user_id=current_user.id,
        consent_type=consent_type
    )
    return {"consent_type": consent_type.value, "granted": has_consent}
