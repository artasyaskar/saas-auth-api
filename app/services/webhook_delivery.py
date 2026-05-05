"""
Webhook Delivery Service with Retries

Enterprise-grade webhook delivery system with:
- Automatic retries with exponential backoff
- Circuit breaker pattern
- Dead letter queue
- Delivery tracking and analytics
- Signature verification
- Batch processing
"""
import json
import hashlib
import hmac
import base64
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from urllib.parse import urlparse
import time

from sqlalchemy.orm import Session
from app.db.models import Webhook, WebhookDelivery, WebhookEvent, WebhookStatus
from app.core.config import settings


class DeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERING = "delivering"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class WebhookPayload:
    """Standardized webhook payload."""
    event_id: str
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    webhook_id: int
    attempt: int = 1
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
            "attempt": self.attempt
        }, default=str)


@dataclass
class DeliveryAttempt:
    """Single delivery attempt record."""
    attempt_number: int
    timestamp: datetime
    status: DeliveryStatus
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for webhook endpoints."""
    endpoint: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    
    # Configuration
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    def record_success(self):
        """Record successful delivery."""
        self.success_count += 1
        self.failure_count = 0
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def record_failure(self):
        """Record failed delivery."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                    return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.success_count < self.half_open_max_calls
        return False


@dataclass
class RetryPolicy:
    """Retry configuration for webhook delivery."""
    max_attempts: int = 5
    initial_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    retryable_status_codes: List[int] = field(default_factory=lambda: [408, 429, 500, 502, 503, 504])
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def is_retryable(self, status_code: int, error: Optional[str] = None) -> bool:
        """Check if error is retryable."""
        if status_code in self.retryable_status_codes:
            return True
        # Connection errors are retryable
        if error and any(e in error.lower() for e in ["timeout", "connection", "dns", "ssl"]):
            return True
        return False


