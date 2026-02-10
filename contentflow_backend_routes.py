# backend/app/api/routes.py
"""
API Route handlers for ContentFlow.
Includes endpoints for content generation, retrieval, and management.
"""

from uuid import UUID, uuid4
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Content, ProcessingJob, ProcessingStatusEnum
from app.schemas import (
    ContentGenerationRequest,
    ContentResponse,
    ContentListResponse,
    ProcessingJobResponse,
    ErrorResponse,
    PaginationParams,
    ContentExportRequest,
)
from app.services.ai_orchestrator import AIOrchestrator
from app.utils.logger import setup_logger
from app.utils.exceptions import ContentFlowException, ValidationError

router = APIRouter(prefix="/v1", tags=["Content API"])
logger = setup_logger(__name__)


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_user_id(request) -> str:
    """Extract user ID from request (auth token, session, etc.)"""
    # TODO: Implement real authentication
    return "user_demo"


# ============================================================================
# CONTENT GENERATION ENDPOINTS
# ============================================================================

@router.post(
    "/generate",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate content from source",
    description="Asynchronously generate content from a YouTube URL or article",
)
async def generate_content(
    request: ContentGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate multi-format social media content from a source.
    
    Returns a processing job ID to track progress via WebSocket.
    
    Example:
    ```json
    {
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "source_type": "youtube",
        "content_types": ["linkedin_carousel", "twitter_thread"],
        "tone": "professional"
    }
    ```
    """
    try:
        session_id = str(uuid4())
        
        # Create content record
        content = Content(
            user_id="user_demo",  # Replace with real user
            source_type=request.source_type,
            source_url=request.source_url,
            source_metadata={
                "tone": request.tone,
                "target_audience": request.target_audience,
                "include_hashtags": request.include_hashtags,
            },
        )
        
        # Create processing job
        job = ProcessingJob(
            content=content,
            status=ProcessingStatusEnum.PENDING,
            session_id=session_id,
            output_content_types=[ct.value for ct in request.content_types],
        )
        
        db.add(content)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"📝 Processing job created: {job.id}")
        
        # Queue background task
        background_tasks.add_task(
            process_content_task,
            job_id=job.id,
            session_id=session_id,
            request=request,
        )
        
        return {
            "job_id": str(job.id),
            "session_id": session_id,
            "status": "queued",
            "message": "Processing started. Connect to WebSocket for updates.",
            "ws_url": f"/ws/process/{session_id}",
        }
        
    except Exception as e:
        logger.error(f"❌ Content generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


async def process_content_task(
    job_id: UUID,
    session_id: str,
    request: ContentGenerationRequest,
):
    """
    Background task to process content asynchronously.
    Updates progress via WebSocket.
    """
    async with get_db() as db:
        try:
            job = await db.get(ProcessingJob, job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return
            
            # Update status
            job.status = ProcessingStatusEnum.PROCESSING
            job.started_at = datetime.utcnow()
            await db.commit()
            
            # Initialize orchestrator
            orchestrator = AIOrchestrator()
            
            # Process content
            logger.info(f"🔄 Processing job {job_id}: {request.source_url}")
            
            # Step 1: Extract content (20%)
            job.current_step = "Extracting content..."
            job.progress_percent = 20
            await db.commit()
            
            content_data = await orchestrator.extract_content(
                url=request.source_url,
                source_type=request.source_type,
            )
            
            # Step 2: Generate content (80%)
            job.current_step = "Generating content..."
            job.progress_percent = 50
            await db.commit()
            
            generated = await orchestrator.generate_content(
                content=content_data,
                content_types=[ct.value for ct in request.content_types],
                tone=request.tone,
                target_audience=request.target_audience,
                include_hashtags=request.include_hashtags,
            )
            
            # Update content with results
            job.content.raw_text = content_data.get("text", \"\")\n            job.content.summary = content_data.get(\"summary\")\n            job.content.key_points = content_data.get(\"key_points\", [])\n            job.content.generated_content = generated\n            job.content.processing_time_ms = int(\n                (datetime.utcnow() - job.started_at).total_seconds() * 1000)\n            )\n            \n            # Mark as complete\n            job.status = ProcessingStatusEnum.COMPLETED\n            job.progress_percent = 100\n            job.completed_at = datetime.utcnow()\n            job.current_step = \"Complete!\"\n            \n            await db.commit()\n            logger.info(f\"✅ Job {job_id} completed successfully\")\n            \n        except Exception as e:\n            logger.error(f\"❌ Job {job_id} failed: {str(e)}\", exc_info=True)\n            job.status = ProcessingStatusEnum.FAILED\n            job.error_message = str(e)\n            job.error_code = \"PROCESSING_ERROR\"\n            job.completed_at = datetime.utcnow()\n            await db.commit()\n\n\n# ============================================================================\n# CONTENT RETRIEVAL ENDPOINTS\n# ============================================================================\n\n@router.get(\n    \"/contents\",\n    response_model=ContentListResponse,\n    summary=\"List user's content\",\n    description=\"Retrieve paginated list of user's processed content\",\n)\nasync def list_contents(\n    skip: int = Query(0, ge=0),\n    limit: int = Query(20, ge=1, le=100),\n    sort_by: str = Query(\"created_at\"),\n    db: AsyncSession = Depends(get_db),\n):\n    \"\"\"Retrieve paginated list of user's contents\"\"\"\n    \n    try:\n        # Base query\n        query = select(Content).where(\n            Content.user_id == \"user_demo\"\n        )\n        \n        # Sort\n        if sort_by == \"created_at\":\n            query = query.order_by(desc(Content.created_at))\n        elif sort_by == \"updated_at\":\n            query = query.order_by(desc(Content.updated_at))\n        \n        # Get total count\n        count_query = select(len(query.froms[0]))\n        result = await db.execute(query)\n        items = [row[0] for row in result.all()]\n        \n        # Paginate\n        paginated_items = items[skip : skip + limit]\n        \n        return ContentListResponse(\n            items=[ContentResponse.from_orm(item) for item in paginated_items],\n            total=len(items),\n            skip=skip,\n            limit=limit,\n            has_more=(skip + limit) < len(items),\n        )\n        \n    except Exception as e:\n        logger.error(f\"❌ Failed to list contents: {str(e)}\", exc_info=True)\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=str(e),\n        )\n\n\n@router.get(\n    \"/contents/{content_id}\",\n    response_model=ContentResponse,\n    summary=\"Get content details\",\n)\nasync def get_content(\n    content_id: UUID,\n    db: AsyncSession = Depends(get_db),\n):\n    \"\"\"Retrieve a specific content by ID\"\"\"\n    \n    try:\n        content = await db.get(Content, content_id)\n        \n        if not content:\n            raise HTTPException(\n                status_code=status.HTTP_404_NOT_FOUND,\n                detail=\"Content not found\",\n            )\n        \n        return ContentResponse.from_orm(content)\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"❌ Failed to get content: {str(e)}\", exc_info=True)\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=str(e),\n        )\n\n\n@router.get(\n    \"/jobs/{job_id}\",\n    response_model=ProcessingJobResponse,\n    summary=\"Get processing job status\",\n)\nasync def get_job_status(\n    job_id: UUID,\n    db: AsyncSession = Depends(get_db),\n):\n    \"\"\"Get the status of a processing job\"\"\"\n    \n    try:\n        job = await db.get(ProcessingJob, job_id)\n        \n        if not job:\n            raise HTTPException(\n                status_code=status.HTTP_404_NOT_FOUND,\n                detail=\"Job not found\",\n            )\n        \n        return ProcessingJobResponse.from_orm(job)\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"❌ Failed to get job: {str(e)}\", exc_info=True)\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=str(e),\n        )\n\n\n# ============================================================================\n# CONTENT MANAGEMENT ENDPOINTS\n# ============================================================================\n\n@router.delete(\n    \"/contents/{content_id}\",\n    status_code=status.HTTP_204_NO_CONTENT,\n    summary=\"Delete content\",\n)\nasync def delete_content(\n    content_id: UUID,\n    db: AsyncSession = Depends(get_db),\n):\n    \"\"\"Delete a content and related processing jobs\"\"\"\n    \n    try:\n        content = await db.get(Content, content_id)\n        \n        if not content:\n            raise HTTPException(\n                status_code=status.HTTP_404_NOT_FOUND,\n                detail=\"Content not found\",\n            )\n        \n        await db.delete(content)\n        await db.commit()\n        \n        logger.info(f\"🗑️ Content {content_id} deleted\")\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        await db.rollback()\n        logger.error(f\"❌ Failed to delete content: {str(e)}\", exc_info=True)\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=str(e),\n        )\n\n\n@router.post(\n    \"/contents/{content_id}/export\",\n    response_model=dict,\n    summary=\"Export content\",\n)\nasync def export_content(\n    content_id: UUID,\n    export_request: ContentExportRequest,\n    db: AsyncSession = Depends(get_db),\n):\n    \"\"\"Export content in various formats\"\"\"\n    \n    try:\n        content = await db.get(Content, content_id)\n        \n        if not content:\n            raise HTTPException(\n                status_code=status.HTTP_404_NOT_FOUND,\n                detail=\"Content not found\",\n            )\n        \n        # Export logic (JSON, CSV, Markdown, etc.)\n        if export_request.format == \"json\":\n            export_data = ContentResponse.from_orm(content).dict()\n        elif export_request.format == \"markdown\":\n            export_data = _content_to_markdown(content)\n        else:\n            raise ValueError(f\"Unsupported format: {export_request.format}\")\n        \n        return {\n            \"success\": True,\n            \"format\": export_request.format,\n            \"data\": export_data,\n        }\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"❌ Export failed: {str(e)}\", exc_info=True)\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=str(e),\n        )\n\n\ndef _content_to_markdown(content: Content) -> str:\n    \"\"\"Convert content to markdown format\"\"\"\n    lines = [\n        f\"# {content.source_title or 'Untitled'}\",\n        f\"\",\n        f\"**Source:** {content.source_url}\",\n        f\"\",\n    ]\n    \n    if content.summary:\n        lines.extend([\"## Summary\", content.summary, \"\"])\n    \n    if content.key_points:\n        lines.extend([\"## Key Points\"])\n        for point in content.key_points:\n            lines.append(f\"- {point}\")\n        lines.append(\"\")\n    \n    return \"\\n\".join(lines)\n