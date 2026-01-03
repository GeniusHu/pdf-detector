#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档处理器 - 按照用户需求的三步骤处理文档

处理流程:
1. 过滤非正文内容 (脚注、引用、批注、页眉页脚等)
2. 段落级别符号清理 (只保留中文、英文、数字)
3. 切分和比对准备 (输出段落供后续切分)

支持格式: PDF (.pdf), Word (.docx)
"""

import os
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Paragraph:
    """段落信息"""
    raw_text: str              # 原始段落文本（带符号）
    clean_text: str            # 清理后的段落文本（只有中英数字）
    start_page: int            # 起始页码/段落号
    start_line: int            # 起始行号
    char_count: int            # 原始字符数
    clean_char_count: int = field(default=0)  # 清理后字符数
    file_type: str = "pdf"     # 文件类型: pdf, docx


@dataclass
class DocumentContent:
    """文档内容"""
    file_path: str
    file_type: str             # pdf, docx
    paragraphs: List[Paragraph]
    total_raw_chars: int
    total_clean_chars: int
    stats: Dict[str, Any] = field(default_factory=dict)


class SymbolCleaner:
    """符号清理器 - 只保留中文、英文、数字"""

    # Unicode 范围定义
    CHINESE_RANGE = ('\u4e00', '\u9fff')      # 中文
    ENGLISH_LOWER = ('a', 'z')
    ENGLISH_UPPER = ('A', 'Z')
    DIGITS = ('0', '9')

    @classmethod
    def is_chinese(cls, char: str) -> bool:
        """判断是否为中文字符"""
        return cls.CHINESE_RANGE[0] <= char <= cls.CHINESE_RANGE[1]

    @classmethod
    def is_english(cls, char: str) -> bool:
        """判断是否为英文字母"""
        return (cls.ENGLISH_LOWER[0] <= char <= cls.ENGLISH_LOWER[1] or
                cls.ENGLISH_UPPER[0] <= char <= cls.ENGLISH_UPPER[1])

    @classmethod
    def is_digit(cls, char: str) -> bool:
        """判断是否为数字"""
        return cls.DIGITS[0] <= char <= cls.DIGITS[1]

    @classmethod
    def is_valid_char(cls, char: str) -> bool:
        """
        判断字符是否有效
        只保留: 中文、英文、数字
        清理: 空格、换行、制表符、中英文标点、特殊符号、数学符号等
        """
        return cls.is_chinese(char) or cls.is_english(char) or cls.is_digit(char)

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        清理文本，只保留中文、英文、数字

        Args:
            text: 原始文本

        Returns:
            清理后的文本（只包含中文、英文、数字）
        """
        cleaned = []
        for char in text:
            if cls.is_valid_char(char):
                cleaned.append(char)
            # 其他所有字符（空格、标点、符号等）全部跳过
        return ''.join(cleaned)

    @classmethod
    def get_clean_char_count(cls, text: str) -> int:
        """获取清理后的字符数"""
        count = 0
        for char in text:
            if cls.is_valid_char(char):
                count += 1
        return count


