#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 相似度检测服务模块

本模块提供了基于优化算法的文档相似度检测服务，主要功能包括：
1. 使用 DocumentProcessor 进行文档内容提取和处理
2. 通过多进程并行比较算法实现高效的相似度检测
3. 支持多种处理模式（超快速、快速、标准）
4. 提供详细的相似度统计和结果导出功能

核心算法：
- 基于字符序列的相似度匹配
- 使用滑动窗口技术生成特征序列
- 多进程并行比较提升性能
- 支持上下文提取和差异分析
"""

# 标准库导入
import asyncio  # 异步编程支持，用于处理并发IO操作
import os  # 操作系统接口，用于文件路径和系统操作
import time  # 时间处理，用于性能计时和时间戳
import json  # JSON数据处理
import csv  # CSV文件处理
from typing import List, Dict, Any, Optional, Tuple, Callable  # 类型注解支持
from pathlib import Path  # 面向对象的文件系统路径操作
import logging  # 日志记录

# 导入项目自定义模块
import sys
# 将项目根目录添加到Python路径，确保可以导入项目模块
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 文档处理相关模块
from document_processor import (
    DocumentProcessor,  # 文档处理器，负责从PDF/DOCX提取内容
    DocumentContent,   # 文档内容数据结构
    Paragraph,         # 段落数据结构
    SequenceGenerator  # 序列生成器，用于生成字符序列
)
from text_processor import CharInfo  # 字符信息类，记录字符的位置和属性

# 优化的序列生成和相似度计算模块
from optimized_sequence_generator import (
    OptimizedSequenceGenerator,  # 优化的序列生成器
    SequenceInfo,               # 序列信息数据结构
    SimilarSequenceInfo,        # 相似序列信息数据结构
    FastSimilarityCalculator    # 快速相似度计算器
)

# PDF文本提取配置
from enhanced_pdf_extractor import TextExtractionConfig

# API模型定义
from models.api_models import (
    SimilarityResult,      # 相似度检测结果模型
    SimilarSequence,       # 相似序列模型
    SimilarityStatistics,  # 相似度统计模型
    ProcessingMode,        # 处理模式枚举
    ExportFormat           # 导出格式枚举
)
from services.document_service import DocumentContent as WebDocumentContent  # Web服务中的文档内容模型

# 模块日志记录器
logger = logging.getLogger(__name__)


class SimilarityService:
    """
    相似度检测服务类

    提供文档相似度检测的核心服务功能，包括：
    - 文档内容比较
    - 相似序列检测
    - 统计信息生成
    - 结果导出

    使用优化算法提升性能：
    - 多进程并行处理
    - 高效的序列匹配算法
    - 智能的内存管理
    """

    def __init__(self):
        """
        初始化相似度检测服务

        创建日志记录器实例用于记录服务运行状态和错误信息
        """
        self.logger = logging.getLogger(__name__)

    def _parse_page_range(self, page_range_str: Optional[str]) -> Optional[Tuple[int, int]]:
        """
        解析页码范围字符串

        将格式为 "1-146" 的页码范围字符串解析为元组 (1, 146)
        用于限制文档处理范围，提升处理速度

        Args:
            page_range_str: 页码范围字符串，格式为 "起始页-结束页"

        Returns:
            Optional[Tuple[int, int]]: 解析后的(起始页, 结束页)元组，解析失败返回None

        Examples:
            >>> _parse_page_range("1-146")
            (1, 146)
            >>> _parse_page_range("10-20")
            (10, 20)
            >>> _parse_page_range(None)
            None
        """
        # 如果输入为空，返回None表示处理全部页面
        if not page_range_str:
            return None

        try:
            # 去除首尾空格并按'-'分割
            parts = page_range_str.strip().split('-')
            if len(parts) == 2:
                # 转换为整数
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                # 验证页码范围的有效性：起始页大于0，结束页不小于起始页
                if start > 0 and end >= start:
                    return (start, end)
        except (ValueError, AttributeError):
            # 捕获类型转换或属性访问异常
            pass

        # 解析失败，返回None
        return None

    async def detect_similarity(
        self,
        doc1_content: WebDocumentContent,
        doc2_content: WebDocumentContent,
        min_similarity: float = 0.90,
        max_sequences: int = 5000,
        sequence_length: int = 8,
        processing_mode: ProcessingMode = ProcessingMode.FAST,
        context_chars: int = 100,
        task_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> SimilarityResult:
        """
        检测两个文档之间的相似度（异步方法）

        这是服务的主要入口方法，协调整个相似度检测流程：
        1. 根据处理模式配置参数
        2. 生成字符序列
        3. 执行相似度比较
        4. 生成详细结果

        Args:
            doc1_content: 第一个文档的内容对象（来自DocumentService）
            doc2_content: 第二个文档的内容对象（来自DocumentService）
            min_similarity: 最小相似度阈值（0.0-1.0），低于此值的序列将被忽略
            max_sequences: 每个文档的最大序列数量限制，防止内存溢出
            sequence_length: 序列生成时的连续字符数量（窗口大小）
            processing_mode: 处理速度模式（ULTRA_FAST/FAST/STANDARD）
            context_chars: 匹配序列周围的上下文字符数量
            task_id: 可选的任务ID，用于进度跟踪
            progress_callback: 可选的进度回调函数，用于报告处理进度

        Returns:
            SimilarityResult: 完整的相似度检测结果，包含：
                - 相似序列列表
                - 统计信息
                - 文件信息
                - 处理时间等

        Raises:
            Exception: 当处理过程中发生错误时抛出异常

        Note:
            此方法使用异步IO，在单独的线程池中执行CPU密集型任务
        """
        # 记录开始日志
        self.logger.info(f"[SIM] Starting similarity detection with sequence_length={sequence_length}")
        start_time = time.time()

        try:
            # 根据处理模式配置处理参数（相似度阈值和最大序列数）
            # 不同模式有不同的默认值，以平衡速度和准确性
            similarity_threshold, max_seqs = self._configure_processing(
                processing_mode, min_similarity, max_sequences
            )

            # 在线程池中执行同步的相似度检测任务
            # 使用 asyncio.to_thread 避免阻塞事件循环
            result = await asyncio.to_thread(
                self._detect_similarity_sync,
                doc1_content.paragraphs,  # 文档1的段落列表
                doc2_content.paragraphs,  # 文档2的段落列表
                doc1_content.file_path,   # 文档1的文件路径
                doc2_content.file_path,   # 文档2的文件路径
                similarity_threshold,     # 配置后的相似度阈值
                max_seqs,                 # 配置后的最大序列数
                sequence_length,          # 序列长度
                context_chars,            # 上下文字符数
                progress_callback         # 进度回调
            )

            # 记录完成日志
            self.logger.info(f"[SIM] Detection completed: {len(result['similarSequences'])} sequences, {time.time() - start_time:.2f}s")

            # 将字典结果转换为 SimilarityResult 对象并返回
            return SimilarityResult(**result)

        except Exception as e:
            # 记录错误详情（包括堆栈跟踪）
            self.logger.error(f"Error in similarity detection: {str(e)}", exc_info=True)
            # 重新抛出异常，让上层处理
            raise

    def _detect_similarity_sync(
        self,
        paragraphs1: List[Paragraph],
        paragraphs2: List[Paragraph],
        file1_path: str,
        file2_path: str,
        similarity_threshold: float,
        max_sequences: int,
        sequence_length: int,
        context_chars: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        同步执行相似度检测（在线程池中运行）

        这是实际的相似度检测实现，包含四个主要步骤：
        1. 从段落生成字符序列
        2. 转换为SequenceInfo对象格式
        3. 多进程并行相似度检测
        4. 构建包含上下文的结果

        Args:
            paragraphs1: 文档1的段落列表
            paragraphs2: 文档2的段落列表
            file1_path: 文档1的文件路径
            file2_path: 文档2的文件路径
            similarity_threshold: 相似度阈值
            max_sequences: 最大序列数
            sequence_length: 序列长度
            context_chars: 上下文字符数
            progress_callback: 进度回调函数

        Returns:
            Dict[str, Any]: 包含完整检测结果的字典
        """
        # 记录开始时间，用于计算总处理时间
        start_time = time.time()

        # ========== 步骤1：从段落生成序列 ==========
        # 使用SequenceGenerator从段落中提取固定长度的字符序列
        # 这是相似度检测的基础，将连续的文本切分为可比较的单元
        print(f"\n[{'='*60}")
        print(f"[SIM] Step 1: Generating sequences from paragraphs")
        print(f"[{'='*60}")

        # 创建序列生成器，使用指定的序列长度
        generator = SequenceGenerator(sequence_length)

        # 从两个文档的段落中生成序列列表
        # 每个序列包含：实际文本、原始文本、段落对象、起始位置等信息
        sequences1_list = generator.generate_from_paragraphs(paragraphs1)
        sequences2_list = generator.generate_from_paragraphs(paragraphs2)

        print(f"[SIM] File 1: {len(sequences1_list):,} sequences generated from {len(paragraphs1)} paragraphs")
        print(f"[SIM] File 2: {len(sequences2_list):,} sequences generated from {len(paragraphs2)} paragraphs")

        # 如果序列数量超过限制，进行截断以防止内存溢出
        # 优先保留前面的序列（通常文档开头更重要）
        if len(sequences1_list) > max_sequences:
            print(f"[SIM] Limiting file 1 sequences from {len(sequences1_list):,} to {max_sequences:,}")
            sequences1_list = sequences1_list[:max_sequences]
        if len(sequences2_list) > max_sequences:
            print(f"[SIM] Limiting file 2 sequences from {len(sequences2_list):,} to {max_sequences:,}")
            sequences2_list = sequences2_list[:max_sequences]

        # ========== 步骤2：转换为SequenceInfo对象格式 ==========
        # 将字典格式的序列列表转换为SequenceInfo对象
        # SequenceInfo包含更丰富的元数据，用于后续的比较算法
        print(f"\n[{'='*60}")
        print(f"[SIM] Step 2: Converting to SequenceInfo format")
        print(f"[{'='*60}")

        sequences1 = self._convert_to_sequence_info(sequences1_list, 0)
        sequences2 = self._convert_to_sequence_info(sequences2_list, 1)

        # ========== 步骤3：多进程相似度检测 ==========
        # 使用OptimizedSequenceGenerator进行高效的并行相似度比较
        print(f"\n[{'='*60}")
        print(f"[SIM] Step 3: Running multi-process similarity detection")
        print(f"[{'='*60}")
        print(f"[SIM] Similarity threshold: {similarity_threshold:.2f}")
        print(f"[SIM] Sequence length: {sequence_length}")
        print(f"[SIM] File 1 sequences: {len(sequences1):,}")
        print(f"[SIM] File 2 sequences: {len(sequences2):,}")

        # 创建优化的序列生成器，使用指定的相似度阈值和序列长度
        opt_generator = OptimizedSequenceGenerator(similarity_threshold, sequence_length)

        # 创建进度包装器，将进度信息标准化后传递给回调函数
        # 进度范围：30%-80%（序列生成占用0-30%，此步骤占用30-80%）
        def progress_wrapper(progress, completed, total):
            if progress_callback:
                progress_callback(0.3 + 0.5 * progress, "Detecting similarities", {"completed": completed, "total": total})
            print(f"   Progress: {completed}/{total} ({progress*100:.1f}%)")

        # 执行并行比较，查找相似的序列对
        # 返回按相似度排序的相似序列列表
        similar_sequences = opt_generator.find_similar_sequences_parallel(
            sequences1, sequences2, progress_wrapper
        )

        # ========== 步骤4：构建包含上下文的结果 ==========
        # 为每个相似序列提取上下文信息，生成完整的结果报告
        print(f"\n[{'='*60}")
        print(f"[SIM] Step 4: Building results")
        print(f"[{'='*60}")
        print(f"[SIM] Found {len(similar_sequences):,} similar sequences")

        # 构建相似序列结果列表，包含上下文和位置信息
        result_similar_sequences = []
        for i, seq_info in enumerate(similar_sequences):
            # 从原始段落中获取上下文信息
            # 注意：使用start_index从sequences_list中找到对应的段落
            para1 = sequences1_list[seq_info.sequence1.start_index]['paragraph']
            para2 = sequences2_list[seq_info.sequence2.start_index]['paragraph']

            # 提取匹配文本前后的上下文（各占context_chars的一半）
            before1, after1 = self._extract_context_from_paragraph(
                para1, seq_info.sequence1.sequence, context_chars // 2
            )
            before2, after2 = self._extract_context_from_paragraph(
                para2, seq_info.sequence2.sequence, context_chars // 2
            )

            # 构建序列详情字典
            seq_dict = {
                # 使用原始序列（如果有的话），否则使用清理后的序列
                "sequence1": seq_info.sequence1.raw_sequence or seq_info.sequence1.sequence,
                "sequence2": seq_info.sequence2.raw_sequence or seq_info.sequence2.sequence,
                "similarity": float(seq_info.similarity),  # 转换为Python float类型
                "position1": {
                    "page": seq_info.sequence1.start_char.page,      # 文档1中的页码
                    "line": seq_info.sequence1.start_char.line,      # 文档1中的行号
                    "charIndex": seq_info.sequence1.start_index      # 文档1中的字符索引
                },
                "position2": {
                    "page": seq_info.sequence2.start_char.page,      # 文档2中的页码
                    "line": seq_info.sequence2.start_char.line,      # 文档2中的行号
                    "charIndex": seq_info.sequence2.start_index      # 文档2中的字符索引
                },
                "context1": {
                    "before": before1,  # 文档1中匹配前的上下文
                    "after": after1     # 文档1中匹配后的上下文
                },
                "context2": {
                    "before": before2,  # 文档2中匹配前的上下文
                    "after": after2     # 文档2中匹配后的上下文
                },
                # 差异列表（如果有的话）
                "differences": seq_info.differences if hasattr(seq_info, 'differences') else []
            }
            result_similar_sequences.append(SimilarSequence(**seq_dict))

        # ========== 创建统计信息 ==========
        # 计算各种相似度统计指标，用于结果分析和展示
        total_seqs = len(sequences1) + len(sequences2)
        similarity_stats = SimilarityStatistics(
            totalSequencesAnalyzed=total_seqs,  # 分析的总序列数
            similarSequencesFound=len(similar_sequences),  # 找到的相似序列数
            # 高相似度序列数量（相似度 > 90%）
            highSimilarityCount=len([s for s in similar_sequences if s.similarity > 0.9]),
            # 中等相似度序列数量（80% < 相似度 <= 90%）
            mediumSimilarityCount=len([s for s in similar_sequences if 0.8 < s.similarity <= 0.9]),
            # 低相似度序列数量（75% <= 相似度 <= 80%）
            lowSimilarityCount=len([s for s in similar_sequences if 0.75 <= s.similarity <= 0.8]),
            # 平均相似度
            averageSimilarity=sum(s.similarity for s in similar_sequences) / len(similar_sequences) if similar_sequences else 0,
            # 最高相似度
            maxSimilarity=max(s.similarity for s in similar_sequences) if similar_sequences else 0,
            # 最低相似度
            minSimilarity=min(s.similarity for s in similar_sequences) if similar_sequences else 0
        )

        # 将统计对象转换为字典（兼容Pydantic v1和v2）
        if hasattr(similarity_stats, 'model_dump'):
            # Pydantic v2
            similarity_stats_dict = similarity_stats.model_dump(by_alias=True)
        else:
            # Pydantic v1
            similarity_stats_dict = similarity_stats.dict(by_alias=True)

        # 将SimilarSequence对象转换为字典列表
        similar_sequences_dicts = []
        for seq in result_similar_sequences:
            if hasattr(seq, 'model_dump'):
                similar_sequences_dicts.append(seq.model_dump(by_alias=True))
            else:
                similar_sequences_dicts.append(seq.dict(by_alias=True))

        # ========== 创建文件统计信息 ==========
        file1_stats = self._create_file_stats(file1_path, paragraphs1)
        file2_stats = self._create_file_stats(file2_path, paragraphs2)

        # 根据相似度阈值确定处理模式字符串
        mode_str = "ultra_fast" if similarity_threshold >= 0.9 else ("fast" if similarity_threshold >= 0.8 else "standard")

        # ========== 构建最终结果 ==========
        result = {
            "taskId": "temp",  # 任务ID（临时值，会被上层覆盖）
            "comparisonInfo": {
                "similarityThreshold": similarity_threshold,  # 使用的相似度阈值
                "maxSequences": max_sequences,                 # 使用的最大序列数
                "processingMode": mode_str,                    # 处理模式
                "contextChars": context_chars,                 # 上下文字符数
                "processedAt": time.time()                     # 处理时间戳
            },
            "file1Stats": file1_stats,           # 文件1的统计信息
            "file2Stats": file2_stats,           # 文件2的统计信息
            "similarityStats": similarity_stats_dict,  # 相似度统计
            "similarSequences": similar_sequences_dicts,  # 相似序列列表
            "processingTimeSeconds": time.time() - start_time,  # 总处理时间
            "exportFiles": {}                    # 导出文件信息（后续填充）
        }

        return result

    def _convert_to_sequence_info(self, sequences_list: List[Dict], file_index: int) -> List[SequenceInfo]:
        """
        将字典格式的序列列表转换为SequenceInfo对象列表

        SequenceInfo对象包含更丰富的元数据，包括：
        - 序列的起始和结束字符信息（CharInfo对象）
        - 序列的哈希签名，用于快速比较
        - 完整的字符列表
        - 原始序列（清理前）

        Args:
            sequences_list: 字典格式的序列列表，来自SequenceGenerator
            file_index: 文件索引（0或1），用于标识来源文件

        Returns:
            List[SequenceInfo]: SequenceInfo对象列表
        """
        from document_processor import SymbolCleaner
        import hashlib

        sequence_infos = []
        cleaner = SymbolCleaner()

        # 遍历每个序列字典，转换为SequenceInfo对象
        for i, seq_dict in enumerate(sequences_list):
            paragraph = seq_dict['paragraph']

            # 创建序列起始位置的字符信息对象
            start_char = CharInfo(
                char=seq_dict['sequence'][0] if seq_dict['sequence'] else '',  # 序列的第一个字符
                page=paragraph.start_page,       # 所在页码
                line=paragraph.start_line,       # 所在行号
                position=seq_dict['start_pos']   # 在段落中的位置
            )

            # 创建序列结束位置的字符信息对象
            end_char = CharInfo(
                char=seq_dict['sequence'][-1] if seq_dict['sequence'] else '',  # 序列的最后一个字符
                page=paragraph.start_page,       # 所在页码
                line=paragraph.start_line,       # 所在行号
                position=seq_dict['start_pos'] + len(seq_dict['sequence']) - 1  # 结束位置
            )

            # 创建哈希签名（使用MD5前8位）用于快速比较和去重
            # MD5虽然不是加密安全的，但对于这个用例已经足够
            hash_signature = hashlib.md5(seq_dict['sequence'].encode()).hexdigest()[:8]

            # 构建SequenceInfo对象
            seq_info = SequenceInfo(
                sequence=seq_dict['sequence'],           # 清理后的序列文本
                raw_sequence=seq_dict.get('raw_sequence', ''),  # 原始序列文本（如果有的话）
                start_index=i,                          # 序列在列表中的索引
                start_char=start_char,                  # 起始字符信息
                end_char=end_char,                      # 结束字符信息
                chars=[],                               # 字符列表（比较时未使用，设为空）
                hash_signature=hash_signature           # 哈希签名
            )
            sequence_infos.append(seq_info)

        return sequence_infos

    def _extract_context_from_paragraph(
        self,
        paragraph: Paragraph,
        matched_text: str,
        context_length: int
    ) -> Tuple[str, str]:
        """
        从段落中提取匹配文本的上下文

        根据清理后的文本找到匹配位置，然后在原始文本中提取相应的上下文
        这样可以保留原始格式信息（如空格、标点等）

        Args:
            paragraph: 段落对象，包含原始文本和清理后文本
            matched_text: 匹配的文本（清理后的版本）
            context_length: 需要提取的上下文长度（字符数）

        Returns:
            Tuple[str, str]: (匹配前的文本, 匹配后的文本)

        Note:
            上下文长度是基于有效字符计算的，不包括空白字符等被过滤的字符
        """
        from document_processor import SymbolCleaner
        cleaner = SymbolCleaner()

        raw = paragraph.raw_text   # 原始文本（包含所有字符）
        clean = paragraph.clean_text  # 清理后的文本（只包含有效字符）

        # 在清理后的文本中查找匹配位置
        match_pos = clean.find(matched_text)
        if match_pos == -1:
            # 未找到匹配，返回空字符串
            return "", ""

        # 在原始文本中找到对应的位置
        # 需要统计有效字符数量，跳过无效字符
        valid_char_count = 0
        raw_pos = 0

        # 遍历原始文本，找到清理后文本中match_pos对应的原始位置
        for raw_pos, char in enumerate(raw):
            if cleaner.is_valid_char(char):
                # 找到有效字符，检查是否达到目标位置
                if valid_char_count == match_pos:
                    break
                valid_char_count += 1

        # ========== 提取匹配前的上下文 ==========
        # 从raw_pos向前查找，收集context_length个有效字符
        before_chars = []
        valid_before_count = 0
        # 反向遍历raw_pos之前的文本
        for char in reversed(raw[:raw_pos]):
            before_chars.append(char)
            if cleaner.is_valid_char(char):
                valid_before_count += 1
                if valid_before_count >= context_length:
                    # 已收集足够的上下文
                    break
        # 反转回来，恢复正确的顺序
        before_text = ''.join(reversed(before_chars))

        # ========== 提取匹配后的上下文 ==========
        # 首先找到匹配文本结束的位置
        match_end_pos = raw_pos
        valid_match_count = 0
        # 从raw_pos开始，统计匹配文本的长度（有效字符）
        while match_end_pos < len(raw) and valid_match_count < len(matched_text):
            if cleaner.is_valid_char(raw[match_end_pos]):
                valid_match_count += 1
            match_end_pos += 1

        # 从match_end_pos开始，提取后续的上下文
        after_chars = []
        valid_after_count = 0
        for char in raw[match_end_pos:]:
            after_chars.append(char)
            if cleaner.is_valid_char(char):
                valid_after_count += 1
                if valid_after_count >= context_length:
                    # 已收集足够的上下文
                    break
        after_text = ''.join(after_chars)

        return before_text, after_text

    def _create_file_stats(self, file_path: str, paragraphs: List[Paragraph]) -> Dict[str, Any]:
        """
        创建文件统计信息

        从段落列表中提取各种统计指标，用于展示文件的基本信息

        Args:
            file_path: 文件路径
            paragraphs: 段落列表

        Returns:
            Dict[str, Any]: 包含文件统计信息的字典
        """
        # 获取文件大小（字节）
        file_size = os.path.getsize(file_path)

        return {
            "filePath": file_path,
            "fileSizeMb": round(file_size / (1024 * 1024), 2),  # 转换为MB
            "totalPages": max([p.start_page for p in paragraphs]) if paragraphs else 0,  # 总页数
            "totalLines": sum([p.char_count for p in paragraphs]),  # 总字符数（原始）
            "mainContentLines": len(paragraphs),  # 主内容段落数
            "filteredLines": 0,  # 过滤的行数（未使用）
            "totalChars": sum([p.clean_char_count for p in paragraphs]),  # 总有效字符数
            "processingTimeSeconds": 0  # 处理时间（未使用）
        }

    def _configure_processing(
        self,
        processing_mode: ProcessingMode,
        min_similarity: float,
        max_sequences: int
    ) -> Tuple[float, int]:
        """
        根据处理模式配置处理参数

        不同的处理模式有不同的默认参数设置，以平衡速度和准确性：
        - ULTRA_FAST: 最高的相似度阈值（0.9），最少的序列数（2000）
        - FAST: 较高的相似度阈值（0.8），中等的序列数（5000）
        - STANDARD: 使用用户指定的参数

        Args:
            processing_mode: 处理模式枚举值
            min_similarity: 用户指定的最小相似度
            max_sequences: 用户指定的最大序列数

        Returns:
            Tuple[float, int]: (实际使用的相似度阈值, 实际使用的最大序列数)
        """
        if processing_mode == ProcessingMode.ULTRA_FAST:
            # 超快速模式：提高阈值，限制序列数
            return max(min_similarity, 0.9), min(max_sequences, 2000)
        elif processing_mode == ProcessingMode.FAST:
            # 快速模式：适度提高阈值，适度限制序列数
            return max(min_similarity, 0.8), min(max_sequences, 5000)
        else:  # STANDARD
            # 标准模式：使用用户指定的参数
            return min_similarity, max_sequences

    async def generate_exports(
        self,
        result: SimilarityResult,
        export_format: ExportFormat = ExportFormat.TEXT,
        task_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成相似度检测结果的导出文件

        支持多种导出格式：
        - TEXT: 纯文本格式报告
        - JSON: 结构化的JSON数据
        - CSV: 表格格式的CSV文件

        Args:
            result: 相似度检测结果对象
            export_format: 导出格式枚举
            task_id: 可选的任务ID，用于文件命名

        Returns:
            Dict[str, str]: 导出文件的路径映射字典

        Raises:
            Exception: 导出过程中发生错误时抛出异常
        """
        try:
            # 创建导出目录（如果不存在）
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)

            # 生成带时间戳的基础文件名
            timestamp = int(time.time())
            base_filename = f"similarity_result_{result.task_id}_{timestamp}"

            export_files = {}

            # 根据导出格式调用相应的导出函数
            if export_format == ExportFormat.TEXT:
                export_files["text"] = await self._generate_text_export(result, export_dir, base_filename)
            elif export_format == ExportFormat.JSON:
                export_files["json"] = await self._generate_json_export(result, export_dir, base_filename)
            elif export_format == ExportFormat.CSV:
                export_files["csv"] = await self._generate_csv_export(result, export_dir, base_filename)

            return export_files

        except Exception as e:
            # 记录错误并重新抛出
            self.logger.error(f"Error generating exports: {str(e)}", exc_info=True)
            raise

    async def _generate_text_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """
        生成纯文本格式的导出文件

        创建易读的文本报告，包含所有关键信息和前50个相似序列

        Args:
            result: 相似度检测结果
            export_dir: 导出目录路径
            base_filename: 基础文件名（不含扩展名）

        Returns:
            str: 生成的文件完整路径
        """
        file_path = export_dir / f"{base_filename}.txt"

        def write_text():
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入报告头部
                f.write("=" * 80 + "\n")
                f.write("PDF SIMILARITY DETECTION REPORT\n")
                f.write("=" * 80 + "\n\n")

                # 写入基本信息
                f.write(f"Task ID: {result.task_id}\n")
                f.write(f"Processing Time: {result.processing_time_seconds:.2f} seconds\n")
                f.write(f"Similarity Threshold: {result.comparison_info['similarityThreshold']:.2f}\n")
                f.write(f"Processing Mode: {result.comparison_info['processingMode']}\n\n")

                # 写入统计信息
                f.write("SIMILARITY STATISTICS\n")
                f.write("-" * 40 + "\n")
                stats = result.similarity_stats
                f.write(f"Total Sequences Analyzed: {stats.totalSequencesAnalyzed}\n")
                f.write(f"Similar Sequences Found: {stats.similarSequencesFound}\n")
                f.write(f"Average Similarity: {stats.averageSimilarity:.2%}\n")
                f.write(f"Max Similarity: {stats.maxSimilarity:.2%}\n")
                f.write(f"Min Similarity: {stats.minSimilarity:.2%}\n\n")

                # 写入相似序列（限制前50个）
                f.write("SIMILAR SEQUENCES\n")
                f.write("-" * 40 + "\n")
                for i, seq in enumerate(result.similar_sequences[:50], 1):
                    f.write(f"\n--- Sequence {i} ---\n")
                    f.write(f"Similarity: {seq.similarity:.2%}\n")
                    f.write(f"Text 1: {seq.sequence1[:100]}...\n")
                    f.write(f"Text 2: {seq.sequence2[:100]}...\n")

        # 在单独的线程中执行文件写入操作
        await asyncio.to_thread(write_text)
        return str(file_path)

    async def _generate_json_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """
        生成JSON格式的导出文件

        创建结构化的JSON数据，包含完整的检测结果

        Args:
            result: 相似度检测结果
            export_dir: 导出目录路径
            base_filename: 基础文件名（不含扩展名）

        Returns:
            str: 生成的文件完整路径
        """
        import json

        file_path = export_dir / f"{base_filename}.json"

        def write_json():
            with open(file_path, 'w', encoding='utf-8') as f:
                # 使用indent=2使JSON更易读，default=str处理特殊类型
                json.dump(result.dict(), f, indent=2, default=str)

        await asyncio.to_thread(write_json)
        return str(file_path)

    async def _generate_csv_export(self, result: SimilarityResult, export_dir: Path, base_filename: str) -> str:
        """
        生成CSV格式的导出文件

        创建表格格式的CSV文件，便于在Excel等工具中查看和分析

        Args:
            result: 相似度检测结果
            export_dir: 导出目录路径
            base_filename: 基础文件名（不含扩展名）

        Returns:
            str: 生成的文件完整路径
        """
        import csv

        file_path = export_dir / f"{base_filename}.csv"

        def write_csv():
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入CSV表头
                writer.writerow(['Similarity', 'Text 1', 'Text 2', 'Differences'])
                # 写入每个相似序列的数据
                for seq in result.similar_sequences:
                    writer.writerow([
                        f"{seq.similarity:.2%}",  # 相似度百分比
                        seq.sequence1[:50].replace('\n', ' '),  # 文本1（限制长度）
                        seq.sequence2[:50].replace('\n', ' '),  # 文本2（限制长度）
                        ';'.join(seq.differences)  # 差异列表（用分号连接）
                    ])

        await asyncio.to_thread(write_csv)
        return str(file_path)
