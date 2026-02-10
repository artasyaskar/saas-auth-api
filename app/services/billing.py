from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import User, Subscription, SubscriptionPlan
import stripe
from app.core.config import settings


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        if settings.stripe_api_key:
            stripe.api_key = settings.stripe_api_key
    
    def create_stripe_customer(self, user: User) -> Optional[str]:
        """Create a Stripe customer for the user"""
        if not settings.stripe_api_key:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={"user_id": user.id}
            )
            return customer.id
        except Exception as e:
            print(f"Error creating Stripe customer: {e}")
            return None
    
    def create_subscription(self, user_id: int, plan: SubscriptionPlan) -> bool:
        """Create a subscription for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Create Stripe customer if doesn't exist
        if not user.stripe_customer_id and settings.stripe_api_key:
            customer_id = self.create_stripe_customer(user)
            if customer_id:
                user.stripe_customer_id = customer_id
                self.db.commit()
        
        # Create subscription record
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        self.db.add(subscription)
        
        # Update user's subscription plan
        user.subscription_plan = plan
        
        self.db.commit()
        return True
    
    def cancel_subscription(self, user_id: int) -> bool:
        """Cancel a user's subscription"""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            return False
        
        subscription.status = "canceled"
        subscription.current_period_end = datetime.utcnow()
        
        # Downgrade user to free plan
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_plan = SubscriptionPlan.FREE
        
        self.db.commit()
        return True
    
    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for a user"""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()
    
    def handle_stripe_webhook(self, event_data: dict) -> bool:
        """Handle Stripe webhook events"""
        event_type = event_data.get("type")
        
        if event_type == "customer.subscription.created":
            subscription_data = event_data["data"]["object"]
            customer_id = subscription_data["customer"]
            
            user = self.db.query(User).filter(
                User.stripe_customer_id == customer_id
            ).first()
            
            if user:
                self.create_subscription(user.id, SubscriptionPlan.PRO)
        
        elif event_type == "customer.subscription.deleted":
            subscription_data = event_data["data"]["object"]
            customer_id = subscription_data["customer"]
            
            user = self.db.query(User).filter(
                User.stripe_customer_id == customer_id
            ).first()
            
            if user:
                self.cancel_subscription(user.id)
        
        return True