class DocumentProcessor:
    """
    文档处理器 - 按三步骤处理文档

    步骤1: 过滤非正文内容
    步骤2: 合并段落 + 符号清理
    步骤3: 返回段落列表（供后续切分）
    """

    def __init__(self, config=None):
        """
        初始化文档处理器

        Args:
            config: TextExtractionConfig 配置对象
        """
        self.config = config
        self.cleaner = SymbolCleaner()

    def process(self, file_path: str) -> DocumentContent:
        """
        处理文档

        Args:
            file_path: 文件路径（PDF或Word）

        Returns:
            DocumentContent: 处理后的文档内容
        """
        # 判断文件类型
        file_ext = os.path.splitext(file_path)[1].lower()
        file_type = 'pdf' if file_ext == '.pdf' else 'docx'

        logger.info(f"[DocumentProcessor] Processing {file_type.upper()}: {file_path}")

        # 步骤1: 提取并过滤非正文内容
        lines = self._extract_and_filter(file_path)

        logger.info(f"[DocumentProcessor] Step 1 complete: {len(lines)} lines extracted")

        # 步骤2: 合并成段落 + 清理符号
        paragraphs = self._merge_and_clean_lines(lines, file_type)

        logger.info(f"[DocumentProcessor] Step 2 complete: {len(paragraphs)} paragraphs created")

        # 统计信息
        total_raw_chars = sum(p.char_count for p in paragraphs)
        total_clean_chars = sum(p.clean_char_count for p in paragraphs)

        # 创建文档内容对象
        content = DocumentContent(
            file_path=file_path,
            file_type=file_type,
            paragraphs=paragraphs,
            total_raw_chars=total_raw_chars,
            total_clean_chars=total_clean_chars,
            stats={
                'total_lines': len(lines),
                'total_paragraphs': len(paragraphs),
                'total_raw_chars': total_raw_chars,
                'total_clean_chars': total_clean_chars,
                'compression_ratio': f"{total_clean_chars / total_raw_chars * 100:.1f}%" if total_raw_chars > 0 else "0%"
            }
        )

        logger.info(f"[DocumentProcessor] Processing complete: "
                   f"{total_raw_chars} raw chars -> {total_clean_chars} clean chars "
                   f"({content.stats['compression_ratio']} compression)")

        return content

    def _extract_and_filter(self, file_path: str) -> List[Tuple[str, int, int]]:
        """
        步骤1: 提取文本并过滤非正文内容

        Returns:
            List[Tuple[str, int, int]]: (文本, 页码/段落号, 行号) 的列表
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            return self._extract_pdf_content(file_path)
        elif file_ext == '.docx':
            return self._extract_word_content(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _extract_pdf_content(self, pdf_path: str) -> List[Tuple[str, int, int]]:
        """提取PDF内容，过滤非正文"""
        from enhanced_pdf_extractor import EnhancedPDFTextExtractor

        extractor = EnhancedPDFTextExtractor(self.config, pdf_path)
        return extractor.extract_main_text_lines(pdf_path)

    def _extract_word_content(self, docx_path: str) -> List[Tuple[str, int, int]]:
        """提取Word内容，过滤非正文"""
        from word_extractor import WordExtractor

        extractor = WordExtractor(self.config)
        return extractor.extract_text_with_positions(docx_path)

    def _merge_and_clean_lines(self, lines: List[Tuple[str, int, int]], file_type: str) -> List[Paragraph]:
        """
        步骤2: 合并行成段落 + 清理符号

        策略: 同一页的所有行合并成一个段落

        Args:
            lines: (文本, 页码, 行号) 的列表
            file_type: 文件类型

        Returns:
            List[Paragraph]: 段落列表
        """
        if not lines:
            return []

        paragraphs = []

        # 按页码分组
        lines_by_page: Dict[int, List[Tuple[str, int, int]]] = {}
        for text, page, line in lines:
            if page not in lines_by_page:
                lines_by_page[page] = []
            lines_by_page[page].append((text, page, line))

        # 每页合并成一个段落
        for page in sorted(lines_by_page.keys()):
            page_lines = lines_by_page[page]
            if not page_lines:
                continue

            # 合并同一页的所有行
            raw_text = ''.join(line[0] for line in page_lines)

            # 清理符号
            clean_text = self.cleaner.clean_text(raw_text)

            # 只有清理后有内容才保留
            if len(clean_text) >= 3:  # 至少3个有效字符
                paragraphs.append(Paragraph(
                    raw_text=raw_text,
                    clean_text=clean_text,
                    start_page=page,
                    start_line=page_lines[0][1],  # 第一行的行号
                    char_count=len(raw_text),
                    clean_char_count=len(clean_text),
                    file_type=file_type
                ))

        return paragraphs

    def get_context_from_paragraph(
        self,
        paragraph: Paragraph,
        matched_text: str,
        context_length: int = 50
    ) -> Tuple[str, str]:
        """
        从段落中提取匹配文本的上下文

        Args:
            paragraph: 段落对象
            matched_text: 匹配的文本（清理后的）
            context_length: 上下文长度（字符数）

        Returns:
            Tuple[str, str]: (前文, 后文)
        """
        # 在原始段落中查找匹配文本的位置
        # 由于清理后符号消失，需要通过查找有效字符序列来定位

        raw = paragraph.raw_text
        clean = paragraph.clean_text

        # 找到匹配文本在清理后文本中的位置
        match_pos = clean.find(matched_text)
        if match_pos == -1:
            # 未找到，返回空上下文
            return "", ""

        # 计算在原始文本中的对应位置
        # 需要统计到匹配位置为止的有效字符数
        valid_char_count = 0
        raw_pos = 0

        for raw_pos, char in enumerate(raw):
            if self.cleaner.is_valid_char(char):
                if valid_char_count == match_pos:
                    # 找到了匹配开始位置
                    break
                valid_char_count += 1

        # 计算上下文范围（基于有效字符）
        before_chars = []
        after_chars = []

        # 提取前文
        valid_before_count = 0
        for char in reversed(raw[:raw_pos]):
            before_chars.append(char)
            if self.cleaner.is_valid_char(char):
                valid_before_count += 1
                if valid_before_count >= context_length:
                    break
        before_text = ''.join(reversed(before_chars))

        # 提取后文
        match_end_pos = raw_pos
        valid_match_count = 0
        while match_end_pos < len(raw) and valid_match_count < len(matched_text):
            if self.cleaner.is_valid_char(raw[match_end_pos]):
                valid_match_count += 1
            match_end_pos += 1

        valid_after_count = 0
        for char in raw[match_end_pos:]:
            after_chars.append(char)
            if self.cleaner.is_valid_char(char):
                valid_after_count += 1
                if valid_after_count >= context_length:
                    break
        after_text = ''.join(after_chars)

        return before_text, after_text


class SequenceGenerator:
    """序列生成器 - 从清理后的段落生成N字序列"""

    def __init__(self, sequence_length: int = 8):
        """
        初始化序列生成器

        Args:
            sequence_length: 序列长度（连续字符数）
        """
        self.sequence_length = sequence_length
        self.cleaner = SymbolCleaner()

    def generate_from_paragraphs(self, paragraphs: List[Paragraph]) -> List[Dict]:
        """
        从段落列表生成序列

        Args:
            paragraphs: 段落列表

        Returns:
            List[Dict]: 序列列表，每个序列包含:
                - sequence: 清理后的序列文本
                - raw_sequence: 原始序列文本（带符号，从原始段落提取）
                - paragraph_index: 所属段落索引
                - start_pos: 在段落中的起始位置
        """
        sequences = []

        for para_idx, paragraph in enumerate(paragraphs):
            clean_text = paragraph.clean_text

            # 跳过太短的段落
            if len(clean_text) < self.sequence_length:
                continue

            # 生成所有连续N字序列
            for i in range(len(clean_text) - self.sequence_length + 1):
                sequence_text = clean_text[i:i + self.sequence_length]

                # 从原始段落提取对应的原始序列
                raw_sequence = self._extract_raw_sequence(
                    paragraph.raw_text,
                    paragraph.clean_text,
                    i,
                    self.sequence_length
                )

                sequences.append({
                    'sequence': sequence_text,
                    'raw_sequence': raw_sequence,
                    'paragraph_index': para_idx,
                    'start_pos': i,
                    'paragraph': paragraph  # 保存段落引用用于上下文提取
                })

        return sequences

    def _extract_raw_sequence(
        self,
        raw_text: str,
        clean_text: str,
        start_pos: int,
        length: int
    ) -> str:
        """
        从原始文本中提取对应位置的序列

        Args:
            raw_text: 原始文本（带符号）
            clean_text: 清理后的文本
            start_pos: 在清理文本中的起始位置
            length: 序列长度

        Returns:
            原始序列文本
        """
        # 找到在原始文本中的对应位置
        valid_char_count = 0
        raw_start = 0

        for raw_start, char in enumerate(raw_text):
            if self.cleaner.is_valid_char(char):
                if valid_char_count == start_pos:
                    break
                valid_char_count += 1

        # 提取原始序列
        raw_chars = []
        valid_count = 0
        for char in raw_text[raw_start:]:
            raw_chars.append(char)
            if self.cleaner.is_valid_char(char):
                valid_count += 1
                if valid_count >= length:
                    break

        return ''.join(raw_chars)


# 便捷函数
def process_document(file_path: str, config=None) -> DocumentContent:
    """
    处理文档的便捷函数

    Args:
        file_path: 文件路径
        config: 提取配置

    Returns:
        DocumentContent: 处理后的文档内容
    """
    processor = DocumentProcessor(config)
    return processor.process(file_path)


def generate_sequences(
    paragraphs: List[Paragraph],
    sequence_length: int = 8
) -> List[Dict]:
    """
    从段落生成序列的便捷函数

    Args:
        paragraphs: 段落列表
        sequence_length: 序列长度

    Returns:
        序列列表
    """
    generator = SequenceGenerator(sequence_length)
    return generator.generate_from_paragraphs(paragraphs)


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Processing: {file_path}")

        content = process_document(file_path)

        print(f"\nDocument Summary:")
        print(f"  File Type: {content.file_type}")
        print(f"  Paragraphs: {len(content.paragraphs)}")
        print(f"  Raw Chars: {content.total_raw_chars}")
        print(f"  Clean Chars: {content.total_clean_chars}")
        print(f"  Compression: {content.stats.get('compression_ratio', 'N/A')}")

        print(f"\nFirst 3 paragraphs:")
        for i, para in enumerate(content.paragraphs[:3]):
            print(f"  Para {i + 1} (Page {para.start_page}):")
            print(f"    Raw: {para.raw_text[:100]}...")
            print(f"    Clean: {para.clean_text[:100]}...")
            print(f"    Chars: {para.char_count} -> {para.clean_char_count}")
    else:
        print("Usage: python document_processor.py <file_path>")
