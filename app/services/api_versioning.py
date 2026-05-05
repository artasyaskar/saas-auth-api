"""
API Versioning and Deprecation Service

Comprehensive API versioning service for managing API versions,
deprecation schedules, and backward compatibility.

Features:
- API version management
- Version routing
- Deprecation scheduling
- Sunset notifications
- Breaking change tracking
- Version compatibility matrix
- Migration guides
- Version analytics
- Canary deployments
- A/B testing by version
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
from sqlalchemy.orm import Session

from app.db.models import User, APIVersion, APIEndpoint
from app.core.config import settings


class VersionStatus(Enum):
    """API version status."""
    DRAFT = "draft"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    RETIRED = "retired"


@dataclass
class VersionConfig:
    """API version configuration."""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None
    breaking_changes: List[str] = field(default_factory=list)
    migration_guide: Optional[str] = None
    canary_percentage: int = 0


@dataclass
class EndpointConfig:
    """Endpoint configuration."""
    path: str
    method: str
    versions: List[str]
    default_version: str
    deprecated_in: Optional[str] = None
    removed_in: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)


class APIVersioningService:
    """
    Enterprise-grade API versioning service.
    
    Features:
    - API version management
    - Version routing
    - Deprecation scheduling
    - Sunset notifications
    - Breaking change tracking
    - Version compatibility matrix
    - Migration guides
    - Version analytics
    - Canary deployments
    - A/B testing by version
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._version_handlers: Dict[str, Dict[str, Callable]] = {}
        self._middleware_registry: List[Callable] = []
    
    def register_version(self, config: VersionConfig) -> str:
        """
        Register a new API version.
        
        Args:
            config: Version configuration
        
        Returns:
            Version ID
        """
        version = APIVersion(
            version=config.version,
            status=config.status.value,
            release_date=config.release_date,
            deprecation_date=config.deprecation_date,
            sunset_date=config.sunset_date,
            retirement_date=config.retirement_date,
            breaking_changes=json.dumps(config.breaking_changes),
            migration_guide=config.migration_guide,
            canary_percentage=config.canary_percentage,
            created_at=datetime.utcnow()
        )
        
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        
        return str(version.id)
    
    def update_version_status(
        self,
        version: str,
        status: VersionStatus,
        dates: Optional[Dict[str, datetime]] = None
    ) -> bool:
        """
        Update version status and dates.
        
        Args:
            version: Version string
            status: New status
            dates: Optional date updates
        
        Returns:
            Success status
        """
        version_record = self.db.query(APIVersion).filter(
            APIVersion.version == version
        ).first()
        
        if not version_record:
            return False
        
        version_record.status = status.value
        
        if dates:
            if 'deprecation_date' in dates:
                version_record.deprecation_date = dates['deprecation_date']
            if 'sunset_date' in dates:
                version_record.sunset_date = dates['sunset_date']
            if 'retirement_date' in dates:
                version_record.retirement_date = dates['retirement_date']
        
        version_record.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific version."""
        version_record = self.db.query(APIVersion).filter(
            APIVersion.version == version
        ).first()
        
        if not version_record:
            return None
        
        return {
            'version': version_record.version,
            'status': version_record.status,
            'release_date': version_record.release_date.isoformat(),
            'deprecation_date': version_record.deprecation_date.isoformat() if version_record.deprecation_date else None,
            'sunset_date': version_record.sunset_date.isoformat() if version_record.sunset_date else None,
            'retirement_date': version_record.retirement_date.isoformat() if version_record.retirement_date else None,
            'breaking_changes': json.loads(version_record.breaking_changes) if version_record.breaking_changes else [],
            'migration_guide': version_record.migration_guide,
            'canary_percentage': version_record.canary_percentage
        }
    
    def get_all_versions(self) -> List[Dict[str, Any]]:
        """Get all API versions."""
        versions = self.db.query(APIVersion).order_by(
            APIVersion.release_date.desc()
        ).all()
        
        return [
            {
                'version': v.version,
                'status': v.status,
                'release_date': v.release_date.isoformat(),
                'is_deprecated': v.status == VersionStatus.DEPRECATED.value,
                'is_sunset': v.status == VersionStatus.SUNSET.value,
                'is_retired': v.status == VersionStatus.RETIRED.value
            }
            for v in versions
        ]
    
    def get_active_versions(self) -> List[str]:
        """Get all active (non-retired) versions."""
        versions = self.db.query(APIVersion).filter(
            APIVersion.status.in_([
                VersionStatus.BETA.value,
                VersionStatus.STABLE.value,
                VersionStatus.DEPRECATED.value
            ])
        ).all()
        
        return [v.version for v in versions]
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest stable version."""
        version = self.db.query(APIVersion).filter(
            APIVersion.status == VersionStatus.STABLE.value
        ).order_by(
            APIVersion.release_date.desc()
        ).first()
        
        return version.version if version else None
    
    def schedule_deprecation(
        self,
        version: str,
        deprecation_date: datetime,
        sunset_date: datetime,
        retirement_date: datetime
    ) -> bool:
        """
        Schedule version deprecation timeline.
        
        Args:
            version: Version to deprecate
            deprecation_date: When to mark as deprecated
            sunset_date: When to mark as sunset
            retirement_date: When to retire
        
        Returns:
            Success status
        """
        return self.update_version_status(
            version,
            VersionStatus.STABLE,
            {
                'deprecation_date': deprecation_date,
                'sunset_date': sunset_date,
                'retirement_date': retirement_date
            }
        )
    
    def check_version_status(self, version: str) -> Dict[str, Any]:
        """
        Check if a version needs status update based on dates.
        
        Args:
            version: Version to check
        
        Returns:
            Status information
        """
        version_info = self.get_version_info(version)
        if not version_info:
            return {'error': 'Version not found'}
        
        now = datetime.utcnow()
        updates_needed = []
        
        # Check if deprecation date has passed
        if version_info['deprecation_date'] and \
           datetime.fromisoformat(version_info['deprecation_date']) <= now and \
           version_info['status'] != VersionStatus.DEPRECATED.value:
            updates_needed.append(('status', VersionStatus.DEPRECATED))
        
        # Check if sunset date has passed
        if version_info['sunset_date'] and \
           datetime.fromisoformat(version_info['sunset_date']) <= now and \
           version_info['status'] != VersionStatus.SUNSET.value:
            updates_needed.append(('status', VersionStatus.SUNSET))
        
        # Check if retirement date has passed
        if version_info['retirement_date'] and \
           datetime.fromisoformat(version_info['retirement_date']) <= now and \
           version_info['status'] != VersionStatus.RETIRED.value:
            updates_needed.append(('status', VersionStatus.RETIRED))
        
        return {
            'version': version,
            'current_status': version_info['status'],
            'updates_needed': updates_needed,
            'days_until_deprecation': self._days_until(version_info['deprecation_date']),
            'days_until_sunset': self._days_until(version_info['sunset_date']),
            'days_until_retirement': self._days_until(version_info['retirement_date'])
        }
    
    def _days_until(self, date_str: Optional[str]) -> Optional[int]:
        """Calculate days until a date."""
        if not date_str:
            return None
        
        date = datetime.fromisoformat(date_str)
        delta = date - datetime.utcnow()
        return max(0, delta.days)
    
    def register_endpoint(self, config: EndpointConfig) -> str:
        """
        Register an endpoint with version information.
        
        Args:
            config: Endpoint configuration
        
        Returns:
            Endpoint ID
        """
        endpoint = APIEndpoint(
            path=config.path,
            method=config.method,
            versions=json.dumps(config.versions),
            default_version=config.default_version,
            deprecated_in=config.deprecated_in,
            removed_in=config.removed_in,
            alternatives=json.dumps(config.alternatives),
            created_at=datetime.utcnow()
        )
        
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        
        return str(endpoint.id)
    
    def route_request(
        self,
        path: str,
        method: str,
        requested_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate version handler.
        
        Args:
            path: Request path
            method: HTTP method
            requested_version: Requested API version
        
        Returns:
            Routing information
        """
        # Find endpoint
        endpoint = self.db.query(APIEndpoint).filter(
            APIEndpoint.path == path,
            APIEndpoint.method == method
        ).first()
        
        if not endpoint:
            return {'error': 'Endpoint not found'}
        
        versions = json.loads(endpoint.versions)
        default_version = endpoint.default_version
        
        # Determine version to use
        if requested_version:
            if requested_version not in versions:
                return {
                    'error': 'Requested version not supported',
                    'available_versions': versions,
                    'default_version': default_version
                }
            target_version = requested_version
        else:
            target_version = default_version
        
        # Check if version is deprecated
        version_info = self.get_version_info(target_version)
        if version_info and version_info['status'] in [
            VersionStatus.DEPRECATED.value,
            VersionStatus.SUNSET.value,
            VersionStatus.RETIRED.value
        ]:
            return {
                'error': 'Version is deprecated or retired',
                'version_status': version_info['status'],
                'sunset_date': version_info['sunset_date'],
                'alternatives': json.loads(endpoint.alternatives) if endpoint.alternatives else []
            }
        
        return {
            'endpoint': path,
            'method': method,
            'version': target_version,
            'handler': self._get_version_handler(target_version, path, method)
        }
    
    def _get_version_handler(
        self,
        version: str,
        path: str,
        method: str
    ) -> Optional[Callable]:
        """Get handler for a specific version and endpoint."""
        if version in self._version_handlers:
            version_handlers = self._version_handlers[version]
            key = f"{method}:{path}"
            return version_handlers.get(key)
        return None
    
    def register_version_handler(
        self,
        version: str,
        path: str,
        method: str,
        handler: Callable
    ):
        """Register a handler for a specific version and endpoint."""
        if version not in self._version_handlers:
            self._version_handlers[version] = {}
        
        key = f"{method}:{path}"
        self._version_handlers[version][key] = handler
    
    def add_version_middleware(self, middleware: Callable):
        """Add middleware for version handling."""
        self._middleware_registry.append(middleware)
    
    def get_version_analytics(
        self,
        version: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific version.
        
        Args:
            version: API version
            start_date: Start date
            end_date: End date
        
        Returns:
            Analytics data
        """
        # In production, this would query usage logs
        return {
            'version': version,
            'total_requests': 0,
            'unique_users': 0,
            'avg_response_time_ms': 0,
            'error_rate': 0,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_compatibility_matrix(self) -> Dict[str, List[str]]:
        """Get version compatibility matrix."""
        versions = self.get_all_versions()
        
        matrix = {}
        for v in versions:
            version_str = v['version']
            # In production, this would be based on actual compatibility
            matrix[version_str] = [
                other['version']
                for other in versions
                if other['version'] != version_str
            ]
        
        return matrix
    
    def generate_migration_guide(
        self,
        from_version: str,
        to_version: str
    ) -> Dict[str, Any]:
        """
        Generate migration guide between versions.
        
        Args:
            from_version: Source version
            to_version: Target version
        
        Returns:
            Migration guide
        """
        from_info = self.get_version_info(from_version)
        to_info = self.get_version_info(to_version)
        
        if not from_info or not to_info:
            return {'error': 'One or both versions not found'}
        
        breaking_changes = to_info.get('breaking_changes', [])
        
        return {
            'from_version': from_version,
            'to_version': to_version,
            'breaking_changes': breaking_changes,
            'migration_steps': [
                f"Review breaking changes: {', '.join(breaking_changes)}",
                f"Update API calls to use {to_version} endpoints",
                f"Test with {to_version} in beta/staging",
                f"Deploy to production with feature flags",
                f"Monitor for errors and rollback if needed"
            ],
            'estimated_effort': 'Medium' if len(breaking_changes) < 5 else 'High',
            'recommended_actions': [
                'Update integration tests',
                'Update API documentation',
                'Notify API consumers',
                'Set up monitoring for migration'
            ]
        }
    
    def set_canary_percentage(self, version: str, percentage: int) -> bool:
        """
        Set canary deployment percentage for a version.
        
        Args:
            version: Version string
            percentage: Percentage (0-100)
        
        Returns:
            Success status
        """
        if not 0 <= percentage <= 100:
            return False
        
        version_record = self.db.query(APIVersion).filter(
            APIVersion.version == version
        ).first()
        
        if not version_record:
            return False
        
        version_record.canary_percentage = percentage
        version_record.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def check_canary_eligibility(self, user_id: int, version: str) -> bool:
        """
        Check if a user should receive canary version.
        
        Args:
            user_id: User ID
            version: Version string
        
        Returns:
            True if user should receive canary
        """
        version_info = self.get_version_info(version)
        if not version_info:
            return False
        
        canary_percentage = version_info.get('canary_percentage', 0)
        
        if canary_percentage == 0:
            return False
        if canary_percentage == 100:
            return True
        
        # Use hash of user_id for consistent selection
        hash_value = hash(user_id) % 100
        return hash_value < canary_percentage
    
    def get_deprecation_schedule(self) -> List[Dict[str, Any]]:
        """Get upcoming deprecation schedule."""
        versions = self.db.query(APIVersion).filter(
            APIVersion.status.in_([
                VersionStatus.STABLE.value,
                VersionStatus.DEPRECATED.value
            ])
        ).all()
        
        schedule = []
        now = datetime.utcnow()
        
        for v in versions:
            if v.deprecation_date and v.deprecation_date > now:
                schedule.append({
                    'version': v.version,
                    'event': 'deprecation',
                    'date': v.deprecation_date.isoformat(),
                    'days_until': (v.deprecation_date - now).days
                })
            
            if v.sunset_date and v.sunset_date > now:
                schedule.append({
                    'version': v.version,
                    'event': 'sunset',
                    'date': v.sunset_date.isoformat(),
                    'days_until': (v.sunset_date - now).days
                })
            
            if v.retirement_date and v.retirement_date > now:
                schedule.append({
                    'version': v.version,
                    'event': 'retirement',
                    'date': v.retirement_date.isoformat(),
                    'days_until': (v.retirement_date - now).days
                })
        
        return sorted(schedule, key=lambda x: x['days_until'])


def get_api_versioning_service(db: Session):
    """Dependency to get API versioning service."""
    return APIVersioningService(db)
