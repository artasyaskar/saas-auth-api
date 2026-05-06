"""
Enterprise timezone handling utilities.

Provides comprehensive timezone management with support for:
- UTC and timezone conversion
- Database timezone handling
- API timezone serialization
- User-specific timezone preferences
- Daylight saving time handling
- Timezone validation and normalization
- Consistent datetime operations across services
"""

import pytz
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass
from enum import Enum
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TimezoneType(Enum):
    """Timezone type enumeration."""
    UTC = "utc"
    USER_LOCAL = "user_local"
    SYSTEM = "system"
    DATABASE = "database"
    API_DEFAULT = "api_default"


@dataclass
class TimezoneConfig:
    """Timezone configuration."""
    default_timezone: str = "UTC"
    database_timezone: str = "UTC"
    api_timezone: str = "UTC"
    enable_user_timezones: bool = True
    auto_detect_user_timezone: bool = False
    validate_timezone_inputs: bool = True
    serialize_as_utc: bool = True
    daylight_saving_handling: bool = True


class TimezoneUtils:
    """
    Enterprise timezone utilities for consistent datetime handling.
    
    Features:
    - UTC and timezone conversion
    - Database timezone handling
    - API timezone serialization
    - User-specific timezone preferences
    - Daylight saving time handling
    - Timezone validation and normalization
    - Consistent datetime operations across services
    """
    
    def __init__(self, config: Optional[TimezoneConfig] = None):
        self.config = config or TimezoneConfig()
        self._timezone_cache: Dict[str, pytz.BaseTzInfo] = {}
        self._load_common_timezones()
    
    def _load_common_timezones(self) -> None:
        """Load commonly used timezones into cache."""
        common_timezones = [
            "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
            "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome",
            "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Asia/Dubai",
            "Australia/Sydney", "Australia/Melbourne",
            "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
            "America/Toronto", "America/Vancouver", "America/Mexico_City",
            "America/Sao_Paulo", "America/Buenos_Aires",
            "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos"
        ]
        
        for tz_name in common_timezones:
            try:
                self._timezone_cache[tz_name] = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {tz_name}")
    
    def get_timezone(self, tz_name: str) -> Optional[pytz.BaseTzInfo]:
        """
        Get timezone object with caching.
        
        Args:
            tz_name: Timezone name
            
        Returns:
            Timezone object or None if invalid
        """
        if not tz_name:
            return None
        
        # Check cache first
        if tz_name in self._timezone_cache:
            return self._timezone_cache[tz_name]
        
        # Try to load timezone
        try:
            tz = pytz.timezone(tz_name)
            self._timezone_cache[tz_name] = tz
            return tz
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {tz_name}")
            return None
    
    def validate_timezone(self, tz_name: str) -> bool:
        """
        Validate timezone name.
        
        Args:
            tz_name: Timezone name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not tz_name:
            return False
        
        try:
            pytz.timezone(tz_name)
            return True
        except pytz.UnknownTimeZoneError:
            return False
    
    def normalize_timezone(self, tz_name: str) -> str:
        """
        Normalize timezone name.
        
        Args:
            tz_name: Timezone name to normalize
            
        Returns:
            Normalized timezone name
        """
        if not tz_name:
            return self.config.default_timezone
        
        # Handle common aliases
        timezone_aliases = {
            "UTC": "UTC",
            "GMT": "UTC",
            "Z": "UTC",
            "EST": "US/Eastern",
            "EDT": "US/Eastern",
            "CST": "US/Central",
            "CDT": "US/Central",
            "MST": "US/Mountain",
            "MDT": "US/Mountain",
            "PST": "US/Pacific",
            "PDT": "US/Pacific"
        }
        
        normalized = timezone_aliases.get(tz_name.upper(), tz_name)
        
        # Validate the normalized timezone
        if self.validate_timezone(normalized):
            return normalized
        
        # Fallback to default
        logger.warning(f"Invalid timezone '{tz_name}', falling back to '{self.config.default_timezone}'")
        return self.config.default_timezone
    
    def to_utc(self, dt: datetime, source_tz: Optional[str] = None) -> datetime:
        """
        Convert datetime to UTC.
        
        Args:
            dt: Datetime to convert
            source_tz: Source timezone (if dt is naive)
            
        Returns:
            UTC datetime
        """
        if dt.tzinfo is None:
            # Naive datetime, assume source timezone
            if source_tz:
                tz = self.get_timezone(source_tz)
                if tz:
                    dt = tz.localize(dt)
                else:
                    # Fallback to UTC
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                # Assume UTC for naive datetime
                dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to UTC
        return dt.astimezone(timezone.utc)
    
    def from_utc(self, dt: datetime, target_tz: str) -> datetime:
        """
        Convert UTC datetime to target timezone.
        
        Args:
            dt: UTC datetime
            target_tz: Target timezone name
            
        Returns:
            Datetime in target timezone
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        tz = self.get_timezone(target_tz)
        if not tz:
            logger.warning(f"Invalid target timezone: {target_tz}, returning UTC")
            return dt
        
        return dt.astimezone(tz)
    
    def convert_timezone(
        self,
        dt: datetime,
        source_tz: str,
        target_tz: str
    ) -> datetime:
        """
        Convert datetime from source to target timezone.
        
        Args:
            dt: Datetime to convert
            source_tz: Source timezone name
            target_tz: Target timezone name
            
        Returns:
            Datetime in target timezone
        """
        # Get timezone objects
        source_tz_obj = self.get_timezone(source_tz)
        target_tz_obj = self.get_timezone(target_tz)
        
        if not source_tz_obj or not target_tz_obj:
            logger.error(f"Invalid timezone conversion: {source_tz} -> {target_tz}")
            return dt
        
        # Ensure datetime has source timezone info
        if dt.tzinfo is None:
            dt = source_tz_obj.localize(dt)
        
        # Convert to target timezone
        return dt.astimezone(target_tz_obj)
    
    def now_utc(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)
    
    def now_in_timezone(self, tz_name: str) -> datetime:
        """
        Get current datetime in specific timezone.
        
        Args:
            tz_name: Timezone name
            
        Returns:
            Current datetime in timezone
        """
        tz = self.get_timezone(tz_name)
        if not tz:
            logger.warning(f"Invalid timezone: {tz_name}, returning UTC")
            return self.now_utc()
        
        return datetime.now(tz)
    
    def parse_datetime(
        self,
        dt_str: str,
        format_str: str,
        timezone: Optional[str] = None
    ) -> datetime:
        """
        Parse datetime string with timezone handling.
        
        Args:
            dt_str: Datetime string to parse
            format_str: Format string for parsing
            timezone: Timezone to apply (if not in string)
            
        Returns:
            Parsed datetime
        """
        try:
            dt = datetime.strptime(dt_str, format_str)
            
            if timezone:
                tz = self.get_timezone(timezone)
                if tz:
                    dt = tz.localize(dt)
                else:
                    dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
        except ValueError as e:
            logger.error(f"Failed to parse datetime '{dt_str}': {str(e)}")
            raise ValueError(f"Invalid datetime format: {str(e)}")
    
    def format_datetime(
        self,
        dt: datetime,
        format_str: str,
        timezone: Optional[str] = None,
        as_utc: Optional[bool] = None
    ) -> str:
        """
        Format datetime with timezone handling.
        
        Args:
            dt: Datetime to format
            format_str: Format string
            timezone: Timezone to use for formatting
            as_utc: Force UTC formatting
            
        Returns:
            Formatted datetime string
        """
        # Handle timezone conversion
        if as_utc or self.config.serialize_as_utc:
            dt = self.to_utc(dt)
        elif timezone:
            dt = self.from_utc(dt, timezone)
        
        return dt.strftime(format_str)
    
    def to_database_timezone(self, dt: datetime) -> datetime:
        """
        Convert datetime to database timezone.
        
        Args:
            dt: Datetime to convert
            
        Returns:
            Datetime in database timezone
        """
        return self.from_utc(self.to_utc(dt), self.config.database_timezone)
    
    def from_database_timezone(self, dt: datetime) -> datetime:
        """
        Convert datetime from database timezone.
        
        Args:
            dt: Datetime from database
            
        Returns:
            UTC datetime
        """
        return self.to_utc(dt, self.config.database_timezone)
    
    def to_api_timezone(self, dt: datetime) -> datetime:
        """
        Convert datetime to API timezone.
        
        Args:
            dt: Datetime to convert
            
        Returns:
            Datetime in API timezone
        """
        return self.from_utc(self.to_utc(dt), self.config.api_timezone)
    
    def from_api_timezone(self, dt: datetime) -> datetime:
        """
        Convert datetime from API timezone.
        
        Args:
            dt: Datetime from API
            
        Returns:
            UTC datetime
        """
        return self.to_utc(dt, self.config.api_timezone)
    
    def get_user_local_time(
        self,
        dt: datetime,
        user_timezone: Optional[str] = None
    ) -> datetime:
        """
        Get datetime in user's local timezone.
        
        Args:
            dt: Datetime to convert
            user_timezone: User's preferred timezone
            
        Returns:
            Datetime in user's local timezone
        """
        if not self.config.enable_user_timezones:
            return dt
        
        if not user_timezone:
            # Try to auto-detect if enabled
            if self.config.auto_detect_user_timezone:
                user_timezone = self._detect_user_timezone()
            else:
                user_timezone = self.config.default_timezone
        
        return self.from_utc(self.to_utc(dt), user_timezone)
    
    def _detect_user_timezone(self) -> str:
        """
        Detect user's timezone (simplified implementation).
        
        Returns:
            Detected timezone name
        """
        # This is a simplified implementation
        # In production, this would use client IP geolocation or browser timezone
        try:
            import locale
            tz_name = time.tzname[0] if time.tzname else self.config.default_timezone
            return self.normalize_timezone(tz_name)
        except Exception:
            return self.config.default_timezone
    
    def is_daylight_saving_time(self, dt: datetime, timezone: str) -> bool:
        """
        Check if datetime is in daylight saving time.
        
        Args:
            dt: Datetime to check
            timezone: Timezone name
            
        Returns:
            True if in DST, False otherwise
        """
        if not self.config.daylight_saving_handling:
            return False
        
        tz = self.get_timezone(timezone)
        if not tz:
            return False
        
        # Ensure datetime has timezone info
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        
        return dt.dst() is not None and dt.dst().total_seconds() > 0
    
    def get_timezone_offset(self, dt: datetime, timezone: str) -> timedelta:
        """
        Get timezone offset for datetime.
        
        Args:
            dt: Datetime to check
            timezone: Timezone name
            
        Returns:
            Timezone offset
        """
        tz = self.get_timezone(timezone)
        if not tz:
            return timedelta(0)
        
        # Ensure datetime has timezone info
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        
        return dt.utcoffset() or timedelta(0)
    
    def get_timezone_info(self, timezone: str) -> Dict[str, Any]:
        """
        Get comprehensive timezone information.
        
        Args:
            timezone: Timezone name
            
        Returns:
            Timezone information dictionary
        """
        tz = self.get_timezone(timezone)
        if not tz:
            return {"error": f"Unknown timezone: {timezone}"}
        
        now = datetime.now(tz)
        
        return {
            "name": timezone,
            "display_name": str(tz),
            "current_time": now.isoformat(),
            "utc_offset": str(now.utcoffset()),
            "dst_active": now.dst() is not None and now.dst().total_seconds() > 0,
            "dst_offset": str(now.dst()) if now.dst() else None,
            "raw_offset": now.utcoffset().total_seconds() if now.utcoffset() else 0
        }
    
    def get_available_timezones(self, region: Optional[str] = None) -> List[str]:
        """
        Get list of available timezones.
        
        Args:
            region: Filter by region (e.g., 'US', 'Europe', 'Asia')
            
        Returns:
            List of timezone names
        """
        all_timezones = pytz.all_timezones
        
        if region:
            filtered_timezones = [
                tz for tz in all_timezones
                if tz.startswith(f"{region}/")
            ]
            return sorted(filtered_timezones)
        
        return sorted(all_timezones)
    
    def get_common_timezones(self) -> List[Dict[str, Any]]:
        """
        Get list of commonly used timezones with metadata.
        
        Returns:
            List of timezone information
        """
        common_tz = [
            {"name": "UTC", "display": "UTC (Coordinated Universal Time)", "offset": "+00:00"},
            {"name": "US/Eastern", "display": "Eastern Time (US & Canada)", "offset": "-05:00"},
            {"name": "US/Central", "display": "Central Time (US & Canada)", "offset": "-06:00"},
            {"name": "US/Mountain", "display": "Mountain Time (US & Canada)", "offset": "-07:00"},
            {"name": "US/Pacific", "display": "Pacific Time (US & Canada)", "offset": "-08:00"},
            {"name": "Europe/London", "display": "London", "offset": "+00:00"},
            {"name": "Europe/Paris", "display": "Paris", "offset": "+01:00"},
            {"name": "Europe/Berlin", "display": "Berlin", "offset": "+01:00"},
            {"name": "Asia/Tokyo", "display": "Tokyo", "offset": "+09:00"},
            {"name": "Asia/Shanghai", "display": "Shanghai", "offset": "+08:00"},
            {"name": "Australia/Sydney", "display": "Sydney", "offset": "+10:00"}
        ]
        
        return common_tz
    
    def add_timezone_offset(self, dt: datetime, offset_hours: Union[int, float]) -> datetime:
        """
        Add timezone offset to datetime.
        
        Args:
            dt: Base datetime
            offset_hours: Hours to offset (can be negative)
            
        Returns:
            Datetime with offset applied
        """
        return dt + timedelta(hours=offset_hours)
    
    def get_iso_format(self, dt: datetime, timezone: Optional[str] = None) -> str:
        """
        Get ISO 8601 formatted datetime string.
        
        Args:
            dt: Datetime to format
            timezone: Timezone to use
            
        Returns:
            ISO 8601 formatted string
        """
        if timezone:
            dt = self.from_utc(self.to_utc(dt), timezone)
        elif self.config.serialize_as_utc:
            dt = self.to_utc(dt)
        
        return dt.isoformat()
    
    def get_user_friendly_time(self, dt: datetime, user_timezone: Optional[str] = None) -> Dict[str, str]:
        """
        Get user-friendly time representation.
        
        Args:
            dt: Datetime to format
            user_timezone: User's timezone
            
        Returns:
            Dictionary with various time formats
        """
        local_dt = self.get_user_local_time(dt, user_timezone)
        
        return {
            "iso": self.get_iso_format(local_dt),
            "rfc2822": local_dt.strftime("%a, %d %b %Y %H:%M:%S %z"),
            "short_date": local_dt.strftime("%m/%d/%Y"),
            "long_date": local_dt.strftime("%B %d, %Y"),
            "short_time": local_dt.strftime("%I:%M %p"),
            "long_time": local_dt.strftime("%I:%M:%S %p %Z"),
            "datetime": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "relative": self._get_relative_time(dt)
        }
    
    def _get_relative_time(self, dt: datetime) -> str:
        """Get relative time string (simplified)."""
        now = self.now_utc()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def validate_datetime_range(
        self,
        start_dt: datetime,
        end_dt: datetime,
        timezone: Optional[str] = None
    ) -> bool:
        """
        Validate datetime range.
        
        Args:
            start_dt: Start datetime
            end_dt: End datetime
            timezone: Timezone for validation
            
        Returns:
            True if valid range, False otherwise
        """
        # Convert to UTC for comparison
        if timezone:
            start_utc = self.to_utc(start_dt, timezone)
            end_utc = self.to_utc(end_dt, timezone)
        else:
            start_utc = self.to_utc(start_dt)
            end_utc = self.to_utc(end_dt)
        
        return start_utc < end_utc
    
    def get_timezone_abbreviation(self, dt: datetime, timezone: str) -> str:
        """
        Get timezone abbreviation for datetime.
        
        Args:
            dt: Datetime to check
            timezone: Timezone name
            
        Returns:
            Timezone abbreviation
        """
        tz = self.get_timezone(timezone)
        if not tz:
            return "UTC"
        
        # Ensure datetime has timezone info
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        
        return dt.tzname() or "UTC"


