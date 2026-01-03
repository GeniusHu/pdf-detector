#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段2: 文档提取

职责：
- 根据文件类型选择合适的提取器（PDF/Word）
- 提取原始文本内容
- 保留位置信息（页码、行号）
- 支持页面范围过滤（如 1-50 页）
"""

from typing import Optional, Callable

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class ExtractionStage(PipelineStage):
    """
    文档提取阶段

    从PDF或Word文档中提取文本内容，保留位置信息
    支持页面范围过滤，只提取指定页面的内容
    """
    stage_name = "文档提取"
    progress_range = (0.1, 0.3)  # 占10%-30%的进度

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.document_service = None

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行文档提取

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 提取结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "开始提取文档内容...")

        # 延迟导入服务（避免循环依赖）
        from services.document_service import DocumentService

        if self.document_service is None:
            self.document_service = DocumentService()

        request = context.request

        # 获取参数（兼容不同命名方式）
        pdf1_path = getattr(request, 'pdf1_path', None) or getattr(request, 'pdf1Path', None)
        pdf2_path = getattr(request, 'pdf2_path', None) or getattr(request, 'pdf2Path', None)
        content_filter = getattr(request, 'content_filter', None) or getattr(request, 'contentFilter', None)
        page_range1 = getattr(request, 'page_range1', None) or getattr(request, 'pageRange1', None)
        page_range2 = getattr(request, 'page_range2', None) or getattr(request, 'pageRange2', None)

        # ========== 步骤1: 提取文档1 ==========
        self._report_progress(0.2, context, progress_callback, f"提取文档1 ({page_range1 or '全部页面'})...")

        try:
            doc1_content = await self.document_service.extract_document_content(
                pdf1_path,
                content_filter=content_filter,
                page_range=page_range1,
                task_id=context.task_id
            )

            context.doc1_paragraphs = doc1_content.paragraphs
            context.doc1_raw_content = doc1_content.lines

            self.logger.info(
                f"[{context.task_id}] 文档1提取完成: "
                f"{len(doc1_content.paragraphs)} 段落, "
                f"{len(doc1_content.lines)} 行"
            )

        except Exception as e:
            context.set_error(f"文档1提取失败: {str(e)}")
            return StageResult(success=False, error=f"文档1提取失败: {str(e)}")

        # ========== 步骤2: 提取文档2 ==========
        self._report_progress(0.6, context, progress_callback, f"提取文档2 ({page_range2 or '全部页面'})...")

        try:
            doc2_content = await self.document_service.extract_document_content(
                pdf2_path,
                content_filter=content_filter,
                page_range=page_range2,
                task_id=context.task_id
            )

            context.doc2_paragraphs = doc2_content.paragraphs
            context.doc2_raw_content = doc2_content.lines

            self.logger.info(
                f"[{context.task_id}] 文档2提取完成: "
                f"{len(doc2_content.paragraphs)} 段落, "
                f"{len(doc2_content.lines)} 行"
            )

        except Exception as e:
            context.set_error(f"文档2提取失败: {str(e)}")
            return StageResult(success=False, error=f"文档2提取失败: {str(e)}")

        # ========== 步骤3: 统计提取结果 ==========
        self._report_progress(0.9, context, progress_callback, "统计提取结果...")

        # 获取文件统计信息
        stats1 = doc1_content.stats
        stats2 = doc2_content.stats

        context.stats.update({
            'doc1_paragraphs': len(doc1_content.paragraphs),
            'doc2_paragraphs': len(doc2_content.paragraphs),
            'doc1_lines': len(doc1_content.lines),
            'doc2_lines': len(doc2_content.lines),
            'doc1_chars': getattr(stats1, 'totalChars', 0),
            'doc2_chars': getattr(stats2, 'totalChars', 0),
            'completed_stages': context.stats.get('completed_stages', []) + ['extraction']
        })

        context.status = ProcessingStatus.EXTRACTING

        self._report_progress(1.0, context, progress_callback, "文档提取完成")

        result = StageResult(
            success=True,
            data={
                'doc1_stats': {
                    'file_path': pdf1_path,
                    'paragraphs': len(doc1_content.paragraphs),
                    'lines': len(doc1_content.lines),
                    'chars': getattr(stats1, 'totalChars', 0)
                },
                'doc2_stats': {
                    'file_path': pdf2_path,
                    'paragraphs': len(doc2_content.paragraphs),
                    'lines': len(doc2_content.lines),
                    'chars': getattr(stats2, 'totalChars', 0)
                }
            },
            stats={
                'extraction_time': True
            }
        )

        self.log_complete(context, result)
        return result
