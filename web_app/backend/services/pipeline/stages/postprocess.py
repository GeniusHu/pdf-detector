#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6: 结果后处理

职责：
- 提取上下文信息
- 生成统计报告
- 格式化最终结果
"""

from typing import Optional, Callable

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class PostProcessingStage(PipelineStage):
    """
    结果后处理阶段

    对相似度检测的结果进行后处理，生成更丰富的统计信息
    """
    stage_name = "结果后处理"
    progress_range = (0.8, 0.9)  # 占80%-90%的进度

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行结果后处理

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 后处理结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "后处理结果...")

        # ========== 步骤1: 验证结果存在 ==========
        if not context.similarity_result:
            context.set_error("缺少相似度检测结果")
            return StageResult(
                success=False,
                error="缺少相似度检测结果"
            )

        result = context.similarity_result

        # ========== 步骤2: 生成统计摘要 ==========
        self._report_progress(0.3, context, progress_callback, "生成统计摘要...")

        similar_sequences = result.similar_sequences or []

        # 按相似度分组统计
        high_count = sum(1 for s in similar_sequences if s.similarity > 0.9)
        medium_count = sum(1 for s in similar_sequences if 0.8 < s.similarity <= 0.9)
        low_count = sum(1 for s in similar_sequences if 0.75 <= s.similarity <= 0.8)

        summary = {
            'high_similarity_count': high_count,
            'medium_similarity_count': medium_count,
            'low_similarity_count': low_count,
            'total_count': len(similar_sequences)
        }

        self.logger.info(
            f"[{context.task_id}] 相似度分布: "
            f"高相似度 {high_count}, 中等 {medium_count}, 低 {low_count}"
        )

        # ========== 步骤3: 构建最终结果 ==========
        self._report_progress(0.6, context, progress_callback, "构建最终结果...")

        # 将相似度结果转换为字典格式
        result_dict = self._build_result_dict(context, result)

        context.stats.update({
            'summary': summary,
            'completed_stages': context.stats.get('completed_stages', []) + ['post_processing']
        })

        context.status = ProcessingStatus.POST_PROCESSING

        self._report_progress(1.0, context, progress_callback, "后处理完成")

        stage_result = StageResult(
            success=True,
            data={
                'summary': summary,
                'result_dict': result_dict
            },
            stats={
                'post_processing_time': True
            }
        )

        self.log_complete(context, stage_result)
        return stage_result

    def _build_result_dict(self, context: PipelineContext, result) -> dict:
        """
        构建结果字典

        Args:
            context: 流水线上下文
            result: 相似度检测结果

        Returns:
            dict: 格式化的结果字典
        """
        # 转换相似度统计
        if hasattr(result, 'model_dump'):
            stats_dict = result.model_dump(by_alias=True)
        elif hasattr(result, 'dict'):
            stats_dict = result.dict(by_alias=True)
        else:
            stats_dict = {}

        # 构建完整结果
        return {
            'taskId': context.task_id,
            'similarSequences': [
                self._sequence_to_dict(seq) for seq in (result.similar_sequences or [])
            ],
            'similarityStats': stats_dict.get('similarityStats', stats_dict),
            'processingTimeSeconds': context.stats.get('detection_time', 0)
        }

    def _sequence_to_dict(self, sequence) -> dict:
        """将序列对象转换为字典"""
        if hasattr(sequence, 'model_dump'):
            return sequence.model_dump(by_alias=True)
        elif hasattr(sequence, 'dict'):
            return sequence.dict(by_alias=True)
        else:
            return sequence
