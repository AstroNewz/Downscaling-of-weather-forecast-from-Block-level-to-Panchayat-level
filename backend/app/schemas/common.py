from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard unified response envelope for all API endpoints."""
    success: bool = Field(default=True, description="Indicates if the operation was successful")
    message: str = Field(default="Operation completed successfully", description="User-friendly message")
    data: Optional[T] = Field(default=None, description="Payload data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of response")

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Detailed error object."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(default=None, description="Optional diagnostic context")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = Field(default=False)
    error: ErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    """Standard query parameters for pagination."""
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard envelope for paginated result sets."""
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)
