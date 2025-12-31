#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API models for PDF similarity detection service

All models use camelCase aliases for API responses while keeping snake_case for internal Python code.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ProcessingMode(str, Enum):
    """Processing mode options"""
    STANDARD = "standard"
    FAST = "fast"
    ULTRA_FAST = "ultra_fast"


class ContentFilter(str, Enum):
    """Content filtering options"""
    ALL_CONTENT = "all"
    MAIN_CONTENT_ONLY = "main_content_only"
    INCLUDE_REFERENCES = "include_references"
    INCLUDE_CITATIONS = "include_citations"


class ExportFormat(str, Enum):
    """Export format options"""
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    PDF_REPORT = "pdf_report"


class TaskStatus(str, Enum):
    """Task status options"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


# Request Models
class ComparisonRequest(BaseModel):
    """PDF comparison request - accepts camelCase from frontend"""
    pdf1_path: str = Field(..., description="Path to the first PDF file", alias="pdf1Path")
    pdf2_path: str = Field(..., description="Path to the second PDF file", alias="pdf2Path")
    similarity_threshold: float = Field(default=0.90, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0-1.0)", alias="similarityThreshold")
    sequence_length: int = Field(default=8, ge=4, le=20, description="Number of consecutive characters for similarity detection (4-20)", alias="sequenceLength")
    content_filter: ContentFilter = Field(default=ContentFilter.MAIN_CONTENT_ONLY, description="Content filtering option", alias="contentFilter")
    processing_mode: ProcessingMode = Field(default=ProcessingMode.FAST, description="Processing speed mode", alias="processingMode")
    max_sequences: int = Field(default=5000, ge=100, le=50000, description="Maximum sequences per file", alias="maxSequences")
    export_format: ExportFormat = Field(default=ExportFormat.TEXT, description="Export format for results", alias="exportFormat")
    context_chars: int = Field(default=100, ge=50, le=500, description="Number of context characters to show", alias="contextChars")

    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case


class UploadResponse(BaseModel):
    """File upload response"""
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to saved file", alias="filePath")
    file_size: int = Field(..., description="File size in bytes", alias="fileSize")
    uploaded_at: str = Field(..., description="Upload timestamp", alias="uploadedAt")

    class Config:
        populate_by_name = True


# Response Models
class ComparisonResponse(BaseModel):
    """PDF comparison initiation response"""
    task_id: str = Field(..., description="Unique task identifier", alias="taskId")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")

    class Config:
        populate_by_name = True


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str = Field(..., description="Task identifier", alias="taskId")
    status: str = Field(..., description="Current task status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    started_at: str = Field(..., description="Task start timestamp", alias="startedAt")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp", alias="completedAt")
    error: Optional[str] = Field(None, description="Error message if any")
    message: Optional[str] = Field(None, description="Current status message")

    class Config:
        populate_by_name = True


class SimilarSequence(BaseModel):
    """Similar sequence information"""
    sequence1: str = Field(..., description="Sequence from file 1")
    sequence2: str = Field(..., description="Sequence from file 2")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    position1: Dict[str, Any] = Field(..., description="Position in file 1")
    position2: Dict[str, Any] = Field(..., description="Position in file 2")
    context1: Dict[str, str] = Field(..., description="Context around sequence 1")
    context2: Dict[str, str] = Field(..., description="Context around sequence 2")
    differences: List[str] = Field(..., description="List of differences")


class SimilarityStatistics(BaseModel):
    """Similarity statistics"""
    total_sequences_analyzed: int = Field(..., description="Total sequences analyzed", alias="totalSequencesAnalyzed")
    similar_sequences_found: int = Field(..., description="Number of similar sequences found", alias="similarSequencesFound")
    high_similarity_count: int = Field(..., description="Count of high similarity sequences (>0.9)", alias="highSimilarityCount")
    medium_similarity_count: int = Field(..., description="Count of medium similarity sequences (0.8-0.9)", alias="mediumSimilarityCount")
    low_similarity_count: int = Field(..., description="Count of low similarity sequences (0.75-0.8)", alias="lowSimilarityCount")
    average_similarity: float = Field(..., ge=0.0, le=1.0, description="Average similarity score", alias="averageSimilarity")
    max_similarity: float = Field(..., ge=0.0, le=1.0, description="Maximum similarity score", alias="maxSimilarity")
    min_similarity: float = Field(..., ge=0.0, le=1.0, description="Minimum similarity score", alias="minSimilarity")

    class Config:
        populate_by_name = True


class FileStatistics(BaseModel):
    """File processing statistics"""
    file_path: str = Field(..., description="File path", alias="filePath")
    file_size_mb: float = Field(..., description="File size in MB", alias="fileSizeMb")
    total_pages: int = Field(..., description="Total pages", alias="totalPages")
    total_lines: int = Field(..., description="Total lines extracted", alias="totalLines")
    main_content_lines: int = Field(..., description="Main content lines after filtering", alias="mainContentLines")
    filtered_lines: int = Field(..., description="Lines filtered out", alias="filteredLines")
    total_chars: int = Field(..., description="Total characters", alias="totalChars")
    processing_time_seconds: float = Field(..., description="Processing time in seconds", alias="processingTimeSeconds")

    class Config:
        populate_by_name = True


class SimilarityResult(BaseModel):
    """Complete similarity detection result"""
    task_id: str = Field(..., description="Task identifier", alias="taskId")
    comparison_info: Dict[str, Any] = Field(..., description="Comparison configuration", alias="comparisonInfo")
    file1_stats: FileStatistics = Field(..., description="File 1 statistics", alias="file1Stats")
    file2_stats: FileStatistics = Field(..., description="File 2 statistics", alias="file2Stats")
    similarity_stats: SimilarityStatistics = Field(..., description="Similarity statistics", alias="similarityStats")
    similar_sequences: List[SimilarSequence] = Field(..., description="List of similar sequences", alias="similarSequences")
    processing_time_seconds: float = Field(..., description="Total processing time", alias="processingTimeSeconds")
    export_files: Dict[str, str] = Field(..., description="Export file paths", alias="exportFiles")

    class Config:
        populate_by_name = True


class ExportFile(BaseModel):
    """Export file information"""
    format: ExportFormat = Field(..., description="Export format")
    file_path: str = Field(..., description="Export file path", alias="filePath")
    file_size: int = Field(..., description="File size in bytes", alias="fileSize")
    download_url: str = Field(..., description="Download URL", alias="downloadUrl")

    class Config:
        populate_by_name = True


# Error Models
class ErrorDetail(BaseModel):
    """Error detail"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Error response"""
    error: ErrorDetail = Field(..., description="Error information")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier", alias="requestId")

    class Config:
        populate_by_name = True


# Health Check Models
class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    last_check: str = Field(..., description="Last check timestamp", alias="lastCheck")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional service details")

    class Config:
        populate_by_name = True


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    services: Dict[str, Any] = Field(..., description="Service statuses")
    uptime_seconds: float = Field(..., description="Service uptime in seconds", alias="uptimeSeconds")
    version: str = Field(..., description="API version")

    class Config:
        populate_by_name = True


# WebSocket Models
class WebSocketMessage(BaseModel):
    """WebSocket message"""
    type: str = Field(..., description="Message type")
    task_id: Optional[str] = Field(None, description="Task identifier", alias="taskId")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: str = Field(..., description="Message timestamp")

    class Config:
        populate_by_name = True


class ProgressUpdate(BaseModel):
    """Progress update message"""
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    message: str = Field(..., description="Progress message")
    current_step: str = Field(..., description="Current processing step", alias="currentStep")
    estimated_remaining_seconds: Optional[int] = Field(None, description="Estimated remaining time", alias="estimatedRemainingSeconds")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional progress details")

    class Config:
        populate_by_name = True
