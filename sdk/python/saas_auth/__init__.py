"""
SaaS Auth API Python SDK

Enterprise authentication and authorization client library.
"""

from .client import SaaSAuthClient
from .auth import AuthAPI
from .users import UsersAPI
from .organizations import OrganizationsAPI
from .exceptions import (
    SaaSAuthError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)

__version__ = "1.1.0"
__all__ = [
    "SaaSAuthClient",
    "AuthAPI", 
    "UsersAPI",
    "OrganizationsAPI",
    "SaaSAuthError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError"
]
