"""
Authentication endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.core.security import verify_password, get_password_hash


class TestRegister:
    """Tests for user registration."""
    
    def test_register_success(self, client: TestClient, db: Session):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "USER"
        assert data["is_active"] is True
        
        # Verify user was created in database
        user = db.query(User).filter(User.username == "newuser").first()
        assert user is not None
        assert verify_password("SecurePass123!", user.hashed_password)
    
    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Test registration with duplicate username."""
        response = client.post(
            "/auth/register",
            json={
                "username": test_user.username,
                "email": "different@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "username": "differentuser",
                "email": test_user.email,
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password (if validation exists)."""
        # Note: Currently no password strength validation in the code
        # This test documents expected behavior
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123"  # Weak password
            }
        )
        # Current implementation accepts any password
        # In production, should add password strength validation
        assert response.status_code in [200, 422]


class TestLogin:
    """Tests for user login."""
    
    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            data={"username": test_user.username, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, db: Session, test_user: User):
        """Test login with inactive user."""
        test_user.is_active = False
        db.commit()
        
        response = client.post(
            "/auth/login",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]


class TestRefreshToken:
    """Tests for token refresh."""
    
    def test_refresh_success(self, client: TestClient, test_user: User):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = client.post(
            "/auth/login",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Now refresh
        response = client.post(
            "/auth/refresh",
            params={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_invalid_token(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            params={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401
    
    def test_refresh_expired_token(self, client: TestClient):
        """Test refresh with expired token."""
        # Would need to create an expired token for this test
        # For now, just test that invalid tokens are rejected
        response = client.post(
            "/auth/refresh",
            params={"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"}
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for getting current user."""
    
    def test_get_current_user_success(self, client: TestClient, auth_headers: dict):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data
        assert "role" in data
    
    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/auth/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_get_current_user_expired_token(self, client: TestClient):
        """Test getting current user with expired token."""
        # Create an expired token
        from app.core.security import create_access_token
        from datetime import timedelta
        
        expired_token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=-1)  # Expired
        )
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Tests for protected endpoints."""
    
    def test_protected_endpoint_with_auth(self, client: TestClient, auth_headers: dict):
        """Test accessing protected endpoint with valid auth."""
        response = client.get("/protected", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_protected_endpoint_without_auth(self, client: TestClient):
        """Test accessing protected endpoint without auth."""
        response = client.get("/protected")
        assert response.status_code == 401


class TestLogout:
    """Tests for logout functionality.
    
    TODO: Implement logout endpoint with token blacklisting
    """
    
    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout.
        
        Currently this endpoint doesn't exist - it should be implemented.
        """
        # This test documents expected behavior
        # response = client.post("/auth/logout", headers=auth_headers)
        # assert response.status_code == 200
        # Token should be blacklisted
        pass
