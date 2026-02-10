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


class TestRateLimit:
    def setup_method(self):
        """Setup for each test method"""
        db = TestingSessionLocal()
        # Clear users table
        db.query(User).delete()
        db.commit()
        
        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            role=UserRole.USER
        )
        db.add(user)
        db.commit()
        db.close()

    def get_auth_headers(self):
        """Get authentication headers for test user"""
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_basic_access(self):
        """Test basic access to protected endpoint"""
        headers = self.get_auth_headers()
        response = client.get("/protected", headers=headers)
        assert response.status_code == 200

    def test_unauthorized_access(self):
        """Test access without authentication"""
        response = client.get("/protected")
        assert response.status_code == 401

    def test_usage_tracking(self):
        """Test that usage is tracked"""
        headers = self.get_auth_headers()
        
        # Make multiple requests
        for _ in range(5):
            response = client.get("/protected", headers=headers)
            assert response.status_code == 200
        
        # Check usage stats
        response = client.get("/users/usage", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] >= 5
