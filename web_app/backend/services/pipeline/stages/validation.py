#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段1: 输入验证

职责：
- 验证文件路径是否存在
- 验证文件类型是否支持（.pdf, .docx）
- 验证文件大小是否合理
- 验证参数范围（相似度阈值、序列长度等）
"""

import os
from typing import Optional, Callable

from ..base import PipelineStage
from ..context import PipelineContext, StageResult, ProcessingStatus


class ValidationStage(PipelineStage):
    """
    输入验证阶段

    在开始任何处理之前，验证所有输入参数的有效性
    这是流程的第一道防线，尽早发现无效输入
    """
    stage_name = "输入验证"
    progress_range = (0.0, 0.1)  # 占前10%的进度

    # 配置常量
    SUPPORTED_TYPES = ['.pdf', '.docx']
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MIN_FILE_SIZE = 100  # 100字节，排除空文件或损坏文件

    async def process(
        self,
        context: PipelineContext,
        progress_callback: Optional[Callable] = None
    ) -> StageResult:
        """
        执行输入验证

        Args:
            context: 流水线上下文
            progress_callback: 进度回调

        Returns:
            StageResult: 验证结果
        """
        self.log_start(context)
        self._report_progress(0.0, context, progress_callback, "开始验证输入参数...")

        request = context.request
        warnings = []
        data = {}

        # ========== 步骤1: 验证文件路径 ==========
        self._report_progress(0.2, context, progress_callback, "验证文件路径...")

        pdf1_path = request.pdf1_path if hasattr(request, 'pdf1_path') else request.pdf1Path
        pdf2_path = request.pdf2_path if hasattr(request, 'pdf2_path') else request.pdf2Path

        # 兼容不同的命名方式
        if not pdf1_path:
            pdf1_path = getattr(request, 'pdf1Path', None)
        if not pdf2_path:
            pdf2_path = getattr(request, 'pdf2Path', None)

        if not pdf1_path or not pdf2_path:
            context.set_error("文件路径不能为空")
            return StageResult(success=False, error="文件路径不能为空")

        # ========== 步骤2: 验证文件1 ==========
        self._report_progress(0.3, context, progress_callback, "验证文件1...")

        result1 = await self._validate_file(pdf1_path, "文件1")
        if not result1['valid']:
            context.set_error(result1['error'])
            return StageResult(success=False, error=result1['error'])

        warnings.extend(result1.get('warnings', []))
        data['file1'] = result1

        # ========== 步骤3: 验证文件2 ==========
        self._report_progress(0.5, context, progress_callback, "验证文件2...")

        result2 = await self._validate_file(pdf2_path, "文件2")
        if not result2['valid']:
            context.set_error(result2['error'])
            return StageResult(success=False, error=result2['error'])

        warnings.extend(result2.get('warnings', []))
        data['file2'] = result2

        # ========== 步骤4: 验证参数范围 ==========
        self._report_progress(0.7, context, progress_callback, "验证参数范围...")

        # 获取相似度阈值（兼容不同命名）
        similarity_threshold = getattr(request, 'similarity_threshold', None) or getattr(request, 'similarityThreshold', 0.8)

        if not 0.0 <= similarity_threshold <= 1.0:
            return StageResult(
                success=False,
                error=f"相似度阈值超出范围: {similarity_threshold}，必须在0.0-1.0之间"
            )

        # 验证序列长度
        sequence_length = getattr(request, 'sequence_length', None) or getattr(request, 'sequenceLength', 8)

        if not 4 <= sequence_length <= 20:
            warnings.append(f"序列长度建议在4-20之间，当前值: {sequence_length}")

        # 验证最大序列数
        max_sequences = getattr(request, 'max_sequences', None) or getattr(request, 'maxSequences', 5000)

        if max_sequences < 100 or max_sequences > 100000:
            warnings.append(f"最大序列数建议在100-100000之间，当前值: {max_sequences}")

        # 验证上下文字符数
        context_chars = getattr(request, 'context_chars', None) or getattr(request, 'contextChars', 100)

        if context_chars < 0 or context_chars > 1000:
            warnings.append(f"上下文字符数建议在0-1000之间，当前值: {context_chars}")

        # ========== 步骤5: 验证完成 ==========
        self._report_progress(1.0, context, progress_callback, "验证完成")

        # 保存验证信息到上下文
        context.stats.update({
            'file1_type': result1['ext'],
            'file2_type': result2['ext'],
            'file1_size': result1['size'],
            'file2_size': result2['size'],
            'file1_size_mb': round(result1['size'] / (1024 * 1024), 2),
            'file2_size_mb': round(result2['size'] / (1024 * 1024), 2),
            'validation_passed': True,
            'completed_stages': ['validation']
        })

        context.status = ProcessingStatus.VALIDATING

        result = StageResult(
            success=True,
            data=data,
            warnings=warnings,
            stats={
                'validation_time': True
            }
        )

        self.log_complete(context, result)
        return result

    async def _validate_file(self, file_path: str, file_label: str) -> dict:
        """
        验证单个文件

        Args:
            file_path: 文件路径
            file_label: 文件标签（用于日志）

        Returns:
            dict: 验证结果
                - valid: 是否有效
                - error: 错误信息（无效时）
                - ext: 文件扩展名
                - size: 文件大小
                - warnings: 警告列表
        """
        warnings = []

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {'valid': False, 'error': f"{file_label}不存在: {file_path}"}

        # 检查是否为文件
        if not os.path.isfile(file_path):
            return {'valid': False, 'error': f"{file_label}不是有效的文件: {file_path}"}

        # 检查文件扩展名
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_TYPES:
            return {'valid': False, 'error': f"不支持的文件类型: {ext}，支持的类型: {', '.join(self.SUPPORTED_TYPES)}"}

        # 检查文件大小
        size = os.path.getsize(file_path)

        if size == 0:
            return {'valid': False, 'error': f"{file_label}为空"}

        if size < self.MIN_FILE_SIZE:
            warnings.append(f"{file_label}文件较小: {size} 字节")

        if size > self.MAX_FILE_SIZE:
            size_mb = size / (1024 * 1024)
            warnings.append(f"{file_label}文件较大: {size_mb:.1f}MB，可能需要较长处理时间")

        return {
            'valid': True,
            'ext': ext,
            'size': size,
            'path': file_path,
            'warnings': warnings
        }
