#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理模块
用于处理文本分字，按照用户规则进行分字

主要功能:
- 将文本分割成字符/单词序列
- 识别并区分中文字符、英文单词和数字
- 过滤标点符号和空格
- 保留每个字符的位置信息（页码、行号、位置）

分字规则:
- 英文单词: 整个单词作为一个单位（不区分大小写）
- 数字: 整个数字（包括小数）作为一个单位
- 中文字符: 每个汉字作为一个单位
- 标点符号: 被过滤掉，不计入字符序列
"""

import re  # 正则表达式模块，用于模式匹配
from typing import List, Tuple, Dict  # 类型注解
from dataclasses import dataclass  # 数据类装饰器，用于创建数据类


@dataclass
class CharInfo:
    """
    字符信息数据类

    用于存储单个字符/单词及其在文档中的位置信息。

    Attributes:
        char (str): 字符内容（可能是英文单词、数字或单个汉字）
        page (int): 该字符所在页码
        line (int): 该字符所在行号
        position (int): 该字符在当前行中的位置索引
    """
    char: str           # 字符/单词内容
    page: int           # 所在页码
    line: int           # 所在行号
    position: int       # 在该行中的位置（从0开始）


class TextProcessor:
    """
    文本预处理器类

    负责将原始文本分割成有意义的字符/单词序列，
    同时保留每个字符在文档中的位置信息。

    处理规则:
    1. 英文单词作为一个整体（不区分大小写）
    2. 数字作为一个整体（支持小数）
    3. 中文字符逐个处理
    4. 标点符号和空格被过滤
    """

    def __init__(self):
        """
        初始化文本处理器

        创建用于识别不同类型文本的正则表达式模式
        """
        # ========== 编译正则表达式模式 ==========
        # 英文单词模式：匹配一个或多个连续的英文字母（不区分大小写）
        self.english_pattern = re.compile(r'[a-zA-Z]+')

        # 数字模式：匹配整数或小数（支持如 123、3.14、1.2.3 等格式）
        # (?:...\)* 表示非捕获组，可以重复0次或多次
        self.number_pattern = re.compile(r'\d+(?:\.\d+)*')

        # 中文字符模式：匹配Unicode中文范围内的字符（\u4e00-\u9fff）
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]')

        # 过滤模式：匹配所有需要过滤的字符（非单词字符和中文字符）
        self.filter_pattern = re.compile(r'[^\w\u4e00-\u9fff]')

    def split_text_into_chars(self, text: str, page: int, line: int) -> List[CharInfo]:
        """
        将文本分割成字符/单词序列，并记录位置信息

        该方法按照以下规则处理输入文本:
        1. 英文单词 -> 作为一个整体（转小写）
        2. 数字 -> 作为一个整体
        3. 中文 -> 每个字作为一个单位
        4. 标点/空格 -> 跳过

        Args:
            text (str): 待处理的输入文本
            page (int): 该文本所在的页码
            line (int): 该文本所在的行号

        Returns:
            List[CharInfo]: 字符信息列表，每个元素包含字符内容和位置信息

        Example:
            >>> processor = TextProcessor()
            >>> chars = processor.split_text_into_chars("Hello 世界123", 1, 1)
            >>> [c.char for c in chars]
            ['hello', '世', '界', '123']
        """
        chars = []  # 初始化空列表，用于存储分割后的字符信息
        position = 0  # 初始化位置计数器

        # ========== 遍历文本进行分割 ==========
        i = 0  # 当前处理位置的索引
        while i < len(text):
            # 跳过空格和标点符号
            if text[i].isspace() or self._is_punctuation(text[i]):
                i += 1  # 移动到下一个字符
                continue

            # ========== 尝试匹配英文单词 ==========
            english_match = self.english_pattern.match(text, i)
            if english_match:
                # 提取匹配的英文单词并转为小写（不区分大小写）
                word = english_match.group().lower()
                # 创建字符信息对象并添加到列表
                chars.append(CharInfo(word, page, line, position))
                position += 1  # 位置计数器加1
                i = english_match.end()  # 跳到单词末尾
                continue

            # ========== 尝试匹配数字 ==========
            number_match = self.number_pattern.match(text, i)
            if number_match:
                # 提取匹配的数字
                number = number_match.group()
                # 创建字符信息对象并添加到列表
                chars.append(CharInfo(number, page, line, position))
                position += 1
                i = number_match.end()
                continue

            # ========== 尝试匹配中文字符 ==========
            chinese_char = text[i]
            if self.chinese_pattern.match(chinese_char):
                # 单个中文字符作为一个单位
                chars.append(CharInfo(chinese_char, page, line, position))
                position += 1
                i += 1
                continue

            # ========== 其他字符直接跳过 ==========
            i += 1

        return chars  # 返回分割后的字符信息列表

    def _is_punctuation(self, char: str) -> bool:
        """
        判断给定字符是否为标点符号

        Args:
            char (str): 待判断的单个字符

        Returns:
            bool: 如果是标点符号返回True，否则返回False

        Note:
            包含中英文常见标点符号
        """
        # 常见标点符号集合（包括中英文标点）
        punctuations = '.,;:!?""''()[]{}<>-+=*/\\|@#%^&~`，。；：！？""''（）【】《》〈〉「」『』［］｛｝－＋×÷＝≠≈＜＞·…～、'
        return char in punctuations

    def process_extracted_text(self, extracted_text: List[Tuple[str, int, int]]) -> List[CharInfo]:
        """
        批量处理从PDF提取的文本列表

        该方法接收从PDF提取的文本行列表（包含位置信息），
        对每一行进行分字处理，并合并所有结果。

        Args:
            extracted_text (List[Tuple[str, int, int]]): 提取的文本列表
                每个元素是一个元组: (文本内容, 页码, 行号)

        Returns:
            List[CharInfo]: 所有文本行处理后的字符信息列表

        Example:
            >>> processor = TextProcessor()
            >>> text_list = [("Hello World", 1, 1), ("你好世界", 1, 2)]
            >>> chars = processor.process_extracted_text(text_list)
            >>> len(chars)
            4  # hello, world, 你, 好, 世, 界
        """
        all_chars = []  # 初始化空列表，用于累积所有字符

        # ========== 遍历每一行文本进行分字 ==========
        for text, page, line in extracted_text:
            # 对当前行进行分字处理
            chars = self.split_text_into_chars(text, page, line)
            # 将处理结果添加到累积列表
            all_chars.extend(chars)

        return all_chars  # 返回所有字符信息

    def create_char_sequence(self, chars: List[CharInfo]) -> List[str]:
        """
        从字符信息列表中提取纯字符序列

        该方法用于从包含位置信息的CharInfo列表中，
        提取出纯字符内容的列表。

        Args:
            chars (List[CharInfo]): 字符信息列表

        Returns:
            List[str]: 纯字符内容列表

        Example:
            >>> chars = [CharInfo("hello", 1, 1, 0), CharInfo("world", 1, 1, 1)]
            >>> processor = TextProcessor()
            >>> processor.create_char_sequence(chars)
            ['hello', 'world']
        """
        # 使用列表推导式提取每个CharInfo对象的char属性
        return [char.char for char in chars]


# ========== 测试函数 ==========
def test_text_processor():
    """
    测试文本处理器的各项功能

    测试用例包括:
    - 纯英文文本
    - 中英文混合
    - 数字
    - 特殊字符处理
    """
    processor = TextProcessor()

    # ========== 定义测试用例 ==========
    # 每个测试用例是一个元组: (文本, 页码, 行号)
    test_cases = [
        ("Hello, world!", 1, 1),      # 纯英文带标点
        ("Python3.8很棒", 1, 2),      # 英文、数字、中文混合
        ("2024年过去了", 1, 3),       # 数字开头
        ("AI技术发展迅速", 1, 4),      # 纯中文
        ("iPhone 15 Pro Max", 1, 5),   # 英文大小写混合
        ("3.14是圆周率", 1, 6),        # 小数
        ("This is a test.", 2, 1),    # 英文句子
        ("中文和English混合", 2, 2),   # 中英混合
    ]

    # ========== 执行测试 ==========
    print("=== 文本分字测试 ===")
    for text, page, line in test_cases:
        # 对测试文本进行分字
        chars = processor.split_text_into_chars(text, page, line)

        # 提取纯字符序列
        char_sequence = processor.create_char_sequence(chars)

        # 显示测试结果
        print(f"原文: {text}")
        print(f"分字: {' | '.join(char_sequence)}")
        print(f"字数: {len(char_sequence)}")
        print(f"详情: {[(c.char, c.page, c.line) for c in chars]}")
        print()  # 空行分隔


# ========== 主程序入口 ==========
if __name__ == "__main__":
    # 运行测试函数
    test_text_processor()