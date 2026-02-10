# backend/app/config.py
"""
Configuration management using Pydantic Settings.
Load from environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    APP_NAME: str = "ContentFlow"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://contentflow:password@localhost:5432/contentflow_db",
        env="DATABASE_URL"
    )
    SQLALCHEMY_ECHO: bool = Field(default=False, env="SQLALCHEMY_ECHO")
    
    # ========================================================================
    # VECTOR DATABASE (Chroma or equivalent)
    # ========================================================================
    VECTOR_DB_PATH: str = Field(default="./chroma_data", env="VECTOR_DB_PATH")
    VECTOR_DB_TYPE: str = Field(default="chroma", env="VECTOR_DB_TYPE")  # chroma, pinecone, etc.
    VECTOR_EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="VECTOR_EMBEDDING_MODEL"
    )
    
    # ========================================================================
    # AI/LLM CONFIGURATION
    # ========================================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    MODEL_MAIN: str = Field(default="gpt-4-turbo-preview", env="MODEL_MAIN")
    MODEL_FAST: str = Field(default="gpt-3.5-turbo", env="MODEL_FAST")
    MODEL_VISION: str = Field(default="gpt-4-vision-preview", env="MODEL_VISION")
    TEMPERATURE: float = Field(default=0.7, env="TEMPERATURE")
    MAX_TOKENS: int = Field(default=2000, env="MAX_TOKENS")
    
    # ========================================================================
    # EXTERNAL SERVICES
    # ========================================================================
    YOUTUBE_API_KEY: Optional[str] = Field(default=None, env="YOUTUBE_API_KEY")
    YT_DLP_PROXY: Optional[str] = Field(default=None, env="YT_DLP_PROXY")
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOWED_HOSTS: list[str] = Field(
        default=["localhost", "127.0.0.1", "*.localhost"],
        env="ALLOWED_HOSTS"
    )
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    ENABLE_RATE_LIMITING: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    ENABLE_CACHE: bool = Field(default=True, env="ENABLE_CACHE")
    ENABLE_VECTOR_DEDUPLICATION: bool = Field(default=True, env="ENABLE_VECTOR_DEDUPLICATION")
    MAX_CONTENT_LENGTH_MB: int = Field(default=500, env="MAX_CONTENT_LENGTH_MB")
    
    # ========================================================================
    # PROCESSING
    # ========================================================================
    PARALLEL_PROCESSING: bool = Field(default=True, env="PARALLEL_PROCESSING")
    WORKER_COUNT: int = Field(default=4, env="WORKER_COUNT")
    TASK_TIMEOUT_SECONDS: int = Field(default=300, env="TASK_TIMEOUT_SECONDS")
    QUEUE_MAX_SIZE: int = Field(default=100, env="QUEUE_MAX_SIZE")
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # json or text
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()


# ========================================================================
# VALIDATION
# ========================================================================
def validate_settings():
    """Validate critical settings on startup"""
    critical_keys = ["OPENAI_API_KEY", "DATABASE_URL"]
    
    for key in critical_keys:
        value = getattr(settings, key, None)
        if not value:
            raise ValueError(f"Missing critical environment variable: {key}")


# Validate on import (if not in development)
if settings.ENVIRONMENT != "development":
    try:
        validate_settings()
    except ValueError as e:
        print(f"⚠️ Warning: {str(e)}")
