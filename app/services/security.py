"""
Security service for security-related operations.

Handles password hashing, token operations, rate limiting,
and other security utilities with proper security considerations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac
import re
from passlib.context import CryptContext
from jose import JWTError, jwt
import redis

from app.core.config import settings
from app.core.exceptions import SecurityError, ValidationError


class SecurityService:
    """
    Security service for security-related operations.
    
    Handles password hashing, token operations, rate limiting,
    and other security utilities with proper security considerations.
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            default="bcrypt",
            bcrypt__rounds=12,
            deprecated="auto"
        )
        
        # TODO: Add Redis-based rate limiting
        # TODO: Add IP-based security checks
        # TODO: Add device fingerprinting
        
        # Initialize rate limiting storage
        self._rate_limit_store = {}  # In production, use Redis
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
            
        Raises:
            SecurityError: If hashing fails
        """
        try:
            # TODO: Add password strength validation
            # TODO: Add password history check
            # TODO: Add pepper support
            
            return self.pwd_context.hash(password)
        except Exception as e:
            raise SecurityError(f"Password hashing failed: {str(e)}")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # TODO: Add proper logging
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            Secure random token
        """
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self) -> str:
        """
        Generate API key with prefix.
        
        Returns:
            API key with prefix
        """
        token = self.generate_secure_token(32)
        return f"sk_{token}"
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength and return detailed feedback.
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "score": 0,
            "issues": [],
            "suggestions": []
        }
        
        # Length check
        if len(password) < 8:
            result["issues"].append("Password must be at least 8 characters long")
            result["suggestions"].append("Use a longer password")
        elif len(password) < 12:
            result["score"] += 10
        else:
            result["score"] += 20
        
        # Character variety checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_upper:
            result["issues"].append("Password must contain uppercase letters")
            result["suggestions"].append("Add uppercase letters")
        else:
            result["score"] += 15
        
        if not has_lower:
            result["issues"].append("Password must contain lowercase letters")
            result["suggestions"].append("Add lowercase letters")
        else:
            result["score"] += 15
        
        if not has_digit:
            result["issues"].append("Password must contain numbers")
            result["suggestions"].append("Add numbers")
        else:
            result["score"] += 15
        
        if not has_special:
            result["issues"].append("Password must contain special characters")
            result["suggestions"].append("Add special characters")
        else:
            result["score"] += 15
        
        # Common password check
        if self._is_common_password(password):
            result["issues"].append("Password is too common")
            result["suggestions"].append("Choose a more unique password")
            result["score"] = max(0, result["score"] - 30)
        
        # Pattern checks
        if re.search(r"(.)\1{2,}", password):
            result["issues"].append("Password contains repeated characters")
            result["suggestions"].append("Avoid repeating characters")
            result["score"] = max(0, result["score"] - 10)
        
        if re.search(r"(012|123|234|345|456|567|678|789|890|987)", password):
            result["issues"].append("Password contains sequential numbers")
            result["suggestions"].append("Avoid sequential numbers")
            result["score"] = max(0, result["score"] - 10)
        
        # Keyboard patterns
        keyboard_patterns = ["qwerty", "asdf", "zxcv", "1234", "password"]
        password_lower = password.lower()
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                result["issues"].append("Password contains keyboard patterns")
                result["suggestions"].append("Avoid keyboard patterns")
                result["score"] = max(0, result["score"] - 20)
                break
        
        result["is_valid"] = len(result["issues"]) == 0
        result["strength"] = self._get_password_strength_level(result["score"])
        
        return result
    
    def _is_common_password(self, password: str) -> bool:
        """
        Check if password is in common password list.
        
        Args:
            password: Password to check
            
        Returns:
            True if common, False otherwise
        """
        # TODO: Use a more comprehensive common password list
        # TODO: Add data breach check integration
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master",
            "hello", "freedom", "whatever", "qazwsx", "trustno1",
            "123qwe", "1q2w3e4r", "abc123", "password1"
        ]
        
        return password.lower() in common_passwords
    
    def _get_password_strength_level(self, score: int) -> str:
        """
        Get password strength level based on score.
        
        Args:
            score: Password strength score
            
        Returns:
            Strength level (weak, fair, good, strong)
        """
        if score < 30:
            return "weak"
        elif score < 60:
            return "fair"
        elif score < 80:
            return "good"
        else:
            return "strong"
    
    def generate_csrf_token(self, session_id: str) -> str:
        """
        Generate CSRF token for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            CSRF token
        """
        # TODO: Use proper CSRF token generation
        # TODO: Add token expiration
        # TODO: Add token binding to session
        
        timestamp = str(int(datetime.utcnow().timestamp()))
        message = f"{session_id}:{timestamp}"
        
        # TODO: Use proper HMAC key from settings
        hmac_key = settings.SECRET_KEY.encode()
        
        token = hmac.new(
            hmac_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{token}:{timestamp}"
    
    def verify_csrf_token(self, session_id: str, token: str, max_age: int = 3600) -> bool:
        """
        Verify CSRF token.
        
        Args:
            session_id: Session identifier
            token: CSRF token to verify
            max_age: Maximum age in seconds
            
        Returns:
            True if valid, False otherwise
        """
        try:
            token_parts = token.split(":")
            if len(token_parts) != 2:
                return False
            
            csrf_hash, timestamp = token_parts
            
            # Check token age
            token_age = int(datetime.utcnow().timestamp()) - int(timestamp)
            if token_age > max_age:
                return False
            
            # Regenerate expected token
            expected_token = self.generate_csrf_token(session_id)
            expected_parts = expected_token.split(":")
            
            # Compare hashes (constant-time comparison)
            return hmac.compare_digest(csrf_hash, expected_parts[0])
            
        except Exception:
            # TODO: Add proper logging
            return False
    
    def is_rate_limited(
        self, 
        identifier: str, 
        action: str = "default",
        limit: int = 100,
        window: int = 3600
    ) -> bool:
        """
        Check if identifier is rate limited.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            action: Type of action (login, registration, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        try:
            now = datetime.utcnow()
            key = f"rate_limit:{action}:{identifier}"
            
            # Get current count
            current_data = self._rate_limit_store.get(key, {"count": 0, "reset_time": now})
            
            # Reset if window expired
            if now > current_data["reset_time"]:
                current_data = {"count": 1, "reset_time": now + timedelta(seconds=window)}
            else:
                current_data["count"] += 1
            
            # Store updated data
            self._rate_limit_store[key] = current_data
            
            return current_data["count"] > limit
            
        except Exception:
            # TODO: Add proper logging
            return False
    
    def get_rate_limit_info(
        self, 
        identifier: str, 
        action: str = "default"
    ) -> Dict[str, Any]:
        """
        Get rate limiting information.
        
        Args:
            identifier: Unique identifier
            action: Type of action
            
        Returns:
            Rate limiting information
        """
        try:
            key = f"rate_limit:{action}:{identifier}"
            current_data = self._rate_limit_store.get(key, {"count": 0, "reset_time": datetime.utcnow()})
            
            now = datetime.utcnow()
            remaining_requests = max(0, 100 - current_data["count"])
            reset_time = current_data["reset_time"]
            
            return {
                "is_limited": current_data["count"] >= 100,
                "current_count": current_data["count"],
                "remaining_requests": remaining_requests,
                "reset_time": reset_time.isoformat(),
                "reset_in_seconds": max(0, (reset_time - now).total_seconds())
            }
            
        except Exception:
            # TODO: Add proper logging
            return {}
    
    def sanitize_input(self, input_string: str, allow_html: bool = False) -> str:
        """
        Sanitize user input to prevent XSS and injection.
        
        Args:
            input_string: Input string to sanitize
            allow_html: Whether HTML is allowed
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return ""
        
        # TODO: Use proper HTML sanitization library
        # TODO: Add SQL injection prevention
        # TODO: Add XSS protection
        
        # Basic sanitization
        sanitized = input_string.strip()
        
        if not allow_html:
            # Remove HTML tags
            sanitized = re.sub(r'<[^>]*>', '', sanitized)
            # Escape HTML entities
            sanitized = sanitized.replace('&', '&amp;')
            sanitized = sanitized.replace('<', '&lt;')
            sanitized = sanitized.replace('>', '&gt;')
            sanitized = sanitized.replace('"', '&quot;')
            sanitized = sanitized.replace("'", '&#x27;')
        
        return sanitized
    
    def validate_email_format(self, email: str) -> bool:
        """
        Validate email format with comprehensive checks.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid format, False otherwise
        """
        # TODO: Use proper email validation library
        # TODO: Add domain validation
        # TODO: Add disposable email detection
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def is_disposable_email(self, email: str) -> bool:
        """
        Check if email is from disposable email provider.
        
        Args:
            email: Email address to check
            
        Returns:
            True if disposable, False otherwise
        """
        # TODO: Use comprehensive disposable email list
        # TODO: Add domain-based detection
        # TODO: Add MX record validation
        
        disposable_domains = [
            "10minutemail.com", "guerrillamail.com", "mailinator.com",
            "tempmail.org", "yopmail.com", "maildrop.cc"
        ]
        
        domain = email.split('@')[-1].lower() if '@' in email else ''
        return domain in disposable_domains
    
    def generate_device_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """
        Generate device fingerprint for security tracking.
        
        Args:
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            Device fingerprint
        """
        # TODO: Implement comprehensive device fingerprinting
        # TODO: Add canvas fingerprinting
        # TODO: Add WebGL fingerprinting
        
        # Basic fingerprint using user agent and IP
        fingerprint_data = f"{user_agent}:{ip_address}"
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def detect_suspicious_activity(
        self, 
        user_id: int, 
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect suspicious user activity patterns.
        
        Args:
            user_id: User ID
            action: Action performed
            context: Additional context
            
        Returns:
            Suspicion analysis result
        """
        # TODO: Implement machine learning-based detection
        # TODO: Add behavior analysis
        # TODO: Add location-based detection
        
        risk_score = 0
        risk_factors = []
        
        # Check for rapid successive actions
        if context.get("rapid_succession", False):
            risk_score += 30
            risk_factors.append("Rapid successive actions")
        
        # Check for unusual time patterns
        if context.get("unusual_time", False):
            risk_score += 20
            risk_factors.append("Unusual time pattern")
        
        # Check for location anomalies
        if context.get("location_anomaly", False):
            risk_score += 25
            risk_factors.append("Location anomaly")
        
        # Check for device changes
        if context.get("device_change", False):
            risk_score += 15
            risk_factors.append("Device change")
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        elif risk_score >= 10:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "requires_review": risk_level in ["medium", "high"],
            "recommended_actions": self._get_security_recommendations(risk_level)
        }
    
    def _get_security_recommendations(self, risk_level: str) -> List[str]:
        """
        Get security recommendations based on risk level.
        
        Args:
            risk_level: Risk level (minimal, low, medium, high)
            
        Returns:
            List of security recommendations
        """
        recommendations = {
            "minimal": [
                "Continue monitoring user activity",
                "Maintain current security settings"
            ],
            "low": [
                "Consider enabling two-factor authentication",
                "Review recent login locations"
            ],
            "medium": [
                "Require two-factor authentication",
                "Send security alert to user",
                "Review account activity logs"
            ],
            "high": [
                "Temporarily lock account",
                "Require manual review",
                "Force password reset",
                "Block suspicious IP addresses"
            ]
        }
        
        return recommendations.get(risk_level, recommendations["minimal"])
    
    def encrypt_sensitive_data(self, data: str, key: str = None) -> str:
        """
        Encrypt sensitive data for storage.
        
        Args:
            data: Data to encrypt
            key: Encryption key (uses default if None)
            
        Returns:
            Encrypted data
        """
        # TODO: Implement proper encryption (AES-256)
        # TODO: Add key rotation support
        # TODO: Add secure key storage
        
        encryption_key = key or settings.ENCRYPTION_KEY
        
        # Placeholder implementation - use proper encryption in production
        return f"encrypted:{hashlib.sha256((data + encryption_key).encode()).hexdigest()}"
    
    def decrypt_sensitive_data(self, encrypted_data: str, key: str = None) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Data to decrypt
            key: Decryption key (uses default if None)
            
        Returns:
            Decrypted data
        """
        # TODO: Implement proper decryption
        # TODO: Add error handling
        # TODO: Add integrity verification
        
        encryption_key = key or settings.ENCRYPTION_KEY
        
        # Placeholder implementation - use proper decryption in production
        if encrypted_data.startswith("encrypted:"):
            # This is a placeholder - implement proper decryption
            return "decrypted_data_placeholder"
        
        return encrypted_data
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup codes for two-factor authentication.
        
        Args:
            count: Number of codes to generate
            
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            codes.append(code)
        
        return codes
    
    def validate_backup_code(self, code: str) -> bool:
        """
        Validate backup code format.
        
        Args:
            code: Backup code to validate
            
        Returns:
            True if valid format, False otherwise
        """
        # TODO: Add more sophisticated validation
        # TODO: Add code expiration check
        
        if not code:
            return False
        
        # Check if code is 8 characters alphanumeric
        return len(code) == 8 and code.isalnum()
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key for storage.
        
        Args:
            api_key: API key to hash
            
        Returns:
            Hashed API key
        """
        # TODO: Use proper API key hashing
        # TODO: Add salt support
        
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_api_key(self, api_key: str, hashed_key: str) -> bool:
        """
        Validate API key against stored hash.
        
        Args:
            api_key: API key to validate
            hashed_key: Stored hashed key
            
        Returns:
            True if valid, False otherwise
        """
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(api_key_hash, hashed_key)
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired security data.
        
        Returns:
            Dictionary with cleanup counts
        """
        # TODO: Implement cleanup logic
        # TODO: Add automated cleanup scheduling
        
        return {
            "expired_tokens": 0,
            "old_rate_limits": 0,
            "expired_sessions": 0,
            "stale_fingerprints": 0
        }
