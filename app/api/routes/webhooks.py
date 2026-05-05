"""
Webhook management endpoints for external integrations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

from app.db.session import get_db
from app.db.models import User
from app.api.auth import get_current_active_user
from app.services.webhooks import WebhookService, WebhookEventType, get_webhook_service

router = APIRouter()


class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl = Field(..., description="Webhook endpoint URL (HTTPS required in production)")
    events: List[str] = Field(..., description="Event types to subscribe to")
    description: Optional[str] = Field(None, max_length=255)


class WebhookSubscriptionResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: str
    secret_preview: str


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    subscription: WebhookSubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new webhook subscription."""
    service = WebhookService(db)
    
    # Convert event strings to enums
    try:
        events = [WebhookEventType(e) for e in subscription.events]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type: {e}"
        )
    
    try:
        new_subscription = service.subscribe(
            user_id=current_user.id,
            url=str(subscription.url),
            events=events,
            description=subscription.description
        )
        
        return {
            "id": new_subscription.id,
            "url": new_subscription.url,
            "events": new_subscription.events,
            "is_active": new_subscription.is_active,
            "created_at": new_subscription.created_at.isoformat(),
            "secret": new_subscription.secret,  # Only shown once
            "message": "Store the secret securely - it won't be shown again"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/subscriptions", response_model=List[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all webhook subscriptions for the current user."""
    subscriptions = db.query(WebhookSubscription).filter(
        WebhookSubscription.user_id == current_user.id,
        WebhookSubscription.is_active == True
    ).all()
    
    return [
        {
            "id": sub.id,
            "url": sub.url,
            "events": sub.events,
            "is_active": sub.is_active,
            "created_at": sub.created_at.isoformat(),
            "secret_preview": f"{sub.secret[:8]}..." if sub.secret else "..."
        }
        for sub in subscriptions
    ]


@router.delete("/subscriptions/{subscription_id}")
async def delete_webhook_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a webhook subscription."""
    service = WebhookService(db)
    
    success = service.unsubscribe(subscription_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return {"message": "Webhook subscription deleted"}


@router.get("/subscriptions/{subscription_id}/deliveries")
async def get_delivery_logs(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get delivery history for a webhook subscription."""
    service = WebhookService(db)
    
    # Verify subscription belongs to user
    from app.db.models import WebhookSubscription
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    deliveries = service.get_delivery_logs(subscription_id, limit)
    
    return {
        "subscription_id": subscription_id,
        "deliveries": deliveries
    }


@router.post("/subscriptions/{subscription_id}/retry")
async def retry_failed_delivery(
    subscription_id: int,
    delivery_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retry a failed webhook delivery."""
    from app.db.models import WebhookSubscription
    
    # Verify subscription belongs to user
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    service = WebhookService(db)
    success = service.retry_failed_delivery(delivery_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retry delivery"
        )
    
    return {"message": "Delivery retry initiated"}


@router.get("/events")
async def list_available_events(
    current_user: User = Depends(get_current_active_user)
):
    """List all available webhook event types."""
    events = [
        {
            "event": e.value,
            "description": _get_event_description(e)
        }
        for e in WebhookEventType
    ]
    
    return {"events": events}


def _get_event_description(event: WebhookEventType) -> str:
    """Get human-readable description for event type."""
    descriptions = {
        WebhookEventType.USER_CREATED: "Triggered when a new user registers",
        WebhookEventType.USER_UPDATED: "Triggered when user profile is updated",
        WebhookEventType.USER_DELETED: "Triggered when user account is deleted",
        WebhookEventType.SUBSCRIPTION_CREATED: "Triggered when a subscription is created",
        WebhookEventType.SUBSCRIPTION_UPDATED: "Triggered when subscription changes",
        WebhookEventType.SUBSCRIPTION_CANCELLED: "Triggered when subscription is cancelled",
        WebhookEventType.PAYMENT_SUCCEEDED: "Triggered when payment is successful",
        WebhookEventType.PAYMENT_FAILED: "Triggered when payment fails",
        WebhookEventType.USAGE_THRESHOLD_REACHED: "Triggered when usage limit approached",
        WebhookEventType.SECURITY_ALERT: "Triggered on security-related events",
        WebhookEventType.API_KEY_CREATED: "Triggered when API key is created",
        WebhookEventType.API_KEY_REVOKED: "Triggered when API key is revoked"
    }
    return descriptions.get(event, "No description available")
