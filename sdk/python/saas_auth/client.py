"""
SaaS Auth API Client

Main client class for interacting with the SaaS Auth API.
"""

import json
import requests
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

from .auth import AuthAPI
from .users import UsersAPI
from .organizations import OrganizationsAPI
from .exceptions import (
    SaaSAuthError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError
)


class SaaSAuthClient:
    """
    Main client for the SaaS Auth API.
    
    Provides access to all API endpoints with automatic authentication,
    error handling, and retry logic.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        retries: int = 3,
        user_agent: str = None
    ):
        """
        Initialize the SaaS Auth client.
        
        Args:
            base_url: Base URL of the SaaS Auth API
            api_key: API key for authentication (alternative to username/password)
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            user_agent: Custom user agent string
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        
        # Set user agent
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            self.session.headers.update({
                'User-Agent': f'saas-auth-python-sdk/1.1.0'
            })
        
        # Authentication
        self.api_key = api_key
        self.username = username
        self.password = password
        self._access_token = None
        self._refresh_token = None
        
        # Initialize API modules
        self.auth = AuthAPI(self)
        self.users = UsersAPI(self)
        self.organizations = OrganizationsAPI(self)
        
        # Auto-authenticate if credentials provided
        if api_key or (username and password):
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with the API."""
        if self.api_key:
            # Use API key authentication
            self.session.headers.update({
                'X-API-Key': self.api_key
            })
        elif self.username and self.password:
            # Use username/password authentication
            tokens = self.auth.login(self.username, self.password)
            self._access_token = tokens['access_token']
            self._refresh_token = tokens['refresh_token']
            self._set_auth_header()
    
    def _set_auth_header(self):
        """Set the authorization header."""
        if self._access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self._access_token}'
            })
    
    def _refresh_access_token(self):
        """Refresh the access token."""
        if not self._refresh_token:
            raise AuthenticationError("No refresh token available")
        
        try:
            tokens = self.auth.refresh_token(self._refresh_token)
            self._access_token = tokens['access_token']
            self._refresh_token = tokens['refresh_token']
            self._set_auth_header()
        except Exception as e:
            raise AuthenticationError(f"Failed to refresh token: {e}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Union[Dict, str]] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            data: Request data (dict or JSON string)
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional request options
            
        Returns:
            Response data as dictionary
            
        Raises:
            SaaSAuthError: For API errors
            AuthenticationError: For authentication failures
            RateLimitError: For rate limit exceeded
            ValidationError: For validation errors
        """
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Prepare data
        json_data = None
        form_data = None
        
        if data:
            if isinstance(data, dict):
                if 'Content-Type' in request_headers and 'multipart/form-data' in request_headers['Content-Type']:
                    form_data = data
                else:
                    json_data = data
                    request_headers.setdefault('Content-Type', 'application/json')
            else:
                json_data = data
                request_headers.setdefault('Content-Type', 'application/json')
        
        # Make request with retry logic
        last_exception = None
        
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    data=form_data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Handle response
                self._handle_response(response)
                
                # Return parsed JSON response
                if response.content:
                    return response.json()
                else:
                    return {}
            
            except requests.exceptions.Timeout as e:
                last_exception = APIError(f"Request timeout: {e}")
                if attempt == self.retries:
                    raise last_exception
                continue
            
            except requests.exceptions.ConnectionError as e:
                last_exception = APIError(f"Connection error: {e}")
                if attempt == self.retries:
                    raise last_exception
                continue
            
            except AuthenticationError as e:
                # Try to refresh token and retry once
                if attempt == 0 and self._refresh_token:
                    try:
                        self._refresh_access_token()
                        continue
                    except:
                        pass
                raise e
            
            except (RateLimitError, ValidationError, SaaSAuthError) as e:
                # Don't retry these errors
                raise e
            
            except Exception as e:
                last_exception = APIError(f"Unexpected error: {e}")
                if attempt == self.retries:
                    raise last_exception
                continue
        
        # This should never be reached
        if last_exception:
            raise last_exception
        else:
            raise APIError("Request failed")
    
    def _handle_response(self, response: requests.Response):
        """Handle HTTP response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed")
        
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 60)
            raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
        
        elif response.status_code == 422:
            try:
                error_data = response.json()
                raise ValidationError(error_data.get('detail', 'Validation error'))
            except json.JSONDecodeError:
                raise ValidationError("Validation error")
        
        elif 400 <= response.status_code < 500:
            try:
                error_data = response.json()
                raise SaaSAuthError(
                    error_data.get('detail', f'HTTP {response.status_code}'),
                    status_code=response.status_code
                )
            except json.JSONDecodeError:
                raise SaaSAuthError(f'HTTP {response.status_code}', status_code=response.status_code)
        
        elif response.status_code >= 500:
            raise APIError(f"Server error: HTTP {response.status_code}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return self._make_request('GET', endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Union[Dict, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return self._make_request('POST', endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Union[Dict, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._make_request('PUT', endpoint, data=data, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Union[Dict, str]] = None, **kwargs) -> Dict[str, Any]:
        """Make a PATCH request."""
        return self._make_request('PATCH', endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._make_request('DELETE', endpoint, **kwargs)
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        return self.get('/health')
    
    def get_api_info(self) -> Dict[str, Any]:
        """Get API information."""
        return self.get('/')
    
    def set_api_key(self, api_key: str):
        """Set API key for authentication."""
        self.api_key = api_key
        self.username = None
        self.password = None
        self._access_token = None
        self._refresh_token = None
        
        # Update session headers
        self.session.headers.update({'X-API-Key': api_key})
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def set_credentials(self, username: str, password: str):
        """Set username/password for authentication."""
        self.username = username
        self.password = password
        self.api_key = None
        self._access_token = None
        self._refresh_token = None
        
        # Remove API key header
        if 'X-API-Key' in self.session.headers:
            del self.session.headers['X-API-Key']
        
        # Authenticate
        self._authenticate()
    
    def logout(self):
        """Logout and clear authentication tokens."""
        try:
            if self._access_token:
                self.auth.logout()
        except:
            pass  # Ignore errors during logout
        
        # Clear tokens
        self._access_token = None
        self._refresh_token = None
        
        # Clear auth headers
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
