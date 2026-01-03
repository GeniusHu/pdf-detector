#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理阶段抽象基类

定义所有处理阶段必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging

from .context import PipelineContext, StageResult


class PipelineStage(ABC):
    """
    处理阶段抽象基类

    所有处理阶段都需要继承这个类并实现 process 方法

    Attributes:
        stage_name: 阶段名称（用于日志和进度追踪）
        progress_range: 阶段进度范围 (start, end)，例如 (0.0, 0.15)
        dependencies: 依赖的阶段列表
        config: 阶段配置
    """
    # 阶段名称（子类必须覆盖）
    stage_name: str = "base_stage"

    # 阶段进度范围 (start, end)，例如 (0.0, 0.15) 表示占前15%
    progress_range: tuple = (0.0, 1.0)

    # 依赖的阶段列表（这些阶段必须先执行）
    dependencies: List[str] = []

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化处理阶段

        Args:
            config: 阶段配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行处理逻辑（子类必须实现）

        Args:
            context: 流水线上下文，包含所有中间数据
            progress_callback: 进度回调函数，签名 (progress: float, message: str) -> None

        Returns:
            StageResult: 处理结果，包含 success、data、error 等信息
        """
        raise NotImplementedError(f"{self.__class__.__name__}.process() must be implemented")

    def _report_progress(
        self,
        progress: float,          # 当前阶段内的进度 (0.0-1.0)
        context: PipelineContext,
        progress_callback: Optional[Callable],
        message: str = ""
    ):
        """
        报告进度的辅助方法

        将阶段内的进度映射到全局进度范围，并更新上下文和回调

        Args:
            progress: 当前阶段内的进度 (0.0-1.0)
            context: 流水线上下文
            progress_callback: 进度回调函数
            message: 进度消息

        Example:
            # 假设当前阶段的 progress_range 是 (0.1, 0.3)
            # 调用 _report_progress(0.5, ...) 会报告全局进度 0.2 (0.1 + 0.5 * 0.2)
        """
        start, end = self.progress_range
        global_progress = start + (end - start) * progress

        context.update_progress(global_progress, message, current_stage=self.stage_name)

        if progress_callback:
            progress_callback(global_progress, message or f"{self.stage_name}...")

    def _validate_context(self, context: PipelineContext) -> Optional[str]:
        """
        验证上下文是否包含执行当前阶段所需的数据

        子类可以覆盖此方法以添加自定义验证逻辑

        Args:
            context: 流水线上下文

        Returns:
            None 如果验证通过，否则返回错误消息
        """
        # 检查依赖的阶段是否已执行
        for dep in self.dependencies:
            if dep not in context.stats.get('completed_stages', []):
                return f"依赖阶段 {dep} 未执行"

        return None

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def log_start(self, context: PipelineContext):
        """记录阶段开始日志"""
        self.logger.info(f"[{context.task_id}] ========== {self.stage_name} 开始 ==========")

    def log_complete(self, context: PipelineContext, result: StageResult):
        """记录阶段完成日志"""
        if result.success:
            self.logger.info(
                f"[{context.task_id}] {self.stage_name} 完成 - "
                f"进度: {context.progress*100:.1f}%"
            )
        else:
            self.logger.error(
                f"[{context.task_id}] {self.stage_name} 失败 - "
                f"错误: {result.error}"
            )


class FilterStage(PipelineStage):
    """
    过滤阶段基类

    用于实现可插入到流水线中的过滤器
    """
    filter_name: str = "base_filter"
    description: str = "基础过滤器"

    @abstractmethod
    async def filter(
        self,
        item: Any,
        context: PipelineContext
    ) -> bool:
        """
        过滤单个项目

        Args:
            item: 要过滤的项目
            context: 流水线上下文

        Returns:
            True 表示保留，False 表示过滤掉
        """
        raise NotImplementedError

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """默认处理：不执行任何操作，子类可以覆盖"""
        return StageResult(success=True)
