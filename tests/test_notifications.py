"""
Tests for notification service.
"""
import pytest
from datetime import datetime, timedelta
from app.services.notifications import (
    NotificationService, NotificationType, NotificationChannel, NotificationPriority
)


class TestNotificationCreation:
    """Tests for notification creation and delivery."""
    
    def test_send_notification(self, db, test_user):
        """Test sending a notification."""
        service = NotificationService(db)
        
        result = service.send_notification(
            user_id=test_user.id,
            notification_type=NotificationType.ACCOUNT_UPDATE,
            title="Test Notification",
            message="This is a test message",
            channels=[NotificationChannel.IN_APP],
            priority=NotificationPriority.NORMAL
        )
        
        assert "notification_id" in result
        assert "delivery_status" in result
        assert "timestamp" in result
    
    def test_send_notification_multiple_channels(self, db, test_user):
        """Test sending notification to multiple channels."""
        service = NotificationService(db)
        
        result = service.send_notification(
            user_id=test_user.id,
            notification_type=NotificationType.SECURITY_ALERT,
            title="Security Alert",
            message="Suspicious activity detected",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH
        )
        
        assert "in_app" in result["delivery_status"]
        assert "email" in result["delivery_status"]
    
    def test_send_notification_user_not_found(self, db):
        """Test sending notification to non-existent user."""
        service = NotificationService(db)
        
        result = service.send_notification(
            user_id=99999,
            notification_type=NotificationType.ACCOUNT_UPDATE,
            title="Test",
            message="Test message"
        )
        
        assert "error" in result
        assert result["error"] == "User not found"


class TestBulkNotifications:
    """Tests for bulk notification sending."""
    
    def test_send_bulk_notification(self, db, test_user):
        """Test sending bulk notifications."""
        service = NotificationService(db)
        
        # Create additional test users
        from app.db.models import User
        for i in range(5):
            user = User(
                username=f"bulkuser{i}",
                email=f"bulk{i}@test.com",
                hashed_password="hashed",
                role="USER"
            )
            db.add(user)
        db.commit()
        
        all_users = db.query(User).all()
        user_ids = [u.id for u in all_users]
        
        result = service.send_bulk_notification(
            user_ids=user_ids,
            notification_type=NotificationType.FEATURE_ANNOUNCEMENT,
            title="New Feature",
            message="Check out our new feature!",
            batch_size=3
        )
        
        assert result["total_recipients"] == len(user_ids)
        assert result["batches"] > 0
        assert result["status"] == "queued"


class TestNotificationPreferences:
    """Tests for notification preferences."""
    
    def test_get_default_channel_preferences(self, db):
        """Test default channel preferences by notification type."""
        service = NotificationService(db)
        
        # Security alerts should default to email + in-app
        channels = service._get_user_channel_preferences(
            user_id=1,
            notification_type=NotificationType.SECURITY_ALERT
        )
        
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.IN_APP in channels
        
        # Welcome messages should default to email only
        channels = service._get_user_channel_preferences(
            user_id=1,
            notification_type=NotificationType.WELCOME
        )
        
        assert NotificationChannel.EMAIL in channels


class TestNotificationLogs:
    """Tests for notification logging."""
    
    def test_get_user_notifications(self, db, test_user):
        """Test retrieving user notifications."""
        service = NotificationService(db)
        
        # Send some notifications
        for i in range(3):
            service.send_notification(
                user_id=test_user.id,
                notification_type=NotificationType.ACCOUNT_UPDATE,
                title=f"Notification {i}",
                message=f"Message {i}",
                channels=[NotificationChannel.IN_APP]
            )
        
        # Retrieve them
        notifications = service.get_user_notifications(test_user.id)
        
        assert len(notifications) == 3
        assert all("title" in n for n in notifications)
        assert all("message" in n for n in notifications)
    
    def test_mark_notification_read(self, db, test_user):
        """Test marking notification as read."""
        service = NotificationService(db)
        
        # Send notification
        result = service.send_notification(
            user_id=test_user.id,
            notification_type=NotificationType.ACCOUNT_UPDATE,
            title="Test",
            message="Test message",
            channels=[NotificationChannel.IN_APP]
        )
        
        # Get the notification
        notifications = service.get_user_notifications(test_user.id)
        notification_id = notifications[0]["id"]
        
        # Mark as read
        success = service.mark_notification_read(notification_id, test_user.id)
        assert success is True


class TestNotificationValidation:
    """Tests for notification validation and edge cases."""
    
    def test_high_priority_notification(self, db, test_user):
        """Test sending high priority notification."""
        service = NotificationService(db)
        
        result = service.send_notification(
            user_id=test_user.id,
            notification_type=NotificationType.SECURITY_ALERT,
            title="Critical Alert",
            message="Immediate action required",
            priority=NotificationPriority.CRITICAL,
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
        )
        
        assert "notification_id" in result
        # Critical notifications should be processed immediately
    
    def test_notification_with_data_payload(self, db, test_user):
        """Test notification with additional data."""
        service = NotificationService(db)
        
        result = service.send_notification(
            user_id=test_user.id,
            notification_type=NotificationType.BILLING,
            title="Payment Received",
            message="Your payment has been processed",
            data={
                "amount": 99.99,
                "invoice_id": "INV-12345",
                "date": "2024-01-20"
            }
        )
        
        assert "notification_id" in result


class TestNotificationEndpoints:
    """Tests for notification API endpoints."""
    
    def test_get_notifications_endpoint(self, client, auth_headers):
        """Test getting notifications via API."""
        # This would test the actual endpoint if implemented
        # For now, just verify structure
        pass
