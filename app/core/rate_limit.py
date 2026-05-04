from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User, RateLimit, SubscriptionPlan
import redis
import json
from app.core.config import settings

redis_client = redis.from_url(settings.redis_url) if settings.redis_url else None


class RateLimiter:
    def __init__(self):
        self.redis_client = redis_client
        
    def get_rate_limits(self, user: User, db: Session) -> Dict[str, int]:
        """Get rate limits based on user's subscription plan"""
        if user.subscription_plan == SubscriptionPlan.PRO:
            return {
                "requests_per_minute": 300,
                "monthly_quota": 10000
            }
        else:  # FREE plan
            return {
                "requests_per_minute": 60,
                "monthly_quota": 1000
            }
    
    def check_rate_limit(self, user_id: int, db: Session) -> bool:
        """Check if user is within rate limits"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        limits = self.get_rate_limits(user, db)
        
        # Check Redis for minute-based rate limiting
        if self.redis_client:
            minute_key = f"rate_limit:{user_id}:minute"
            current_requests = self.redis_client.get(minute_key)
            
            if current_requests is None:
                self.redis_client.setex(minute_key, 60, 1)
            else:
                current_requests = int(current_requests)
                if current_requests >= limits["requests_per_minute"]:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Too many requests per minute."
                    )
                self.redis_client.incr(minute_key)
        
        # Check monthly quota in database
        rate_limit_record = db.query(RateLimit).filter(RateLimit.user_id == user_id).first()
        
        if not rate_limit_record:
            rate_limit_record = RateLimit(
                user_id=user_id,
                requests_per_minute=limits["requests_per_minute"],
                monthly_quota=limits["monthly_quota"],
                current_monthly_usage=0,
                last_monthly_reset=datetime.utcnow()
            )
            db.add(rate_limit_record)
            db.commit()
        
        # Reset monthly counter if needed
        now = datetime.utcnow()
        if (now - rate_limit_record.last_monthly_reset).days >= 30:
            rate_limit_record.current_monthly_usage = 0
            rate_limit_record.last_monthly_reset = now
            db.commit()
        
        # Check monthly quota
        if rate_limit_record.current_monthly_usage >= rate_limit_record.monthly_quota:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Monthly quota exceeded. Please upgrade your plan."
            )
        
        # Increment usage
        rate_limit_record.current_monthly_usage += 1
        db.commit()
        
        return True


rate_limiter = RateLimiter()
