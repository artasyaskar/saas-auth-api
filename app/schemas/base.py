"""
Base schemas for common API patterns.

Provides reusable base models for responses,
pagination, and common API patterns.
"""

from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """
    Base response model.
    
    Provides a standard response structure with
    optional data, message, and metadata.
    """
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    
    Standardizes pagination across all list endpoints.
    """
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Items per page (1-100)")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response model.
    
    Standardizes paginated responses with metadata.
    """
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether next page exists")
    has_prev: bool = Field(..., description="Whether previous page exists")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        size: int
    ) -> "PaginatedResponse[T]":
        """
        Create paginated response from raw data.
        
        Args:
            items: List of items
            total: Total number of items
            page: Current page number
            size: Items per page
            
        Returns:
            PaginatedResponse instance
        """
        pages = (total + size - 1) // size if total > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    Provides consistent error response format.
    """
    success: bool = False
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")


class ValidationErrorResponse(BaseModel):
    """
    Validation error response model.
    
    Used for field validation errors.
    """
    success: bool = False
    error: str = Field("validation_error", description="Error type")
    message: str = Field("Validation failed", description="Error message")
    field_errors: Dict[str, List[str]] = Field(..., description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")


class HealthResponse(BaseModel):
    """
    Health check response model.
    
    Standardizes health check responses.
    """
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    checks: Optional[Dict[str, Any]] = Field(None, description="Detailed health checks")


class MetricsResponse(BaseModel):
    """
    Metrics response model.
    
    Used for metrics and monitoring endpoints.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: Dict[str, Any] = Field(..., description="Metrics data")
    labels: Optional[Dict[str, str]] = Field(None, description="Metric labels")


class BulkOperationResponse(BaseModel):
    """
    Bulk operation response model.
    
    Used for bulk create/update/delete operations.
    """
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    total_count: int = Field(..., description="Total number of operations")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed error information")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100


class FileUploadResponse(BaseModel):
    """
    File upload response model.
    
    Standardizes file upload responses.
    """
    filename: str = Field(..., description="Original filename")
    file_id: str = Field(..., description="File identifier")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    url: Optional[str] = Field(None, description="File URL")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class SearchParams(BaseModel):
    """
    Search parameters for search endpoints.
    
    Standardizes search functionality.
    """
    q: str = Field(..., min_length=1, max_length=100, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    pagination: PaginationParams = Field(default_factory=PaginationParams)


class ExportParams(BaseModel):
    """
    Export parameters for data export endpoints.
    
    Standardizes export functionality.
    """
    format: str = Field("json", regex="^(json|csv|xlsx)$", description="Export format")
    fields: Optional[List[str]] = Field(None, description="Fields to include")
    filters: Optional[Dict[str, Any]] = Field(None, description="Export filters")
    date_from: Optional[datetime] = Field(None, description="Start date")
    date_to: Optional[datetime] = Field(None, description="End date")


class NotificationResponse(BaseModel):
    """
    Notification response model.
    
    Used for real-time notifications.
    """
    id: str = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = Field(None, description="When notification was read")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
