"""
Analytics and reporting endpoints for admin dashboards.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.api.auth import get_current_active_user
from app.api.admin import get_admin_user
from app.db.models import User
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics(
    days: int = 30,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard metrics for admin overview.
    
    Includes:
    - User growth metrics
    - Revenue metrics (MRR, ARR)
    - API usage statistics
    - Security events summary
    """
    analytics = AnalyticsService(db)
    
    return {
        "user_metrics": analytics.get_user_growth_metrics(days),
        "revenue_metrics": analytics.get_revenue_metrics(),
        "popular_endpoints": analytics.get_endpoint_popularity(days=7),
        "security_summary": analytics.get_security_events_summary(days),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/users/growth")
async def get_user_growth(
    days: int = 30,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user growth and retention metrics."""
    analytics = AnalyticsService(db)
    return analytics.get_user_growth_metrics(days)


@router.get("/users/cohorts")
async def get_cohort_analysis(
    cohort_days: int = 7,
    periods: int = 4,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user cohort retention analysis.
    
    Tracks how well users retain over time based on
    when they signed up.
    """
    analytics = AnalyticsService(db)
    return {
        "cohorts": analytics.get_user_cohort_analysis(cohort_days, periods),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/revenue")
async def get_revenue_analytics(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get revenue and subscription metrics."""
    analytics = AnalyticsService(db)
    return analytics.get_revenue_metrics()


@router.get("/api/endpoints")
async def get_endpoint_analytics(
    days: int = 7,
    limit: int = 20,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get API endpoint usage and performance analytics."""
    analytics = AnalyticsService(db)
    return {
        "endpoints": analytics.get_endpoint_popularity(days, limit),
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/api/errors")
async def get_error_trends(
    days: int = 7,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get API error rate trends over time."""
    analytics = AnalyticsService(db)
    return {
        "error_trends": analytics.get_error_rate_trends(days),
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/security/summary")
async def get_security_summary(
    days: int = 30,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get security events and health summary."""
    analytics = AnalyticsService(db)
    return analytics.get_security_events_summary(days)