# Global timezone utilities instance
timezone_utils = TimezoneUtils()


def get_timezone(tz_name: str) -> Optional[pytz.BaseTzInfo]:
    """Get timezone object."""
    return timezone_utils.get_timezone(tz_name)


def validate_timezone(tz_name: str) -> bool:
    """Validate timezone name."""
    return timezone_utils.validate_timezone(tz_name)


def to_utc(dt: datetime, source_tz: Optional[str] = None) -> datetime:
    """Convert datetime to UTC."""
    return timezone_utils.to_utc(dt, source_tz)


def from_utc(dt: datetime, target_tz: str) -> datetime:
    """Convert UTC datetime to target timezone."""
    return timezone_utils.from_utc(dt, target_tz)


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return timezone_utils.now_utc()


def to_database_timezone(dt: datetime) -> datetime:
    """Convert datetime to database timezone."""
    return timezone_utils.to_database_timezone(dt)


def from_database_timezone(dt: datetime) -> datetime:
    """Convert datetime from database timezone."""
    return timezone_utils.from_database_timezone(dt)


def get_iso_format(dt: datetime, timezone: Optional[str] = None) -> str:
    """Get ISO 8601 formatted datetime."""
    return timezone_utils.get_iso_format(dt, timezone)


def get_user_friendly_time(dt: datetime, user_timezone: Optional[str] = None) -> Dict[str, str]:
    """Get user-friendly time representation."""
    return timezone_utils.get_user_friendly_time(dt, user_timezone)
