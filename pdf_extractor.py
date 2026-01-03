#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文本提取模块
用于从PDF文件中提取文本，并保留位置信息（页码、行号）

主要功能:
- 从PDF文件中提取所有文本内容
- 保留每个文本行的页码和行号位置信息
- 提供原始文本提取（无位置信息）和带位置信息的文本提取
"""

import pdfplumber  # PDF处理库，用于从PDF中提取文本和位置信息
from typing import List, Tuple  # 类型注解：List用于列表，Tuple用于元组
import re  # 正则表达式模块（预留，用于可能的文本处理）


class PDFTextExtractor:
    """
    PDF文本提取器类

    负责从PDF文件中提取文本内容，并保留文本在PDF中的位置信息。
    使用pdfplumber库进行PDF解析，能够准确提取文本及其在页面中的位置。
    """

    def __init__(self, pdf_path: str):
        """
        初始化PDF文本提取器

        Args:
            pdf_path (str): PDF文件的完整路径

        Attributes:
            pdf_path (str): 存储PDF文件路径，供后续方法使用
        """
        self.pdf_path = pdf_path  # 保存PDF文件路径到实例变量

    def extract_text_with_positions(self) -> List[Tuple[str, int, int]]:
        """
        提取PDF文本并保留每个文本行的位置信息

        该方法会遍历PDF的每一页，提取所有文本行，
        并为每行文本记录其所在的页码和行号。

        Returns:
            List[Tuple[str, int, int]]: 文本行列表，每个元素是一个元组:
                - [0] 文本内容 (str): 该行的文本内容
                - [1] 页码 (int): 该行所在的页码（从1开始）
                - [2] 行号 (int): 该行在页面中的行号（从1开始）

        Example:
            >>> extractor = PDFTextExtractor("example.pdf")
            >>> lines = extractor.extract_text_with_positions()
            >>> for text, page, line in lines[:3]:
            ...     print(f"页{page}行{line}: {text}")
        """
        extracted_text = []  # 初始化空列表，用于存储所有提取的文本行及其位置信息

        try:
            # 使用pdfplumber打开PDF文件
            with pdfplumber.open(self.pdf_path) as pdf:
                # 遍历PDF的每一页，enumerate从1开始计数（页码从1开始更直观）
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取当前页的文本内容
                    # extract_text()方法返回页面中的所有文本，保留基本布局
                    text = page.extract_text()

                    # 如果该页包含文本内容
                    if text:
                        # 将文本按换行符分割成行
                        lines = text.split('\n')

                        # 遍历该页的每一行
                        for line_num, line in enumerate(lines, 1):
                            # 去除行首尾的空白字符
                            line = line.strip()

                            # 只保留非空行
                            if line:
                                # 将文本及其位置信息添加到结果列表
                                extracted_text.append((line, page_num, line_num))

            # 返回所有提取的文本行及其位置信息
            return extracted_text

        except Exception as e:
            # 捕获并处理PDF提取过程中的异常
            print(f"提取PDF文本时出错: {e}")
            return []  # 出错时返回空列表

    def extract_raw_text(self) -> str:
        """
        提取PDF原始文本（不包含位置信息）

        该方法提取PDF中的所有文本内容，合并为一个字符串，
        不保留页码、行号等位置信息。适用于只需要文本内容的场景。

        Returns:
            str: 提取的完整文本内容，各页文本用换行符分隔

        Example:
            >>> extractor = PDFTextExtractor("example.pdf")
            >>> text = extractor.extract_raw_text()
            >>> print(f"提取了 {len(text)} 个字符")
        """
        try:
            # 使用pdfplumber打开PDF文件
            with pdfplumber.open(self.pdf_path) as pdf:
                text = ""  # 初始化空字符串，用于累积所有页面的文本

                # 遍历PDF的每一页
                for page in pdf.pages:
                    # 提取当前页的文本
                    page_text = page.extract_text()

                    # 如果该页有文本内容
                    if page_text:
                        # 将页面文本追加到总文本，并在页面之间添加换行符
                        text += page_text + "\n"

                # 返回合并后的完整文本
                return text

        except Exception as e:
            # 捕获并处理PDF提取过程中的异常
            print(f"提取PDF文本时出错: {e}")
            return ""  # 出错时返回空字符串


# 以下是模块的测试代码
# 当直接运行此模块时（而非被导入时），执行以下测试
if __name__ == "__main__":
    # 创建PDF提取器实例，使用测试PDF文件
    extractor = PDFTextExtractor("test.pdf")

    # ========== 测试1: 带位置信息的文本提取 ==========
    print("=== 带位置信息的文本提取 ===")
    text_with_positions = extractor.extract_text_with_positions()

    # 只显示前5行文本及其位置信息作为示例
    for text, page, line in text_with_positions[:5]:
        print(f"页{page} 行{line}: {text}")

    # ========== 测试2: 原始文本提取 ==========
    print("\n=== 原始文本提取 ===")
    raw_text = extractor.extract_raw_text()

    # 显示提取的文本总长度
    print(f"总文本长度: {len(raw_text)}")

    # 显示前200个字符作为预览
    print(raw_text[:200])