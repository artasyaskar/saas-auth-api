"""
SaaS Auth API - Python SDK

Comprehensive Python SDK for authentication and user management.
"""

import requests
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuthResponse:
    """Authentication response dataclass."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@dataclass
class UserProfile:
    """User profile dataclass."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    subscription_plan: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


@dataclass
class APIKey:
    """API key dataclass."""
    id: int
    key: str
    name: str
    scopes: List[str]
    rate_limit: int
    created_at: datetime


@dataclass
class Webhook:
    """Webhook dataclass."""
    id: int
    name: str
    url: str
    events: List[str]
    status: str
    created_at: datetime


class AuthClient:
    """SaaS Auth API Python Client."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the Auth client.
        
        Args:
            base_url: Base URL of the API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.access_token = None
        self.refresh_token = None
        self.session = requests.Session()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        requires_auth: bool = False
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            requires_auth: Whether authentication is required
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        if requires_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            # Handle 401 and attempt refresh
            if response.status_code == 401 and self.refresh_token:
                self._refresh_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    # ==================== Authentication ====================
    
    def login(self, email: str, password: str) -> AuthResponse:
        """
        Login a user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            AuthResponse with tokens
        """
        data = {"email": email, "password": password}
        response = self._request("POST", "/auth/login", data)
        
        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        
        return AuthResponse(
            access_token=response["access_token"],
            refresh_token=response["refresh_token"],
            token_type=response["token_type"],
            expires_in=response["expires_in"]
        )
    
    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            username: Username
            email: Email address
            password: Password
            
        Returns:
            User data
        """
        data = {"username": username, "email": email, "password": password}
        return self._request("POST", "/auth/register", data)
    
    def logout(self) -> Dict[str, Any]:
        """Logout the current user."""
        return self._request("POST", "/auth/logout", requires_auth=True)
    
    def _refresh_token(self) -> AuthResponse:
        """Refresh the access token."""
        data = {"refresh_token": self.refresh_token}
        response = self._request("POST", "/auth/refresh", data)
        
        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        
        return AuthResponse(
            access_token=response["access_token"],
            refresh_token=response["refresh_token"],
            token_type=response["token_type"],
            expires_in=response["expires_in"]
        )
    
    # ==================== User Management ====================
    
    def get_profile(self) -> UserProfile:
        """
        Get the current user's profile.
        
        Returns:
            UserProfile data
        """
        response = self._request("GET", "/users/me", requires_auth=True)
        return UserProfile(
            id=response["id"],
            username=response["username"],
            email=response["email"],
            role=response["role"],
            is_active=response["is_active"],
            subscription_plan=response.get("subscription_plan"),
            created_at=datetime.fromisoformat(response["created_at"]),
            updated_at=datetime.fromisoformat(response["updated_at"]) if response.get("updated_at") else None
        )
    
    def update_profile(self, **kwargs) -> UserProfile:
        """
        Update the current user's profile.
        
        Args:
            **kwargs: Fields to update
            
        Returns:
            Updated UserProfile
        """
        response = self._request("PUT", "/users/me", data=kwargs, requires_auth=True)
        return UserProfile(
            id=response["id"],
            username=response["username"],
            email=response["email"],
            role=response["role"],
            is_active=response["is_active"],
            subscription_plan=response.get("subscription_plan"),
            created_at=datetime.fromisoformat(response["created_at"]),
            updated_at=datetime.fromisoformat(response["updated_at"]) if response.get("updated_at") else None
        )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for the current user."""
        return self._request("GET", "/users/usage", requires_auth=True)
    
    # ==================== Password Management ====================
    
    def request_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Request a password reset.
        
        Args:
            email: User email
            
        Returns:
            Response data
        """
        data = {"email": email}
        return self._request("POST", "/auth/password-reset/request", data)
    
    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password with token.
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            Response data
        """
        data = {"token": token, "new_password": new_password}
        return self._request("POST", "/auth/password-reset/confirm", data)
    
    def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change password for authenticated user.
        
        Args:
            current_password: Current password
            new_password: New password
            
        Returns:
            Response data
        """
        data = {"current_password": current_password, "new_password": new_password}
        return self._request("POST", "/auth/change-password", data, requires_auth=True)
    
    # ==================== Two-Factor Authentication ====================
    
    def enable_2fa(self) -> Dict[str, Any]:
        """Enable two-factor authentication."""
        return self._request("POST", "/auth/2fa/enable", requires_auth=True)
    
    def verify_2fa(self, code: str) -> Dict[str, Any]:
        """
        Verify 2FA code.
        
        Args:
            code: 2FA code
            
        Returns:
            Response data
        """
        data = {"code": code}
        return self._request("POST", "/auth/2fa/verify", data, requires_auth=True)
    
    def disable_2fa(self, code: str) -> Dict[str, Any]:
        """
        Disable 2FA.
        
        Args:
            code: 2FA code
            
        Returns:
            Response data
        """
        data = {"code": code}
        return self._request("POST", "/auth/2fa/disable", data, requires_auth=True)
    
    # ==================== OAuth2/OIDC ====================
    
    def get_oauth_url(self, provider: str, redirect_uri: str) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            provider: OAuth provider (google, github, apple)
            redirect_uri: Redirect URI after auth
            
        Returns:
            Authorization URL
        """
        return f"{self.base_url}/auth/oauth/{provider}?redirect_uri={redirect_uri}"
    
    def exchange_oauth_code(self, provider: str, code: str, redirect_uri: str) -> AuthResponse:
        """
        Exchange OAuth code for tokens.
        
        Args:
            provider: OAuth provider
            code: Authorization code
            redirect_uri: Redirect URI
            
        Returns:
            AuthResponse with tokens
        """
        data = {"code": code, "redirect_uri": redirect_uri}
        response = self._request("POST", f"/auth/oauth/{provider}/callback", data)
        
        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        
        return AuthResponse(
            access_token=response["access_token"],
            refresh_token=response["refresh_token"],
            token_type=response["token_type"],
            expires_in=response["expires_in"]
        )
    
    # ==================== API Keys ====================
    
    def create_api_key(self, name: str, scopes: List[str], rate_limit: int = 1000) -> APIKey:
        """
        Create an API key.
        
        Args:
            name: Key name
            scopes: List of scopes
            rate_limit: Rate limit
            
        Returns:
            APIKey data
        """
        data = {"name": name, "scopes": scopes, "rate_limit": rate_limit}
        response = self._request("POST", "/api-keys", data, requires_auth=True)
        return APIKey(
            id=response["id"],
            key=response["key"],
            name=response["name"],
            scopes=response["scopes"],
            rate_limit=response["rate_limit"],
            created_at=datetime.fromisoformat(response["created_at"])
        )
    
    def list_api_keys(self) -> List[APIKey]:
        """List all API keys for the current user."""
        response = self._request("GET", "/api-keys", requires_auth=True)
        return [
            APIKey(
                id=key["id"],
                key=key["key"],
                name=key["name"],
                scopes=key["scopes"],
                rate_limit=key["rate_limit"],
                created_at=datetime.fromisoformat(key["created_at"])
            )
            for key in response
        ]
    
    def delete_api_key(self, key_id: int) -> Dict[str, Any]:
        """
        Delete an API key.
        
        Args:
            key_id: API key ID
            
        Returns:
            Response data
        """
        return self._request("DELETE", f"/api-keys/{key_id}", requires_auth=True)
    
    # ==================== Webhooks ====================
    
    def create_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None
    ) -> Webhook:
        """
        Create a webhook.
        
        Args:
            name: Webhook name
            url: Webhook URL
            events: List of events to subscribe to
            secret: Optional secret for signature verification
            
        Returns:
            Webhook data
        """
        data = {"name": name, "url": url, "events": events}
        if secret:
            data["secret"] = secret
        response = self._request("POST", "/webhooks", data, requires_auth=True)
        return Webhook(
            id=response["id"],
            name=response["name"],
            url=response["url"],
            events=response["events"],
            status=response["status"],
            created_at=datetime.fromisoformat(response["created_at"])
        )
    
    def list_webhooks(self) -> List[Webhook]:
        """List all webhooks for the current user."""
        response = self._request("GET", "/webhooks", requires_auth=True)
        return [
            Webhook(
                id=webhook["id"],
                name=webhook["name"],
                url=webhook["url"],
                events=webhook["events"],
                status=webhook["status"],
                created_at=datetime.fromisoformat(webhook["created_at"])
            )
            for webhook in response
        ]
    
    def delete_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Response data
        """
        return self._request("DELETE", f"/webhooks/{webhook_id}", requires_auth=True)
    
    # ==================== Feature Flags ====================
    
    def check_feature_flag(self, flag_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Feature flag name
            user_id: Optional user ID for evaluation
            
        Returns:
            Flag evaluation result
        """
        data = {"user_id": user_id} if user_id else {}
        return self._request("POST", f"/feature-flags/{flag_name}/evaluate", data, requires_auth=True)
    
    def list_feature_flags(self) -> List[Dict[str, Any]]:
        """List all feature flags."""
        return self._request("GET", "/feature-flags", requires_auth=True)
    
    # ==================== Helper Methods ====================
    
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self.access_token is not None
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for quick usage
def create_client(base_url: str = "http://localhost:8000/v1", api_key: Optional[str] = None) -> AuthClient:
    """
    Create an Auth client instance.
    
    Args:
        base_url: Base URL of the API
        api_key: Optional API key
        
    Returns:
        AuthClient instance
    """
    return AuthClient(base_url=base_url, api_key=api_key)
