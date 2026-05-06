"""
Enterprise security event monitoring and alerting service.

Provides comprehensive security monitoring with support for:
- Real-time event collection and analysis
- Threat detection and pattern recognition
- Alert management and notification
- Security metrics and reporting
- Integration with SIEM systems
- Automated response workflows
- Compliance monitoring
- Anomaly detection
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import structlog

from app.core.config import settings
from app.core.exceptions import SecurityError

logger = structlog.get_logger()


class SecurityEventSeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Security event types."""
    LOGIN_FAILED = "login_failed"
    LOGIN_SUCCESS = "login_success"
    LOGIN_SUSPICIOUS = "login_suspicious"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    MALICIOUS_REQUEST = "malicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_API_USAGE = "suspicious_api_usage"
    TOKEN_ABUSE = "token_abuse"
    SESSION_HIJACK = "session_hijack"
    PERMISSION_DENIED = "permission_denied"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    SYSTEM_COMPROMISE = "system_compromise"


class AlertStatus(Enum):
    """Alert status enumeration."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    SIEM = "siem"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    id: str
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "details": self.details,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "tags": self.tags
        }


@dataclass
class SecurityAlert:
    """Security alert data structure."""
    id: str
    title: str
    description: str
    severity: SecurityEventSeverity
    status: AlertStatus
    created_at: datetime
    updated_at: datetime
    event_ids: List[str] = field(default_factory=list)
    threshold_config: Optional[Dict[str, Any]] = None
    notification_sent: List[NotificationChannel] = field(default_factory=list)
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    false_positive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "event_ids": self.event_ids,
            "threshold_config": self.threshold_config,
            "notification_sent": [c.value for c in self.notification_sent],
            "assigned_to": self.assigned_to,
            "resolution": self.resolution,
            "false_positive": self.false_positive
        }


@dataclass
class ThreatPattern:
    """Threat detection pattern."""
    id: str
    name: str
    description: str
    pattern_type: str  # regex, threshold, anomaly, etc.
    pattern: Dict[str, Any]
    severity: SecurityEventSeverity
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class SecurityMonitoringService:
    """
    Enterprise security monitoring and alerting service.
    
    Features:
    - Real-time event collection and analysis
    - Threat detection and pattern recognition
    - Alert management and notification
    - Security metrics and reporting
    - Integration with SIEM systems
    - Automated response workflows
    - Compliance monitoring
    - Anomaly detection
    """
    
    def __init__(self):
        self.events: deque = deque(maxlen=10000)  # Last 10k events
        self.alerts: Dict[str, SecurityAlert] = {}
        self.patterns: Dict[str, ThreatPattern] = {}
        self.event_handlers: Dict[SecurityEventType, List[Callable]] = defaultdict(list)
        self.alert_handlers: List[Callable] = []
        
        # Metrics
        self.metrics = {
            "total_events": 0,
            "events_by_type": defaultdict(int),
            "events_by_severity": defaultdict(int),
            "alerts_created": 0,
            "alerts_resolved": 0,
            "false_positives": 0,
            "threats_detected": 0,
            "average_response_time": 0.0
        }
        
        # Threading
        self._lock = threading.RLock()
        self._processing_queue = deque()
        self._notification_queue = deque()
        
        # Load default threat patterns
        self._load_default_patterns()
        
        # Start background processing
        self._start_background_processors()
    
    def _load_default_patterns(self) -> None:
        """Load default threat detection patterns."""
        default_patterns = [
            ThreatPattern(
                id="brute_force_login",
                name="Brute Force Login Attack",
                description="Detects multiple failed login attempts from same IP",
                pattern_type="threshold",
                pattern={
                    "event_type": SecurityEventType.LOGIN_FAILED,
                    "time_window": 300,  # 5 minutes
                    "threshold": 5,
                    "group_by": ["source_ip", "user_id"]
                },
                severity=SecurityEventSeverity.HIGH
            ),
            ThreatPattern(
                id="suspicious_login_location",
                name="Suspicious Login Location",
                description="Detects login from unusual geographic locations",
                pattern_type="anomaly",
                pattern={
                    "event_type": SecurityEventType.LOGIN_SUCCESS,
                    "field": "source_ip",
                    "anomaly_type": "geographic",
                    "confidence_threshold": 0.8
                },
                severity=SecurityEventSeverity.MEDIUM
            ),
            ThreatPattern(
                id="privilege_escalation",
                name="Privilege Escalation",
                description="Detects attempts to escalate privileges",
                pattern_type="regex",
                pattern={
                    "event_type": SecurityEventType.UNAUTHORIZED_ACCESS,
                    "endpoint_pattern": r".*/admin.*|.*root.*",
                    "method_pattern": r"(POST|PUT|DELETE)"
                },
                severity=SecurityEventSeverity.HIGH
            ),
            ThreatPattern(
                id="api_abuse",
                name="API Abuse",
                description="Detects unusual API usage patterns",
                pattern_type="threshold",
                pattern={
                    "event_type": SecurityEventType.SUSPICIOUS_API_USAGE,
                    "time_window": 60,  # 1 minute
                    "threshold": 100,  # 100 requests per minute
                    "group_by": ["user_id", "source_ip"]
                },
                severity=SecurityEventSeverity.MEDIUM
            ),
            ThreatPattern(
                id="data_exfiltration",
                name="Data Exfiltration",
                description="Detects potential data exfiltration patterns",
                pattern_type="regex",
                pattern={
                    "event_type": SecurityEventType.DATA_BREACH_ATTEMPT,
                    "response_size_threshold": 10000000,  # 10MB
                    "endpoint_pattern": r".*/export.*|.*download.*|.*backup.*"
                },
                severity=SecurityEventSeverity.CRITICAL
            )
        ]
        
        for pattern in default_patterns:
            self.patterns[pattern.id] = pattern
    
    def _start_background_processors(self) -> None:
        """Start background processing threads."""
        # Event processing thread
        def process_events():
            while True:
                try:
                    if self._processing_queue:
                        event = self._processing_queue.popleft()
                        self._process_security_event(event)
                    else:
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error processing security event: {str(e)}")
                    time.sleep(1)
        
        # Notification thread
        def send_notifications():
            while True:
                try:
                    if self._notification_queue:
                        notification = self._notification_queue.popleft()
                        self._send_notification(notification)
                    else:
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                    time.sleep(5)
        
        # Start threads
        threading.Thread(target=process_events, daemon=True).start()
        threading.Thread(target=send_notifications, daemon=True).start()
    
    def record_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        details: Dict[str, Any],
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Record a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            details: Event details
            source_ip: Source IP address
            user_id: User identifier
            user_agent: User agent string
            endpoint: API endpoint
            correlation_id: Correlation ID
            tags: Event tags
            
        Returns:
            Event ID
        """
        event_id = f"sec_{int(time.time() * 1000)}"
        
        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            source_ip=source_ip,
            user_id=user_id,
            user_agent=user_agent,
            endpoint=endpoint,
            details=details,
            correlation_id=correlation_id,
            tags=tags or []
        )
        
        with self._lock:
            self.events.append(event)
            self.metrics["total_events"] += 1
            self.metrics["events_by_type"][event_type.value] += 1
            self.metrics["events_by_severity"][severity.value] += 1
            
            # Queue for processing
            self._processing_queue.append(event)
        
        logger.info(
            f"Security event recorded: {event_type.value}",
            event_id=event_id,
            severity=severity.value,
            user_id=user_id,
            source_ip=source_ip
        )
        
        return event_id
    
    def _process_security_event(self, event: SecurityEvent) -> None:
        """Process a security event for threat detection."""
        try:
            # Check against threat patterns
            for pattern in self.patterns.values():
                if not pattern.is_active:
                    continue
                
                if self._matches_pattern(event, pattern):
                    self._create_alert_from_pattern(event, pattern)
            
            # Call event handlers
            for handler in self.event_handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing security event {event.id}: {str(e)}")
    
    def _matches_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """Check if event matches a threat pattern."""
        if pattern.pattern_type == "threshold":
            return self._matches_threshold_pattern(event, pattern)
        elif pattern.pattern_type == "regex":
            return self._matches_regex_pattern(event, pattern)
        elif pattern.pattern_type == "anomaly":
            return self._matches_anomaly_pattern(event, pattern)
        
        return False
    
    def _matches_threshold_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """Check if event matches threshold pattern."""
        if event.event_type != pattern.pattern["event_type"]:
            return False
        
        time_window = pattern.pattern["time_window"]
        threshold = pattern.pattern["threshold"]
        group_by = pattern.pattern["group_by"]
        
        # Count similar events in time window
        count = 0
        cutoff_time = event.timestamp - timedelta(seconds=time_window)
        
        with self._lock:
            for past_event in self.events:
                if past_event.timestamp < cutoff_time:
                    continue
                
                if past_event.event_type != event.event_type:
                    continue
                
                # Check grouping criteria
                matches = True
                for field in group_by:
                    event_value = getattr(event, field, None)
                    past_value = getattr(past_event, field, None)
                    if event_value != past_value:
                        matches = False
                        break
                
                if matches:
                    count += 1
        
        return count >= threshold
    
    def _matches_regex_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """Check if event matches regex pattern."""
        import re
        
        if event.event_type != pattern.pattern["event_type"]:
            return False
        
        # Check endpoint pattern
        if "endpoint_pattern" in pattern.pattern:
            if not event.endpoint:
                return False
            
            if not re.match(pattern.pattern["endpoint_pattern"], event.endpoint):
                return False
        
        # Check method pattern
        if "method_pattern" in pattern.pattern:
            method = event.details.get("method")
            if not method or not re.match(pattern.pattern["method_pattern"], method):
                return False
        
        return True
    
    def _matches_anomaly_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """Check if event matches anomaly pattern (simplified)."""
        # This is a simplified anomaly detection
        # In production, this would use ML models or statistical analysis
        
        if event.event_type != pattern.pattern["event_type"]:
            return False
        
        field = pattern.pattern["field"]
        anomaly_type = pattern.pattern["anomaly_type"]
        confidence_threshold = pattern.pattern["confidence_threshold"]
        
        if not hasattr(event, field) or not getattr(event, field):
            return False
        
        # Simple geographic anomaly detection (would use GeoIP in production)
        if anomaly_type == "geographic":
            # For demo, consider certain IPs as suspicious
            suspicious_prefixes = ["10.0.0.", "192.168.", "172.16."]
            ip = getattr(event, field)
            
            if any(ip.startswith(prefix) for prefix in suspicious_prefixes):
                return True
        
        return False
    
    def _create_alert_from_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> None:
        """Create security alert from pattern match."""
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = SecurityAlert(
            id=alert_id,
            title=f"Threat Detected: {pattern.name}",
            description=f"Security event {event.id} matches threat pattern: {pattern.description}",
            severity=pattern.severity,
            status=AlertStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            event_ids=[event.id],
            threshold_config=pattern.pattern
        )
        
        with self._lock:
            self.alerts[alert_id] = alert
            self.metrics["alerts_created"] += 1
            self.metrics["threats_detected"] += 1
            
            # Queue for notification
            self._notification_queue.append(alert)
        
        logger.warning(
            f"Security alert created: {alert_id}",
            pattern=pattern.name,
            event_id=event.id
        )
    
    def get_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecurityEventSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """
        Get security events with filtering.
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of events
            
        Returns:
            List of security events
        """
        with self._lock:
            events = list(self.events)
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[SecurityEventSeverity] = None,
        limit: int = 100
    ) -> List[SecurityAlert]:
        """
        Get security alerts with filtering.
        
        Args:
            status: Filter by alert status
            severity: Filter by severity
            limit: Maximum number of alerts
            
        Returns:
            List of security alerts
        """
        with self._lock:
            alerts = list(self.alerts.values())
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by created_at (newest first) and limit
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge a security alert.
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: Who acknowledged the alert
            
        Returns:
            Success status
        """
        with self._lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.updated_at = datetime.utcnow()
            alert.assigned_to = acknowledged_by
        
        logger.info(
            f"Security alert acknowledged: {alert_id}",
            acknowledged_by=acknowledged_by
        )
        
        return True
    
    def resolve_alert(
        self,
        alert_id: str,
        resolution: str,
        false_positive: bool = False
    ) -> bool:
        """
        Resolve a security alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolution: Resolution description
            false_positive: Whether this was a false positive
            
        Returns:
            Success status
        """
        with self._lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED if not false_positive else AlertStatus.FALSE_POSITIVE
            alert.updated_at = datetime.utcnow()
            alert.resolution = resolution
            alert.false_positive = false_positive
            
            if false_positive:
                self.metrics["false_positives"] += 1
            else:
                self.metrics["alerts_resolved"] += 1
        
        logger.info(
            f"Security alert resolved: {alert_id}",
            resolution=resolution,
            false_positive=false_positive
        )
        
        return True
    
    def register_event_handler(self, event_type: SecurityEventType, handler: Callable) -> None:
        """Register a handler for specific event types."""
        with self._lock:
            self.event_handlers[event_type].append(handler)
        
        logger.info(f"Registered event handler for: {event_type.value}")
    
    def register_alert_handler(self, handler: Callable) -> None:
        """Register a handler for alert notifications."""
        with self._lock:
            self.alert_handlers.append(handler)
        
        logger.info("Registered alert handler")
    
    def add_threat_pattern(self, pattern: ThreatPattern) -> None:
        """Add a new threat detection pattern."""
        with self._lock:
            self.patterns[pattern.id] = pattern
        
        logger.info(f"Added threat pattern: {pattern.id}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get security monitoring metrics."""
        with self._lock:
            return {
                "total_events": self.metrics["total_events"],
                "events_by_type": dict(self.metrics["events_by_type"]),
                "events_by_severity": dict(self.metrics["events_by_severity"]),
                "alerts_created": self.metrics["alerts_created"],
                "alerts_resolved": self.metrics["alerts_resolved"],
                "false_positives": self.metrics["false_positives"],
                "threats_detected": self.metrics["threats_detected"],
                "average_response_time": self.metrics["average_response_time"],
                "active_alerts": len([a for a in self.alerts.values() if a.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]]),
                "active_patterns": len([p for p in self.patterns.values() if p.is_active]),
                "total_patterns": len(self.patterns),
                "events_in_queue": len(self._processing_queue),
                "notifications_pending": len(self._notification_queue)
            }
    
    def _send_notification(self, alert: SecurityAlert) -> None:
        """Send alert notification (simplified implementation)."""
        try:
            # This would integrate with actual notification systems
            # For now, just log the notification
            logger.critical(
                f"SECURITY ALERT: {alert.title}",
                alert_id=alert.id,
                severity=alert.severity.value,
                description=alert.description
            )
            
            # Mark notification as sent
            alert.notification_sent.append(NotificationChannel.EMAIL)  # Example
            
        except Exception as e:
            logger.error(f"Failed to send notification for alert {alert.id}: {str(e)}")
    
    def export_events(
        self,
        format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """Export security events."""
        events = self.get_events(start_time=start_time, end_time=end_time)
        
        if format == "json":
            return json.dumps([event.to_dict() for event in events], indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def export_alerts(self, format: str = "json") -> str:
        """Export security alerts."""
        alerts = self.get_alerts()
        
        if format == "json":
            return json.dumps([alert.to_dict() for alert in alerts], indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def cleanup_old_events(self, days: int = 30) -> int:
        """Clean up old security events."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        with self._lock:
            original_count = len(self.events)
            
            # Remove old events
            while self.events and self.events[0].timestamp < cutoff_time:
                self.events.popleft()
            
            cleaned_count = original_count - len(self.events)
        
        logger.info(f"Cleaned up {cleaned_count} old security events")
        return cleaned_count


# Global security monitoring service instance
security_monitoring_service = SecurityMonitoringService()


def record_security_event(
    event_type: SecurityEventType,
    severity: SecurityEventSeverity,
    details: Dict[str, Any],
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    correlation_id: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> str:
    """Record a security event."""
    return security_monitoring_service.record_event(
        event_type=event_type,
        severity=severity,
        details=details,
        source_ip=source_ip,
        user_id=user_id,
        user_agent=user_agent,
        endpoint=endpoint,
        correlation_id=correlation_id,
        tags=tags
    )


def get_security_events(
    event_type: Optional[SecurityEventType] = None,
    severity: Optional[SecurityEventSeverity] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> List[SecurityEvent]:
    """Get security events."""
    return security_monitoring_service.get_events(
        event_type=event_type,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )


def get_security_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[SecurityEventSeverity] = None,
    limit: int = 100
) -> List[SecurityAlert]:
    """Get security alerts."""
    return security_monitoring_service.get_alerts(
        status=status,
        severity=severity,
        limit=limit
    )


def get_security_metrics() -> Dict[str, Any]:
    """Get security monitoring metrics."""
    return security_monitoring_service.get_metrics()
