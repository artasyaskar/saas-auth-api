from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import User, UserRole, UsageLog, SubscriptionPlan
from app.api.auth import get_current_active_user

router = APIRouter()


def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    subscription_plan: SubscriptionPlan
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUsageStats(BaseModel):
    user_id: int
    username: str
    email: str
    total_requests: int
    requests_this_month: int
    subscription_plan: SubscriptionPlan
    last_request: Optional[datetime]


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_requests_today: int
    total_requests_this_month: int
    free_plan_users: int
    pro_plan_users: int


@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    status_msg = "activated" if user.is_active else "suspended"
    return {"message": f"User {user.username} {status_msg} successfully"}


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: UserRole,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = new_role
    db.commit()
    
    return {"message": f"User {user.username} role updated to {new_role.value}"}


@router.get("/usage", response_model=List[UserUsageStats])
async def get_usage_stats(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get current month start
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Query usage stats
    usage_stats = db.query(
        User.id,
        User.username,
        User.email,
        User.subscription_plan,
        func.count(UsageLog.id).label('total_requests'),
        func.sum(
            func.case(
                (UsageLog.timestamp >= month_start, 1),
                else_=0
            )
        ).label('requests_this_month'),
        func.max(UsageLog.timestamp).label('last_request')
    ).join(
        UsageLog, User.id == UsageLog.user_id, isouter=True
    ).group_by(
        User.id, User.username, User.email, User.subscription_plan
    ).offset(skip).limit(limit).all()
    
    result = []
    for stat in usage_stats:
        result.append(UserUsageStats(
            user_id=stat.id,
            username=stat.username,
            email=stat.email,
            total_requests=stat.total_requests or 0,
            requests_this_month=stat.requests_this_month or 0,
            subscription_plan=stat.subscription_plan,
            last_request=stat.last_request
        ))
    
    return result


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    # Get date ranges
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Total users
    total_users = db.query(User).count()
    
    # Active users
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Requests today
    requests_today = db.query(UsageLog).filter(
        UsageLog.timestamp >= today_start
    ).count()
    
    # Requests this month
    requests_this_month = db.query(UsageLog).filter(
        UsageLog.timestamp >= month_start
    ).count()
    
    # Plan distribution
    free_plan_users = db.query(User).filter(
        User.subscription_plan == SubscriptionPlan.FREE
    ).count()
    
    pro_plan_users = db.query(User).filter(
        User.subscription_plan == SubscriptionPlan.PRO
    ).count()
    
    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        total_requests_today=requests_today,
        total_requests_this_month=requests_this_month,
        free_plan_users=free_plan_users,
        pro_plan_users=pro_plan_users
    )
