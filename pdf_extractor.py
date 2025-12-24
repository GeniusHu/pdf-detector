#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文本提取模块
用于从PDF文件中提取文本，并保留位置信息（页码、行号）
"""

import pdfplumber
from typing import List, Tuple
import re


class PDFTextExtractor:
    """PDF文本提取器"""

    def __init__(self, pdf_path: str):
        """
        初始化PDF文本提取器

        Args:
            pdf_path: PDF文件路径
        """
        self.pdf_path = pdf_path

    def extract_text_with_positions(self) -> List[Tuple[str, int, int]]:
        """
        提取PDF文本并保留位置信息

        Returns:
            List[Tuple[str, int, int]]: (文本, 页码, 行号) 的列表
        """
        extracted_text = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取当前页的文本
                    text = page.extract_text()
                    if text:
                        # 按行分割
                        lines = text.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            # 去除空行
                            line = line.strip()
                            if line:
                                extracted_text.append((line, page_num, line_num))
            return extracted_text

        except Exception as e:
            print(f"提取PDF文本时出错: {e}")
            return []

    def extract_raw_text(self) -> str:
        """
        提取PDF原始文本（不包含位置信息）

        Returns:
            str: 提取的文本内容
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except Exception as e:
            print(f"提取PDF文本时出错: {e}")
            return ""


if __name__ == "__main__":
    # 测试代码
    extractor = PDFTextExtractor("test.pdf")

    # 测试带位置信息的提取
    print("=== 带位置信息的文本提取 ===")
    text_with_positions = extractor.extract_text_with_positions()
    for text, page, line in text_with_positions[:5]:  # 只显示前5行
        print(f"页{page} 行{line}: {text}")

    # 测试原始文本提取
    print("\n=== 原始文本提取 ===")
    raw_text = extractor.extract_raw_text()
    print(f"总文本长度: {len(raw_text)}")
    print(raw_text[:200])  # 只显示前200字符