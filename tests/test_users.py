"""
User endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User, UsageLog
from app.services.usage import UsageService


class TestUserProfile:
    """Tests for user profile endpoints."""
    
    def test_get_profile_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting user profile."""
        response = client.get("/users/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
    
    def test_get_profile_unauthorized(self, client: TestClient):
        """Test getting profile without authentication."""
        response = client.get("/users/profile")
        assert response.status_code == 401


class TestUsageStats:
    """Tests for usage statistics endpoints."""
    
    def test_get_usage_stats_empty(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting usage stats with no activity."""
        response = client.get("/users/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["requests_this_month"] == 0
        assert data["most_used_endpoint"] == "N/A"
        assert data["average_response_time"] == 0.0
    
    def test_get_usage_stats_with_data(
        self, client: TestClient, auth_headers: dict, test_user: User, db: Session
    ):
        """Test getting usage stats with activity logged."""
        # Create some usage logs
        from datetime import datetime
        
        for i in range(5):
            log = UsageLog(
                user_id=test_user.id,
                endpoint="/test/endpoint",
                method="GET",
                status_code=200,
                response_time_ms=100.0 + i,
                timestamp=datetime.utcnow()
            )
            db.add(log)
        db.commit()
        
        response = client.get("/users/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 5
        assert data["requests_this_month"] == 5
        assert data["most_used_endpoint"] == "/test/endpoint"
        assert data["average_response_time"] > 0


class TestUpdateProfile:
    """Tests for updating user profile.
    
    TODO: Implement profile update endpoint
    """
    
    def test_update_profile(self, client: TestClient, auth_headers: dict):
        """Test updating user profile.
        
        This endpoint doesn't exist yet - should be implemented.
        """
        # response = client.put(
        #     "/users/profile",
        #     headers=auth_headers,
        #     json={"email": "newemail@example.com"}
        # )
        # assert response.status_code == 200
        pass


class TestChangePassword:
    """Tests for changing password.
    
    TODO: Implement change password endpoint
    """
    
    def test_change_password_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test changing password.
        
        This endpoint doesn't exist yet - should be implemented.
        """
        # response = client.post(
        #     "/users/change-password",
        #     headers=auth_headers,
        #     json={
        #         "current_password": "testpassword123",
        #         "new_password": "NewPassword123!"
        #     }
        # )
        # assert response.status_code == 200
        pass
    
    def test_change_password_wrong_current(self, client: TestClient, auth_headers: dict):
        """Test changing password with wrong current password."""
        # response = client.post(
        #     "/users/change-password",
        #     headers=auth_headers,
        #     json={
        #         "current_password": "wrongpassword",
        #         "new_password": "NewPassword123!"
        #     }
        # )
        # assert response.status_code == 400
        pass
