"""
Enterprise Analytics and Business Intelligence Service

Comprehensive analytics service for tracking user behavior,
system metrics, revenue analytics, and business intelligence.

Features:
- User acquisition and retention analytics
- Cohort analysis
- Revenue metrics (MRR, ARR, churn)
- API usage patterns
- Security event tracking
- Performance metrics
- Funnel analysis
- Real-time dashboards
- Custom report generation
- Data export
- Predictive analytics
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, case
from app.db.models import (
    User, UsageLog, UserRole, SubscriptionPlan,
    TokenBlacklist, PasswordResetToken, AuditLog
)
from app.services.usage import UsageService
import json


class AnalyticsService:
    """
    Enterprise-grade analytics service for SaaS metrics and insights.
    
    Tracks:
    - User acquisition and retention
    - Revenue metrics (MRR, ARR, churn)
    - API usage patterns
    - Security events
    - Performance metrics
    - Funnel analysis
    - Cohort analysis
    - Predictive analytics
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
            'total_new_users': sum(d[1] for d in daily_signups),
            'avg_daily_signups': (sum(d[1] for d in daily_signups) / days) if daily_signups else 0,
            'daily_signups': [
                {'date': str(d[0]), 'count': d[1]} 
                for d in daily_signups
            ],
            'daily_active_users': [
                {'date': str(d[0]), 'count': d[1]} 
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
            AuditLog.created_at >= thirty_days_ago
        ).count()
        
        downgrades = self.db.query(AuditLog).filter(
            AuditLog.action == 'subscription_downgraded',
            AuditLog.created_at >= thirty_days_ago
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
            AuditLog.created_at >= start_date
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
            AuditLog.created_at >= start_date,
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
        score -= min(failed_logins * 0.5, 40)
        
        # Deduct for suspicious IPs
        score -= min(suspicious_ips * 10, 35)
        
        # Deduct for password resets (some are normal)
        score -= min(password_resets * 0.3, 25)
        
        return max(0, score)
    
    # ==================== FUNNEL ANALYTICS ====================
    
    def get_conversion_funnel(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user conversion funnel.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Funnel metrics for each stage
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Stage 1: Visits (assuming we track page views)
        visits = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= start_date,
            UsageLog.endpoint == '/'
        ).count()
        
        # Stage 2: Signups
        signups = self.db.query(User).filter(
            User.created_at >= start_date
        ).count()
        
        # Stage 3: Email verified
        verified = self.db.query(User).filter(
            User.created_at >= start_date,
            User.email_verified == True
        ).count()
        
        # Stage 4: Active users (made API call)
        active = self.db.query(func.distinct(UsageLog.user_id)).filter(
            UsageLog.timestamp >= start_date
        ).count()
        
        # Stage 5: Paid users
        paid = self.db.query(User).filter(
            User.created_at >= start_date,
            User.subscription_plan.in_([SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE])
        ).count()
        
        return {
            'period_days': days,
            'funnel': {
                'visits': visits,
                'signups': signups,
                'verified': verified,
                'active': active,
                'paid': paid
            },
            'conversion_rates': {
                'visit_to_signup': (signups / visits * 100) if visits > 0 else 0,
                'signup_to_verified': (verified / signups * 100) if signups > 0 else 0,
                'verified_to_active': (active / verified * 100) if verified > 0 else 0,
                'active_to_paid': (paid / active * 100) if active > 0 else 0,
                'overall': (paid / visits * 100) if visits > 0 else 0
            }
        }
    
    # ==================== REAL-TIME ANALYTICS ====================
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_minute = now - timedelta(minutes=1)
        
        # Requests in last minute
        requests_last_minute = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= last_minute
        ).count()
        
        # Requests in last hour
        requests_last_hour = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= last_hour
        ).count()
        
        # Active users in last 5 minutes
        last_5_min = now - timedelta(minutes=5)
        active_users = self.db.query(func.distinct(UsageLog.user_id)).filter(
            UsageLog.timestamp >= last_5_min
        ).count()
        
        # Error rate in last hour
        total_last_hour = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= last_hour
        ).count()
        errors_last_hour = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= last_hour,
            UsageLog.status_code >= 400
        ).count()
        
        error_rate = (errors_last_hour / total_last_hour * 100) if total_last_hour > 0 else 0
        
        # Average response time in last hour
        avg_response = self.db.query(func.avg(UsageLog.response_time_ms)).filter(
            UsageLog.timestamp >= last_hour
        ).scalar() or 0
        
        return {
            'timestamp': now.isoformat(),
            'requests_per_minute': requests_last_minute,
            'requests_per_hour': requests_last_hour,
            'active_users_5m': active_users,
            'error_rate_percent': error_rate,
            'avg_response_time_ms': float(avg_response)
        }
    
    # ==================== CUSTOM REPORTS ====================
    
    def generate_custom_report(
        self,
        metrics: List[str],
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate custom analytics report.
        
        Args:
            metrics: List of metrics to include
            start_date: Report start date
            end_date: Report end date
            group_by: Group by field (day, week, month)
        
        Returns:
            Custom report data
        """
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'metrics': {}
        }
        
        for metric in metrics:
            if metric == 'user_growth':
                report['metrics']['user_growth'] = self.get_user_growth_metrics(
                    days=(end_date - start_date).days
                )
            elif metric == 'revenue':
                report['metrics']['revenue'] = self.get_revenue_metrics()
            elif metric == 'endpoint_popularity':
                report['metrics']['endpoint_popularity'] = self.get_endpoint_popularity(
                    days=(end_date - start_date).days
                )
            elif metric == 'security':
                report['metrics']['security'] = self.get_security_events_summary(
                    days=(end_date - start_date).days
                )
            elif metric == 'funnel':
                report['metrics']['funnel'] = self.get_conversion_funnel(
                    days=(end_date - start_date).days
                )
        
        return report
    
    # ==================== PREDICTIVE ANALYTICS ====================
    
    def predict_churn_risk(self, user_id: int) -> Dict[str, Any]:
        """
        Predict churn risk for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Churn risk assessment
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'error': 'User not found'}
        
        # Get user activity
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_activity = self.db.query(UsageLog).filter(
            UsageLog.user_id == user_id,
            UsageLog.timestamp >= thirty_days_ago
        ).count()
        
        # Get last activity
        last_activity = self.db.query(func.max(UsageLog.timestamp)).filter(
            UsageLog.user_id == user_id
        ).scalar()
        
        days_since_last_activity = (datetime.utcnow() - last_activity).days if last_activity else 999
        
        # Calculate risk factors
        risk_score = 0
        risk_factors = []
        
        # Factor 1: Low activity
        if recent_activity < 10:
            risk_score += 30
            risk_factors.append('Low activity')
        
        # Factor 2: Inactive for long time
        if days_since_last_activity > 14:
            risk_score += 40
            risk_factors.append('Inactive for 14+ days')
        
        # Factor 3: Free plan
        if user.subscription_plan == SubscriptionPlan.FREE:
            risk_score += 20
            risk_factors.append('Free plan')
        
        # Factor 4: No 2FA
        # (would need to check 2FA status)
        
        risk_level = 'low' if risk_score < 30 else 'medium' if risk_score < 60 else 'high'
        
        return {
            'user_id': user_id,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recent_activity': recent_activity,
            'days_since_last_activity': days_since_last_activity
        }
    
    # ==================== DATA EXPORT ====================
    
    def export_analytics_data(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = 'json'
    ) -> str:
        """
        Export analytics data for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            format: Export format (json, csv)
        
        Returns:
            Exported data as string
        """
        # Get all usage logs for the period
        logs = self.db.query(UsageLog).filter(
            UsageLog.timestamp >= start_date,
            UsageLog.timestamp <= end_date
        ).all()
        
        if format == 'json':
            return json.dumps([
                {
                    'user_id': log.user_id,
                    'endpoint': log.endpoint,
                    'method': log.method,
                    'status_code': log.status_code,
                    'response_time_ms': log.response_time_ms,
                    'timestamp': log.timestamp.isoformat()
                }
                for log in logs
            ], indent=2)
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'user_id', 'endpoint', 'method', 'status_code',
                'response_time_ms', 'timestamp'
            ])
            writer.writeheader()
            
            for log in logs:
                writer.writerow({
                    'user_id': log.user_id,
                    'endpoint': log.endpoint,
                    'method': log.method,
                    'status_code': log.status_code,
                    'response_time_ms': log.response_time_ms,
                    'timestamp': log.timestamp.isoformat()
                })
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


def get_analytics_service(db: Session):
    """Dependency to get analytics service."""
    return AnalyticsService(db)
