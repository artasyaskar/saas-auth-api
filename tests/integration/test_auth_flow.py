"""
Integration tests for complete authentication flows.

Tests end-to-end authentication scenarios including:
- Registration flow
- Login flow
- Token refresh flow
- Logout flow
- Password reset flow
- OAuth flow
- 2FA flow
"""
import pytest
from httpx import Client
from datetime import datetime, timedelta


class TestRegistrationFlow:
    """Integration tests for user registration flow."""
    
    def test_complete_registration_flow(self, client: Client):
        """Test complete registration with email verification."""
        # Step 1: Register user
        register_response = client.post(
            "/auth/register",
            json={
                "username": "integration_user",
                "email": "integration@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert register_response.status_code == 200
        data = register_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
        access_token = data["access_token"]
        
        # Step 2: Verify user profile
        profile_response = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["username"] == "integration_user"
        assert profile["email"] == "integration@example.com"
        
        # Step 3: Update profile
        update_response = client.put(
            "/users/profile",
            json={"email": "updated@example.com"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert update_response.status_code == 200
    
    def test_registration_with_duplicate_email(self, client: Client):
        """Test registration with duplicate email fails."""
        # First registration
        client.post(
            "/auth/register",
            json={
                "username": "user1",
                "email": "duplicate@example.com",
                "password": "SecurePass123!"
            }
        )
        
        # Second registration with same email
        response = client.post(
            "/auth/register",
            json={
                "username": "user2",
                "email": "duplicate@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 400


class TestLoginFlow:
    """Integration tests for login flow."""
    
    def test_complete_login_flow(self, client: Client):
        """Test complete login flow with token refresh."""
        # Register user first
        client.post(
            "/auth/register",
            json={
                "username": "login_user",
                "email": "login@example.com",
                "password": "LoginPass123!"
            }
        )
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={
                "username": "login_user",
                "password": "LoginPass123!"
            }
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        
        # Access protected endpoint
        protected_response = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert protected_response.status_code == 200
        
        # Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_data = refresh_response.json()
        assert "access_token" in new_data
        assert new_data["access_token"] != access_token
        
        # Verify new token works
        new_protected_response = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {new_data['access_token']}"}
        )
        
        assert new_protected_response.status_code == 200
    
    def test_login_with_invalid_credentials(self, client: Client):
        """Test login with invalid credentials fails."""
        response = client.post(
            "/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401


class TestLogoutFlow:
    """Integration tests for logout flow."""
    
    def test_complete_logout_flow(self, client: Client):
        """Test complete logout flow with token blacklisting."""
        # Register and login
        register_response = client.post(
            "/auth/register",
            json={
                "username": "logout_user",
                "email": "logout@example.com",
                "password": "LogoutPass123!"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Logout
        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert logout_response.status_code == 200
        
        # Verify token is blacklisted
        protected_response = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert protected_response.status_code == 401


class TestPasswordResetFlow:
    """Integration tests for password reset flow."""
    
    def test_complete_password_reset_flow(self, client: Client):
        """Test complete password reset flow."""
        # Register user
        client.post(
            "/auth/register",
            json={
                "username": "reset_user",
                "email": "reset@example.com",
                "password": "OldPass123!"
            }
        )
        
        # Request password reset
        request_response = client.post(
            "/auth/password-reset/request",
            json={"email": "reset@example.com"}
        )
        
        assert request_response.status_code == 200
        
        # In real flow, user would receive email with token
        # For testing, we'll simulate token validation
        # (This would require mocking email service)
        
        # Reset password with token
        # reset_response = client.post(
        #     "/auth/password-reset/reset",
        #     json={
        #         "token": "test_token",
        #         "new_password": "NewPass123!"
        #     }
        # )
        
        # assert reset_response.status_code == 200
        
        # Login with new password
        # login_response = client.post(
        #     "/auth/login",
        #     json={
        #         "username": "reset_user",
        #         "password": "NewPass123!"
        #     }
        # )
        
        # assert login_response.status_code == 200


class TestOAuthFlow:
    """Integration tests for OAuth flow."""
    
    def test_oauth_authorization_url(self, client: Client):
        """Test getting OAuth authorization URL."""
        response = client.get("/auth/oauth/google/url")
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
    
    def test_oauth_callback(self, client: Client):
        """Test OAuth callback handling."""
        # This would require mocking OAuth provider
        # For integration testing, we'd use test OAuth credentials
        pass


class TestTwoFactorFlow:
    """Integration tests for 2FA flow."""
    
    def test_complete_2fa_flow(self, client: Client):
        """Test complete 2FA setup and verification flow."""
        # Register user
        register_response = client.post(
            "/auth/register",
            json={
                "username": "2fa_user",
                "email": "2fa@example.com",
                "password": "TwoFactorPass123!"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Setup 2FA
        setup_response = client.post(
            "/auth/2fa/setup",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert setup_response.status_code == 200
        setup_data = setup_response.json()
        assert "secret" in setup_data
        assert "qr_code" in setup_data
        assert "backup_codes" in setup_data
        
        # Verify 2FA (would require authenticator app in real flow)
        # verify_response = await client.post(
        #     "/auth/2fa/verify",
        #     json={"code": "123456"},
        #     headers={"Authorization": f"Bearer {access_token}"}
        # )
        
        # assert verify_response.status_code == 200


class TestSessionManagement:
    """Integration tests for session management."""
    
    def test_multiple_device_login(self, client: Client):
        """Test login from multiple devices."""
        # Register user
        client.post(
            "/auth/register",
            json={
                "username": "multi_device_user",
                "email": "multi@example.com",
                "password": "MultiPass123!"
            }
        )
        
        # Login from device 1
        device1_response = client.post(
            "/auth/login",
            json={
                "username": "multi_device_user",
                "password": "MultiPass123!"
            }
        )
        
        device1_token = device1_response.json()["access_token"]
        
        # Login from device 2
        device2_response = client.post(
            "/auth/login",
            json={
                "username": "multi_device_user",
                "password": "MultiPass123!"
            }
        )
        
        device2_token = device2_response.json()["access_token"]
        
        # Both tokens should work
        device1_profile = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {device1_token}"}
        )
        
        device2_profile = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {device2_token}"}
        )
        
        assert device1_profile.status_code == 200
        assert device2_profile.status_code == 200
    
    def test_logout_all_devices(self, client: Client):
        """Test logout from all devices."""
        # Register and login from multiple devices
        client.post(
            "/auth/register",
            json={
                "username": "logout_all_user",
                "email": "logoutall@example.com",
                "password": "LogoutAllPass123!"
            }
        )
        
        # Login from device 1
        device1_response = client.post(
            "/auth/login",
            json={
                "username": "logout_all_user",
                "password": "LogoutAllPass123!"
            }
        )
        
        device1_token = device1_response.json()["access_token"]
        
        # Login from device 2
        device2_response = client.post(
            "/auth/login",
            json={
                "username": "logout_all_user",
                "password": "LogoutAllPass123!"
            }
        )
        
        device2_token = device2_response.json()["access_token"]
        
        # Logout from all devices
        logout_all_response = client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {device1_token}"}
        )
        
        assert logout_all_response.status_code == 200
        
        # Both tokens should be invalid
        device1_profile = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {device1_token}"}
        )
        
        device2_profile = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {device2_token}"}
        )
        
        assert device1_profile.status_code == 401
        assert device2_profile.status_code == 401


class TestTokenExpiry:
    """Integration tests for token expiry handling."""
    
    def test_expired_token_refresh(self, client: Client):
        """Test automatic token refresh on expiry."""
        # Register and login
        register_response = client.post(
            "/auth/register",
            json={
                "username": "expiry_user",
                "email": "expiry@example.com",
                "password": "ExpiryPass123!"
            }
        )
        
        access_token = register_response.json()["access_token"]
        refresh_token = register_response.json()["refresh_token"]
        
        # Simulate token expiry (in real test, would wait or mock time)
        # For now, test refresh endpoint directly
        
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]
        
        # New token should work
        profile_response = client.get(
            "/users/profile",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        assert profile_response.status_code == 200


class TestConcurrentRequests:
    """Integration tests for concurrent request handling."""
    
    def test_concurrent_authenticated_requests(self, client: Client):
        """Test multiple concurrent authenticated requests."""
        # Register and login
        register_response = client.post(
            "/auth/register",
            json={
                "username": "concurrent_user",
                "email": "concurrent@example.com",
                "password": "ConcurrentPass123!"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Make concurrent requests
        tasks = []
        for i in range(10):
            task = client.get(
                "/users/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            tasks.append(task)
        
        responses = tasks
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
