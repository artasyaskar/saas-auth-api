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


class TestAuth:
    def setup_method(self):
        """Setup for each test method"""
        db = TestingSessionLocal()
        # Clear users table
        db.query(User).delete()
        db.commit()
        db.close()

    def test_register_user(self):
        """Test user registration"""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "USER"

    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        # First user
        client.post(
            "/auth/register",
            json={
                "username": "user1",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        # Second user with same email
        response = client.post(
            "/auth/register",
            json={
                "username": "user2",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_login_success(self):
        """Test successful login"""
        # Register user first
        client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        # Login
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_get_current_user(self):
        """Test getting current user info"""
        # Register and login
        client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        login_response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_token_refresh(self):
        """Test token refresh"""
        # Register and login
        client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        login_response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
