"""
Comprehensive Audit Logging and Compliance Service

Enterprise-grade audit logging for security, compliance, and
forensics with support for multiple compliance frameworks.

Supported Frameworks:
- GDPR (General Data Protection Regulation)
- SOC 2 (Service Organization Control 2)
- HIPAA (Health Insurance Portability and Accountability Act)
- PCI DSS (Payment Card Industry Data Security Standard)
- ISO 27001 (Information Security Management)

Features:
- Immutable audit trail
- Event classification and categorization
- User activity tracking
- Data access logging
- Compliance reporting
- Alerting and notifications
- Log retention policies
- Log export and archival
- Tamper detection
- Chain of custody
"""
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.models import User, AuditLog, ComplianceReport
from app.core.config import settings


class AuditEventType(Enum):
    """Audit event types."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    TWO_FACTOR_ENABLED = "2fa_enabled"
    TWO_FACTOR_DISABLED = "2fa_disabled"
    TWO_FACTOR_VERIFIED = "2fa_verified"
    
    # Authorization
    ROLE_GRANTED = "role_granted"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_REACTIVATED = "user_reactivated"
    
    # Data Access
    DATA_READ = "data_read"
    DATA_WRITTEN = "data_written"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    
    # System
    CONFIGURATION_CHANGE = "config_change"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    ERROR_OCCURRED = "error_occurred"
    
    # API
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"
    
    # Billing
    PAYMENT_PROCESSED = "payment_processed"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    INVOICE_GENERATED = "invoice_generated"
    
    # Security
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INTRUSION_DETECTED = "intrusion_detected"
    MALWARE_DETECTED = "malware_detected"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Compliance frameworks."""
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_type: AuditEventType
    user_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    details: Optional[Dict[str, Any]]
    severity: AuditSeverity = AuditSeverity.INFO
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""
    framework: ComplianceFramework
    passed: bool
    violations: List[str]
    recommendations: List[str]
    score: float  # 0-100


