#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流水线上下文和结果数据类

定义在各个处理阶段之间传递的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ProcessingStatus(str, Enum):
    """
    处理状态枚举

    定义任务在各个阶段可能的状态
    """
    PENDING = "pending"              # 等待处理
    VALIDATING = "validating"        # 输入验证中
    EXTRACTING = "extracting"        # 文档提取中
    PREPROCESSING = "preprocessing"  # 内容预处理中
    GENERATING_SEQUENCES = "generating_sequences"  # 序列生成中
    DETECTING = "detecting"          # 相似度检测中
    POST_PROCESSING = "post_processing"  # 后处理中
    EXPORTING = "exporting"          # 导出中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败


@dataclass
class StageResult:
    """
    处理阶段结果

    每个处理阶段返回标准化的结果对象

    Attributes:
        success: 是否成功
        data: 阶段输出数据字典
        error: 错误信息（失败时）
        warnings: 警告信息列表
        stats: 阶段统计信息
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """布尔值转换，方便判断: if result: ..."""
        return self.success


@dataclass
class PipelineContext:
    """
    流水线上下文

    在各个处理阶段之间传递数据和状态的核心数据结构

    Attributes:
        # === 输入参数 ===
        task_id: 任务唯一标识符
        request: 比对请求对象 (ComparisonRequest)

        # === 文档原始数据 ===
        doc1_raw_content: 文档1原始内容列表 [(text, page, line), ...]
        doc2_raw_content: 文档2原始内容列表

        # === 文档结构化数据 ===
        doc1_paragraphs: 文档1处理后的段落列表
        doc2_paragraphs: 文档2处理后的段落列表

        # === 序列数据 ===
        doc1_sequences: 文档1的N字序列列表
        doc2_sequences: 文档2的N字序列列表

        # === 检测结果 ===
        similar_sequences: 找到的相似序列列表
        similarity_result: 完整的相似度检测结果对象

        # === 导出文件 ===
        export_files: 导出文件路径字典 {format: file_path}

        # === 处理状态 ===
        current_stage: 当前执行到的阶段名称
        progress: 全局进度 (0.0-1.0)
        status: 当前处理状态 (ProcessingStatus枚举)

        # === 错误信息 ===
        error: 错误消息
        error_details: 错误详细信息

        # === 统计信息 ===
        stats: 各种统计数据的字典

        # === 时间戳 ===
        started_at: 开始时间戳
        completed_at: 完成时间戳
    """
    # === 输入参数 ===
    task_id: str
    request: Any

    # === 文档原始数据 ===
    doc1_raw_content: Optional[List[tuple]] = None
    doc2_raw_content: Optional[List[tuple]] = None

    # === 文档结构化数据 ===
    doc1_paragraphs: Optional[List] = None
    doc2_paragraphs: Optional[List] = None

    # === 序列数据 ===
    doc1_sequences: Optional[List] = None
    doc2_sequences: Optional[List] = None

    # === 检测结果 ===
    similar_sequences: Optional[List] = None
    similarity_result: Optional[Any] = None

    # === 导出文件 ===
    export_files: Dict[str, str] = field(default_factory=dict)

    # === 处理状态 ===
    current_stage: str = "pending"
    progress: float = 0.0
    status: ProcessingStatus = ProcessingStatus.PENDING

    # === 错误信息 ===
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # === 统计信息 ===
    stats: Dict[str, Any] = field(default_factory=dict)

    # === 时间戳 ===
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def get_progress_range(self, start: float, end: float) -> tuple:
        """
        获取当前阶段的进度范围

        Args:
            start: 阶段起始进度 (0.0-1.0)
            end: 阶段结束进度 (0.0-1.0)

        Returns:
            (start, end) 进度范围元组
        """
        return (start, end)

    def update_progress(self, progress: float, message: str = "", **kwargs):
        """
        更新进度

        Args:
            progress: 进度值 (0.0-1.0)
            message: 进度消息
            **kwargs: 额外的状态信息
        """
        self.progress = progress
        if message:
            self.stats['last_message'] = message
        if kwargs:
            self.stats.update(kwargs)

    def set_error(self, error: str, details: Optional[Dict] = None):
        """
        设置错误状态

        Args:
            error: 错误消息
            details: 错误详情
        """
        self.error = error
        self.error_details = details
        self.status = ProcessingStatus.FAILED

    def is_failed(self) -> bool:
        """检查是否已失败"""
        return self.status == ProcessingStatus.FAILED

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.status == ProcessingStatus.COMPLETED

    def get_processing_time(self) -> Optional[float]:
        """
        获取处理耗时（秒）

        Returns:
            处理耗时，未完成时返回 None
        """
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
