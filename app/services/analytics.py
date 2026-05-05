"""
Comprehensive analytics service for tracking user behavior,
system metrics, and business intelligence.
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from app.db.models import (
    User, UsageLog, UserRole, SubscriptionPlan,
    TokenBlacklist, PasswordResetToken, AuditLog
)
from app.services.usage import UsageService
import json


class AnalyticsService:
    """
    Advanced analytics service for SaaS metrics and insights.
    
    Tracks:
    - User acquisition and retention
    - Revenue metrics (MRR, ARR, churn)
    - API usage patterns
    - Security events
    - Performance metrics
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.usage_service = UsageService(db)
    
    # ==================== USER ANALYTICS ====================
    
    def get_user_growth_metrics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate user growth metrics over time.
        
        Returns:
            Dict with daily signups, active users, retention rates
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily new signups
        daily_signups = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= start_date
        ).group_by(
            func.date(User.created_at)
        ).order_by('date').all()
        
        # Daily active users (made at least one API call)
        daily_active = self.db.query(
            func.date(UsageLog.timestamp).label('date'),
            func.count(func.distinct(UsageLog.user_id)).label('count')
        ).filter(
            UsageLog.timestamp >= start_date
        ).group_by(
            func.date(UsageLog.timestamp)
        ).order_by('date').all()
        
        # Calculate retention (users who signed up and were active)
        retention_data = []
        for signup_day in range(days):
            signup_date = start_date + timedelta(days=signup_day)
            next_day = signup_date + timedelta(days=1)
            
            # Users who signed up on this day
            new_users = self.db.query(User.id).filter(
                User.created_at >= signup_date,
                User.created_at < next_day
            ).all()
            new_user_ids = [u.id for u in new_users]
            
            if new_user_ids:
                # How many were active in the next 7 days
                retained = self.db.query(func.distinct(UsageLog.user_id)).filter(
                    UsageLog.user_id.in_(new_user_ids),
                    UsageLog.timestamp >= next_day,
                    UsageLog.timestamp < next_day + timedelta(days=7)
                ).count()
                
                retention_rate = (retained / len(new_user_ids)) * 100
            else:
                retention_rate = 0
            
            retention_data.append({
                'date': signup_date.date().isoformat(),
                'new_users': len(new_user_ids),
                'retained_7d': retention_rate
            })
        
        return {
            'period_days': days,
            'total_new_users': sum(d['count'] for d in daily_signups),
            'avg_daily_signups': sum(d['count'] for d in daily_signups) / days,
            'daily_signups': [
                {'date': str(d.date), 'count': d.count} 
                for d in daily_signups
            ],
            'daily_active_users': [
                {'date': str(d.date), 'count': d.count} 
                for d in daily_active
            ],
            'retention_data': retention_data
        }
    
    def get_user_cohort_analysis(
        self,
        cohort_size_days: int = 7,
        periods: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Perform cohort analysis on user retention.
        
        Args:
            cohort_size_days: Size of each cohort in days
            periods: Number of periods to track retention
        
        Returns:
            List of cohort data with retention percentages
        """
        end_date = datetime.utcnow()
        cohorts = []
        
        for cohort_num in range(periods):
            cohort_start = end_date - timedelta(
                days=(cohort_num + 1) * cohort_size_days
            )
            cohort_end = cohort_start + timedelta(days=cohort_size_days)
            
            # Get users in this cohort
            cohort_users = self.db.query(User.id).filter(
                User.created_at >= cohort_start,
                User.created_at < cohort_end
            ).all()
            cohort_user_ids = [u.id for u in cohort_users]
            
            if not cohort_user_ids:
                continue
            
            cohort_size = len(cohort_user_ids)
            
            # Calculate retention for each subsequent period
            retention_rates = []
            for period in range(1, periods + 1):
                period_start = cohort_end
                period_end = period_start + timedelta(
                    days=cohort_size_days * period
                )
                
                active_users = self.db.query(func.distinct(UsageLog.user_id)).filter(
                    UsageLog.user_id.in_(cohort_user_ids),
                    UsageLog.timestamp >= period_start,
                    UsageLog.timestamp < period_end
                ).count()
                
                retention_rates.append({
                    'period': period,
                    'retention_pct': (active_users / cohort_size) * 100
                })
            
            cohorts.append({
                'cohort_id': f"{cohort_start.date()}_to_{cohort_end.date()}",
                'cohort_size': cohort_size,
                'retention_by_period': retention_rates
            })
        
        return cohorts
    
    # ==================== REVENUE ANALYTICS ====================
    
    def get_revenue_metrics(self) -> Dict[str, Any]:
        """
        Calculate revenue metrics.
        
        Returns:
            MRR, ARR, churn rate, upgrade/downgrade metrics
        """
        # Count users by plan
        plan_counts = self.db.query(
            User.subscription_plan,
            func.count(User.id).label('count')
        ).group_by(User.subscription_plan).all()
        
        # Pricing (simplified)
        pricing = {
            SubscriptionPlan.FREE: 0,
            SubscriptionPlan.PRO: 29,
            SubscriptionPlan.ENTERPRISE: 99
        }
        
        # Calculate MRR
        mrr = sum(
            pricing.get(plan, 0) * count 
            for plan, count in plan_counts
        )
        
        # Plan distribution
        plan_distribution = {
            plan.value if hasattr(plan, 'value') else str(plan): count 
            for plan, count in plan_counts
        }
        
        # Upgrades in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        upgrades = self.db.query(AuditLog).filter(
            AuditLog.action == 'subscription_upgraded',
            AuditLog.timestamp >= thirty_days_ago
        ).count()
        
        downgrades = self.db.query(AuditLog).filter(
            AuditLog.action == 'subscription_downgraded',
            AuditLog.timestamp >= thirty_days_ago
        ).count()
        
        return {
            'mrr': mrr,
            'arr': mrr * 12,
            'plan_distribution': plan_distribution,
            'upgrades_last_30d': upgrades,
            'downgrades_last_30d': downgrades,
            'net_revenue_retention': (
                (upgrades * 29) - (downgrades * 29) 
                if upgrades or downgrades else 0
            )
        }
    
    # ==================== API ANALYTICS ====================
    
    def get_endpoint_popularity(
        self,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get most popular endpoints by request count."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        results = self.db.query(
            UsageLog.endpoint,
            UsageLog.method,
            func.count(UsageLog.id).label('request_count'),
            func.avg(UsageLog.response_time_ms).label('avg_response_time'),
            func.sum(
                case((UsageLog.status_code >= 400, 1), else_=0)
            ).label('error_count')
        ).filter(
            UsageLog.timestamp >= start_date
        ).group_by(
            UsageLog.endpoint,
            UsageLog.method
        ).order_by(
            desc('request_count')
        ).limit(limit).all()
        
        return [
            {
                'endpoint': r.endpoint,
                'method': r.method,
                'request_count': r.request_count,
                'avg_response_time_ms': float(r.avg_response_time or 0),
                'error_count': r.error_count,
                'error_rate': (r.error_count / r.request_count * 100) 
                    if r.request_count > 0 else 0
            }
            for r in results
        ]
    
    def get_error_rate_trends(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Track error rates over time."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        daily_errors = self.db.query(
            func.date(UsageLog.timestamp).label('date'),
            func.count(UsageLog.id).label('total_requests'),
            func.sum(
                case((UsageLog.status_code >= 400, 1), else_=0)
            ).label('error_count')
        ).filter(
            UsageLog.timestamp >= start_date
        ).group_by(
            func.date(UsageLog.timestamp)
        ).order_by('date').all()
        
        return [
            {
                'date': str(d.date),
                'total_requests': d.total_requests,
                'error_count': d.error_count,
                'error_rate': (d.error_count / d.total_requests * 100) 
                    if d.total_requests > 0 else 0
            }
            for d in daily_errors
        ]
    
    # ==================== SECURITY ANALYTICS ====================
    
    def get_security_events_summary(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Summary of security-related events."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Failed login attempts
        failed_logins = self.db.query(AuditLog).filter(
            AuditLog.action == 'login_failed',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Password resets
        password_resets = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.created_at >= start_date
        ).count()
        
        # Suspended users
        suspended = self.db.query(User).filter(
            User.is_active == False
        ).count()
        
        # Tokens revoked
        revoked_tokens = self.db.query(TokenBlacklist).filter(
            TokenBlacklist.blacklisted_at >= start_date
        ).count()
        
        # Suspicious activity (multiple failed logins from same IP)
        suspicious_ips = self.db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('failed_attempts')
        ).filter(
            AuditLog.action == 'login_failed',
            AuditLog.timestamp >= start_date,
            AuditLog.ip_address.isnot(None)
        ).group_by(
            AuditLog.ip_address
        ).having(
            func.count(AuditLog.id) >= 5
        ).all()
        
        return {
            'period_days': days,
            'failed_login_attempts': failed_logins,
            'password_reset_requests': password_resets,
            'suspended_accounts': suspended,
            'revoked_tokens': revoked_tokens,
            'suspicious_ips': [
                {'ip': ip, 'failed_attempts': count} 
                for ip, count in suspicious_ips
            ],
            'security_score': self._calculate_security_score(
                failed_logins, password_resets, len(suspicious_ips)
            )
        }
    
    def _calculate_security_score(
        self,
        failed_logins: int,
        password_resets: int,
        suspicious_ips: int
    ) -> int:
        """Calculate a security health score (0-100)."""
        score = 100
        
        # Deduct for failed logins
        score -= min(failed_logins // 10, 20)
        
        # Deduct for suspicious IPs
        score -= min(suspicious_ips * 5, 30)
        
        # Deduct for password resets (some are normal)
        score -= min(password_resets // 5, 10)
        
        return max(0, score)


# Helper function for case expression
def case(*conditions, else_=None):
    """Build a SQL CASE expression."""
    from sqlalchemy import case as sql_case
    return sql_case(*conditions, else_=else_)
