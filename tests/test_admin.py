"""
Admin endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User, UserRole, UsageLog


class TestAdminUsers:
    """Tests for admin user management endpoints."""
    
    def test_get_all_users_as_admin(self, client: TestClient, admin_headers: dict, db: Session):
        """Test getting all users as admin."""
        # Create additional test users
        from app.core.security import get_password_hash
        for i in range(3):
            user = User(
                username=f"user{i}",
                email=f"user{i}@test.com",
                hashed_password=get_password_hash("password123"),
                role=UserRole.USER
            )
            db.add(user)
        db.commit()
        
        response = client.get("/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4  # admin + 3 test users + test_user fixture
    
    def test_get_all_users_as_regular_user(self, client: TestClient, auth_headers: dict):
        """Test getting all users as regular user (should fail)."""
        response = client.get("/admin/users", headers=auth_headers)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    def test_get_all_users_unauthorized(self, client: TestClient):
        """Test getting all users without authentication."""
        response = client.get("/admin/users")
        assert response.status_code == 401
    
    def test_get_specific_user(self, client: TestClient, admin_headers: dict, test_user: User):
        """Test getting a specific user by ID."""
        response = client.get(f"/admin/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
    
    def test_get_nonexistent_user(self, client: TestClient, admin_headers: dict):
        """Test getting a non-existent user."""
        response = client.get("/admin/users/99999", headers=admin_headers)
        assert response.status_code == 404


class TestAdminSuspend:
    """Tests for admin user suspension."""
    
    def test_suspend_user(self, client: TestClient, admin_headers: dict, test_user: User, db: Session):
        """Test suspending a user."""
        response = client.put(
            f"/admin/users/{test_user.id}/suspend",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "suspended" in response.json()["message"]
        
        # Verify user is suspended
        db.refresh(test_user)
        assert test_user.is_active is False
    
    def test_unsuspend_user(self, client: TestClient, admin_headers: dict, test_user: User, db: Session):
        """Test unsuspending a user."""
        # First suspend
        test_user.is_active = False
        db.commit()
        
        # Then unsuspend
        response = client.put(
            f"/admin/users/{test_user.id}/suspend",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "activated" in response.json()["message"]
        
        # Verify user is active
        db.refresh(test_user)
        assert test_user.is_active is True
    
    def test_suspend_nonexistent_user(self, client: TestClient, admin_headers: dict):
        """Test suspending a non-existent user."""
        response = client.put("/admin/users/99999/suspend", headers=admin_headers)
        assert response.status_code == 404


class TestAdminRoleChange:
    """Tests for admin role management."""
    
    def test_change_user_role(self, client: TestClient, admin_headers: dict, test_user: User, db: Session):
        """Test changing a user's role."""
        response = client.put(
            f"/admin/users/{test_user.id}/role",
            headers=admin_headers,
            params={"new_role": "ADMIN"}
        )
        assert response.status_code == 200
        assert "ADMIN" in response.json()["message"]
        
        # Verify role changed
        db.refresh(test_user)
        assert test_user.role == UserRole.ADMIN
    
    def test_change_role_invalid_role(self, client: TestClient, admin_headers: dict, test_user: User):
        """Test changing to an invalid role."""
        response = client.put(
            f"/admin/users/{test_user.id}/role",
            headers=admin_headers,
            params={"new_role": "SUPERUSER"}  # Invalid role
        )
        assert response.status_code == 422  # Validation error


class TestAdminStats:
    """Tests for admin statistics endpoints."""
    
    def test_get_system_stats(self, client: TestClient, admin_headers: dict):
        """Test getting system statistics."""
        response = client.get("/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields
        assert "total_users" in data
        assert "active_users" in data
        assert "total_requests_today" in data
        assert "total_requests_this_month" in data
        assert "free_plan_users" in data
        assert "pro_plan_users" in data
        
        # Validate data types
        assert isinstance(data["total_users"], int)
        assert data["active_users"] <= data["total_users"]
    
    def test_get_usage_stats(self, client: TestClient, admin_headers: dict, db: Session):
        """Test getting admin usage statistics."""
        # Create some usage data
        from datetime import datetime
        from app.core.security import get_password_hash
        
        test_user = User(
            username="statstest",
            email="statstest@test.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(test_user)
        db.commit()
        
        # Add usage logs
        for i in range(10):
            log = UsageLog(
                user_id=test_user.id,
                endpoint="/api/test",
                method="GET",
                status_code=200,
                timestamp=datetime.utcnow()
            )
            db.add(log)
        db.commit()
        
        response = client.get("/admin/usage", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        # Check first item has expected fields
        first_item = data[0]
        assert "user_id" in first_item
        assert "username" in first_item
        assert "total_requests" in first_item


class TestAdminSecurity:
    """Tests for admin endpoint security."""
    
    def test_admin_endpoints_require_auth(self, client: TestClient):
        """Test that all admin endpoints require authentication."""
        endpoints = [
            "/admin/users",
            "/admin/stats",
            "/admin/usage",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require auth"
    
    def test_admin_endpoints_require_admin_role(self, client: TestClient, auth_headers: dict):
        """Test that admin endpoints require admin role."""
        response = client.get("/admin/users", headers=auth_headers)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
