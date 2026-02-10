# backend/app/main.py
"""
ContentFlow - FastAPI Backend Entry Point
Orchestrates video-to-content transformation using LangGraph agents.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base, get_db
from app.api.routes import router as api_router
from app.utils.logger import setup_logger
from app.utils.exceptions import ContentFlowException

# Initialize logger
logger = setup_logger(__name__)


# ============================================================================
# LIFESPAN EVENT HANDLERS
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.
    - Create database tables
    - Initialize vector store
    - Load AI models
    """
    try:
        # Startup
        logger.info("🚀 Starting ContentFlow Backend")
        
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables initialized")
        
        # Initialize vector store (Chroma or similar)
        from app.services.vector_store import init_vector_store
        await init_vector_store()
        logger.info("✅ Vector store initialized")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down ContentFlow Backend")
        await engine.dispose()
        logger.info("✅ Database connections closed")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================
app = FastAPI(
    title="ContentFlow API",
    description="Transform videos into viral social media content using AI",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE STACK (Order matters!)
# ============================================================================

# 1. Trusted Host - Security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# 2. GZIP - Compression
app.add_middleware(GZIPMiddleware, minimum_size=1000)

# 3. CORS - Cross-Origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# ============================================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================================
@app.exception_handler(ContentFlowException)
async def content_flow_exception_handler(request, exc: ContentFlowException):
    """Handle domain-specific exceptions"""
    logger.error(f"ContentFlow Error: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API documentation link"""
    return {
        "name": "ContentFlow API",
        "docs": "/api/docs",
        "version": "1.0.0",
    }


# ============================================================================
# REGISTER ROUTES
# ============================================================================
app.include_router(api_router, prefix="/api", tags=["Content Generation"])


# ============================================================================
# WEBSOCKET HANDLER (Real-time processing updates)
# ============================================================================
active_connections: dict[str, WebSocket] = {}


@app.websocket("/ws/process/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time processing updates.
    Clients connect here to receive streaming progress updates.
    
    Message format:
    {
        "type": "status" | "progress" | "error" | "complete",
        "data": {...}
    }
    """
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        logger.info(f"📡 WebSocket connected: {session_id}")
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug(f"Received from {session_id}: {data}")
            
    except WebSocketDisconnect:
        del active_connections[session_id]
        logger.info(f"📡 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {str(e)}")
        if session_id in active_connections:
            del active_connections[session_id]


async def broadcast_update(session_id: str, message: dict):
    """Broadcast progress updates to connected clients"""
    if session_id in active_connections:
        try:
            await active_connections[session_id].send_json(message)
        except Exception as e:
            logger.error(f"Failed to send update to {session_id}: {str(e)}")


# ============================================================================
# STARTUP LOGGING
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug: {settings.DEBUG}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        workers=1 if settings.DEBUG else 4,
    )
