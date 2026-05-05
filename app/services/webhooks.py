"""
Webhook service for sending real-time events to external systems.
Manages webhook subscriptions, delivery, and retry logic.
"""
import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import requests
from sqlalchemy.orm import Session
from app.db.models import WebhookSubscription, WebhookDelivery, User
from app.core.config import settings


class WebhookEventType(Enum):
    """Available webhook event types."""
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    USAGE_THRESHOLD_REACHED = "usage.threshold_reached"
    SECURITY_ALERT = "security.alert"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"


class WebhookService:
    """
    Enterprise-grade webhook service with delivery guarantees.
    
    Features:
    - Event subscription management
    - Reliable delivery with retries
    - HMAC signature verification
    - Delivery tracking and logs
    - Circuit breaker pattern
    - Payload signing
    """
    
    # Retry configuration
    MAX_RETRIES = 5
    RETRY_DELAYS = [5, 25, 125, 625, 3125]  # Exponential backoff (seconds)
    
    # Circuit breaker configuration
    CIRCUIT_FAILURE_THRESHOLD = 5
    CIRCUIT_RESET_TIMEOUT = 300  # 5 minutes
    
    def __init__(self, db: Session):
        self.db = db
        self._circuit_states: Dict[str, Dict] = {}
    
    def subscribe(
        self,
        user_id: int,
        url: str,
        events: List[WebhookEventType],
        secret: Optional[str] = None,
        description: Optional[str] = None,
        active: bool = True
    ) -> WebhookSubscription:
        """
        Create a new webhook subscription.
        
        Args:
            user_id: Owner of the subscription
            url: Webhook endpoint URL (must be HTTPS in production)
            events: List of events to subscribe to
            secret: Secret for HMAC signature (auto-generated if None)
            description: Optional description
            active: Whether subscription is active
        
        Returns:
            Created webhook subscription
        """
        # Validate URL
        if settings.is_production() and not url.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS in production")
        
        # Generate secret if not provided
        if not secret:
            secret = self._generate_secret()
        
        # Create subscription
        subscription = WebhookSubscription(
            user_id=user_id,
            url=url,
            events=[e.value for e in events],
            secret=secret,
            description=description,
            is_active=active,
            created_at=datetime.utcnow(),
            event_types_version="v1"
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def unsubscribe(self, subscription_id: int, user_id: int) -> bool:
        """Delete a webhook subscription."""
        subscription = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.id == subscription_id,
            WebhookSubscription.user_id == user_id
        ).first()
        
        if subscription:
            self.db.delete(subscription)
            self.db.commit()
            return True
        
        return False
    
    def send_event(
        self,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Send webhook event to all relevant subscribers.
        
        Args:
            event_type: Type of event
            payload: Event data
            user_id: If specified, only send to this user's subscriptions
        
        Returns:
            List of delivery results
        """
        # Get subscriptions for this event
        query = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.is_active == True
        )
        
        if user_id:
            query = query.filter(WebhookSubscription.user_id == user_id)
        
        # Filter by event type
        subscriptions = [
            s for s in query.all()
            if event_type.value in s.events
        ]
        
        results = []
        for subscription in subscriptions:
            result = self._deliver_event(subscription, event_type, payload)
            results.append(result)
        
        return results
    
    def _deliver_event(
        self,
        subscription: WebhookSubscription,
        event_type: WebhookEventType,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deliver event to a single subscription."""
        # Check circuit breaker
        if self._is_circuit_open(subscription.url):
            return {
                "subscription_id": subscription.id,
                "status": "circuit_open",
                "message": "Circuit breaker is open"
            }
        
        # Build webhook payload
        webhook_payload = {
            "event_id": self._generate_event_id(),
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
            "subscription_id": subscription.id
        }
        
        # Sign payload
        signature = self._sign_payload(
            webhook_payload,
            subscription.secret
        )
        
        # Create delivery record
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_id=webhook_payload["event_id"],
            event_type=event_type.value,
            payload=json.dumps(webhook_payload),
            status="pending",
            attempt_count=0,
            created_at=datetime.utcnow()
        )
        self.db.add(delivery)
        self.db.commit()
        
        # Attempt delivery
        success = self._attempt_delivery(
            subscription,
            delivery,
            webhook_payload,
            signature
        )
        
        return {
            "subscription_id": subscription.id,
            "event_id": webhook_payload["event_id"],
            "status": "delivered" if success else "failed"
        }
    
    def _attempt_delivery(
        self,
        subscription: WebhookSubscription,
        delivery: WebhookDelivery,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """Attempt to deliver webhook with retries."""
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": payload["event_type"],
            "X-Webhook-ID": payload["event_id"],
            "X-Webhook-Timestamp": payload["timestamp"],
            "User-Agent": "SaaS-Auth-API-Webhook/1.0"
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                delivery.attempt_count = attempt + 1
                delivery.last_attempt_at = datetime.utcnow()
                
                response = requests.post(
                    subscription.url,
                    json=payload,
                    headers=headers,
                    timeout=30,
                    verify=True
                )
                
                delivery.http_status_code = response.status_code
                delivery.response_body = response.text[:1000]  # Truncate
                
                if response.status_code >= 200 and response.status_code < 300:
                    # Success
                    delivery.status = "delivered"
                    delivery.delivered_at = datetime.utcnow()
                    self.db.commit()
                    
                    # Record success for circuit breaker
                    self._record_success(subscription.url)
                    
                    return True
                else:
                    # Failure
                    if attempt < self.MAX_RETRIES - 1:
                        # Wait before retry
                        import time
                        time.sleep(self.RETRY_DELAYS[attempt])
                    
            except Exception as e:
                delivery.error_message = str(e)[:500]
                
                if attempt < self.MAX_RETRIES - 1:
                    import time
                    time.sleep(self.RETRY_DELAYS[attempt])
        
        # All retries failed
        delivery.status = "failed"
        self.db.commit()
        
        # Record failure for circuit breaker
        self._record_failure(subscription.url)
        
        return False
    
    def _sign_payload(
        self,
        payload: Dict[str, Any],
        secret: str
    ) -> str:
        """Generate HMAC signature for payload."""
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook payload signature."""
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    def _is_circuit_open(self, url: str) -> bool:
        """Check if circuit breaker is open for URL."""
        state = self._circuit_states.get(url)
        if not state:
            return False
        
        if state["failures"] >= self.CIRCUIT_FAILURE_THRESHOLD:
            # Check if enough time has passed to try again
            last_failure = state.get("last_failure")
            if last_failure:
                elapsed = (datetime.utcnow() - last_failure).total_seconds()
                if elapsed < self.CIRCUIT_RESET_TIMEOUT:
                    return True
                else:
                    # Reset circuit
                    state["failures"] = 0
        
        return False
    
    def _record_failure(self, url: str):
        """Record a delivery failure for circuit breaker."""
        if url not in self._circuit_states:
            self._circuit_states[url] = {"failures": 0}
        
        self._circuit_states[url]["failures"] += 1
        self._circuit_states[url]["last_failure"] = datetime.utcnow()
    
    def _record_success(self, url: str):
        """Record a successful delivery."""
        if url in self._circuit_states:
            self._circuit_states[url]["failures"] = 0
    
    def _generate_secret(self) -> str:
        """Generate a secure webhook secret."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_delivery_logs(
        self,
        subscription_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get delivery history for a subscription."""
        deliveries = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.subscription_id == subscription_id
        ).order_by(
            WebhookDelivery.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": d.id,
                "event_id": d.event_id,
                "event_type": d.event_type,
                "status": d.status,
                "http_status": d.http_status_code,
                "attempt_count": d.attempt_count,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "error": d.error_message
            }
            for d in deliveries
        ]
    
    def retry_failed_delivery(self, delivery_id: int) -> bool:
        """Manually retry a failed webhook delivery."""
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.status == "failed"
        ).first()
        
        if not delivery:
            return False
        
        subscription = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.id == delivery.subscription_id
        ).first()
        
        if not subscription:
            return False
        
        # Reset delivery status
        delivery.status = "pending"
        delivery.attempt_count = 0
        delivery.error_message = None
        self.db.commit()
        
        # Re-deliver
        payload = json.loads(delivery.payload)
        signature = self._sign_payload(payload, subscription.secret)
        
        return self._attempt_delivery(
            subscription,
            delivery,
            payload,
            signature
        )
    
    def rotate_secret(self, subscription_id: int) -> str:
        """Rotate webhook secret."""
        subscription = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        new_secret = self._generate_secret()
        subscription.secret = new_secret
        subscription.secret_rotated_at = datetime.utcnow()
        self.db.commit()
        
        return new_secret


def get_webhook_service(db: Session):
    """Dependency to get webhook service."""
    return WebhookService(db)
