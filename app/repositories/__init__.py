"""
Repository layer for data access.

This layer abstracts database operations and provides a clean interface
for the service layer to interact with the database.
"""

from .base import BaseRepository
from .user import UserRepository
from .auth import AuthRepository
from .organization import OrganizationRepository

__all__ = [
    "BaseRepository",
    "UserRepository", 
    "AuthRepository",
    "OrganizationRepository"
]
