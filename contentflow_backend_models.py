# backend/app/models.py
"""
SQLAlchemy ORM models for ContentFlow.
Includes Content, ProcessingJob, and EmbeddingCache models.
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float, JSON, Enum, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, VECTOR
from sqlalchemy.orm import relationship

from app.database import Base
import enum


# ============================================================================
# ENUMS
# ============================================================================

class ProcessingStatusEnum(str, enum.Enum):
    """Status of a processing job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentTypeEnum(str, enum.Enum):
    """Types of generated content"""
    LINKEDIN_CAROUSEL = "linkedin_carousel"
    TWITTER_THREAD = "twitter_thread"
    BLOG_POST = "blog_post"
    INSTAGRAM_CAPTION = "instagram_caption"
    NEWSLETTER = "newsletter"


class ContentSourceEnum(str, enum.Enum):
    """Source of original content"""
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    ARTICLE = "article"
    TRANSCRIPT = "transcript"


# ============================================================================
# MODELS
# ============================================================================

class Content(Base):
    """
    Stores processed content and metadata.
    Links to source material and generated outputs.
    """
    __tablename__ = "contents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Source information
    source_type = Column(Enum(ContentSourceEnum), nullable=False)
    source_url = Column(String(2048), nullable=False)
    source_title = Column(String(512), nullable=True)
    source_metadata = Column(JSONB, default={})
    
    # Extracted content
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    key_points = Column(JSONB, default=[])
    summary = Column(Text, nullable=True)
    
    # Embeddings for semantic search
    embedding = Column(VECTOR(1536), nullable=True)  # OpenAI embedding dimension
    embedding_model = Column(String(255), nullable=True)
    
    # Generated outputs
    generated_content = Column(JSONB, default={})  # {content_type: {...}, ...}
    
    # Metadata
    processing_time_ms = Column(Integer, nullable=True)
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="content", cascade="all, delete-orphan")
    
    # Indexes for fast queries
    __table_args__ = (
        Index("ix_content_user_id", "user_id"),
        Index("ix_content_source_type", "source_type"),
        Index("ix_content_created_at", "created_at"),
        Index("ix_content_embedding", "embedding", postgresql_using="ivfflat", postgresql_with={"opclass": "vector_cosine_ops"}),
    )
    
    def __repr__(self):
        return f"<Content id={self.id} source={self.source_type}>"


class ProcessingJob(Base):
    """
    Tracks the status and progress of content processing.
    Used for job queue and real-time status updates.
    """
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.id"), nullable=False)
    
    # Processing information
    status = Column(Enum(ProcessingStatusEnum), default=ProcessingStatusEnum.PENDING, nullable=False)
    progress_percent = Column(Integer, default=0, nullable=False)
    current_step = Column(String(255), nullable=True)
    
    # Results
    output_content_types = Column(JSON, default=[])  # e.g., ["linkedin_carousel", "twitter_thread"]
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_time_remaining_seconds = Column(Integer, nullable=True)
    
    # Session tracking (for WebSocket)
    session_id = Column(String(255), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="processing_jobs")
    
    __table_args__ = (
        Index("ix_processing_job_status", "status"),
        Index("ix_processing_job_session_id", "session_id"),
    )
    
    def __repr__(self):
        return f"<ProcessingJob id={self.id} status={self.status}>"


class EmbeddingCache(Base):
    """
    Caches embeddings for content chunks to avoid recomputing.
    Improves performance when processing similar content.
    """
    __tablename__ = "embedding_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Content identifier
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    content_preview = Column(String(512), nullable=False)
    
    # Embedding
    embedding = Column(VECTOR(1536), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    
    # Metadata
    similarity_score = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_embedding_cache_content_hash", "content_hash"),
        Index("ix_embedding_cache_embedding", "embedding", postgresql_using="ivfflat"),
    )
    
    def __repr__(self):
        return f"<EmbeddingCache id={self.id} model={self.embedding_model}>"


class APIKey(Base):
    """
    Manages user API keys for programmatic access.
    """
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_name = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
    )
    
    def __repr__(self):
        return f"<APIKey user={self.user_id}>"


class AuditLog(Base):
    """
    Audit trail for important actions (deletion, sharing, etc.)
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)  # create, update, delete, share
    resource_type = Column(String(50), nullable=False)  # content, api_key
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    details = Column(JSONB, default={})
    ip_address = Column(String(45), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<AuditLog action={self.action} resource={self.resource_type}>"
