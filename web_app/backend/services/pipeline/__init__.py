#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档比对流水线模块

提供标准化的文档比对流程，支持模块化的处理阶段
"""

from .context import PipelineContext, StageResult, ProcessingStatus
from .base import PipelineStage, FilterStage
from .pipeline import ComparisonPipeline, create_pipeline

# 导出所有阶段类
from .stages import (
    ValidationStage,
    ExtractionStage,
    PreprocessingStage,
    SequenceGenerationStage,
    SimilarityDetectionStage,
    PostProcessingStage,
    ExportStage,
    DEFAULT_STAGES,
)

__all__ = [
    # 核心类
    'PipelineContext',
    'StageResult',
    'ProcessingStatus',
    'PipelineStage',
    'FilterStage',
    'ComparisonPipeline',
    'create_pipeline',

    # 处理阶段
    'ValidationStage',
    'ExtractionStage',
    'PreprocessingStage',
    'SequenceGenerationStage',
    'SimilarityDetectionStage',
    'PostProcessingStage',
    'ExportStage',
    'DEFAULT_STAGES',
]
