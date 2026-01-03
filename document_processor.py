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
    tokens: List["Token"] = field(default_factory=list)  # 分词后的token列表


@dataclass
class Token:
    """
    语义单元（Token）

    用于序列生成的最小单位：
    - 中文字符：每个汉字是一个token
    - 英文单词：完整单词是一个token
    - 数字：完整数字是一个token（小数点已过滤）
    """
    text: str                  # token文本
    token_type: str            # token类型: 'chinese', 'english', 'number'
    start_pos: int             # 在clean_text中的起始位置
    end_pos: int               # 在clean_text中的结束位置（不包含）


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
        清理文本，保留中文、英文单词、数字，并智能处理空格

        清理规则：
        - 英文字母：转为小写
        - 数字：保留（但小数点会被过滤）
        - 中文字符：保留
        - 空格：根据上下文智能处理
          * 纯英文/数字序列内部：保留空格
          * 中文字符之间：不保留空格
          * 中英文/数字边界：不保留空格
        - 其他字符（标点、符号等）：全部过滤

        Args:
            text: 原始文本

        Returns:
            清理后的文本

        Examples:
            >>> SymbolCleaner.clean_text("Hello World")
            "hello world"
            >>> SymbolCleaner.clean_text("你好 世界")
            "你好世界"
            >>> SymbolCleaner.clean_text("Hello世界")
            "hello世界"
            >>> SymbolCleaner.clean_text("Python 3.14")
            "python 314"
        """
        result = []
        i = 0
        n = len(text)

        while i < n:
            char = text[i]

            # ========== 处理英文字母 ==========
            if cls.is_english(char):
                # 提取完整的英文单词（连续的字母），转为小写
                word_chars = []
                while i < n and cls.is_english(text[i]):
                    word_chars.append(text[i].lower())
                    i += 1
                word = ''.join(word_chars)

                # 跳过后面的空格
                while i < n and text[i].isspace():
                    i += 1

                # 检查后面是否是英文、数字，或者是结束/中文
                # 如果是英文/数字，说明在英文序列中，需要加空格
                if i < n and (cls.is_english(text[i]) or cls.is_digit(text[i])):
                    # 后面是英文/数字，说明还在英文序列中
                    result.append(word)
                    result.append(' ')
                else:
                    # 后面是中文或结束，不加空格
                    result.append(word)
                continue

            # ========== 处理数字 ==========
            elif cls.is_digit(char):
                # 提取完整的数字（连续的数字，包括小数点后的数字）
                # 注意：小数点会被过滤掉，但小数点前后的数字应该连在一起
                num_chars = []
                while i < n and cls.is_digit(text[i]):
                    num_chars.append(text[i])
                    i += 1

                # 跳过小数点（继续提取小数点后的数字）
                while i < n and text[i] == '.':
                    i += 1
                    # 小数点后面可能有数字，继续提取
                    while i < n and cls.is_digit(text[i]):
                        num_chars.append(text[i])
                        i += 1

                number = ''.join(num_chars)

                # 跳过后面的空格
                while i < n and text[i].isspace():
                    i += 1

                # 检查后面是否是英文、数字
                if i < n and (cls.is_english(text[i]) or cls.is_digit(text[i])):
                    # 后面是英文/数字，说明还在英文/数字序列中
                    result.append(number)
                    result.append(' ')
                else:
                    # 后面是中文或结束，不加空格
                    result.append(number)
                continue

            # ========== 处理中文字符 ==========
            elif cls.is_chinese(char):
                # 中文字符之间不加空格
                result.append(char)
                i += 1
                continue

            # ========== 其他字符（空格、标点、符号等）直接跳过 ==========
            else:
                i += 1

        # 清理末尾可能的多余空格
        while result and result[-1] == ' ':
            result.pop()

        return ''.join(result)

    @classmethod
    def get_clean_char_count(cls, text: str) -> int:
        """获取清理后的字符数"""
        count = 0
        for char in text:
            if cls.is_valid_char(char):
                count += 1
        return count


class Tokenizer:
    """
    分词器 - 将文本分割成语义单元（Token）

    分词规则：
    - 中文字符：每个汉字是一个token
    - 英文单词：完整单词是一个token（转为小写）
    - 数字：完整数字是一个token（小数点已过滤）
    - 空格：用于分隔英文单词，但不作为token
    """

    def __init__(self):
        self.cleaner = SymbolCleaner()

    def tokenize(self, clean_text: str) -> List[Token]:
        """
        将清理后的文本分割成token列表

        Args:
            clean_text: 已经经过SymbolCleaner处理的文本

        Returns:
            List[Token]: token列表

        Examples:
            >>> tokenizer = Tokenizer()
            >>> tokenizer.tokenize("hello world")
            [Token('hello', 'english', 0, 5), Token('world', 'english', 6, 11)]

            >>> tokenizer.tokenize("今天天气很好")
            [Token('今', 'chinese', 0, 1), Token('天', 'chinese', 1, 2), ...]
        """
        tokens = []
        i = 0
        n = len(clean_text)
        current_pos = 0  # 当前在clean_text中的位置

        while i < n:
            char = clean_text[i]

            # ========== 处理英文字母 ==========
            if self.cleaner.is_english(char):
                start_pos = current_pos
                # 提取完整的英文单词
                word_chars = []
                while i < n and self.cleaner.is_english(clean_text[i]):
                    word_chars.append(clean_text[i])
                    i += 1
                    current_pos += 1
                word = ''.join(word_chars)

                tokens.append(Token(
                    text=word,
                    token_type='english',
                    start_pos=start_pos,
                    end_pos=current_pos
                ))

                # 跳过空格
                while i < n and clean_text[i].isspace():
                    i += 1
                    current_pos += 1
                continue

            # ========== 处理数字 ==========
            elif self.cleaner.is_digit(char):
                start_pos = current_pos
                # 提取完整的数字
                num_chars = []
                while i < n and self.cleaner.is_digit(clean_text[i]):
                    num_chars.append(clean_text[i])
                    i += 1
                    current_pos += 1
                number = ''.join(num_chars)

                tokens.append(Token(
                    text=number,
                    token_type='number',
                    start_pos=start_pos,
                    end_pos=current_pos
                ))

                # 跳过空格
                while i < n and clean_text[i].isspace():
                    i += 1
                    current_pos += 1
                continue

            # ========== 处理中文字符 ==========
            elif self.cleaner.is_chinese(char):
                tokens.append(Token(
                    text=char,
                    token_type='chinese',
                    start_pos=current_pos,
                    end_pos=current_pos + 1
                ))
                i += 1
                current_pos += 1
                continue

            # ========== 跳过空格 ==========
            elif char.isspace():
                i += 1
                current_pos += 1
                continue

            # ========== 其他字符（理论上不应该出现） ==========
            else:
                i += 1
                current_pos += 1

        return tokens


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
    """
    序列生成器 - 基于语义单元（Token）生成序列

    序列长度N的含义：
    - 中文：N个连续字符
    - 英文：N个连续单词
    - 数字：作为完整单词

    示例：
    - "今天天气很好" N=3 → ["今天天", "天天气", "天气很", "气很好"]
    - "hello world java" N=2 → ["hello world", "world java"]
    - "Python版本38" N=3 → ["Python版本本", "版本38"]
    """

    def __init__(self, sequence_length: int = 8):
        """
        初始化序列生成器

        Args:
            sequence_length: 序列长度（token数量）
        """
        self.sequence_length = sequence_length
        self.tokenizer = Tokenizer()

    def generate_from_paragraphs(self, paragraphs: List[Paragraph]) -> List[Dict]:
        """
        从段落列表生成基于token的序列

        Args:
            paragraphs: 段落列表

        Returns:
            List[Dict]: 序列列表，每个序列包含:
                - sequence: 用于比对的序列文本（去除空格）
                - display_sequence: 用于显示的序列文本（保留空格）
                - tokens: 组成该序列的token列表
                - paragraph_index: 所属段落索引
                - start_token_pos: 起始token位置
                - paragraph: 段落引用
        """
        sequences = []

        for para_idx, paragraph in enumerate(paragraphs):
            # 对段落进行分词
            if not paragraph.tokens:
                paragraph.tokens = self.tokenizer.tokenize(paragraph.clean_text)

            tokens = paragraph.tokens

            # 跳过token数不足的段落
            if len(tokens) < self.sequence_length:
                continue

            # 生成所有连续N token序列
            for i in range(len(tokens) - self.sequence_length + 1):
                window_tokens = tokens[i:i + self.sequence_length]

                # 用于比对的序列（去除空格）
                sequence_text = ''.join(token.text for token in window_tokens)

                # 用于显示的序列（英文单词之间保留空格）
                display_tokens = []
                for j, token in enumerate(window_tokens):
                    display_tokens.append(token.text)
                    # 如果当前token是英文或数字，且下一个token也是英文或数字，则加空格
                    if j < len(window_tokens) - 1:
                        next_token = window_tokens[j + 1]
                        if (token.token_type in ['english', 'number'] and
                            next_token.token_type in ['english', 'number']):
                            display_tokens.append(' ')
                display_sequence = ''.join(display_tokens)

                # 计算字符位置（用于向后兼容）
                char_start_pos = window_tokens[0].start_pos if window_tokens else 0
                char_end_pos = window_tokens[-1].end_pos if window_tokens else 0

                sequences.append({
                    'sequence': sequence_text,
                    'display_sequence': display_sequence,
                    'raw_sequence': display_sequence,  # 向后兼容：raw_sequence 等同于 display_sequence
                    'tokens': window_tokens,
                    'paragraph_index': para_idx,
                    'start_token_pos': i,
                    'start_pos': char_start_pos,  # 字符起始位置（向后兼容）
                    'end_pos': char_end_pos,      # 字符结束位置
                    'paragraph': paragraph
                })

        return sequences

    def generate_from_text(self, text: str) -> List[str]:
        """
        便捷方法：直接从文本生成序列列表

        Args:
            text: 输入文本（需要是已经清理过的）

        Returns:
            List[str]: 序列字符串列表（用于比对）
        """
        cleaner = SymbolCleaner()
        clean_text = cleaner.clean_text(text)
        tokens = self.tokenizer.tokenize(clean_text)

        if len(tokens) < self.sequence_length:
            return []

        sequences = []
        for i in range(len(tokens) - self.sequence_length + 1):
            window_tokens = tokens[i:i + self.sequence_length]
            sequence_text = ''.join(token.text for token in window_tokens)
            sequences.append(sequence_text)

        return sequences


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
