import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import get_db, Base
from app.db.models import User, UserRole
from app.core.security import get_password_hash

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestAdmin:
    def setup_method(self):
        """Setup for each test method"""
        db = TestingSessionLocal()
        # Clear users table
        db.query(User).delete()
        db.commit()
        
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        
        # Create regular user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            role=UserRole.USER
        )
        db.add(user)
        db.commit()
        db.close()

    def get_admin_headers(self):
        """Get authentication headers for admin user"""
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def get_user_headers(self):
        """Get authentication headers for regular user"""
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_admin_access_success(self):
        """Test admin can access admin endpoints"""
        headers = self.get_admin_headers()
        response = client.get("/admin/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1  # At least the admin user

    def test_user_access_denied(self):
        """Test regular user cannot access admin endpoints"""
        headers = self.get_user_headers()
        response = client.get("/admin/users", headers=headers)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_system_stats(self):
        """Test getting system statistics"""
        headers = self.get_admin_headers()
        response = client.get("/admin/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert data["total_users"] >= 2  # Admin + test user

    def test_suspend_user(self):
        """Test suspending a user"""
        headers = self.get_admin_headers()
        
        # Get user ID first
        users_response = client.get("/admin/users", headers=headers)
        users = users_response.json()
        test_user = next((u for u in users if u["username"] == "testuser"), None)
        
        assert test_user is not None
        
        # Suspend user
        response = client.put(f"/admin/users/{test_user['id']}/suspend", headers=headers)
        assert response.status_code == 200
        assert "suspended successfully" in response.json()["message"]
        
        # Verify user is suspended
        user_response = client.get(f"/admin/users/{test_user['id']}", headers=headers)
        user_data = user_response.json()
        assert user_data["is_active"] is False
