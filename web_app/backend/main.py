#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Similarity Detection Web Backend
FastAPI application for PDF similarity detection with polling-based status updates
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import uuid
import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging
from datetime import datetime

# Import our custom modules
from models.api_models import (
    ComparisonRequest, ComparisonResponse,
    TaskStatusResponse, ErrorResponse
)
from utils.logger import setup_logger
from utils.file_utils import save_upload_file, cleanup_files

# Setup logging
logger = setup_logger(__name__)

# Global state for tasks
active_tasks: Dict[str, Dict] = {}
# Track application start time for uptime calculation
app_start_time = datetime.utcnow()

# Initialize services (will be set in lifespan)
pdf_service_instance = None
similarity_service_instance = None

# Dependency injection
def get_pdf_service():
    return pdf_service_instance

def get_similarity_service():
    return similarity_service_instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global pdf_service_instance, similarity_service_instance

    logger.info("Starting PDF Similarity Detection Service...")

    # Import and initialize services
    from services.pdf_service import PDFService
    from services.similarity_service import SimilarityService

    pdf_service_instance = PDFService()
    similarity_service_instance = SimilarityService()

    logger.info("Services initialized successfully")
    yield

    logger.info("Shutting down PDF Similarity Detection Service...")
    # Cleanup any running tasks
    for task_id, task_info in active_tasks.items():
        if not task_info.get('completed', True):
            task_info['task'].cancel()
    logger.info("Shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="PDF Similarity Detection API",
    description="AI-powered PDF similarity detection",
    version="1.0.0",
    lifespan=lifespan
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests"""
    import time
    start_time = time.time()

    logger.info(f"[REQUEST] {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.info(f"[RESPONSE] {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")

    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://yourdomain.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PDF Similarity Detection API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint - returns camelCase to match frontend expectations"""
    now = datetime.utcnow()
    uptime_seconds = (now - app_start_time).total_seconds()

    return {
        "status": "healthy",
        "timestamp": now.isoformat(),
        "services": {
            "pdf_processor": {
                "name": "PDF Processor",
                "status": "operational",
                "lastCheck": now.isoformat()
            },
            "similarity_detector": {
                "name": "Similarity Detector",
                "status": "operational",
                "lastCheck": now.isoformat()
            }
        },
        "uptimeSeconds": uptime_seconds,
        "version": "1.0.0"
    }

@app.post("/api/v1/compare")
async def compare_pdfs(
    request: ComparisonRequest,
    pdf_service = Depends(get_pdf_service),
    similarity_service = Depends(get_similarity_service)
):
    """
    Compare two PDF files for similarity

    This endpoint initiates a PDF similarity comparison task with the following options:
    - Content filtering (main text only vs full content)
    - Similarity threshold adjustment
    - Processing speed options
    - Export format selection
    """
    logger.info(f"[COMPARE] Received compare request: pdf1={request.pdf1_path}, pdf2={request.pdf2_path}")
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Validate input
        if not request.pdf1_path or not request.pdf2_path:
            logger.warning("[COMPARE] Missing file paths")
            raise HTTPException(status_code=400, detail="Both PDF file paths are required")

        if not os.path.exists(request.pdf1_path) or not os.path.exists(request.pdf2_path):
            logger.warning(f"[COMPARE] Files not found: pdf1 exists={os.path.exists(request.pdf1_path)}, pdf2 exists={os.path.exists(request.pdf2_path)}")
            raise HTTPException(status_code=404, detail="One or both PDF files not found")

        # Initialize task
        active_tasks[task_id] = {
            "taskId": task_id,
            "status": "pending",
            "progress": 0,
            "startedAt": datetime.utcnow().isoformat(),
            "completedAt": None,
            "completed": False,
            "result": None,
            "error": None,
            "message": "Task initialized"
        }

        # Create background task
        task = asyncio.create_task(
            process_pdf_comparison(
                task_id, request, pdf_service, similarity_service
            )
        )
        active_tasks[task_id]["task"] = task

        logger.info(f"[COMPARE] Task created: {task_id}")

        return {
            "taskId": task_id,
            "status": "pending",
            "message": "Comparison task started successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[COMPARE] Error starting PDF comparison: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for comparison - returns camelCase to match frontend expectations"""
    logger.info(f"[UPLOAD] Received upload request: filename={file.filename}")
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"[UPLOAD] Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Save file
        file_path = await save_upload_file(file)

        # Get file info
        file_size = os.path.getsize(file_path)

        logger.info(f"[UPLOAD] File saved successfully: {file_path} ({file_size} bytes)")

        return {
            "filename": file.filename,
            "filePath": file_path,
            "fileSize": file_size,
            "uploadedAt": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] Error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/api/v1/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of a comparison task"""
    logger.info(f"[STATUS] Checking status for task: {task_id}")
    if task_id not in active_tasks:
        logger.warning(f"[STATUS] Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = active_tasks[task_id]
    logger.info(f"[STATUS] Task {task_id}: status={task_info.get('status')}, progress={task_info.get('progress')}")

    return {
        "taskId": task_info.get("taskId", task_id),
        "status": task_info.get("status", "unknown"),
        "progress": task_info.get("progress", 0),
        "startedAt": task_info.get("startedAt", ""),
        "completedAt": task_info.get("completedAt"),
        "error": task_info.get("error"),
        "message": task_info.get("message", "")
    }

@app.get("/api/v1/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Get the result of a completed comparison task"""
    logger.info(f"[RESULT] Getting result for task: {task_id}")
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = active_tasks[task_id]

    if task_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current status: {task_info.get('status')}"
        )

    # Extract similarity_result from nested structure
    result_data = task_info.get("result", {})
    similarity_result = result_data.get("similarity_result", {})
    export_files = result_data.get("export_files", {})

    # Log for debugging
    logger.info(f"[RESULT] similarSequences type: {type(similarity_result.get('similarSequences'))}")
    logger.info(f"[RESULT] similarSequences length: {len(similarity_result.get('similarSequences', []))}")
    logger.info(f"[RESULT] Keys in similarity_result: {list(similarity_result.keys())}")

    # Merge export_files into similarity_result
    similarity_result["exportFiles"] = export_files

    return similarity_result

@app.delete("/api/v1/task/{task_id}")
async def delete_task(task_id: str):
    """Delete a completed task and its associated files"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = active_tasks[task_id]

    # Cancel if running
    if not task_info.get("completed", False) and task_info.get("task"):
        task_info["task"].cancel()

    # Cleanup files if result exists
    if task_info.get("result") and "files_to_cleanup" in task_info["result"]:
        await cleanup_files(task_info["result"]["files_to_cleanup"])

    # Remove from active tasks
    del active_tasks[task_id]

    logger.info(f"Deleted task: {task_id}")

    return {"message": "Task deleted successfully"}

async def process_pdf_comparison(
    task_id: str,
    request: ComparisonRequest,
    pdf_service,
    similarity_service
):
    """Background task to process PDF comparison"""
    try:
        # Update status - extracting content
        active_tasks[task_id]["status"] = "processing"
        active_tasks[task_id]["progress"] = 0.1
        active_tasks[task_id]["message"] = "Extracting PDF content..."
        logger.info(f"[TASK {task_id}] Starting PDF content extraction")

        # Extract PDF content
        pdf1_content = await pdf_service.extract_pdf_content(
            request.pdf1_path,
            content_filter=request.content_filter
        )

        active_tasks[task_id]["progress"] = 0.3
        active_tasks[task_id]["message"] = "Extracting second PDF..."

        pdf2_content = await pdf_service.extract_pdf_content(
            request.pdf2_path,
            content_filter=request.content_filter
        )

        active_tasks[task_id]["progress"] = 0.5
        active_tasks[task_id]["message"] = "Detecting similarities..."
        logger.info(f"[TASK {task_id}] Starting similarity detection")

        # Perform similarity detection
        similarity_result = await similarity_service.detect_similarity(
            pdf1_content,
            pdf2_content,
            min_similarity=request.similarity_threshold,
            max_sequences=request.max_sequences,
            sequence_length=request.sequence_length,
            processing_mode=request.processing_mode
        )

        active_tasks[task_id]["progress"] = 0.9
        active_tasks[task_id]["message"] = "Generating export files..."

        # Generate export files
        export_files = await similarity_service.generate_exports(
            similarity_result,
            export_format=request.export_format,
            task_id=task_id
        )

        # Complete task
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["progress"] = 1.0
        active_tasks[task_id]["completedAt"] = datetime.utcnow().isoformat()
        active_tasks[task_id]["completed"] = True
        active_tasks[task_id]["message"] = "Comparison completed successfully"

        # Handle result serialization - use by_alias=True for camelCase
        if hasattr(similarity_result, 'model_dump'):
            result_dict = similarity_result.model_dump(by_alias=True)
        elif hasattr(similarity_result, 'dict'):
            result_dict = similarity_result.dict(by_alias=True)
        else:
            result_dict = similarity_result

        active_tasks[task_id]["result"] = {
            "similarity_result": result_dict,
            "export_files": export_files,
            "files_to_cleanup": [request.pdf1_path, request.pdf2_path],
        }

        logger.info(f"[TASK {task_id}] Completed successfully")

    except Exception as e:
        logger.error(f"[TASK {task_id}] Error processing: {str(e)}", exc_info=True)
        active_tasks[task_id]["status"] = "error"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["message"] = f"Error: {str(e)}"
        active_tasks[task_id]["completed"] = True

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"[ERROR] Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}}
    )
