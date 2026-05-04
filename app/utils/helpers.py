"""
General helper utilities.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string."""
    return dt.isoformat()


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse ISO format datetime string."""
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def add_days(days: int) -> datetime:
    """Get datetime X days from now."""
    return datetime.utcnow() + timedelta(days=days)
