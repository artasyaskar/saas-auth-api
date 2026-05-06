"""
Validation utilities for common validation patterns.

Provides reusable validation functions for email,
password, and other common data validation needs.
"""

import re
from typing import Optional, List, Dict, Any
from datetime import timezone, datetime


class ValidationError(Exception):
    """Custom validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, errors: Optional[List[str]] = None):
        self.message = message
        self.field = field
        self.errors = errors or []
        super().__init__(message)


class EmailValidator:
    """Email validation utilities."""
    
    # Standard email regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def validate(cls, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        # Ensure single @ symbol
        if email.count('@') != 1:
            return False
        
        # Check against regex pattern
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_with_details(cls, email: str) -> Dict[str, Any]:
        """
        Validate email with detailed error information.
        
        Args:
            email: Email address to validate
            
        Returns:
            Validation result with details
        """
        result = {
            "is_valid": True,
            "errors": []
        }
        
        if not email:
            result["is_valid"] = False
            result["errors"].append("Email is required")
            return result
        
        if not isinstance(email, str):
            result["is_valid"] = False
            result["errors"].append("Email must be a string")
            return result
        
        # Check length
        if len(email) > 254:
            result["is_valid"] = False
            result["errors"].append("Email is too long (max 254 characters)")
        
        # Check for single @ symbol
        if email.count('@') != 1:
            result["is_valid"] = False
            result["errors"].append("Email must contain exactly one @ symbol")
            return result
        
        # Check against regex pattern
        if not cls.EMAIL_PATTERN.match(email):
            result["is_valid"] = False
            result["errors"].append("Email format is invalid")
        
        return result


class PasswordValidator:
    """Password validation utilities."""
    
    @classmethod
    def validate_strength(cls, password: str, requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate password strength against requirements.
        
        Args:
            password: Password to validate
            requirements: Password requirements configuration
            
        Returns:
            Password strength validation result
        """
        # Default requirements
        default_requirements = {
            "min_length": 8,
            "max_length": 128,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_symbols": True,
            "forbidden_patterns": ["password", "123456", "qwerty"]
        }
        
        if requirements:
            default_requirements.update(requirements)
        
        result = {
            "is_valid": True,
            "strength": "weak",
            "errors": [],
            "suggestions": []
        }
        
        if not password:
            result["is_valid"] = False
            result["errors"].append("Password is required")
            return result
        
        # Check length
        if len(password) < default_requirements["min_length"]:
            result["is_valid"] = False
            result["errors"].append(f"Password must be at least {default_requirements['min_length']} characters")
        
        if len(password) > default_requirements["max_length"]:
            result["is_valid"] = False
            result["errors"].append(f"Password must be less than {default_requirements['max_length']} characters")
        
        # Check character requirements
        if default_requirements["require_uppercase"] and not re.search(r'[A-Z]', password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one uppercase letter")
        
        if default_requirements["require_lowercase"] and not re.search(r'[a-z]', password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one lowercase letter")
        
        if default_requirements["require_numbers"] and not re.search(r'\d', password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one number")
        
        if default_requirements["require_symbols"] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one special character")
        
        # Check forbidden patterns
        password_lower = password.lower()
        for pattern in default_requirements["forbidden_patterns"]:
            if pattern in password_lower:
                result["is_valid"] = False
                result["errors"].append(f"Password cannot contain '{pattern}'")
        
        # Calculate strength
        if result["is_valid"]:
            strength_score = cls._calculate_strength_score(password)
            if strength_score >= 4:
                result["strength"] = "strong"
            elif strength_score >= 3:
                result["strength"] = "medium"
            else:
                result["strength"] = "weak"
        
        # Add suggestions
        if result["strength"] == "weak":
            result["suggestions"].extend([
                "Use a longer password",
                "Include a mix of character types",
                "Avoid common patterns"
            ])
        
        return result
    
    @classmethod
    def _calculate_strength_score(cls, password: str) -> int:
        """Calculate password strength score."""
        score = 0
        
        # Length contribution
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        
        # Character variety
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        
        return score


class TokenValidator:
    """Token validation utilities."""
    
    @classmethod
    def validate_jwt_format(cls, token: str) -> bool:
        """
        Validate JWT token format.
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not token or not isinstance(token, str):
            return False
        
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        return len(parts) == 3
    
    @classmethod
    def validate_token_expiration(cls, exp_timestamp: float) -> bool:
        """
        Validate token expiration timestamp.
        
        Args:
            exp_timestamp: Expiration timestamp
            
        Returns:
            True if not expired, False if expired
        """
        try:
            from datetime import timezone
            exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            return current_time < exp_time
        except (ValueError, OSError):
            return False


class PhoneNumberValidator:
    """Phone number validation utilities."""
    
    # Basic international phone number pattern
    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')
    
    @classmethod
    def validate(cls, phone: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not phone or not isinstance(phone, str):
            return False
        
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        return bool(cls.PHONE_PATTERN.match(cleaned))
    
    @classmethod
    def normalize(cls, phone: str) -> str:
        """
        Normalize phone number format.
        
        Args:
            phone: Phone number to normalize
            
        Returns:
            Normalized phone number
        """
        if not phone:
            return ""
        
        # Remove formatting characters
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Add + if missing for international numbers
        if cleaned and not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        
        return cleaned


class URLValidator:
    """URL validation utilities."""
    
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    @classmethod
    def validate(cls, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        return bool(cls.URL_PATTERN.match(url))


class UsernameValidator:
    """Username validation utilities."""
    
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    
    @classmethod
    def validate(cls, username: str) -> Dict[str, Any]:
        """
        Validate username format.
        
        Args:
            username: Username to validate
            
        Returns:
            Validation result with details
        """
        result = {
            "is_valid": True,
            "errors": []
        }
        
        if not username:
            result["is_valid"] = False
            result["errors"].append("Username is required")
            return result
        
        if not isinstance(username, str):
            result["is_valid"] = False
            result["errors"].append("Username must be a string")
            return result
        
        # Check length
        if len(username) < 3:
            result["is_valid"] = False
            result["errors"].append("Username must be at least 3 characters")
        
        if len(username) > 30:
            result["is_valid"] = False
            result["errors"].append("Username must be less than 30 characters")
        
        # Check pattern
        if not cls.USERNAME_PATTERN.match(username):
            result["is_valid"] = False
            result["errors"].append("Username can only contain letters, numbers, underscores, and hyphens")
        
        # Check for reserved usernames
        reserved_usernames = ['admin', 'root', 'system', 'api', 'www', 'mail', 'ftp']
        if username.lower() in reserved_usernames:
            result["is_valid"] = False
            result["errors"].append("Username is reserved")
        
        return result


class CommonValidator:
    """Common validation utilities."""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """
        Validate required fields in data.
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Returns:
            List of missing field names
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)
        
        return missing_fields
    
    @staticmethod
    def validate_field_length(value: str, min_length: int = 0, max_length: int = None) -> List[str]:
        """
        Validate field length.
        
        Args:
            value: Value to validate
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(value, str):
            errors.append("Field must be a string")
            return errors
        
        if len(value) < min_length:
            errors.append(f"Field must be at least {min_length} characters")
        
        if max_length and len(value) > max_length:
            errors.append(f"Field must be less than {max_length} characters")
        
        return errors
    
    @staticmethod
    def validate_numeric_range(value: Any, min_value: float = None, max_value: float = None) -> List[str]:
        """
        Validate numeric range.
        
        Args:
            value: Value to validate
            min_value: Minimum value
            max_value: Maximum value
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            errors.append("Field must be a number")
            return errors
        
        if min_value is not None and numeric_value < min_value:
            errors.append(f"Field must be at least {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            errors.append(f"Field must be less than {max_value}")
        
        return errors
    
    @staticmethod
    def sanitize_string(value: str, allow_html: bool = False) -> str:
        """
        Sanitize string input.
        
        Args:
            value: String to sanitize
            allow_html: Whether to allow HTML tags
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return ""
        
        # Basic sanitization
        sanitized = value.strip()
        
        if not allow_html:
            # Remove HTML tags
            sanitized = re.sub(r'<[^>]+>', '', sanitized)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        return sanitized
