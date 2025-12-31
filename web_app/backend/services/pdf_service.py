#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF processing service for extracting and filtering content
Incorporates optimized algorithms from the command-line version
"""

import asyncio
import pdfplumber
import os
import time
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# Import our enhanced PDF extractor from the command-line version
import sys
# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_pdf_extractor import EnhancedPDFTextExtractor, TextExtractionConfig
from models.api_models import ContentFilter, FileStatistics

logger = logging.getLogger(__name__)


@dataclass
class PDFContent:
    """PDF content container"""
    file_path: str
    lines: List[Tuple[str, int, int]]  # (text, page, line_number)
    chars: List[Any]  # CharInfo objects
    sequences: List[Any]  # Sequence objects
    stats: FileStatistics
    extraction_time: float


class PDFService:
    """PDF processing service with enhanced extraction and filtering"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def extract_pdf_content(
        self,
        pdf_path: str,
        content_filter: ContentFilter = ContentFilter.MAIN_CONTENT_ONLY,
        task_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> PDFContent:
        """
        Extract content from PDF with configurable filtering

        Args:
            pdf_path: Path to PDF file
            content_filter: Content filtering option
            task_id: Optional task ID for progress tracking
            progress_callback: Optional progress callback function

        Returns:
            PDFContent: Extracted content with statistics
        """
        self.logger.info(f"[PDF] Starting extraction: {pdf_path}")
        start_time = time.time()

        try:
            # Create extraction configuration based on filter option
            config = self._create_extraction_config(content_filter)

            # Run blocking PDF extraction in thread pool
            lines, stats = await asyncio.to_thread(self._extract_sync, pdf_path, config)

            self.logger.info(f"[PDF] Extraction completed: {len(lines)} lines extracted from PDF")

            # Convert to our API model
            file_stats = self._convert_to_file_statistics(pdf_path, stats, time.time() - start_time)

            # Create content object
            content = PDFContent(
                file_path=pdf_path,
                lines=lines,
                chars=[],
                sequences=[],
                stats=file_stats,
                extraction_time=time.time() - start_time
            )

            return content

        except Exception as e:
            self.logger.error(f"Error extracting PDF content from {pdf_path}: {str(e)}", exc_info=True)
            raise

    def _extract_sync(self, pdf_path: str, config):
        """Synchronous PDF extraction - runs in thread pool"""
        from enhanced_pdf_extractor import EnhancedPDFTextExtractor

        # Create enhanced extractor
        extractor = EnhancedPDFTextExtractor(config)

        # Extract main text lines
        lines = extractor.extract_main_text_lines(pdf_path)

        # Get extraction statistics
        stats = extractor.get_extraction_stats(pdf_path)

        return lines, stats

    def _create_extraction_config(self, content_filter: ContentFilter) -> TextExtractionConfig:
        """Create extraction configuration based on filter option"""

        if content_filter == ContentFilter.ALL_CONTENT:
            return TextExtractionConfig(
                include_references=True,
                include_footnotes=True,
                include_citations=True,
                include_page_numbers=True,
                include_headers_footers=True,
                include_annotations=False,  # Still not supported
                min_line_length=5,  # Lower threshold
                remove_duplicate_lines=True
            )

        elif content_filter == ContentFilter.INCLUDE_REFERENCES:
            return TextExtractionConfig(
                include_references=True,
                include_footnotes=False,
                include_citations=False,
                include_page_numbers=False,
                include_headers_footers=False,
                include_annotations=False,
                min_line_length=10,
                remove_duplicate_lines=True
            )

        elif content_filter == ContentFilter.INCLUDE_CITATIONS:
            return TextExtractionConfig(
                include_references=False,
                include_footnotes=False,
                include_citations=True,
                include_page_numbers=False,
                include_headers_footers=False,
                include_annotations=False,
                min_line_length=10,
                remove_duplicate_lines=True
            )

        else:  # MAIN_CONTENT_ONLY (default)
            return TextExtractionConfig(
                include_references=False,
                include_footnotes=False,
                include_citations=False,
                include_page_numbers=False,
                include_headers_footers=False,
                include_annotations=False,
                min_line_length=5,  # Reduced from 10 to capture more content
                remove_duplicate_lines=True
            )

    def _convert_to_file_statistics(
        self,
        pdf_path: str,
        extraction_stats: Dict[str, Any],
        processing_time: float
    ) -> FileStatistics:
        """Convert extraction statistics to API model"""

        file_size = os.path.getsize(pdf_path)
        file_size_mb = round(file_size / (1024 * 1024), 2)

        return FileStatistics(
            file_path=pdf_path,
            file_size_mb=file_size_mb,
            total_pages=extraction_stats.get("total_pages", 0),
            total_lines=extraction_stats.get("total_lines", 0),
            main_content_lines=extraction_stats.get("main_content_lines", 0),
            filtered_lines=extraction_stats.get("filtered_lines", 0),
            total_chars=extraction_stats.get("total_chars", 0),
            processing_time_seconds=processing_time
        )

    async def validate_pdf_file(self, pdf_path: str) -> Dict[str, Any]:
        """
        Validate PDF file and return basic information

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict: Validation results
        """
        try:
            if not os.path.exists(pdf_path):
                return {"valid": False, "error": "File not found"}

            if not pdf_path.lower().endswith('.pdf'):
                return {"valid": False, "error": "Not a PDF file"}

            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                return {"valid": False, "error": "Empty file"}

            # Try to open with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)

            return {
                "valid": True,
                "file_path": pdf_path,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "page_count": page_count
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Invalid PDF file: {str(e)}"
            }

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return [".pdf"]

    def estimate_processing_time(
        self,
        file_size_mb: float,
        page_count: int,
        content_filter: ContentFilter,
        processing_mode: str
    ) -> float:
        """
        Estimate processing time based on file characteristics

        Args:
            file_size_mb: File size in MB
            page_count: Number of pages
            content_filter: Content filtering option
            processing_mode: Processing mode

        Returns:
            float: Estimated processing time in seconds
        """
        # Base processing time (seconds per page)
        base_time_per_page = 0.5

        # Adjust based on content filter
        if content_filter == ContentFilter.ALL_CONTENT:
            filter_multiplier = 1.5
        elif content_filter == ContentFilter.MAIN_CONTENT_ONLY:
            filter_multiplier = 1.0
        else:
            filter_multiplier = 1.2

        # Adjust based on processing mode
        if processing_mode == "ultra_fast":
            mode_multiplier = 0.3
        elif processing_mode == "fast":
            mode_multiplier = 0.6
        else:
            mode_multiplier = 1.0

        # Calculate estimated time
        estimated_time = (
            page_count * base_time_per_page *
            filter_multiplier * mode_multiplier
        )

        # Add overhead for large files
        if file_size_mb > 50:
            estimated_time *= 1.5
        elif file_size_mb > 20:
            estimated_time *= 1.2

        return max(estimated_time, 5.0)  # Minimum 5 seconds