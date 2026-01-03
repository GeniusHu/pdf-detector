#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理阶段模块

导出所有处理阶段类，方便统一导入
"""

from .validation import ValidationStage
from .extraction import ExtractionStage
from .preprocessing import PreprocessingStage
from .sequence import SequenceGenerationStage
from .detection import SimilarityDetectionStage
from .postprocess import PostProcessingStage
from .export import ExportStage


# 默认的处理阶段列表（按执行顺序）
DEFAULT_STAGES = [
    ValidationStage,
    ExtractionStage,
    PreprocessingStage,
    SequenceGenerationStage,
    SimilarityDetectionStage,
    PostProcessingStage,
    ExportStage,
]

# 快速模式使用的阶段列表（可能跳过某些阶段）
FAST_STAGES = [
    ValidationStage,
    ExtractionStage,
    PreprocessingStage,
    SequenceGenerationStage,
    SimilarityDetectionStage,
    PostProcessingStage,
    ExportStage,
]

__all__ = [
    'ValidationStage',
    'ExtractionStage',
    'PreprocessingStage',
    'SequenceGenerationStage',
    'SimilarityDetectionStage',
    'PostProcessingStage',
    'ExportStage',
    'DEFAULT_STAGES',
    'FAST_STAGES',
]
