#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段7: 结果导出

职责：
- 生成各种格式的导出文件（TEXT, JSON, CSV）
- 保存导出文件到磁盘
- 返回导出文件路径
"""

from typing import Optional, Callable
import time

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class ExportStage(PipelineStage):
    """
    结果导出阶段

    将检测结果导出为各种格式的文件
    导出失败不影响主流程
    """
    stage_name = "结果导出"
    progress_range = (0.9, 1.0)  # 占90%-100%的进度

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.similarity_service = None

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行结果导出

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 导出结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "生成导出文件...")

        # ========== 步骤1: 检查是否有结果需要导出 ==========
        if not context.similarity_result:
            self.logger.warning(f"[{context.task_id}] 没有检测结果，跳过导出")
            return StageResult(success=True, warnings=["没有检测结果，跳过导出"])

        # ========== 步骤2: 获取导出格式 ==========
        request = context.request
        export_format = getattr(
            request, 'export_format',
            getattr(request, 'exportFormat', 'json')
        )

        self._report_progress(0.2, context, progress_callback, f"生成 {export_format.upper()} 格式导出...")

        # ========== 步骤3: 生成导出文件 ==========
        from services.similarity_service import SimilarityService

        if self.similarity_service is None:
            self.similarity_service = SimilarityService()

        start_time = time.time()

        try:
            export_files = await self.similarity_service.generate_exports(
                context.similarity_result,
                export_format=export_format,
                task_id=context.task_id
            )

            context.export_files = export_files

            export_time = time.time() - start_time

            self.logger.info(
                f"[{context.task_id}] 导出完成: "
                f"{len(export_files)} 个文件, "
                f"耗时 {export_time:.2f}秒"
            )

        except Exception as e:
            # 导出失败不作为整体失败
            self.logger.warning(f"[{context.task_id}] 导出失败: {str(e)}")
            return StageResult(
                success=True,
                warnings=[f"导出失败: {str(e)}"]
            )

        # ========== 步骤4: 更新统计信息 ==========
        context.stats.update({
            'export_files_count': len(export_files),
            'export_formats': list(export_files.keys()) if export_files else [],
            'completed_stages': context.stats.get('completed_stages', []) + ['export']
        })

        context.status = ProcessingStatus.EXPORTING

        self._report_progress(1.0, context, progress_callback, "导出完成")

        result = StageResult(
            success=True,
            data={
                'export_files': export_files,
                'export_count': len(export_files)
            },
            stats={
                'export_time': time.time() - start_time
            }
        )

        self.log_complete(context, result)
        return result
