"""
Data export service for GDPR compliance and data portability.
Supports multiple export formats and comprehensive data gathering.
"""
import json
import csv
import io
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, BinaryIO
from sqlalchemy.orm import Session
from app.db.models import (
    User, UsageLog, Subscription, RateLimit,
    TokenBlacklist, PasswordResetToken, AuditLog
)


class ExportFormat:
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    ZIP = "zip"


class DataExportService:
    """
    Comprehensive data export service for user data portability.
    
    Features:
    - GDPR-compliant data export
    - Multiple export formats
    - Data anonymization options
    - Scheduled exports
    - Progress tracking
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def export_user_data(
        self,
        user_id: int,
        format: str = ExportFormat.JSON,
        include_analytics: bool = True,
        anonymize: bool = False
    ) -> Dict[str, Any]:
        """
        Export all data for a specific user.
        
        Args:
            user_id: User ID to export
            format: Export format (json, csv, zip)
            include_analytics: Include usage analytics
            anonymize: Anonymize sensitive data
        
        Returns:
            Export result with download URL or data
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {"error": "User not found"}
        
        # Gather all user data
        export_data = {
            "export_metadata": {
                "user_id": user_id,
                "username": user.username if not anonymize else "ANON_" + str(user_id),
                "export_date": datetime.utcnow().isoformat(),
                "format": format,
                "version": "1.0"
            },
            "profile": self._export_profile(user, anonymize),
            "usage_history": self._export_usage_history(user_id, include_analytics),
            "security_events": self._export_security_events(user_id),
            "subscriptions": self._export_subscriptions(user_id),
            "rate_limits": self._export_rate_limits(user_id),
            "audit_logs": self._export_audit_logs(user_id)
        }
        
        # Convert to requested format
        if format == ExportFormat.JSON:
            return self._to_json(export_data)
        elif format == ExportFormat.CSV:
            return self._to_csv(export_data)
        elif format == ExportFormat.ZIP:
            return self._to_zip(export_data)
        else:
            return {"error": "Unsupported format"}
    
    def _export_profile(self, user: User, anonymize: bool) -> Dict[str, Any]:
        """Export user profile data."""
        return {
            "id": user.id,
            "username": user.username if not anonymize else f"ANON_{user.id}",
            "email": user.email if not anonymize else f"user_{user.id}@example.com",
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": getattr(user, 'last_login', None),
            "subscription_plan": user.subscription_plan.value if user.subscription_plan else None
        }
    
    def _export_usage_history(
        self,
        user_id: int,
        include_analytics: bool
    ) -> Dict[str, Any]:
        """Export usage history and analytics."""
        logs = self.db.query(UsageLog).filter(
            UsageLog.user_id == user_id
        ).order_by(UsageLog.timestamp.desc()).all()
        
        usage_entries = [
            {
                "id": log.id,
                "endpoint": log.endpoint,
                "method": log.method,
                "status_code": log.status_code,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "response_time_ms": log.response_time_ms,
                "ip_address": log.ip_address
            }
            for log in logs
        ]
        
        result = {"entries": usage_entries, "total_requests": len(usage_entries)}
        
        if include_analytics:
            # Calculate analytics
            endpoints = {}
            for log in logs:
                ep = log.endpoint
                if ep not in endpoints:
                    endpoints[ep] = {"count": 0, "total_time": 0}
                endpoints[ep]["count"] += 1
                endpoints[ep]["total_time"] += (log.response_time_ms or 0)
            
            result["analytics"] = {
                "endpoints": {
                    ep: {
                        "request_count": data["count"],
                        "avg_response_time": data["total_time"] / data["count"] if data["count"] > 0 else 0
                    }
                    for ep, data in endpoints.items()
                }
            }
        
        return result
    
    def _export_security_events(self, user_id: int) -> List[Dict[str, Any]]:
        """Export security-related events."""
        # Get password reset tokens
        reset_tokens = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id
        ).all()
        
        # Get blacklisted tokens
        blacklisted = self.db.query(TokenBlacklist).filter(
            TokenBlacklist.user_id == user_id
        ).all()
        
        return {
            "password_resets": [
                {
                    "id": t.id,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                    "used_at": t.used_at.isoformat() if t.used_at else None
                }
                for t in reset_tokens
            ],
            "token_blacklist_events": [
                {
                    "id": b.id,
                    "blacklisted_at": b.blacklisted_at.isoformat() if b.blacklisted_at else None,
                    "token_type": b.token_type,
                    "reason": b.reason
                }
                for b in blacklisted
            ]
        }
    
    def _export_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Export subscription history."""
        subscriptions = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).all()
        
        return [
            {
                "id": sub.id,
                "stripe_subscription_id": sub.stripe_subscription_id,
                "status": sub.status,
                "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None
            }
            for sub in subscriptions
        ]
    
    def _export_rate_limits(self, user_id: int) -> Dict[str, Any]:
        """Export rate limit configuration and usage."""
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id
        ).first()
        
        if not rate_limit:
            return {}
        
        return {
            "requests_per_minute": rate_limit.requests_per_minute,
            "monthly_quota": rate_limit.monthly_quota,
            "current_monthly_usage": rate_limit.current_monthly_usage,
            "last_monthly_reset": rate_limit.last_monthly_reset.isoformat() if rate_limit.last_monthly_reset else None
        }
    
    def _export_audit_logs(self, user_id: int) -> List[Dict[str, Any]]:
        """Export audit logs."""
        logs = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(1000).all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ]
    
    def _to_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert export data to JSON format."""
        return {
            "format": "json",
            "data": data,
            "export_timestamp": datetime.utcnow().isoformat()
        }
    
    def _to_csv(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert export data to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write usage data as CSV
        writer.writerow(["Export Type", "Data"])
        writer.writerow(["Profile", json.dumps(data["profile"])])
        usage_count = len(data["usage_history"]) if isinstance(data["usage_history"], list) else 0
        writer.writerow(["Usage Count", usage_count])
        security_events = data.get("security_events", [])
        writer.writerow(["Security Events", json.dumps(security_events)])
        
        return {
            "format": "csv",
            "content": output.getvalue(),
            "export_timestamp": datetime.utcnow().isoformat()
        }
    
    def _to_zip(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert export data to ZIP format."""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add JSON data
            zip_file.writestr(
                'export.json',
                json.dumps(data, indent=2)
            )
            
            # Add usage CSV
            usage_csv = io.StringIO()
            writer = csv.writer(usage_csv)
            writer.writerow(['ID', 'Endpoint', 'Method', 'Status', 'Timestamp', 'Response Time'])
            
            for entry in data["usage_history"]["entries"]:
                writer.writerow([
                    entry['id'],
                    entry['endpoint'],
                    entry['method'],
                    entry['status_code'],
                    entry['timestamp'],
                    entry['response_time_ms']
                ])
            
            zip_file.writestr('usage_history.csv', usage_csv.getvalue())
            
            # Add README
            readme = f"""
Data Export Package
Generated: {datetime.utcnow().isoformat()}
User ID: {data['export_metadata']['user_id']}

Contents:
- export.json: Complete data export in JSON format
- usage_history.csv: API usage history

For support, contact privacy@example.com
            """
            zip_file.writestr('README.txt', readme.strip())
        
        zip_buffer.seek(0)
        
        return {
            "format": "zip",
            "content": zip_buffer.getvalue(),
            "filename": f"data_export_{data['export_metadata']['user_id']}_{datetime.utcnow().strftime('%Y%m%d')}.zip"
        }
    
    def export_all_users(
        self,
        format: str = ExportFormat.CSV,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export data for multiple users (admin only).
        
        Args:
            format: Export format
            filters: Optional filters (role, plan, status)
        
        Returns:
            Export result
        """
        query = self.db.query(User)
        
        if filters:
            if 'role' in filters:
                query = query.filter(User.role == filters['role'])
            if 'plan' in filters:
                query = query.filter(User.subscription_plan == filters['plan'])
            if 'is_active' in filters:
                query = query.filter(User.is_active == filters['is_active'])
        
        users = query.all()
        
        export_data = {
            "export_metadata": {
                "total_users": len(users),
                "export_date": datetime.utcnow().isoformat(),
                "format": format,
                "filters": filters
            },
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role.value if u.role else None,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "subscription_plan": u.subscription_plan.value if u.subscription_plan else None
                }
                for u in users
            ]
        }
        
        if format == ExportFormat.JSON:
            return self._to_json(export_data)
        elif format == ExportFormat.CSV:
            return self._export_users_to_csv(users)
        else:
            return {"error": "Unsupported format for bulk export"}
    
    def _export_users_to_csv(self, users: List[User]) -> Dict[str, Any]:
        """Export user list to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'ID', 'Username', 'Email', 'Role', 'Active',
            'Plan', 'Created At'
        ])
        
        for u in users:
            writer.writerow([
                u.id,
                u.username,
                u.email,
                u.role.value if u.role else None,
                u.is_active,
                u.subscription_plan.value if u.subscription_plan else None,
                u.created_at.isoformat() if u.created_at else None
            ])
        
        return {
            "format": "csv",
            "content": output.getvalue(),
            "filename": f"users_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }


def get_export_service(db: Session):
    """Dependency to get export service."""
    return DataExportService(db)
