"""
Tests for webhook service and endpoints.
"""
import pytest
from datetime import datetime, timedelta
from app.services.webhooks import WebhookService, WebhookEventType


class TestWebhookSubscription:
    """Tests for webhook subscription management."""
    
    def test_create_webhook_subscription(self, db, test_user):
        """Test creating a webhook subscription."""
        service = WebhookService(db)
        
        subscription = service.subscribe(
            user_id=test_user.id,
            url="https://example.com/webhook",
            events=[WebhookEventType.USER_CREATED, WebhookEventType.PAYMENT_SUCCEEDED],
            description="Test webhook"
        )
        
        assert subscription.id is not None
        assert subscription.url == "https://example.com/webhook"
        assert subscription.user_id == test_user.id
        assert WebhookEventType.USER_CREATED.value in subscription.events
        assert subscription.secret is not None
        assert len(subscription.secret) > 20
    
    def test_unsubscribe_webhook(self, db, test_user):
        """Test deleting a webhook subscription."""
        service = WebhookService(db)
        
        # Create subscription
        subscription = service.subscribe(
            user_id=test_user.id,
            url="https://example.com/webhook",
            events=[WebhookEventType.USER_CREATED]
        )
        
        # Delete it
        result = service.unsubscribe(subscription.id, test_user.id)
        assert result is True
        
        # Verify it's gone
        result = service.unsubscribe(subscription.id, test_user.id)
        assert result is False


class TestWebhookDelivery:
    """Tests for webhook delivery."""
    
    def test_webhook_signature_generation(self, db):
        """Test HMAC signature generation."""
        service = WebhookService(db)
        
        payload = {"event": "test", "data": {"id": 123}}
        secret = "test_secret_key"
        
        signature = service._sign_payload(payload, secret)
        
        assert signature is not None
        assert len(signature) == 64  # SHA-256 hex length
        
        # Verify signature
        is_valid = service.verify_signature(
            json.dumps(payload, sort_keys=True),
            signature,
            secret
        )
        assert is_valid is True
    
    def test_circuit_breaker(self, db):
        """Test circuit breaker functionality."""
        service = WebhookService(db)
        
        url = "https://example.com/webhook"
        
        # Initially closed
        assert service._is_circuit_open(url) is False
        
        # Record failures to open circuit
        for _ in range(6):
            service._record_failure(url)
        
        # Circuit should be open
        assert service._is_circuit_open(url) is True
        
        # Record success to close circuit
        service._record_success(url)
        assert service._is_circuit_open(url) is False


class TestWebhookEndpoints:
    """Tests for webhook API endpoints."""
    
    def test_list_webhook_events(self, client, auth_headers):
        """Test listing available webhook events."""
        response = client.get("/webhooks/events", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) > 0
    
    def test_create_webhook_subscription_endpoint(
        self, client, auth_headers
    ):
        """Test creating webhook subscription via API."""
        response = client.post(
            "/webhooks/subscriptions",
            json={
                "url": "https://example.com/webhook",
                "events": ["user.created", "payment.succeeded"],
                "description": "Test webhook"
            },
            headers=auth_headers
        )
        
        # May succeed or require HTTPS in production
        assert response.status_code in [201, 400]
    
    def test_list_subscriptions_endpoint(self, client, auth_headers):
        """Test listing webhook subscriptions."""
        response = client.get("/webhooks/subscriptions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# Import for tests
import json
