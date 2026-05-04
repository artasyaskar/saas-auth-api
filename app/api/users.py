from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.db.session import get_db
from app.db.models import User, UserRole, UsageLog
from app.api.auth import get_current_active_user

router = APIRouter()


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    subscription_plan: str
    
    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    total_requests: int
    requests_this_month: int
    most_used_endpoint: str
    average_response_time: float


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Get total usage
    total_requests = db.query(UsageLog).filter(UsageLog.user_id == current_user.id).count()
    
    # Get current month usage
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    monthly_requests = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.timestamp >= month_start
    ).count()
    
    # Get most used endpoint
    most_used_result = db.query(UsageLog.endpoint).filter(
        UsageLog.user_id == current_user.id
    ).group_by(UsageLog.endpoint).order_by(db.func.count().desc()).first()
    
    most_used_endpoint = most_used_result[0] if most_used_result else "N/A"
    
    # Get average response time
    avg_response_time = db.query(db.func.avg(UsageLog.response_time_ms)).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.response_time_ms.isnot(None)
    ).scalar() or 0.0
    
    return UsageStats(
        total_requests=total_requests,
        requests_this_month=monthly_requests,
        most_used_endpoint=most_used_endpoint,
        average_response_time=float(avg_response_time)
    )