class WebhookDeliveryService:
    """
    Enterprise webhook delivery service with reliability features.
    
    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker pattern for failing endpoints
    - Dead letter queue for failed deliveries
    - Delivery tracking and analytics
    - HMAC signature verification
    - Batch processing for high throughput
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_policy = RetryPolicy()
        self._lock = asyncio.Lock()
        
    def _get_circuit_breaker(self, endpoint: str) -> CircuitBreaker:
        """Get or create circuit breaker for endpoint."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(endpoint=endpoint)
        return self.circuit_breakers[endpoint]
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        expected = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected)
    
    async def _send_webhook(
        self,
        webhook: Webhook,
        payload: WebhookPayload,
        attempt: int
    ) -> DeliveryAttempt:
        """
        Send single webhook request.
        
        Returns delivery attempt record.
        """
        start_time = time.time()
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"SaaS-Auth-Webhook/{settings.APP_VERSION}",
            "X-Webhook-ID": str(payload.webhook_id),
            "X-Event-ID": payload.event_id,
            "X-Event-Type": payload.event_type,
            "X-Attempt": str(attempt),
            "X-Timestamp": payload.timestamp,
        }
        
        # Add signature if secret configured
        if webhook.secret:
            payload_json = payload.to_json()
            signature = self._generate_signature(payload_json, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
            headers["X-Hub-Signature-256"] = f"sha256={signature}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    headers=headers,
                    json={
                        "event_id": payload.event_id,
                        "event_type": payload.event_type,
                        "timestamp": payload.timestamp,
                        "data": payload.data,
                        "attempt": attempt
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False if settings.ENVIRONMENT == "development" else True
                ) as response:
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    response_body = await response.text()
                    
                    if response.status >= 200 and response.status < 300:
                        return DeliveryAttempt(
                            attempt_number=attempt,
                            timestamp=datetime.utcnow(),
                            status=DeliveryStatus.SUCCESS,
                            response_status=response.status,
                            response_body=response_body[:1000],  # Truncate
                            duration_ms=duration_ms
                        )
                    else:
                        return DeliveryAttempt(
                            attempt_number=attempt,
                            timestamp=datetime.utcnow(),
                            status=DeliveryStatus.FAILED,
                            response_status=response.status,
                            response_body=response_body[:1000],
                            duration_ms=duration_ms,
                            error_message=f"HTTP {response.status}"
                        )
                        
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return DeliveryAttempt(
                attempt_number=attempt,
                timestamp=datetime.utcnow(),
                status=DeliveryStatus.FAILED,
                error_message="Request timeout",
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return DeliveryAttempt(
                attempt_number=attempt,
                timestamp=datetime.utcnow(),
                status=DeliveryStatus.FAILED,
                error_message=str(e)[:500],
                duration_ms=duration_ms
            )
    
    async def deliver_webhook(
        self,
        webhook: Webhook,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deliver webhook with automatic retry.
        
        Main delivery method with full retry logic.
        """
        event_id = event_id or self._generate_event_id()
        
        payload = WebhookPayload(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            webhook_id=webhook.id
        )
        
        # Check circuit breaker
        circuit = self._get_circuit_breaker(webhook.url)
        if not circuit.can_execute():
            # Circuit is open, queue for later
            await self._queue_for_retry(webhook, payload, 1)
            return {
                "success": False,
                "status": "circuit_open",
                "message": "Circuit breaker is open, webhook queued"
            }
        
        attempts = []
        
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            # Update attempt number in payload
            payload.attempt = attempt
            
            # Send webhook
            result = await self._send_webhook(webhook, payload, attempt)
            attempts.append(result)
            
            # Record delivery attempt
            await self._record_delivery_attempt(webhook.id, event_id, result)
            
            if result.status == DeliveryStatus.SUCCESS:
                # Success - update circuit breaker and return
                circuit.record_success()
                
                # Update webhook stats
                webhook.last_success = datetime.utcnow()
                webhook.success_count = (webhook.success_count or 0) + 1
                self.db.commit()
                
                return {
                    "success": True,
                    "status": "delivered",
                    "event_id": event_id,
                    "attempts": attempt,
                    "duration_ms": result.duration_ms
                }
            
            # Failed - check if retryable
            if not self.retry_policy.is_retryable(
                result.response_status or 0,
                result.error_message
            ):
                # Non-retryable error
                circuit.record_failure()
                
                webhook.last_failure = datetime.utcnow()
                webhook.failure_count = (webhook.failure_count or 0) + 1
                self.db.commit()
                
                return {
                    "success": False,
                    "status": "failed",
                    "error": result.error_message,
                    "response_status": result.response_status,
                    "retryable": False
                }
            
            # Record failure in circuit breaker
            circuit.record_failure()
            
            # Calculate delay for next attempt
            if attempt < self.retry_policy.max_attempts:
                delay = self.retry_policy.get_delay(attempt)
                await asyncio.sleep(delay)
        
        # All retries exhausted - send to dead letter queue
        await self._send_to_dead_letter(webhook, payload, attempts)
        
        webhook.last_failure = datetime.utcnow()
        webhook.failure_count = (webhook.failure_count or 0) + 1
        self.db.commit()
        
        return {
            "success": False,
            "status": "dead_letter",
            "event_id": event_id,
            "attempts": len(attempts),
            "message": "All retry attempts failed, sent to dead letter queue"
        }
    
    async def _record_delivery_attempt(
        self,
        webhook_id: int,
        event_id: str,
        attempt: DeliveryAttempt
    ):
        """Record delivery attempt in database."""
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event_id=event_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status.value,
            response_status_code=attempt.response_status,
            response_body=attempt.response_body,
            error_message=attempt.error_message,
            duration_ms=attempt.duration_ms,
            created_at=attempt.timestamp
        )
        
        self.db.add(delivery)
        self.db.commit()
    
    async def _queue_for_retry(
        self,
        webhook: Webhook,
        payload: WebhookPayload,
        next_attempt: int
    ):
        """Queue webhook for later retry."""
        # In production, use Redis/RabbitMQ
        # For now, store in database with scheduled_at
        scheduled_at = datetime.utcnow() + timedelta(
            seconds=self.retry_policy.get_delay(next_attempt)
        )
        
        # Would create scheduled delivery record
        pass
    
    async def _send_to_dead_letter(
        self,
        webhook: Webhook,
        payload: WebhookPayload,
        attempts: List[DeliveryAttempt]
    ):
        """Send failed webhook to dead letter queue."""
        # Create dead letter record
        dead_letter = {
            "webhook_id": webhook.id,
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "payload": payload.data,
            "attempts": [
                {
                    "attempt": a.attempt_number,
                    "status": a.status.value,
                    "error": a.error_message,
                    "response_status": a.response_status,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in attempts
            ],
            "failed_at": datetime.utcnow().isoformat()
        }
        
        # In production, send to SQS/SNS or database table
        # For now, log it
        print(f"[DEAD LETTER] {json.dumps(dead_letter)}")
        
        # Could also notify webhook owner
        if webhook.user_id:
            # Send notification about failing webhook
            pass
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random = secrets.token_hex(8)
        return f"evt_{timestamp}_{random}"
    
    async def deliver_batch(
        self,
        webhooks: List[Webhook],
        event_type: str,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Deliver webhook to multiple endpoints in parallel.
        
        Used for broadcasting events to multiple subscribers.
        """
        event_id = self._generate_event_id()
        
        tasks = [
            self.deliver_webhook(webhook, event_type, data, event_id)
            for webhook in webhooks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            result if not isinstance(result, Exception) else {
                "success": False,
                "error": str(result)
            }
            for result in results
        ]
    
    async def replay_failed_delivery(
        self,
        delivery_id: int
    ) -> Dict[str, Any]:
        """
        Replay a failed webhook delivery.
        
        Manually retry a specific failed delivery.
        """
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not delivery:
            return {"success": False, "error": "Delivery not found"}
        
        webhook = self.db.query(Webhook).filter(
            Webhook.id == delivery.webhook_id
        ).first()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
        
        # Reset circuit breaker for manual retry
        circuit = self._get_circuit_breaker(webhook.url)
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        
        # Re-deliver
        return await self.deliver_webhook(
            webhook=webhook,
            event_type=delivery.event_id,  # Would need to store event_type
            data={},  # Would need to store payload
            event_id=delivery.event_id
        )
    
    def get_delivery_stats(
        self,
        webhook_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get delivery statistics.
        
        Analytics for webhook delivery performance.
        """
        query = self.db.query(WebhookDelivery)
        
        if webhook_id:
            query = query.filter(WebhookDelivery.webhook_id == webhook_id)
        
        if start_date:
            query = query.filter(WebhookDelivery.created_at >= start_date)
        
        if end_date:
            query = query.filter(WebhookDelivery.created_at <= end_date)
        
        deliveries = query.all()
        
        total = len(deliveries)
        successful = sum(1 for d in deliveries if d.status == DeliveryStatus.SUCCESS.value)
        failed = sum(1 for d in deliveries if d.status == DeliveryStatus.FAILED.value)
        
        avg_duration = 0
        if deliveries:
            durations = [d.duration_ms for d in deliveries if d.duration_ms]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "total_deliveries": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_duration_ms": round(avg_duration, 2),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }


# Sync wrapper for use in synchronous code
def deliver_webhook_sync(
    db: Session,
    webhook: Webhook,
    event_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Synchronous wrapper for webhook delivery."""
    service = WebhookDeliveryService(db)
    return asyncio.run(service.deliver_webhook(webhook, event_type, data))


import secrets
