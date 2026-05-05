"""
Consent Management and GDPR Compliance Service

Comprehensive consent management for GDPR, CCPA, and
other privacy regulations.

Features:
- Consent tracking and management
- Cookie consent
- Data processing consent
- Marketing consent
- Right to be forgotten
- Data export (GDPR Article 15)
- Data portability
- Consent withdrawal
- Audit trail for consent changes
- Consent templates
- Age verification
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.db.models import User, ConsentRecord, DataExportRequest
from app.core.config import settings


class ConsentType(Enum):
    """Types of consent that can be collected."""
    MARKETING_EMAILS = "marketing_emails"
    NEWSLETTER = "newsletter"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY_SHARING = "third_party_sharing"
    COOKIES_ESSENTIAL = "cookies_essential"
    COOKIES_MARKETING = "cookies_marketing"
    COOKIES_ANALYTICS = "cookies_analytics"
    DATA_PROCESSING = "data_processing"
    LOCATION_TRACKING = "location_tracking"
    SMS_NOTIFICATIONS = "sms_notifications"


class ConsentStatus(Enum):
    """Consent status."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class DataExportStatus(Enum):
    """Data export request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class ConsentRecord:
    """Consent record data structure."""
    consent_type: ConsentType
    status: ConsentStatus
    user_id: int
    granted_at: datetime
    granted_from: str  # IP address, user agent, etc.
    metadata: Optional[Dict[str, Any]] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class ConsentTemplate:
    """Consent template for UI display."""
    consent_type: ConsentType
    title: str
    description: str
    required: bool = False
    default_value: bool = False
    legal_basis: Optional[str] = None
    retention_period_days: Optional[int] = None


class ConsentService:
    """
    Enterprise-grade consent management service.
    
    Features:
    - Consent tracking and management
    - Cookie consent
    - Data processing consent
    - Marketing consent
    - Right to be forgotten
    - Data export (GDPR Article 15)
    - Data portability
    - Consent withdrawal
    - Audit trail for consent changes
    - Consent templates
    - Age verification
    """
    
    # Default consent templates
    CONSENT_TEMPLATES = {
        ConsentType.MARKETING_EMAILS: ConsentTemplate(
            consent_type=ConsentType.MARKETING_EMAILS,
            title="Marketing Emails",
            description="Receive marketing emails about new features, promotions, and updates.",
            required=False,
            default_value=False,
            legal_basis="Legitimate Interest",
            retention_period_days=365
        ),
        ConsentType.NEWSLETTER: ConsentTemplate(
            consent_type=ConsentType.NEWSLETTER,
            title="Newsletter",
            description="Subscribe to our weekly newsletter with industry insights.",
            required=False,
            default_value=False,
            legal_basis="Consent",
            retention_period_days=365
        ),
        ConsentType.ANALYTICS: ConsentTemplate(
            consent_type=ConsentType.ANALYTICS,
            title="Analytics",
            description="Allow us to collect anonymous usage data to improve our services.",
            required=False,
            default_value=True,
            legal_basis="Legitimate Interest",
            retention_period_days=730
        ),
        ConsentType.PERSONALIZATION: ConsentTemplate(
            consent_type=ConsentType.PERSONALIZATION,
            title="Personalization",
            description="Allow us to personalize your experience based on your preferences.",
            required=False,
            default_value=True,
            legal_basis="Consent",
            retention_period_days=365
        ),
        ConsentType.THIRD_PARTY_SHARING: ConsentTemplate(
            consent_type=ConsentType.THIRD_PARTY_SHARING,
            title="Third-Party Sharing",
            description="Allow us to share your data with trusted third-party partners.",
            required=False,
            default_value=False,
            legal_basis="Consent",
            retention_period_days=365
        ),
        ConsentType.COOKIES_ESSENTIAL: ConsentTemplate(
            consent_type=ConsentType.COOKIES_ESSENTIAL,
            title="Essential Cookies",
            description="Required for the website to function properly.",
            required=True,
            default_value=True,
            legal_basis="Contractual Necessity",
            retention_period_days=None
        ),
        ConsentType.COOKIES_MARKETING: ConsentTemplate(
            consent_type=ConsentType.COOKIES_MARKETING,
            title="Marketing Cookies",
            description="Used to deliver relevant advertisements and measure campaign effectiveness.",
            required=False,
            default_value=False,
            legal_basis="Consent",
            retention_period_days=90
        ),
        ConsentType.COOKIES_ANALYTICS: ConsentTemplate(
            consent_type=ConsentType.COOKIES_ANALYTICS,
            title="Analytics Cookies",
            description="Help us understand how visitors use our website.",
            required=False,
            default_value=True,
            legal_basis="Legitimate Interest",
            retention_period_days=730
        ),
        ConsentType.DATA_PROCESSING: ConsentTemplate(
            consent_type=ConsentType.DATA_PROCESSING,
            title="Data Processing",
            description="Consent to process your personal data for account management.",
            required=True,
            default_value=True,
            legal_basis="Contractual Necessity",
            retention_period_days=None
        ),
        ConsentType.SMS_NOTIFICATIONS: ConsentTemplate(
            consent_type=ConsentType.SMS_NOTIFICATIONS,
            title="SMS Notifications",
            description="Receive important notifications via SMS.",
            required=False,
            default_value=False,
            legal_basis="Consent",
            retention_period_days=365
        )
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def grant_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
        granted_from: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConsentRecord:
        """
        Grant consent for a specific type.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            granted_from: Source of consent (IP, user agent, etc.)
            metadata: Additional metadata
        
        Returns:
            Consent record
        """
        # Check if consent already exists
        existing = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type.value,
            ConsentRecord.status == ConsentStatus.GRANTED.value
        ).first()
        
        if existing:
            # Update existing record
            existing.metadata = json.dumps(metadata) if metadata else existing.metadata
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return ConsentRecord(
                consent_type=ConsentType(existing.consent_type),
                status=ConsentStatus(existing.status),
                user_id=existing.user_id,
                granted_at=existing.granted_at,
                granted_from=existing.granted_from,
                metadata=json.loads(existing.metadata) if existing.metadata else None,
                withdrawn_at=existing.withdrawn_at,
                expires_at=existing.expires_at
            )
        
        # Create new consent record
        template = self.CONSENT_TEMPLATES.get(consent_type)
        expires_at = None
        if template and template.retention_period_days:
            expires_at = datetime.utcnow() + timedelta(days=template.retention_period_days)
        
        consent_record = ConsentRecord(
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            user_id=user_id,
            granted_at=datetime.utcnow(),
            granted_from=granted_from,
            metadata=metadata,
            expires_at=expires_at
        )
        
        # Save to database
        db_record = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type.value
        ).first()
        
        if db_record:
            db_record.status = ConsentStatus.GRANTED.value
            db_record.granted_at = datetime.utcnow()
            db_record.granted_from = granted_from
            db_record.withdrawn_at = None
            db_record.expires_at = expires_at
            db_record.metadata = json.dumps(metadata) if metadata else db_record.metadata
            db_record.updated_at = datetime.utcnow()
        else:
            db_record = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type.value,
                status=ConsentStatus.GRANTED.value,
                granted_at=datetime.utcnow(),
                granted_from=granted_from,
                expires_at=expires_at,
                metadata=json.dumps(metadata) if metadata else None
            )
            self.db.add(db_record)
        
        self.db.commit()
        self.db.refresh(db_record)
        
        return consent_record
    
    def withdraw_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
        reason: Optional[str] = None
    ) -> bool:
        """
        Withdraw previously granted consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to withdraw
            reason: Reason for withdrawal
        
        Returns:
            Success status
        """
        consent_record = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type.value,
            ConsentRecord.status == ConsentStatus.GRANTED.value
        ).first()
        
        if not consent_record:
            return False
        
        consent_record.status = ConsentStatus.WITHDRAWN.value
        consent_record.withdrawn_at = datetime.utcnow()
        consent_record.withdrawal_reason = reason
        consent_record.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def get_user_consents(self, user_id: int) -> Dict[str, Any]:
        """
        Get all consent records for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary of consent statuses
        """
        records = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id
        ).all()
        
        consents = {}
        for record in records:
            consent_type = record.consent_type
            consents[consent_type] = {
                'status': record.status,
                'granted_at': record.granted_at.isoformat() if record.granted_at else None,
                'withdrawn_at': record.withdrawn_at.isoformat() if record.withdrawn_at else None,
                'expires_at': record.expires_at.isoformat() if record.expires_at else None,
                'granted_from': record.granted_from
            }
        
        return consents
    
    def check_consent(
        self,
        user_id: int,
        consent_type: ConsentType
    ) -> bool:
        """
        Check if user has granted specific consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to check
        
        Returns:
            True if consent is granted and not expired
        """
        record = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type.value,
            ConsentRecord.status == ConsentStatus.GRANTED.value
        ).first()
        
        if not record:
            return False
        
        # Check if expired
        if record.expires_at and record.expires_at < datetime.utcnow():
            return False
        
        return True
    
    def get_consent_templates(self) -> List[Dict[str, Any]]:
        """Get all consent templates for UI display."""
        return [
            {
                'type': template.consent_type.value,
                'title': template.title,
                'description': template.description,
                'required': template.required,
                'default_value': template.default_value,
                'legal_basis': template.legal_basis,
                'retention_period_days': template.retention_period_days
            }
            for template in self.CONSENT_TEMPLATES.values()
        ]
    
    def batch_grant_consents(
        self,
        user_id: int,
        consent_types: List[ConsentType],
        granted_from: str
    ) -> List[ConsentRecord]:
        """
        Grant multiple consents at once.
        
        Args:
            user_id: User ID
            consent_types: List of consent types to grant
            granted_from: Source of consent
        
        Returns:
            List of consent records
        """
        records = []
        for consent_type in consent_types:
            record = self.grant_consent(user_id, consent_type, granted_from)
            records.append(record)
        
        return records
    
    def request_data_export(
        self,
        user_id: int,
        include_deleted: bool = False
    ) -> str:
        """
        Request data export (GDPR Article 15).
        
        Args:
            user_id: User ID
            include_deleted: Include deleted data
        
        Returns:
            Export request ID
        """
        request_id = str(uuid.uuid4())
        
        export_request = DataExportRequest(
            user_id=user_id,
            request_id=request_id,
            status=DataExportStatus.PENDING.value,
            include_deleted=include_deleted,
            created_at=datetime.utcnow()
        )
        
        self.db.add(export_request)
        self.db.commit()
        self.db.refresh(export_request)
        
        # In production, this would trigger an async job
        # to collect and package the data
        
        return request_id
    
    def get_export_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of data export request.
        
        Args:
            request_id: Export request ID
        
        Returns:
            Export status information
        """
        export_request = self.db.query(DataExportRequest).filter(
            DataExportRequest.request_id == request_id
        ).first()
        
        if not export_request:
            return None
        
        return {
            'request_id': export_request.request_id,
            'status': export_request.status,
            'created_at': export_request.created_at.isoformat(),
            'completed_at': export_request.completed_at.isoformat() if export_request.completed_at else None,
            'download_url': export_request.download_url,
            'expires_at': export_request.expires_at.isoformat() if export_request.expires_at else None,
            'error_message': export_request.error_message
        }
    
    def process_data_export(self, request_id: str) -> bool:
        """
        Process data export request (collect and package data).
        
        Args:
            request_id: Export request ID
        
        Returns:
            Success status
        """
        export_request = self.db.query(DataExportRequest).filter(
            DataExportRequest.request_id == request_id
        ).first()
        
        if not export_request:
            return False
        
        export_request.status = DataExportStatus.PROCESSING.value
        self.db.commit()
        
        try:
            # Collect user data
            user = self.db.query(User).filter(User.id == export_request.user_id).first()
            if not user:
                raise Exception("User not found")
            
            # Collect all user-related data
            user_data = {
                'profile': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value if user.role else None,
                    'subscription_plan': user.subscription_plan.value if user.subscription_plan else None,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at.isoformat(),
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                },
                'consents': self.get_user_consents(user.id),
                'export_request_id': request_id,
                'exported_at': datetime.utcnow().isoformat()
            }
            
            # In production, this would be saved to S3 or similar
            # For now, we'll simulate a download URL
            download_url = f"https://yourapp.com/exports/{request_id}.json"
            
            export_request.status = DataExportStatus.COMPLETED.value
            export_request.completed_at = datetime.utcnow()
            export_request.download_url = download_url
            export_request.expires_at = datetime.utcnow() + timedelta(days=7)
            
            self.db.commit()
            
            return True
            
        except Exception as e:
            export_request.status = DataExportStatus.FAILED.value
            export_request.error_message = str(e)
            export_request.completed_at = datetime.utcnow()
            self.db.commit()
            return False
    
    def request_data_deletion(
        self,
        user_id: int,
        reason: Optional[str] = None
    ) -> str:
        """
        Request data deletion (GDPR Right to be Forgotten).
        
        Args:
            user_id: User ID
            reason: Reason for deletion request
        
        Returns:
            Deletion request ID
        """
        request_id = str(uuid.uuid4())
        
        # In production, this would create a deletion request
        # and trigger an async job to delete all user data
        
        # For now, we'll mark the user as deleted
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False
            user.email = f"deleted_{user_id}@deleted.local"
            user.username = f"deleted_user_{user_id}"
            self.db.commit()
        
        return request_id
    
    def get_consent_audit_trail(
        self,
        user_id: int,
        consent_type: Optional[ConsentType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail of consent changes for a user.
        
        Args:
            user_id: User ID
            consent_type: Optional consent type filter
        
        Returns:
            List of consent change events
        """
        query = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id
        )
        
        if consent_type:
            query = query.filter(ConsentRecord.consent_type == consent_type.value)
        
        records = query.order_by(ConsentRecord.created_at.desc()).all()
        
        return [
            {
                'consent_type': record.consent_type,
                'status': record.status,
                'granted_at': record.granted_at.isoformat() if record.granted_at else None,
                'withdrawn_at': record.withdrawn_at.isoformat() if record.withdrawn_at else None,
                'granted_from': record.granted_from,
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat() if record.updated_at else None
            }
            for record in records
        ]
    
    def cleanup_expired_consents(self) -> int:
        """
        Clean up expired consent records.
        
        Returns:
            Number of records cleaned up
        """
        now = datetime.utcnow()
        
        # Mark expired consents
        expired = self.db.query(ConsentRecord).filter(
            ConsentRecord.status == ConsentStatus.GRANTED.value,
            ConsentRecord.expires_at < now
        ).all()
        
        count = 0
        for record in expired:
            record.status = ConsentStatus.EXPIRED.value
            count += 1
        
        self.db.commit()
        
        return count


def get_consent_service(db: Session):
    """Dependency to get consent service."""
    return ConsentService(db)
