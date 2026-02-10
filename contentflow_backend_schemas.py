# backend/app/schemas.py
"""
Pydantic models for request/response validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, validator


# ============================================================================
# ENUMS
# ============================================================================

class ProcessingStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentTypeEnum(str, Enum):
    LINKEDIN_CAROUSEL = "linkedin_carousel"
    TWITTER_THREAD = "twitter_thread"
    BLOG_POST = "blog_post"
    INSTAGRAM_CAPTION = "instagram_caption"
    NEWSLETTER = "newsletter"


class ContentSourceEnum(str, Enum):
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    ARTICLE = "article"
    TRANSCRIPT = "transcript"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ContentGenerationRequest(BaseModel):
    """Request to generate content from a source"""
    
    source_url: str = Field(..., description="URL of the source (YouTube, article, etc.)")
    source_type: ContentSourceEnum = Field(..., description="Type of source")
    
    content_types: List[ContentTypeEnum] = Field(
        default=[ContentTypeEnum.LINKEDIN_CAROUSEL, ContentTypeEnum.TWITTER_THREAD],
        description="Types of content to generate"
    )
    
    tone: Optional[str] = Field(
        default="professional",
        description="Tone of generated content (professional, casual, inspirational)"
    )
    
    target_audience: Optional[str] = Field(
        default=None,
        description="Target audience (e.g., 'marketing professionals')"
    )
    
    include_hashtags: bool = Field(default=True, description="Include hashtags")
    include_emojis: bool = Field(default=False, description="Include emojis")
    language: str = Field(default="en", description="Output language (ISO 639-1 code)")
    
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Custom instructions for content generation"
    )
    
    @validator("source_url")
    def validate_source_url(cls, v):
        """Validate that source_url is a valid URL"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Source URL must start with http:// or https://")
        return v


class ContentExportRequest(BaseModel):
    """Request to export generated content"""
    
    content_id: UUID = Field(..., description="ID of the content to export")
    format: str = Field(default="json", description="Export format (json, csv, markdown)")
    include_metadata: bool = Field(default=True, description="Include metadata in export")


class BatchProcessingRequest(BaseModel):
    """Request to process multiple URLs"""
    
    urls: List[str] = Field(..., description="List of source URLs")
    source_type: ContentSourceEnum = Field(..., description="Type of source")
    content_types: List[ContentTypeEnum] = Field(default=[ContentTypeEnum.LINKEDIN_CAROUSEL])
    
    class Config:
        max_items = 10


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ProcessingJobResponse(BaseModel):
    """Response for a processing job"""
    
    id: UUID
    content_id: UUID
    status: ProcessingStatusEnum
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: Optional[str] = None
    estimated_time_remaining_seconds: Optional[int] = None
    
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class GeneratedContentItem(BaseModel):
    """A single piece of generated content"""
    
    content_type: ContentTypeEnum
    title: Optional[str] = None
    body: str
    
    # Platform-specific
    hashtags: Optional[List[str]] = None
    call_to_action: Optional[str] = None
    
    # Metadata
    character_count: int
    estimated_engagement: Optional[float] = None
    
    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    """Full response for processed content"""
    
    id: UUID
    user_id: str
    
    # Source
    source_type: ContentSourceEnum
    source_url: str
    source_title: Optional[str] = None
    
    # Extracted content
    summary: Optional[str] = None
    key_points: List[str]
    
    # Generated content
    generated_content: Dict[str, Any] = {}
    
    # Metadata
    processing_time_ms: Optional[int] = None
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    cost_usd: Optional[float] = None
    
    is_public: bool = False
    
    created_at: datetime
    updated_at: datetime
    
    # Related
    processing_job: Optional[ProcessingJobResponse] = None
    
    class Config:
        from_attributes = True


class ContentListResponse(BaseModel):
    """List of contents with pagination"""
    
    items: List[ContentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Error response format"""
    
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check response"""
    
    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    """Common pagination parameters"""
    
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum items to return")
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc, desc)")


# ============================================================================
# STATISTICS & ANALYTICS
# ============================================================================

class ContentStatistics(BaseModel):
    """Statistics about generated content"""
    
    total_processed: int
    total_tokens_used: int
    total_cost_usd: float
    average_processing_time_ms: float
    
    by_content_type: Dict[str, int]
    by_source_type: Dict[str, int]
    
    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    
    type: str = Field(..., description="Message type (status, progress, error, complete)")
    data: Dict[str, Any] = Field(default={}, description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
