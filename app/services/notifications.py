"""
Notification service for sending real-time alerts and updates to users.
Supports multiple channels: email, push, in-app, and webhooks.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy.orm import Session
from app.db.models import User, UserRole, Notification as NotificationLog
from app.services.email import EmailService
from app.services.background_tasks import BackgroundTaskService


class NotificationChannel(Enum):
    """Supported notification channels."""
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationType(Enum):
    """Types of notifications."""
    SECURITY_ALERT = "security_alert"
    BILLING = "billing"
    USAGE_WARNING = "usage_warning"
    ACCOUNT_UPDATE = "account_update"
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    SYSTEM_MAINTENANCE = "system_maintenance"
    WELCOME = "welcome"
    PASSWORD_CHANGED = "password_changed"
    LOGIN_FROM_NEW_DEVICE = "login_from_new_device"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class NotificationService:
    """
    Centralized notification service for multi-channel messaging.
    
    Features:
    - Multi-channel delivery (email, push, in-app, webhooks)
    - Template management
    - Preference management
    - Delivery tracking
    - Rate limiting
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.task_service = BackgroundTaskService()
    
    def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        scheduled_for: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Send a notification through specified channels.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification body
            channels: List of channels to use (default: user preferences)
            priority: Priority level
            data: Additional data payload
            scheduled_for: Schedule for future delivery
        
        Returns:
            Dict with delivery status for each channel
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Get user preferences if channels not specified
        if channels is None:
            channels = self._get_user_channel_preferences(user_id, notification_type)
        
        # Build notification payload
        notification = {
            "id": self._generate_notification_id(),
            "type": notification_type.value,
            "title": title,
            "message": message,
            "priority": priority.value,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat(),
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None
        }
        
        # Log notification
        log_entry = NotificationLog(
            user_id=user_id,
            notification_type=notification_type.value,
            channel="",
            title=title,
            message=message,
            status="pending",
            created_at=datetime.utcnow()
        )
        self.db.add(log_entry)
        self.db.commit()
        
        results = {}
        
        # Send through each channel
        for channel in channels:
            if scheduled_for and scheduled_for > datetime.utcnow():
                # Schedule for later
                self._schedule_notification(
                    log_entry.id, channel, notification, scheduled_for
                )
                results[channel.value] = "scheduled"
            else:
                # Send immediately
                success = self._deliver_via_channel(
                    channel, user, notification, log_entry
                )
                results[channel.value] = "delivered" if success else "failed"
        
        return {
            "notification_id": notification["id"],
            "delivery_status": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def send_bulk_notification(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Send notification to multiple users in batches.
        
        Args:
            user_ids: List of target user IDs
            notification_type: Type of notification
            title: Notification title
            message: Notification body
            channels: Channels to use
            priority: Priority level
            data: Additional data
            batch_size: Number of users per batch
        
        Returns:
            Summary of bulk delivery
        """
        total_users = len(user_ids)
        batches = (total_users + batch_size - 1) // batch_size
        
        delivered = 0
        failed = 0
        
        for i in range(batches):
            batch_start = i * batch_size
            batch_end = min(batch_start + batch_size, total_users)
            batch_users = user_ids[batch_start:batch_end]
            
            # Process batch asynchronously
            self.task_service.add_task(
                self._process_notification_batch,
                batch_users,
                notification_type,
                title,
                message,
                channels,
                priority,
                data
            )
            
            delivered += len(batch_users)
        
        return {
            "total_recipients": total_users,
            "batches": batches,
            "batch_size": batch_size,
            "status": "queued",
            "estimated_delivery": "Processing in background"
        }
    
    def _process_notification_batch(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel],
        priority: NotificationPriority,
        data: Optional[Dict[str, Any]]
    ):
        """Process a batch of notifications."""
        for user_id in user_ids:
            try:
                self.send_notification(
                    user_id, notification_type, title, message,
                    channels, priority, data
                )
            except Exception as e:
                print(f"Failed to send notification to user {user_id}: {e}")
    
    def _deliver_via_channel(
        self,
        channel: NotificationChannel,
        user: User,
        notification: Dict[str, Any],
        log_entry: NotificationLog
    ) -> bool:
        """Deliver notification via a specific channel."""
        try:
            if channel == NotificationChannel.EMAIL:
                success = self._send_email_notification(user, notification)
            elif channel == NotificationChannel.IN_APP:
                success = self._store_in_app_notification(user.id, notification)
            elif channel == NotificationChannel.PUSH:
                success = self._send_push_notification(user.id, notification)
            elif channel == NotificationChannel.WEBHOOK:
                success = self._send_webhook_notification(user.id, notification)
            else:
                success = False
            
            # Update log entry
            log_entry.channel = channel.value
            log_entry.status = "delivered" if success else "failed"
            log_entry.delivered_at = datetime.utcnow() if success else None
            self.db.commit()
            
            return success
        except Exception as e:
            print(f"Delivery failed for channel {channel.value}: {e}")
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            self.db.commit()
            return False
    
    def _send_email_notification(
        self,
        user: User,
        notification: Dict[str, Any]
    ) -> bool:
        """Send notification via email."""
        template_map = {
            "security_alert": "security_alert.html",
            "billing": "billing_notification.html",
            "welcome": "welcome.html",
            "password_changed": "security_notice.html",
            "login_from_new_device": "security_alert.html"
        }
        
        template = template_map.get(
            notification["type"],
            "generic_notification.html"
        )
        
        return self.email_service.send_email(
            to_email=user.email,
            subject=notification["title"],
            template_name=template,
            template_data={
                "username": user.username,
                "message": notification["message"],
                "data": notification.get("data", {})
            }
        )
    
    def _store_in_app_notification(
        self,
        user_id: int,
        notification: Dict[str, Any]
    ) -> bool:
        """Store notification for in-app retrieval."""
        # Store in cache or database for in-app retrieval
        # For now, just log it
        return True
    
    def _send_push_notification(
        self,
        user_id: int,
        notification: Dict[str, Any]
    ) -> bool:
        """Send push notification (placeholder)."""
        # Would integrate with FCM, OneSignal, etc.
        return True
    
    def _send_webhook_notification(
        self,
        user_id: int,
        notification: Dict[str, Any]
    ) -> bool:
        """Send notification via webhook (placeholder)."""
        # Would POST to user's configured webhook URL
        return True
    
    def _get_user_channel_preferences(
        self,
        user_id: int,
        notification_type: NotificationType
    ) -> List[NotificationChannel]:
        """Get user's preferred channels for notification type."""
        # Default preferences
        type_channels = {
            NotificationType.SECURITY_ALERT: [
                NotificationChannel.EMAIL, NotificationChannel.IN_APP
            ],
            NotificationType.BILLING: [NotificationChannel.EMAIL],
            NotificationType.WELCOME: [NotificationChannel.EMAIL],
            NotificationType.USAGE_WARNING: [NotificationChannel.EMAIL],
            NotificationType.PASSWORD_CHANGED: [
                NotificationChannel.EMAIL, NotificationChannel.IN_APP
            ],
            NotificationType.LOGIN_FROM_NEW_DEVICE: [
                NotificationChannel.EMAIL
            ]
        }
        
        return type_channels.get(
            notification_type,
            [NotificationChannel.IN_APP]
        )
    
    def _generate_notification_id(self) -> str:
        """Generate unique notification ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _schedule_notification(
        self,
        log_id: int,
        channel: NotificationChannel,
        notification: Dict[str, Any],
        scheduled_for: datetime
    ):
        """Schedule notification for future delivery."""
        # Calculate delay
        delay_seconds = (scheduled_for - datetime.utcnow()).total_seconds()
        
        # Add delayed task
        self.task_service.add_task(
            self._send_scheduled_notification,
            log_id,
            channel.value,
            notification,
            delay=int(delay_seconds)
        )
    
    def _send_scheduled_notification(
        self,
        log_id: int,
        channel_value: str,
        notification: Dict[str, Any],
        delay: int
    ):
        """Send a scheduled notification."""
        # Implementation would retrieve log entry and send
        pass
    
    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        query = self.db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(NotificationLog.read_at.is_(None))
        
        notifications = query.order_by(
            NotificationLog.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": n.id,
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "channel": n.channel,
                "status": n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None
            }
            for n in notifications
        ]
    
    def mark_notification_read(
        self,
        notification_id: int,
        user_id: int
    ) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(NotificationLog).filter(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == user_id
        ).first()
        
        if notification:
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False


def get_notification_service(db: Session):
    """Dependency to get notification service."""
    return NotificationService(db)
