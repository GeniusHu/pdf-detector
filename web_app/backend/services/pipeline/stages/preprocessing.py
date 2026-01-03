#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段3: 内容预处理

职责：
- 符号清理（过滤标点、特殊符号）
- 段落合并和规范化
- 为序列生成做准备

注意：
当前实现中，DocumentProcessor 已经在提取阶段完成了大部分预处理工作
此阶段作为扩展点，可以添加额外的预处理逻辑
"""

from typing import Optional, Callable

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class PreprocessingStage(PipelineStage):
    """
    内容预处理阶段

    对提取的文本进行进一步处理，为序列生成做准备
    当前版本中大部分预处理已在提取阶段完成
    此阶段保留作为扩展点
    """
    stage_name = "内容预处理"
    progress_range = (0.3, 0.4)  # 占30%-40%的进度

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行内容预处理

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 预处理结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "预处理内容...")

        # ========== 验证必要数据是否存在 ==========
        if not context.doc1_paragraphs or not context.doc2_paragraphs:
            context.set_error("缺少文档段落数据，请先执行文档提取阶段")
            return StageResult(
                success=False,
                error="缺少文档段落数据"
            )

        # ========== 当前预处理逻辑 ==========
        # DocumentProcessor 已经在提取阶段完成了：
        # - 符号清理（只保留中文、英文、数字）
        # - 段落合并（按页面合并）
        # - 去重处理

        # 这里可以作为扩展点，添加额外的预处理逻辑
        # 例如：
        # - 文本规范化（繁简转换、大小写统一）
        # - 敏感信息过滤
        # - 自定义规则应用

        self._report_progress(0.5, context, progress_callback, "检查预处理结果...")

        # 统计预处理后的数据
        doc1_clean_chars = sum(
            getattr(p, 'clean_char_count', len(getattr(p, 'clean_text', '')))
            for p in context.doc1_paragraphs
        )
        doc2_clean_chars = sum(
            getattr(p, 'clean_char_count', len(getattr(p, 'clean_text', '')))
            for p in context.doc2_paragraphs
        )

        context.stats.update({
            'doc1_clean_chars': doc1_clean_chars,
            'doc2_clean_chars': doc2_clean_chars,
            'completed_stages': context.stats.get('completed_stages', []) + ['preprocessing']
        })

        context.status = ProcessingStatus.PREPROCESSING

        self._report_progress(1.0, context, progress_callback, "预处理完成")

        result = StageResult(
            success=True,
            data={
                'doc1_clean_chars': doc1_clean_chars,
                'doc2_clean_chars': doc2_clean_chars
            },
            stats={
                'preprocessing_time': True
            }
        )

        self.log_complete(context, result)
        return result
