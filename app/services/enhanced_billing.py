"""
Enhanced billing service for comprehensive subscription management.

Handles subscription plans, usage tracking, billing cycles,
and comprehensive billing features with proper integration.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.db.models import (
    User, Subscription, SubscriptionPlan, Usage, BillingCycle,
    Invoice, Payment, PaymentMethod
)
from app.repositories.user import UserRepository
from app.core.config import settings
from app.core.exceptions import (
    ValidationError, NotFoundError, BusinessError,
    DatabaseError, ExternalServiceError
)


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class BillingCycleType(str, Enum):
    """Billing cycle type enumeration."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class EnhancedBillingService:
    """
    Enhanced billing service for comprehensive subscription management.
    
    Handles subscription plans, usage tracking, billing cycles,
    and comprehensive billing features with proper integration.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        
        # TODO: Add payment gateway integration
        # TODO: Add invoice generation
        # TODO: Add dunning management
        # TODO: Add proration calculations
    
    def create_subscription_plan(
        self,
        name: str,
        description: str,
        price: Decimal,
        billing_cycle: BillingCycleType,
        features: Dict[str, Any],
        limits: Dict[str, Any],
        is_active: bool = True,
        trial_days: Optional[int] = None,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Create new subscription plan.
        
        Args:
            name: Plan name
            description: Plan description
            price: Monthly price
            billing_cycle: Billing cycle type
            features: Plan features
            limits: Plan limits
            is_active: Whether plan is active
            trial_days: Trial period in days
            created_by: User ID creating the plan
            
        Returns:
            Created plan data
        """
        try:
            # Validate plan data
            self._validate_plan_data(name, description, price, billing_cycle, features, limits)
            
            # Create subscription plan
            plan = SubscriptionPlan(
                name=name,
                description=description,
                price=price,
                billing_cycle=billing_cycle.value,
                features=features,
                limits=limits,
                is_active=is_active,
                trial_days=trial_days,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            
            return {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "price": float(plan.price),
                "billing_cycle": plan.billing_cycle,
                "features": plan.features,
                "limits": plan.limits,
                "is_active": plan.is_active,
                "trial_days": plan.trial_days,
                "created_at": plan.created_at.isoformat()
            }
            
        except (ValidationError, BusinessError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create subscription plan: {str(e)}")
    
    def subscribe_user(
        self,
        user_id: int,
        plan_id: int,
        payment_method_id: Optional[int] = None,
        trial: bool = False
    ) -> Dict[str, Any]:
        """
        Subscribe user to a plan.
        
        Args:
            user_id: User ID
            plan_id: Plan ID
            payment_method_id: Payment method ID
            trial: Whether this is a trial subscription
            
        Returns:
            Subscription data
        """
        try:
            # Get user and plan
            user = self.user_repo.get(user_id)
            plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
            
            if not user:
                raise NotFoundError("User not found")
            
            if not plan:
                raise NotFoundError("Subscription plan not found")
            
            if not plan.is_active:
                raise BusinessError("Subscription plan is not active")
            
            # Check for existing active subscription
            existing_subscription = self._get_active_subscription(user_id)
            if existing_subscription:
                raise BusinessError("User already has an active subscription")
            
            # Calculate billing dates
            now = datetime.utcnow()
            if trial and plan.trial_days:
                trial_end = now + timedelta(days=plan.trial_days)
                next_billing = trial_end
                status = SubscriptionStatus.TRIAL
            else:
                trial_end = None
                next_billing = self._calculate_next_billing(now, plan.billing_cycle)
                status = SubscriptionStatus.ACTIVE
            
            # Create subscription
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                payment_method_id=payment_method_id,
                status=status.value,
                trial_end=trial_end,
                next_billing=next_billing,
                current_period_start=now,
                current_period_end=next_billing,
                created_at=now,
                updated_at=now
            )
            
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            # Create initial invoice if not trial
            if not trial:
                self._create_invoice(subscription)
            
            return {
                "id": subscription.id,
                "user_id": user_id,
                "plan": self._format_plan(plan),
                "status": subscription.status,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "next_billing": subscription.next_billing.isoformat() if subscription.next_billing else None,
                "created_at": subscription.created_at.isoformat()
            }
            
        except (NotFoundError, BusinessError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to subscribe user: {str(e)}")
    
    def cancel_subscription(
        self,
        user_id: int,
        reason: str,
        cancel_immediately: bool = False,
        refund_proportionally: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel user subscription.
        
        Args:
            user_id: User ID
            reason: Cancellation reason
            cancel_immediately: Whether to cancel immediately
            refund_proportionally: Whether to refund proportionally
            
        Returns:
            Cancellation result
        """
        try:
            # Get active subscription
            subscription = self._get_active_subscription(user_id)
            
            if not subscription:
                raise BusinessError("No active subscription found")
            
            # Update subscription
            now = datetime.utcnow()
            
            if cancel_immediately:
                subscription.status = SubscriptionStatus.CANCELLED.value
                subscription.cancelled_at = now
                subscription.ends_at = now
            else:
                subscription.status = SubscriptionStatus.CANCELLED.value
                subscription.cancelled_at = now
                # Keep current period end as ends_at
            
            subscription.cancellation_reason = reason
            subscription.updated_at = now
            
            self.db.commit()
            
            # Process refund if requested
            refund_amount = None
            if refund_proportionally:
                refund_amount = self._calculate_proportional_refund(subscription)
            
            # Create final invoice if needed
            if refund_amount and refund_amount > 0:
                self._create_refund_invoice(subscription, refund_amount, reason)
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
                "ends_at": subscription.ends_at.isoformat() if subscription.ends_at else None,
                "refund_amount": float(refund_amount) if refund_amount else None,
                "reason": reason
            }
            
        except (BusinessError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to cancel subscription: {str(e)}")
    
    def upgrade_subscription(
        self,
        user_id: int,
        new_plan_id: int,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """
        Upgrade user subscription.
        
        Args:
            user_id: User ID
            new_plan_id: New plan ID
            prorate: Whether to prorate the upgrade
            
        Returns:
            Upgrade result
        """
        try:
            # Get current subscription and new plan
            current_subscription = self._get_active_subscription(user_id)
            new_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == new_plan_id).first()
            
            if not current_subscription:
                raise BusinessError("No active subscription found")
            
            if not new_plan:
                raise NotFoundError("New subscription plan not found")
            
            if not new_plan.is_active:
                raise BusinessError("New subscription plan is not active")
            
            # Calculate proration
            proration_amount = None
            if prorate:
                proration_amount = self._calculate_upgrade_proration(current_subscription, new_plan)
            
            # Update subscription
            now = datetime.utcnow()
            current_subscription.plan_id = new_plan_id
            current_subscription.status = SubscriptionStatus.ACTIVE.value
            current_subscription.next_billing = self._calculate_next_billing(now, new_plan.billing_cycle)
            current_subscription.current_period_start = now
            current_subscription.current_period_end = current_subscription.next_billing
            current_subscription.updated_at = now
            
            self.db.commit()
            
            # Create proration invoice
            if proration_amount and proration_amount != 0:
                self._create_proration_invoice(current_subscription, new_plan, proration_amount)
            
            return {
                "id": current_subscription.id,
                "previous_plan": self._format_plan(self._get_plan_by_id(current_subscription.plan_id)),
                "new_plan": self._format_plan(new_plan),
                "proration_amount": float(proration_amount) if proration_amount else None,
                "next_billing": current_subscription.next_billing.isoformat(),
                "upgraded_at": now.isoformat()
            }
            
        except (BusinessError, NotFoundError):
            raise
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to upgrade subscription: {str(e)}")
    
    def record_usage(
        self,
        user_id: int,
        usage_type: str,
        amount: int,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record usage for billing.
        
        Args:
            user_id: User ID
            usage_type: Type of usage
            amount: Usage amount
            resource_id: Resource identifier
            metadata: Additional metadata
            
        Returns:
            True if recorded successfully
        """
        try:
            # Get user's subscription
            subscription = self._get_active_subscription(user_id)
            
            if not subscription:
                return False
            
            # Check plan limits
            plan = self._get_plan_by_id(subscription.plan_id)
            if not plan:
                return False
            
            # Check if usage exceeds limits
            if not self._check_usage_limits(user_id, usage_type, amount, plan):
                return False
            
            # Record usage
            usage_record = Usage(
                user_id=user_id,
                subscription_id=subscription.id,
                usage_type=usage_type,
                amount=amount,
                resource_id=resource_id,
                metadata=metadata or {},
                recorded_at=datetime.utcnow()
            )
            
            self.db.add(usage_record)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to record usage: {str(e)}")
    
    def get_usage_statistics(
        self,
        user_id: int,
        usage_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for user.
        
        Args:
            user_id: User ID
            usage_type: Filter by usage type
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Usage statistics
        """
        try:
            # Build query
            query = self.db.query(Usage).filter(Usage.user_id == user_id)
            
            if usage_type:
                query = query.filter(Usage.usage_type == usage_type)
            
            if start_date:
                query = query.filter(Usage.recorded_at >= start_date)
            
            if end_date:
                query = query.filter(Usage.recorded_at <= end_date)
            
            # Get usage records
            usage_records = query.order_by(desc(Usage.recorded_at)).all()
            
            # Calculate statistics
            stats = {
                "total_usage": sum(record.amount for record in usage_records),
                "usage_by_type": {},
                "usage_by_day": {},
                "peak_usage": 0,
                "average_daily_usage": 0,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None
            }
            
            # Group by type
            for record in usage_records:
                record_type = record.usage_type
                if record_type not in stats["usage_by_type"]:
                    stats["usage_by_type"][record_type] = 0
                stats["usage_by_type"][record_type] += record.amount
            
            # Group by day
            for record in usage_records:
                day = record.recorded_at.date().isoformat()
                if day not in stats["usage_by_day"]:
                    stats["usage_by_day"][day] = 0
                stats["usage_by_day"][day] += record.amount
                stats["peak_usage"] = max(stats["peak_usage"], record.amount)
            
            # Calculate average
            if stats["usage_by_day"]:
                stats["average_daily_usage"] = sum(stats["usage_by_day"].values()) / len(stats["usage_by_day"])
            
            return stats
            
        except Exception as e:
            raise DatabaseError(f"Failed to get usage statistics: {str(e)}")
    
    def get_subscription_details(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive subscription details for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Subscription details
        """
        try:
            # Get active subscription
            subscription = self._get_active_subscription(user_id)
            
            if not subscription:
                return {
                    "has_subscription": False,
                    "message": "No active subscription found"
                }
            
            # Get plan details
            plan = self._get_plan_by_id(subscription.plan_id)
            
            # Get usage statistics
            current_period_start = subscription.current_period_start or subscription.created_at
            usage_stats = self.get_usage_statistics(
                user_id,
                start_date=current_period_start,
                end_date=datetime.utcnow()
            )
            
            # Get billing information
            billing_info = self._get_billing_info(subscription)
            
            return {
                "has_subscription": True,
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.status,
                    "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                    "next_billing": subscription.next_billing.isoformat() if subscription.next_billing else None,
                    "current_period": {
                        "start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                        "end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
                    },
                    "created_at": subscription.created_at.isoformat(),
                    "updated_at": subscription.updated_at.isoformat()
                },
                "plan": self._format_plan(plan),
                "usage": usage_stats,
                "billing": billing_info
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get subscription details: {str(e)}")
    
    def get_available_plans(self) -> List[Dict[str, Any]]:
        """
        Get all available subscription plans.
        
        Returns:
            List of available plans
        """
        try:
            plans = self.db.query(SubscriptionPlan).filter(
                SubscriptionPlan.is_active == True
            ).order_by(SubscriptionPlan.price).all()
            
            return [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "description": plan.description,
                    "price": float(plan.price),
                    "billing_cycle": plan.billing_cycle,
                    "features": plan.features,
                    "limits": plan.limits,
                    "trial_days": plan.trial_days,
                    "created_at": plan.created_at.isoformat()
                }
                for plan in plans
            ]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get available plans: {str(e)}")
    
    def _validate_plan_data(self, name: str, description: str, price: Decimal, billing_cycle: BillingCycleType, features: Dict[str, Any], limits: Dict[str, Any]):
        """Validate subscription plan data."""
        errors = []
        
        if not name or len(name.strip()) < 2:
            errors.append("Plan name must be at least 2 characters long")
        
        if len(name) > 100:
            errors.append("Plan name must be less than 100 characters")
        
        if not description or len(description.strip()) < 10:
            errors.append("Plan description must be at least 10 characters long")
        
        if price < 0:
            errors.append("Plan price must be non-negative")
        
        if not features or len(features) == 0:
            errors.append("Plan must have at least one feature")
        
        if not limits or len(limits) == 0:
            errors.append("Plan must have at least one limit")
        
        if errors:
            raise ValidationError("Plan validation failed", errors=errors)
    
    def _get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        return self.db.query(Subscription).filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIAL.value])
            )
        ).first()
    
    def _get_plan_by_id(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID."""
        return self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    def _calculate_next_billing(self, current_date: datetime, billing_cycle: str) -> datetime:
        """Calculate next billing date based on cycle."""
        if billing_cycle == BillingCycleType.MONTHLY.value:
            # Add one month
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif billing_cycle == BillingCycleType.QUARTERLY.value:
            # Add three months
            month = current_date.month + 3
            year = current_date.year
            if month > 12:
                month -= 12
                year += 1
            return current_date.replace(year=year, month=month)
        elif billing_cycle == BillingCycleType.YEARLY.value:
            # Add one year
            return current_date.replace(year=current_date.year + 1)
        else:
            # Default to monthly
            return self._calculate_next_billing(current_date, BillingCycleType.MONTHLY.value)
    
    def _calculate_proportional_refund(self, subscription: Subscription) -> Decimal:
        """Calculate proportional refund for cancelled subscription."""
        # TODO: Implement proper proration calculation
        # TODO: Consider used vs unused portion
        # TODO: Add refund policy support
        
        # Placeholder implementation
        return Decimal("0.00")
    
    def _calculate_upgrade_proration(self, current_subscription: Subscription, new_plan: SubscriptionPlan) -> Decimal:
        """Calculate proration amount for subscription upgrade."""
        # TODO: Implement proper upgrade proration
        # TODO: Consider remaining value of current plan
        # TODO: Add upgrade fee calculation
        
        # Placeholder implementation
        return Decimal("0.00")
    
    def _check_usage_limits(self, user_id: int, usage_type: str, amount: int, plan: SubscriptionPlan) -> bool:
        """Check if usage exceeds plan limits."""
        # TODO: Implement comprehensive limit checking
        # TODO: Add usage aggregation
        # TODO: Add limit enforcement
        
        # Placeholder implementation
        return True
    
    def _format_plan(self, plan: SubscriptionPlan) -> Dict[str, Any]:
        """Format plan data for API response."""
        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "price": float(plan.price),
            "billing_cycle": plan.billing_cycle,
            "features": plan.features,
            "limits": plan.limits,
            "trial_days": plan.trial_days,
            "is_active": plan.is_active
        }
    
    def _get_billing_info(self, subscription: Subscription) -> Dict[str, Any]:
        """Get billing information for subscription."""
        # TODO: Implement billing information retrieval
        # TODO: Add payment method details
        # TODO: Add invoice history
        # TODO: Add payment history
        
        return {
            "payment_method": None,
            "next_invoice_date": subscription.next_billing.isoformat() if subscription.next_billing else None,
            "amount_due": float(subscription.plan.price) if subscription.plan else 0.0
        }
    
    def _create_invoice(self, subscription: Subscription):
        """Create invoice for subscription."""
        # TODO: Implement invoice creation
        # TODO: Add invoice line items
        # TODO: Add tax calculation
        # TODO: Add discount support
        
        pass
    
    def _create_refund_invoice(self, subscription: Subscription, amount: Decimal, reason: str):
        """Create refund invoice."""
        # TODO: Implement refund invoice creation
        # TODO: Add refund line items
        # TODO: Add refund processing
        # TODO: Add refund tracking
        
        pass
    
    def _create_proration_invoice(self, subscription: Subscription, new_plan: SubscriptionPlan, amount: Decimal):
        """Create proration invoice for upgrade."""
        # TODO: Implement proration invoice creation
        # TODO: Add proration line items
        # TODO: Add upgrade fee calculation
        # TODO: Add proration tracking
        
        pass


# Factory function
def get_enhanced_billing_service(db: Session) -> EnhancedBillingService:
    """
    Get enhanced billing service instance.
    
    Args:
        db: Database session
        
    Returns:
        EnhancedBillingService instance
    """
    return EnhancedBillingService(db)
