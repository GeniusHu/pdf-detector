#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段4: 序列生成

职责：
- 从段落生成N字序列
- 保留序列位置信息
- 生成哈希签名（用于快速匹配）
- 应用序列数量限制
"""

from typing import Optional, Callable

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class SequenceGenerationStage(PipelineStage):
    """
    序列生成阶段

    将预处理后的段落切分成固定长度的字符序列
    这些序列将用于后续的相似度匹配
    """
    stage_name = "序列生成"
    progress_range = (0.4, 0.5)  # 占40%-50%的进度

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行序列生成

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 生成结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "生成字符序列...")

        # 获取序列长度参数
        sequence_length = getattr(
            context.request, 'sequence_length',
            getattr(context.request, 'sequenceLength', 8)
        )

        # ========== 步骤1: 初始化序列生成器 ==========
        self._report_progress(0.1, context, progress_callback, f"初始化序列生成器 (长度={sequence_length})...")

        from document_processor import SequenceGenerator
        generator = SequenceGenerator(sequence_length)

        # ========== 步骤2: 生成文档1的序列 ==========
        self._report_progress(0.3, context, progress_callback, "生成文档1序列...")

        doc1_sequences = generator.generate_from_paragraphs(context.doc1_paragraphs)

        self.logger.info(f"[{context.task_id}] 文档1生成 {len(doc1_sequences):,} 个序列")

        # ========== 步骤3: 生成文档2的序列 ==========
        self._report_progress(0.6, context, progress_callback, "生成文档2序列...")

        doc2_sequences = generator.generate_from_paragraphs(context.doc2_paragraphs)

        self.logger.info(f"[{context.task_id}] 文档2生成 {len(doc2_sequences):,} 个序列")

        # ========== 步骤4: 应用序列数量限制 ==========
        self._report_progress(0.8, context, progress_callback, "应用序列数量限制...")

        max_sequences = getattr(
            context.request, 'max_sequences',
            getattr(context.request, 'maxSequences', 5000)
        )

        original_doc1_count = len(doc1_sequences)
        original_doc2_count = len(doc2_sequences)

        if len(doc1_sequences) > max_sequences:
            doc1_sequences = doc1_sequences[:max_sequences]
            self.logger.warning(
                f"[{context.task_id}] 文档1序列数从 {original_doc1_count:,} 限制到 {max_sequences:,}"
            )

        if len(doc2_sequences) > max_sequences:
            doc2_sequences = doc2_sequences[:max_sequences]
            self.logger.warning(
                f"[{context.task_id}] 文档2序列数从 {original_doc2_count:,} 限制到 {max_sequences:,}"
            )

        # 保存到上下文
        context.doc1_sequences = doc1_sequences
        context.doc2_sequences = doc2_sequences

        # 更新统计信息
        context.stats.update({
            'doc1_sequences': len(doc1_sequences),
            'doc2_sequences': len(doc2_sequences),
            'doc1_sequences_limited': original_doc1_count > max_sequences,
            'doc2_sequences_limited': original_doc2_count > max_sequences,
            'completed_stages': context.stats.get('completed_stages', []) + ['sequence_generation']
        })

        context.status = ProcessingStatus.GENERATING_SEQUENCES

        self._report_progress(1.0, context, progress_callback, f"序列生成完成 (共{len(doc1_sequences)+len(doc2_sequences):,}个)")

        result = StageResult(
            success=True,
            data={
                'doc1_sequence_count': len(doc1_sequences),
                'doc2_sequence_count': len(doc2_sequences),
                'total_sequences': len(doc1_sequences) + len(doc2_sequences),
                'sequence_length': sequence_length
            },
            stats={
                'sequence_generation_time': True
            }
        )

        self.log_complete(context, result)
        return result
