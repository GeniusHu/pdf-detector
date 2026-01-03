#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5: 相似度检测

职责：
- 序列匹配
- 相似度计算
- 差异分析
- 这是核心计算阶段，耗时最长
"""

from typing import Optional, Callable
import time

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class SimilarityDetectionStage(PipelineStage):
    """
    相似度检测阶段

    核心计算阶段，使用多进程并行算法检测两个文档之间的相似序列
    """
    stage_name = "相似度检测"
    progress_range = (0.5, 0.8)  # 占50%-80%的进度（核心阶段，占比最大）

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.similarity_service = None

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行相似度检测

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 检测结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "开始相似度检测...")

        # 延迟导入服务
        from services.similarity_service import SimilarityService

        if self.similarity_service is None:
            self.similarity_service = SimilarityService()

        request = context.request

        # 获取参数（兼容不同命名方式）
        min_similarity = getattr(
            request, 'similarity_threshold',
            getattr(request, 'similarityThreshold', 0.8)
        )
        max_sequences = getattr(
            request, 'max_sequences',
            getattr(request, 'maxSequences', 5000)
        )
        sequence_length = getattr(
            request, 'sequence_length',
            getattr(request, 'sequenceLength', 8)
        )
        processing_mode = getattr(
            request, 'processing_mode',
            getattr(request, 'processingMode', 'fast')
        )
        context_chars = getattr(
            request, 'context_chars',
            getattr(request, 'contextChars', 100)
        )

        self.logger.info(
            f"[{context.task_id}] 相似度检测参数: "
            f"阈值={min_similarity}, 序列长度={sequence_length}, "
            f"模式={processing_mode}"
        )

        # 定义内部进度回调（将阶段进度映射到全局进度）
        def inner_progress(progress: float, message: str = "", details=None):
            self._report_progress(progress, context, progress_callback, message)
            if details:
                self.logger.debug(f"[{context.task_id}] {message}: {details}")

        start_time = time.time()

        try:
            # ========== 执行相似度检测 ==========
            similarity_result = await self.similarity_service.detect_similarity(
                context.doc1_paragraphs,
                context.doc2_paragraphs,
                min_similarity=min_similarity,
                max_sequences=max_sequences,
                sequence_length=sequence_length,
                processing_mode=processing_mode,
                context_chars=context_chars,
                task_id=context.task_id,
                progress_callback=inner_progress
            )

            # 保存结果到上下文
            context.similar_sequences = similarity_result.similar_sequences
            context.similarity_result = similarity_result

            detection_time = time.time() - start_time

            self.logger.info(
                f"[{context.task_id}] 相似度检测完成: "
                f"找到 {len(similarity_result.similar_sequences)} 个相似序列, "
                f"耗时 {detection_time:.2f}秒"
            )

            # 更新统计信息
            stats_dict = self._pydantic_to_dict(similarity_result.similarity_stats) if similarity_result.similarity_stats else {}
            context.stats.update({
                'similar_sequences_found': len(similarity_result.similar_sequences),
                'average_similarity': stats_dict.get('averageSimilarity', 0),
                'max_similarity': stats_dict.get('maxSimilarity', 0),
                'detection_time': detection_time,
                'completed_stages': context.stats.get('completed_stages', []) + ['detection']
            })

            context.status = ProcessingStatus.DETECTING

            self._report_progress(1.0, context, progress_callback, f"检测完成 (找到{len(similarity_result.similar_sequences)}个相似序列)")

            result = StageResult(
                success=True,
                data={
                    'similar_sequences_count': len(similarity_result.similar_sequences),
                    'statistics': stats_dict
                },
                stats={
                    'detection_time': detection_time
                }
            )

            self.log_complete(context, result)
            return result

        except Exception as e:
            context.set_error(f"相似度检测失败: {str(e)}")
            self.logger.error(f"[{context.task_id}] 相似度检测失败: {str(e)}", exc_info=True)
            return StageResult(success=False, error=f"相似度检测失败: {str(e)}")

    def _pydantic_to_dict(self, model) -> dict:
        """将 Pydantic 模型转换为字典"""
        if hasattr(model, 'model_dump'):
            return model.model_dump(by_alias=True)
        elif hasattr(model, 'dict'):
            return model.dict(by_alias=True)
        elif isinstance(model, dict):
            return model
        return {}
