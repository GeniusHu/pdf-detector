#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理模块
用于处理文本分字，按照用户规则进行分字
"""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class CharInfo:
    """字符信息类"""
    char: str           # 字符内容
    page: int           # 页码
    line: int           # 行号
    position: int       # 在该行的位置


class TextProcessor:
    """文本预处理器"""

    def __init__(self):
        # 正则表达式模式
        # 英文单词模式（不区分大小写）
        self.english_pattern = re.compile(r'[a-zA-Z]+')
        # 数字模式（支持小数）
        self.number_pattern = re.compile(r'\d+(?:\.\d+)*')
        # 中文字符模式
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        # 需要过滤的标点符号和空格
        self.filter_pattern = re.compile(r'[^\w\u4e00-\u9fff]')

    def split_text_into_chars(self, text: str, page: int, line: int) -> List[CharInfo]:
        """
        将文本分割成字符，并记录位置信息

        Args:
            text: 输入文本
            page: 页码
            line: 行号

        Returns:
            List[CharInfo]: 字符信息列表
        """
        chars = []
        position = 0

        i = 0
        while i < len(text):
            # 跳过空格和标点
            if text[i].isspace() or self._is_punctuation(text[i]):
                i += 1
                continue

            # 匹配英文单词
            english_match = self.english_pattern.match(text, i)
            if english_match:
                word = english_match.group().lower()  # 不区分大小写
                chars.append(CharInfo(word, page, line, position))
                position += 1
                i = english_match.end()
                continue

            # 匹配数字
            number_match = self.number_pattern.match(text, i)
            if number_match:
                number = number_match.group()
                chars.append(CharInfo(number, page, line, position))
                position += 1
                i = number_match.end()
                continue

            # 匹配中文字符
            chinese_char = text[i]
            if self.chinese_pattern.match(chinese_char):
                chars.append(CharInfo(chinese_char, page, line, position))
                position += 1
                i += 1
                continue

            # 其他字符跳过
            i += 1

        return chars

    def _is_punctuation(self, char: str) -> bool:
        """判断是否是标点符号"""
        # 常见标点符号
        punctuations = '.,;:!?""''()[]{}<>-+=*/\\|@#%^&~`，。；：！？""''（）【】《》〈〉「」『』［］｛｝－＋×÷＝≠≈＜＞·…～、'
        return char in punctuations

    def process_extracted_text(self, extracted_text: List[Tuple[str, int, int]]) -> List[CharInfo]:
        """
        处理提取的文本列表

        Args:
            extracted_text: (文本, 页码, 行号) 的列表

        Returns:
            List[CharInfo]: 处理后的字符信息列表
        """
        all_chars = []

        for text, page, line in extracted_text:
            chars = self.split_text_into_chars(text, page, line)
            all_chars.extend(chars)

        return all_chars

    def create_char_sequence(self, chars: List[CharInfo]) -> List[str]:
        """
        创建字符序列（仅包含字符内容）

        Args:
            chars: 字符信息列表

        Returns:
            List[str]: 字符序列
        """
        return [char.char for char in chars]


def test_text_processor():
    """测试文本处理器"""
    processor = TextProcessor()

    # 测试用例
    test_cases = [
        ("Hello, world!", 1, 1),
        ("Python3.8很棒", 1, 2),
        ("2024年过去了", 1, 3),
        ("AI技术发展迅速", 1, 4),
        ("iPhone 15 Pro Max", 1, 5),
        ("3.14是圆周率", 1, 6),
        ("This is a test.", 2, 1),
        ("中文和English混合", 2, 2),
    ]

    print("=== 文本分字测试 ===")
    for text, page, line in test_cases:
        chars = processor.split_text_into_chars(text, page, line)
        char_sequence = processor.create_char_sequence(chars)
        print(f"原文: {text}")
        print(f"分字: {' | '.join(char_sequence)}")
        print(f"字数: {len(char_sequence)}")
        print(f"详情: {[(c.char, c.page, c.line) for c in chars]}")
        print()


if __name__ == "__main__":
    test_text_processor()