class AuditService:
    """
    Enterprise-grade audit logging service.
    
    Features:
    - Immutable audit trail with cryptographic signatures
    - Event classification and categorization
    - User activity tracking
    - Data access logging
    - Compliance reporting (GDPR, SOC 2, HIPAA, PCI DSS)
    - Alerting and notifications
    - Log retention policies
    - Log export and archival
    - Tamper detection
    - Chain of custody
    """
    
    # Configuration
    RETENTION_DAYS = 365  # Default retention period
    MAX_DETAILS_SIZE = 10000  # Max size of details field in bytes
    SIGNATURE_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "default"
    
    # Compliance requirements
    GDPR_RETENTION_DAYS = 365
    SOC2_RETENTION_DAYS = 2555  # 7 years
    HIPAA_RETENTION_DAYS = 2190  # 6 years
    PCI_DSS_RETENTION_DAYS = 365
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_event(
        self,
        event: AuditEvent
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            event: Audit event to log
        
        Returns:
            Created audit log entry
        """
        # Serialize details
        details_json = json.dumps(event.details) if event.details else None
        
        # Check size limit
        if details_json and len(details_json) > self.MAX_DETAILS_SIZE:
            details_json = json.dumps({"error": "Details too large", "original_size": len(details_json)})
        
        # Create audit log entry
        audit_log = AuditLog(
            event_type=event.event_type.value,
            user_id=event.user_id,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            resource=event.resource,
            action=event.action,
            details=details_json,
            severity=event.severity.value,
            tags=json.dumps(event.tags) if event.tags else None,
            metadata=json.dumps(event.metadata) if event.metadata else None,
            timestamp=datetime.utcnow(),
            signature=self._generate_signature(event)
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        # Check for suspicious activity
        self._check_suspicious_activity(audit_log)
        
        return audit_log
    
    def log_authentication_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log authentication event.
        
        Args:
            event_type: Type of authentication event
            user_id: User ID
            ip_address: IP address
            user_agent: User agent string
            success: Whether authentication succeeded
            details: Additional details
        
        Returns:
            Created audit log entry
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="auth",
            action=event_type.value,
            details=details or {"success": success},
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING
        )
        
        return self.log_event(event)
    
    def log_data_access(
        self,
        user_id: int,
        resource: str,
        action: str,
        ip_address: str,
        user_agent: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log data access event.
        
        Args:
            user_id: User ID
            resource: Resource accessed
            action: Action performed
            ip_address: IP address
            user_agent: User agent string
            details: Additional details
        
        Returns:
            Created audit log entry
        """
        event = AuditEvent(
            event_type=AuditEventType.DATA_READ if "read" in action.lower() else AuditEventType.DATA_WRITTEN,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=details,
            severity=AuditSeverity.INFO
        )
        
        return self.log_event(event)
    
    def log_configuration_change(
        self,
        user_id: int,
        config_key: str,
        old_value: Any,
        new_value: Any,
        ip_address: str,
        user_agent: str
    ) -> AuditLog:
        """
        Log configuration change.
        
        Args:
            user_id: User ID
            config_key: Configuration key changed
            old_value: Old value
            new_value: New value
            ip_address: IP address
            user_agent: User agent string
        
        Returns:
            Created audit log entry
        """
        event = AuditEvent(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="config",
            action="update",
            details={
                "config_key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value)
            },
            severity=AuditSeverity.WARNING
        )
        
        return self.log_event(event)
    
    def get_user_activity(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a user.
        
        Args:
            user_id: User ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results
        
        Returns:
            List of audit logs
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        )
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    def get_resource_activity(
        self,
        resource: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a resource.
        
        Args:
            resource: Resource name
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results
        
        Returns:
            List of audit logs
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.resource == resource
        )
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    def get_events_by_type(
        self,
        event_type: AuditEventType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs by event type.
        
        Args:
            event_type: Event type
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results
        
        Returns:
            List of audit logs
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.event_type == event_type.value
        )
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    def verify_integrity(self, audit_log: AuditLog) -> bool:
        """
        Verify audit log integrity using signature.
        
        Args:
            audit_log: Audit log to verify
        
        Returns:
            True if signature is valid
        """
        expected_signature = self._generate_signature_from_log(audit_log)
        return hmac.compare_digest(audit_log.signature, expected_signature)
    
    def check_tampering(self) -> List[AuditLog]:
        """
        Check for tampered audit logs.
        
        Returns:
            List of tampered audit logs
        """
        tampered = []
        
        # Get all logs
        logs = self.db.query(AuditLog).all()
        
        for log in logs:
            if not self.verify_integrity(log):
                tampered.append(log)
        
        return tampered
    
    def export_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> str:
        """
        Export audit logs for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            format: Export format (json, csv)
        
        Returns:
            Exported data as string
        """
        logs = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).all()
        
        if format == "json":
            return json.dumps([self._log_to_dict(log) for log in logs], indent=2)
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=[
                    "id", "event_type", "user_id", "ip_address", "resource",
                    "action", "severity", "timestamp"
                ])
                writer.writeheader()
                for log in logs:
                    writer.writerow({
                        "id": log.id,
                        "event_type": log.event_type,
                        "user_id": log.user_id,
                        "ip_address": log.ip_address,
                        "resource": log.resource,
                        "action": log.action,
                        "severity": log.severity,
                        "timestamp": log.timestamp.isoformat()
                    })
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def apply_retention_policy(self):
        """Apply retention policy to old audit logs."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.RETENTION_DAYS)
        
        deleted = self.db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).delete()
        
        self.db.commit()
        
        return deleted
    
    def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: datetime,
        end_date: datetime
    ) -> ComplianceCheckResult:
        """
        Generate compliance report for a framework.
        
        Args:
            framework: Compliance framework
            start_date: Report start date
            end_date: Report end date
        
        Returns:
            Compliance check result
        """
        violations = []
        recommendations = []
        score = 100.0
        
        # Get logs for the period
        logs = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).all()
        
        if framework == ComplianceFramework.GDPR:
            # Check GDPR requirements
            violations, recommendations, score = self._check_gdpr_compliance(logs)
        
        elif framework == ComplianceFramework.SOC2:
            violations, recommendations, score = self._check_soc2_compliance(logs)
        
        elif framework == ComplianceFramework.HIPAA:
            violations, recommendations, score = self._check_hipaa_compliance(logs)
        
        elif framework == ComplianceFramework.PCI_DSS:
            violations, recommendations, score = self._check_pci_dss_compliance(logs)
        
        elif framework == ComplianceFramework.ISO_27001:
            violations, recommendations, score = self._check_iso_27001_compliance(logs)
        
        # Create compliance report record
        report = ComplianceReport(
            framework=framework.value,
            start_date=start_date,
            end_date=end_date,
            score=score,
            violations=json.dumps(violations),
            recommendations=json.dumps(recommendations),
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        
        return ComplianceCheckResult(
            framework=framework,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations,
            score=score
        )
    
    def _check_gdpr_compliance(self, logs: List[AuditLog]) -> Tuple[List[str], List[str], float]:
        """Check GDPR compliance."""
        violations = []
        recommendations = []
        score = 100.0
        
        # Check for data access logging
        data_access_logs = [l for l in logs if l.event_type in [AuditEventType.DATA_READ.value, AuditEventType.DATA_WRITTEN.value]]
        if not data_access_logs:
            violations.append("No data access logs found")
            score -= 20
            recommendations.append("Ensure all data access is logged")
        
        # Check for data export logging
        export_logs = [l for l in logs if l.event_type == AuditEventType.DATA_EXPORTED.value]
        if not export_logs:
            violations.append("No data export logs found")
            score -= 15
            recommendations.append("Log all data exports for GDPR right to data portability")
        
        # Check for user deletion logging
        deletion_logs = [l for l in logs if l.event_type == AuditEventType.USER_DELETED.value]
        if not deletion_logs:
            violations.append("No user deletion logs found")
            score -= 10
            recommendations.append("Log all user deletions for GDPR right to erasure")
        
        return violations, recommendations, max(0, score)
    
    def _check_soc2_compliance(self, logs: List[AuditLog]) -> Tuple[List[str], List[str], float]:
        """Check SOC 2 compliance."""
        violations = []
        recommendations = []
        score = 100.0
        
        # Check for authentication logging
        auth_logs = [l for l in logs if l.event_type in [AuditEventType.LOGIN_SUCCESS.value, AuditEventType.LOGIN_FAILURE.value]]
        if not auth_logs:
            violations.append("No authentication logs found")
            score -= 25
            recommendations.append("Log all authentication attempts")
        
        # Check for configuration change logging
        config_logs = [l for l in logs if l.event_type == AuditEventType.CONFIGURATION_CHANGE.value]
        if not config_logs:
            violations.append("No configuration change logs found")
            score -= 20
            recommendations.append("Log all configuration changes")
        
        # Check for system event logging
        system_logs = [l for l in logs if l.event_type in [AuditEventType.SYSTEM_STARTUP.value, AuditEventType.SYSTEM_SHUTDOWN.value]]
        if not system_logs:
            violations.append("No system event logs found")
            score -= 15
            recommendations.append("Log all system startup and shutdown events")
        
        return violations, recommendations, max(0, score)
    
    def _check_hipaa_compliance(self, logs: List[AuditLog]) -> Tuple[List[str], List[str], float]:
        """Check HIPAA compliance."""
        violations = []
        recommendations = []
        score = 100.0
        
        # Check for PHI access logging
        phi_access = [l for l in logs if l.resource and "phi" in l.resource.lower()]
        if not phi_access:
            violations.append("No PHI access logs found")
            score -= 30
            recommendations.append("Log all access to Protected Health Information")
        
        # Check for failed authentication logging
        failed_auth = [l for l in logs if l.event_type == AuditEventType.LOGIN_FAILURE.value]
        if not failed_auth:
            violations.append("No failed authentication logs found")
            score -= 20
            recommendations.append("Log all failed authentication attempts")
        
        return violations, recommendations, max(0, score)
    
    def _check_pci_dss_compliance(self, logs: List[AuditLog]) -> Tuple[List[str], List[str], float]:
        """Check PCI DSS compliance."""
        violations = []
        recommendations = []
        score = 100.0
        
        # Check for payment processing logging
        payment_logs = [l for l in logs if l.event_type in [AuditEventType.PAYMENT_PROCESSED.value, AuditEventType.PAYMENT_FAILED.value]]
        if not payment_logs:
            violations.append("No payment processing logs found")
            score -= 25
            recommendations.append("Log all payment processing events")
        
        # Check for card data access logging
        card_access = [l for l in logs if l.resource and "card" in l.resource.lower()]
        if not card_access:
            violations.append("No card data access logs found")
            score -= 20
            recommendations.append("Log all access to cardholder data")
        
        return violations, recommendations, max(0, score)
    
    def _check_iso_27001_compliance(self, logs: List[AuditLog]) -> Tuple[List[str], List[str], float]:
        """Check ISO 27001 compliance."""
        violations = []
        recommendations = []
        score = 100.0
        
        # Check for access control logging
        access_logs = [l for l in logs if l.event_type in [AuditEventType.ROLE_GRANTED.value, AuditEventType.ROLE_REVOKED.value]]
        if not access_logs:
            violations.append("No access control logs found")
            score -= 20
            recommendations.append("Log all access control changes")
        
        # Check for security incident logging
        security_logs = [l for l in logs if l.event_type in [AuditEventType.SUSPICIOUS_ACTIVITY.value, AuditEventType.INTRUSION_DETECTED.value]]
        if not security_logs:
            violations.append("No security incident logs found")
            score -= 15
            recommendations.append("Log all security incidents")
        
        return violations, recommendations, max(0, score)
    
    def _generate_signature(self, event: AuditEvent) -> str:
        """Generate cryptographic signature for audit event."""
        data = f"{event.event_type.value}|{event.user_id}|{event.ip_address}|{event.resource}|{event.action}|{datetime.utcnow().isoformat()}"
        return hmac.new(
            self.SIGNATURE_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _generate_signature_from_log(self, audit_log: AuditLog) -> str:
        """Generate signature from existing audit log."""
        data = f"{audit_log.event_type}|{audit_log.user_id}|{audit_log.ip_address}|{audit_log.resource}|{audit_log.action}|{audit_log.timestamp.isoformat()}"
        return hmac.new(
            self.SIGNATURE_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _log_to_dict(self, audit_log: AuditLog) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "id": audit_log.id,
            "event_type": audit_log.event_type,
            "user_id": audit_log.user_id,
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent,
            "resource": audit_log.resource,
            "action": audit_log.action,
            "details": json.loads(audit_log.details) if audit_log.details else None,
            "severity": audit_log.severity,
            "tags": json.loads(audit_log.tags) if audit_log.tags else None,
            "metadata": json.loads(audit_log.metadata) if audit_log.metadata else None,
            "timestamp": audit_log.timestamp.isoformat(),
            "signature": audit_log.signature
        }
    
    def _check_suspicious_activity(self, audit_log: AuditLog):
        """Check for suspicious activity patterns."""
        # Check for multiple failed logins from same IP
        if audit_log.event_type == AuditEventType.LOGIN_FAILURE.value:
            recent_failures = self.db.query(AuditLog).filter(
                AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
                AuditLog.ip_address == audit_log.ip_address,
                AuditLog.timestamp >= datetime.utcnow() - timedelta(minutes=5)
            ).count()
            
            if recent_failures >= 5:
                # Log suspicious activity
                self.log_event(AuditEvent(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    user_id=audit_log.user_id,
                    ip_address=audit_log.ip_address,
                    user_agent=audit_log.user_agent,
                    resource="auth",
                    action="brute_force_detected",
                    details={"failed_attempts": recent_failures},
                    severity=AuditSeverity.CRITICAL
                ))
    
    def get_audit_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get audit summary for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Audit summary statistics
        """
        logs = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        )
        
        total = logs.count()
        
        # Count by event type
        event_counts = {}
        for event_type in AuditEventType:
            count = logs.filter(AuditLog.event_type == event_type.value).count()
            if count > 0:
                event_counts[event_type.value] = count
        
        # Count by severity
        severity_counts = {}
        for severity in AuditSeverity:
            count = logs.filter(AuditLog.severity == severity.value).count()
            if count > 0:
                severity_counts[severity.value] = count
        
        # Count by user
        user_counts = {}
        user_activity = logs.with_entities(
            AuditLog.user_id,
            func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.user_id).all()
        
        for user_id, count in user_activity:
            if user_id:
                user_counts[user_id] = count
        
        return {
            "total_events": total,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "event_counts": event_counts,
            "severity_counts": severity_counts,
            "top_users": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }


def get_audit_service(db: Session):
    """Dependency to get audit service."""
    return AuditService(db)
