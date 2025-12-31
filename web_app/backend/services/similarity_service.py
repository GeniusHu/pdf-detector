#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Similarity detection service with optimized algorithms
Incorporates all performance optimizations from the command-line version
"""

import asyncio
import os
import time
import json
import csv
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

# Import our optimized detector from the command-line version
import sys
# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_pdf_extractor import EnhancedPDFTextExtractor, TextExtractionConfig
from text_processor import TextProcessor
from optimized_sequence_generator import OptimizedSequenceGenerator

from models.api_models import (
    SimilarityResult, SimilarSequence, SimilarityStatistics,
    ProcessingMode, ExportFormat
)
from services.pdf_service import PDFContent

logger = logging.getLogger(__name__)


class SimilarityService:
    """Similarity detection service with optimized algorithms"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def detect_similarity(
        self,
        pdf1_content: PDFContent,
        pdf2_content: PDFContent,
        min_similarity: float = 0.90,
        max_sequences: int = 5000,
        sequence_length: int = 8,
        processing_mode: ProcessingMode = ProcessingMode.FAST,
        context_chars: int = 100,
        task_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> SimilarityResult:
        """
        Detect similarities between two PDF contents with optimized algorithms

        Args:
            pdf1_content: First PDF content
            pdf2_content: Second PDF content
            min_similarity: Minimum similarity threshold
            max_sequences: Maximum sequences per file
            sequence_length: Number of consecutive characters for sequence generation
            processing_mode: Processing speed mode
            context_chars: Number of context characters
            task_id: Optional task ID for progress tracking
            progress_callback: Optional progress callback function

        Returns:
            SimilarityResult: Complete similarity detection result
        """
        self.logger.info(f"[SIM] Starting similarity detection with sequence_length={sequence_length}")
        start_time = time.time()

        try:
            # Configure processing parameters based on mode
            similarity_threshold, max_seqs = self._configure_processing(
                processing_mode, min_similarity, max_sequences
            )

            # Run blocking similarity detection in thread pool
            result = await asyncio.to_thread(
                self._detect_similarity_sync,
                pdf1_content, pdf2_content,
                similarity_threshold, max_seqs, sequence_length, context_chars
            )

            self.logger.info(f"[SIM] Detection completed: {len(result['similarSequences'])} sequences, {time.time() - start_time:.2f}s")

            # Return SimilarityResult object
            return SimilarityResult(**result)

        except Exception as e:
            self.logger.error(f"Error in similarity detection: {str(e)}", exc_info=True)
            raise

    def _detect_similarity_sync(
        self,
        pdf1_content: PDFContent,
        pdf2_content: PDFContent,
        similarity_threshold: float,
        max_sequences: int,
        sequence_length: int,
        context_chars: int
    ) -> Dict[str, Any]:
        """Synchronous similarity detection - runs in thread pool"""
        from text_processor import CharInfo
        from collections import defaultdict

        start_time = time.time()

        # Create sequence generator with sequence_length
        generator = OptimizedSequenceGenerator(similarity_threshold, sequence_length)

        # Convert lines to CharInfo objects
        # pdf1_content.lines is List[Tuple[str, int, int]] = (text, page, line_number)
        print(f"\n[CONVERSION] Converting lines to CharInfo...")
        print(f"[CONVERSION] File 1: {len(pdf1_content.lines)} lines -> CharInfo...")
        chars1 = self._lines_to_char_info(pdf1_content.lines)
        print(f"[CONVERSION] File 2: {len(pdf2_content.lines)} lines -> CharInfo...")
        chars2 = self._lines_to_char_info(pdf2_content.lines)

        print(f"[CONVERSION] File 1: {len(chars1)} chars | File 2: {len(chars2)} chars")
        self.logger.info(f"[SIM] Converted to CharInfo: file1={len(chars1)} chars from {len(pdf1_content.lines)} lines, file2={len(chars2)} chars from {len(pdf2_content.lines)} lines")

        # Generate sequences from CharInfo objects
        sequences1 = generator.generate_sequences(chars1)
        sequences2 = generator.generate_sequences(chars2)

        self.logger.info(f"[SIM] Generated sequences (length={sequence_length}): file1={len(sequences1)} sequences, file2={len(sequences2)} sequences")

        # No limit on sequences - compare all
        # sequences1 = sequences1[:max_sequences]
        # sequences2 = sequences2[:max_sequences]

        # Convert to dictionary format for find_similar_sequences
        # Dict[str, List[SequenceInfo]] where key is sequence string
        sequences1_dict = self._sequences_to_dict(sequences1)
        sequences2_dict = self._sequences_to_dict(sequences2)

        # Find similar sequences
        similar_sequences = generator.find_similar_sequences(sequences1_dict, sequences2_dict)

        # Log page range of similar sequences
        if similar_sequences:
            pages1 = set(s.sequence1.start_char.page for s in similar_sequences)
            pages2 = set(s.sequence2.start_char.page for s in similar_sequences)
            print(f"\n{'='*60}")
            print(f"[RESULT] Found {len(similar_sequences)} similar sequences")
            print(f"[RESULT] File 1 similarities on pages: {sorted(pages1)}")
            print(f"[RESULT] File 2 similarities on pages: {sorted(pages2)}")
            print(f"{'='*60}\n")
            self.logger.info(f"[SIM] Found {len(similar_sequences)} similar sequences")
            self.logger.info(f"[SIM] Similarities in file1: pages {sorted(pages1)}")
            self.logger.info(f"[SIM] Similarities in file2: pages {sorted(pages2)}")
        else:
            print(f"\n{'='*60}")
            print(f"[RESULT] No similar sequences found!")
            print(f"{'='*60}\n")
            self.logger.info(f"[SIM] Found 0 similar sequences")

        # Convert similar sequences to our API model
        result_similar_sequences = []
        for seq_info in similar_sequences:
            seq_dict = {
                "sequence1": seq_info.sequence1.sequence,
                "sequence2": seq_info.sequence2.sequence,
                "similarity": float(seq_info.similarity),
                "position1": {
                    "page": seq_info.sequence1.start_char.page,
                    "line": seq_info.sequence1.start_char.line,
                    "charIndex": seq_info.sequence1.start_index
                },
                "position2": {
                    "page": seq_info.sequence2.start_char.page,
                    "line": seq_info.sequence2.start_char.line,
                    "charIndex": seq_info.sequence2.start_index
                },
                "context1": {"before": "", "after": ""},
                "context2": {"before": "", "after": ""},
                "differences": seq_info.differences if hasattr(seq_info, 'differences') else []
            }
            result_similar_sequences.append(SimilarSequence(**seq_dict))

        # Create statistics
        total_seqs = len(sequences1) + len(sequences2)
        similarity_stats = SimilarityStatistics(
            totalSequencesAnalyzed=total_seqs,
            similarSequencesFound=len(similar_sequences),
            highSimilarityCount=len([s for s in similar_sequences if s.similarity > 0.9]),
            mediumSimilarityCount=len([s for s in similar_sequences if 0.8 < s.similarity <= 0.9]),
            lowSimilarityCount=len([s for s in similar_sequences if 0.75 <= s.similarity <= 0.8]),
            averageSimilarity=sum(s.similarity for s in similar_sequences) / len(similar_sequences) if similar_sequences else 0,
            maxSimilarity=max(s.similarity for s in similar_sequences) if similar_sequences else 0,
            minSimilarity=min(s.similarity for s in similar_sequences) if similar_sequences else 0
        )

        # Convert statistics to dict for proper serialization
        if hasattr(similarity_stats, 'model_dump'):
            similarity_stats_dict = similarity_stats.model_dump(by_alias=True)
        elif hasattr(similarity_stats, 'dict'):
            similarity_stats_dict = similarity_stats.dict(by_alias=True)
        else:
            similarity_stats_dict = similarity_stats

        # Convert SimilarSequence objects to dicts for proper serialization
        similar_sequences_dicts = []
        for seq in result_similar_sequences:
            if hasattr(seq, 'model_dump'):
                similar_sequences_dicts.append(seq.model_dump(by_alias=True))
            elif hasattr(seq, 'dict'):
                similar_sequences_dicts.append(seq.dict(by_alias=True))
            else:
                similar_sequences_dicts.append(seq)

        # Determine processing mode string
        mode_str = "ultra_fast" if similarity_threshold >= 0.9 else ("fast" if similarity_threshold >= 0.8 else "standard")

        # Create result - use primitive types and dicts, not Pydantic objects
        result = {
            "taskId": "temp",
            "comparisonInfo": {
                "similarityThreshold": similarity_threshold,
                "maxSequences": max_sequences,
                "processingMode": mode_str,
                "contextChars": context_chars,
                "processedAt": time.time()
            },
            "file1Stats": self._convert_stats_to_dict(pdf1_content.stats),
            "file2Stats": self._convert_stats_to_dict(pdf2_content.stats),
            "similarityStats": similarity_stats_dict,
            "similarSequences": similar_sequences_dicts,
            "processingTimeSeconds": time.time() - start_time,
            "exportFiles": {}
        }

        return result

    def _lines_to_char_info(self, lines: List[Tuple[str, int, int]]) -> List:
        """Convert lines (text, page, line_number) to CharInfo objects"""
        from text_processor import CharInfo

        chars = []
        char_position = 0

        for text, page, line_number in lines:
            # For Chinese text, split by characters instead of spaces
            # First try to split by spaces (for English), then handle Chinese
            words = text.split()

            if not words:
                continue

            # Check if this is mostly Chinese text (high ratio of non-ASCII)
            total_chars = sum(len(word) for word in words)
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

            if chinese_chars > total_chars * 0.3:  # If >30% Chinese, treat as Chinese text
                # Split into individual characters for Chinese
                for char in text:
                    if char.strip():  # Skip whitespace
                        chars.append(CharInfo(
                            char=char,
                            page=page,
                            line=line_number,
                            position=char_position
                        ))
                        char_position += 1
            else:
                # For English text, use word-based splitting
                for word in words:
                    if word.strip():
                        chars.append(CharInfo(
                            char=word,
                            page=page,
                            line=line_number,
                            position=char_position
                        ))
                        char_position += 1

        return chars

    def _sequences_to_dict(self, sequences: List) -> Dict[str, List]:
        """Convert list of SequenceInfo to dict format expected by find_similar_sequences"""
        from collections import defaultdict

        result = defaultdict(list)
        for seq_info in sequences:
            result[seq_info.sequence].append(seq_info)

        return dict(result)

    def _convert_stats_to_dict(self, stats) -> Dict[str, Any]:
        """Convert FileStatistics to dict with camelCase keys"""
        if hasattr(stats, 'model_dump'):
            return stats.model_dump(by_alias=True)
        elif hasattr(stats, 'dict'):
            return stats.dict(by_alias=True)
        else:
            return {
                "filePath": getattr(stats, 'file_path', ''),
                "fileSizeMb": getattr(stats, 'file_size_mb', 0),
                "totalPages": getattr(stats, 'total_pages', 0),
                "totalLines": getattr(stats, 'total_lines', 0),
                "mainContentLines": getattr(stats, 'main_content_lines', 0),
                "filteredLines": getattr(stats, 'filtered_lines', 0),
                "totalChars": getattr(stats, 'total_chars', 0),
                "processingTimeSeconds": getattr(stats, 'processing_time_seconds', 0)
            }

    def _configure_processing(
        self,
        processing_mode: ProcessingMode,
        min_similarity: float,
        max_sequences: int
    ) -> Tuple[float, int]:
        """Configure processing parameters based on mode"""

        if processing_mode == ProcessingMode.ULTRA_FAST:
            return max(min_similarity, 0.9), min(max_sequences, 2000)
        elif processing_mode == ProcessingMode.FAST:
            return max(min_similarity, 0.8), min(max_sequences, 5000)
        else:  # STANDARD
            return min_similarity, max_sequences

    async def generate_exports(
        self,
        result: SimilarityResult,
        export_format: ExportFormat = ExportFormat.TEXT,
        task_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate export files for similarity results

        Args:
            result: Similarity detection result
            export_format: Export format
            task_id: Optional task ID

        Returns:
            Dict: Export file paths and URLs
        """
        try:
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)

            timestamp = int(time.time())
            base_filename = f"similarity_result_{result.task_id}_{timestamp}"

            export_files = {}

            if export_format == ExportFormat.TEXT:
                export_files["text"] = await self._generate_text_export(result, export_dir, base_filename)
            elif export_format == ExportFormat.JSON:
                export_files["json"] = await self._generate_json_export(result, export_dir, base_filename)
            elif export_format == ExportFormat.CSV:
                export_files["csv"] = await self._generate_csv_export(result, export_dir, base_filename)

            return export_files

        except Exception as e:
            self.logger.error(f"Error generating exports: {str(e)}", exc_info=True)
            raise

    async def _generate_text_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """Generate text format export"""
        file_path = export_dir / f"{base_filename}.txt"

        def write_text():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("PDF SIMILARITY DETECTION REPORT\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Task ID: {result.task_id}\n")
                f.write(f"Processing Time: {result.processing_time_seconds:.2f} seconds\n")
                f.write(f"Similarity Threshold: {result.comparison_info['similarityThreshold']:.2f}\n")
                f.write(f"Processing Mode: {result.comparison_info['processingMode']}\n\n")

                f.write("SIMILARITY STATISTICS\n")
                f.write("-" * 40 + "\n")
                stats = result.similarity_stats
                f.write(f"Total Sequences Analyzed: {stats.totalSequencesAnalyzed}\n")
                f.write(f"Similar Sequences Found: {stats.similarSequencesFound}\n")
                f.write(f"Average Similarity: {stats.averageSimilarity:.2%}\n")
                f.write(f"Max Similarity: {stats.maxSimilarity:.2%}\n")
                f.write(f"Min Similarity: {stats.minSimilarity:.2%}\n\n")

                f.write("SIMILAR SEQUENCES\n")
                f.write("-" * 40 + "\n")
                for i, seq in enumerate(result.similar_sequences[:50], 1):
                    f.write(f"\n--- Sequence {i} ---\n")
                    f.write(f"Similarity: {seq.similarity:.2%}\n")
                    f.write(f"Text 1: {seq.sequence1[:100]}...\n")
                    f.write(f"Text 2: {seq.sequence2[:100]}...\n")

        await asyncio.to_thread(write_text)
        return str(file_path)

    async def _generate_json_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """Generate JSON format export"""
        import json

        file_path = export_dir / f"{base_filename}.json"

        def write_json():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result.dict(), f, indent=2, default=str)

        await asyncio.to_thread(write_json)
        return str(file_path)

    async def _generate_csv_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """Generate CSV format export"""
        import csv

        file_path = export_dir / f"{base_filename}.csv"

        def write_csv():
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Similarity', 'Text 1', 'Text 2', 'Differences'])
                for seq in result.similar_sequences:
                    writer.writerow([
                        f"{seq.similarity:.2%}",
                        seq.sequence1[:50].replace('\n', ' '),
                        seq.sequence2[:50].replace('\n', ' '),
                        ';'.join(seq.differences)
                    ])

        await asyncio.to_thread(write_csv)
        return str(file_path)
