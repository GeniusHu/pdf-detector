#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流水线执行器

负责协调各个处理阶段的执行，处理阶段间的数据传递和错误处理
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Type

from .base import PipelineStage
from .context import PipelineContext, StageResult, ProcessingStatus
from .stages import DEFAULT_STAGES

logger = logging.getLogger(__name__)


class ComparisonPipeline:
    """
    文档比对流水线

    负责协调各个处理阶段的执行：
    - 按顺序执行各个阶段
    - 处理阶段间的数据传递
    - 统一的错误处理
    - 进度追踪和报告
    """

    def __init__(
        self,
        stages: Optional[List[Type[PipelineStage]]] = None,
        config: Optional[Dict] = None
    ):
        """
        初始化流水线

        Args:
            stages: 自定义处理阶段列表（默认使用 DEFAULT_STAGES）
            config: 流水线全局配置
        """
        self.stage_classes = stages or DEFAULT_STAGES
        self.config = config or {}
        self.stages: List[PipelineStage] = []
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def add_stage(self, stage_class: Type[PipelineStage], position: Optional[int] = None):
        """
        动态添加处理阶段

        Args:
            stage_class: 阶段类（不是实例）
            position: 插入位置（None表示追加到末尾）

        Example:
            pipeline.add_stage(CustomStage, position=2)  # 插入到第2个位置
        """
        if position is None:
            self.stage_classes.append(stage_class)
        else:
            self.stage_classes.insert(position, stage_class)

        self.logger.info(f"添加处理阶段: {stage_class.stage_name} 到位置 {position if position else '末尾'}")

    def remove_stage(self, stage_name: str):
        """
        移除处理阶段

        Args:
            stage_name: 阶段名称
        """
        original_count = len(self.stage_classes)
        self.stage_classes = [
            s for s in self.stage_classes
            if s.stage_name != stage_name
        ]

        if len(self.stage_classes) < original_count:
            self.logger.info(f"移除处理阶段: {stage_name}")
        else:
            self.logger.warning(f"未找到要移除的阶段: {stage_name}")

    def replace_stage(self, old_stage_name: str, new_stage_class: Type[PipelineStage]):
        """
        替换处理阶段

        Args:
            old_stage_name: 要替换的阶段名称
            new_stage_class: 新的阶段类
        """
        for i, stage_class in enumerate(self.stage_classes):
            if stage_class.stage_name == old_stage_name:
                self.stage_classes[i] = new_stage_class
                self.logger.info(f"替换处理阶段: {old_stage_name} -> {new_stage_class.stage_name}")
                return
        raise ValueError(f"阶段不存在: {old_stage_name}")

    def get_stage_names(self) -> List[str]:
        """
        获取所有阶段名称

        Returns:
            阶段名称列表
        """
        return [s.stage_name for s in self.stage_classes]

    async def execute(
        self,
        request: Any,
        task_id: str,
        progress_callback: Optional[Callable] = None,
        document_service: Any = None,
        similarity_service: Any = None
    ) -> Dict[str, Any]:
        """
        执行流水线

        Args:
            request: 比对请求 (ComparisonRequest)
            task_id: 任务唯一标识符
            progress_callback: 进度回调函数 (progress, message) -> None
            document_service: 文档服务实例（可选，用于依赖注入）
            similarity_service: 相似度服务实例（可选，用于依赖注入）

        Returns:
            Dict: 处理结果，包含:
                - success: 是否成功
                - task_id: 任务ID
                - result: 检测结果数据
                - stats: 统计信息
                - error: 错误信息（失败时）
                - failed_at_stage: 失败的阶段名称（失败时）
        """
        # 创建上下文
        context = PipelineContext(
            task_id=task_id,
            request=request,
            started_at=time.time()
        )

        self.logger.info(f"[Pipeline {task_id}] 开始执行流水线")
        self.logger.info(f"[Pipeline {task_id}] 配置的阶段: {[s.stage_name for s in self.stage_classes]}")

        # 初始化阶段实例
        self.stages = [stage_class(self.config) for stage_class in self.stage_classes]

        # 如果提供了服务实例，注入到需要它们的阶段
        if document_service is not None:
            for stage in self.stages:
                if hasattr(stage, 'document_service'):
                    stage.document_service = document_service

        if similarity_service is not None:
            for stage in self.stages:
                if hasattr(stage, 'similarity_service'):
                    stage.similarity_service = similarity_service

        # ========== 执行各个阶段 ==========
        for i, stage in enumerate(self.stages):
            stage_name = stage.stage_name
            context.current_stage = stage_name
            context.status = ProcessingStatus.VALIDATING if i == 0 else ProcessingStatus.EXTRACTING

            self.logger.info(
                f"[Pipeline {task_id}] "
                f"执行阶段 {i+1}/{len(self.stages)}: {stage_name}"
            )

            # 执行阶段
            result = await stage.process(context, progress_callback)

            # 检查结果
            if not result.success:
                # 阶段失败
                context.status = ProcessingStatus.FAILED
                context.error = result.error
                context.completed_at = time.time()

                self.logger.error(
                    f"[Pipeline {task_id}] 阶段失败: {stage_name} - {result.error}"
                )

                # 返回错误结果
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': result.error,
                    'failed_at_stage': stage_name,
                    'stats': context.stats,
                    'progress': context.progress
                }

            # 记录警告
            if result.warnings:
                for warning in result.warnings:
                    self.logger.warning(f"[Pipeline {task_id}] 警告: {warning}")

            # 合并统计信息
            if result.stats:
                context.stats.update(result.stats)

            # 更新已完成阶段列表
            if 'completed_stages' not in context.stats:
                context.stats['completed_stages'] = []
            if stage_name not in context.stats['completed_stages']:
                context.stats['completed_stages'].append(stage_name)

        # ========== 所有阶段完成 ==========
        context.status = ProcessingStatus.COMPLETED
        context.progress = 1.0
        context.completed_at = time.time()

        processing_time = context.completed_at - context.started_at

        self.logger.info(
            f"[Pipeline {task_id}] 流水线执行完成, "
            f"耗时: {processing_time:.2f}秒"
        )

        # 构建最终结果
        return {
            'success': True,
            'task_id': task_id,
            'result': context.similarity_result,
            'stats': context.stats,
            'export_files': context.export_files,
            'processing_time': processing_time,
            'progress': 1.0
        }


def create_pipeline(
    mode: str = "standard",
    custom_stages: Optional[List[Type[PipelineStage]]] = None
) -> ComparisonPipeline:
    """
    创建流水线实例的工厂函数

    Args:
        mode: 流水线模式 ("standard", "fast", "ultra_fast")
        custom_stages: 自定义阶段列表

    Returns:
        ComparisonPipeline: 流水线实例

    Example:
        # 使用标准模式
        pipeline = create_pipeline(mode="standard")

        # 使用自定义阶段
        pipeline = create_pipeline(custom_stages=[ValidationStage, CustomStage])
    """
    if custom_stages:
        return ComparisonPipeline(stages=custom_stages)

    # 根据模式选择配置
    config = {
        'mode': mode,
        'optimize': mode in ['fast', 'ultra_fast']
    }

    return ComparisonPipeline(config=config)


# 导出
__all__ = [
    'ComparisonPipeline',
    'create_pipeline',
]
