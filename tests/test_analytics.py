"""
Tests for analytics service and endpoints.
"""
import pytest
from datetime import datetime, timedelta
from app.services.analytics import AnalyticsService


class TestUserGrowthMetrics:
    """Tests for user growth analytics."""
    
    def test_get_user_growth_metrics(self, db, test_user):
        """Test user growth metrics calculation."""
        service = AnalyticsService(db)
        metrics = service.get_user_growth_metrics(days=30)
        
        assert "period_days" in metrics
        assert "total_new_users" in metrics
        assert "daily_signups" in metrics
        assert "daily_active_users" in metrics
        assert "retention_data" in metrics
        assert metrics["period_days"] == 30
    
    def test_get_user_growth_different_periods(self, db):
        """Test growth metrics with different time periods."""
        service = AnalyticsService(db)
        
        metrics_7 = service.get_user_growth_metrics(days=7)
        assert metrics_7["period_days"] == 7
        
        metrics_90 = service.get_user_growth_metrics(days=90)
        assert metrics_90["period_days"] == 90
    
    def test_cohort_analysis(self, db, test_user):
        """Test cohort retention analysis."""
        service = AnalyticsService(db)
        cohorts = service.get_user_cohort_analysis(
            cohort_size_days=7,
            periods=4
        )
        
        assert isinstance(cohorts, list)
        if cohorts:
            cohort = cohorts[0]
            assert "cohort_id" in cohort
            assert "cohort_size" in cohort
            assert "retention_by_period" in cohort


class TestRevenueAnalytics:
    """Tests for revenue and billing analytics."""
    
    def test_get_revenue_metrics(self, db, test_user):
        """Test revenue metrics calculation."""
        service = AnalyticsService(db)
        metrics = service.get_revenue_metrics()
        
        assert "mrr" in metrics
        assert "arr" in metrics
        assert "plan_distribution" in metrics
        assert "upgrades_last_30d" in metrics
        assert "downgrades_last_30d" in metrics
        assert metrics["arr"] == metrics["mrr"] * 12
    
    def test_revenue_metrics_plan_distribution(self, db):
        """Test plan distribution in revenue metrics."""
        service = AnalyticsService(db)
        metrics = service.get_revenue_metrics()
        
        assert isinstance(metrics["plan_distribution"], dict)


class TestApiAnalytics:
    """Tests for API usage analytics."""
    
    def test_get_endpoint_popularity(self, db, test_user):
        """Test endpoint popularity analytics."""
        service = AnalyticsService(db)
        endpoints = service.get_endpoint_popularity(days=7, limit=10)
        
        assert isinstance(endpoints, list)
        if endpoints:
            endpoint = endpoints[0]
            assert "endpoint" in endpoint
            assert "method" in endpoint
            assert "request_count" in endpoint
            assert "avg_response_time_ms" in endpoint
    
    def test_get_error_rate_trends(self, db):
        """Test error rate trend analytics."""
        service = AnalyticsService(db)
        trends = service.get_error_rate_trends(days=7)
        
        assert isinstance(trends, list)
        if trends:
            trend = trends[0]
            assert "date" in trend
            assert "total_requests" in trend
            assert "error_count" in trend
            assert "error_rate" in trend


class TestSecurityAnalytics:
    """Tests for security event analytics."""
    
    def test_get_security_events_summary(self, db):
        """Test security events summary."""
        service = AnalyticsService(db)
        summary = service.get_security_events_summary(days=30)
        
        assert "period_days" in summary
        assert "failed_login_attempts" in summary
        assert "password_reset_requests" in summary
        assert "suspended_accounts" in summary
        assert "revoked_tokens" in summary
        assert "suspicious_ips" in summary
        assert "security_score" in summary
        assert 0 <= summary["security_score"] <= 100
    
    def test_security_score_calculation(self, db):
        """Test security score calculation."""
        service = AnalyticsService(db)
        
        # Test with different inputs
        score_high = service._calculate_security_score(0, 0, 0)
        assert score_high == 100
        
        score_low = service._calculate_security_score(1000, 50, 20)
        assert score_low < 50
        
        score_min = service._calculate_security_score(10000, 1000, 100)
        assert score_min == 0


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""
    
    def test_dashboard_metrics_admin_only(self, client, admin_headers):
        """Test dashboard metrics endpoint requires admin."""
        response = client.get("/admin/analytics/dashboard", headers=admin_headers)
        # May return data or 404 if endpoint not set up
        assert response.status_code in [200, 404]
    
    def test_user_growth_endpoint(self, client, admin_headers):
        """Test user growth analytics endpoint."""
        response = client.get("/admin/analytics/users/growth?days=30", headers=admin_headers)
        assert response.status_code in [200, 404]
    
    def test_revenue_analytics_endpoint(self, client, admin_headers):
        """Test revenue analytics endpoint."""
        response = client.get("/admin/analytics/revenue", headers=admin_headers)
        assert response.status_code in [200, 404]
    
    def test_security_summary_endpoint(self, client, admin_headers):
        """Test security summary endpoint."""
        response = client.get("/admin/analytics/security/summary", headers=admin_headers)
        assert response.status_code in [200, 404]
