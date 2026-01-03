#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档提取器抽象层
支持PDF和Word文档的统一接口
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
import os


class BaseDocumentExtractor(ABC):
    """文档提取器抽象基类"""

    @abstractmethod
    def extract_text_with_positions(self, file_path: str) -> List[Tuple[str, int, int]]:
        """
        提取文档文本及其位置信息

        Args:
            file_path: 文档文件路径

        Returns:
            List[Tuple[str, int, int]]: (文本, 页码/段码, 行号) 的列表
        """
        pass

    @abstractmethod
    def supports_file_type(self, file_path: str) -> bool:
        """
        判断是否支持该文件类型

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否支持
        """
        pass


def create_document_extractor(file_path: str, config=None):
    """
    根据文件类型创建对应的提取器

    Args:
        file_path: 文件路径
        config: 提取配置（用于PDF）

    Returns:
        BaseDocumentExtractor: 对应的文档提取器
    """
    from pdf_extractor import PDFTextExtractor

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        # 使用PDF提取器
        if config:
            from enhanced_pdf_extractor import EnhancedPDFTextExtractor
            return EnhancedPDFTextExtractor(config, file_path)
        else:
            return PDFTextExtractor(file_path)

    elif ext == '.docx':
        # 使用Word提取器
        from word_extractor import WordExtractor
        return WordExtractor(config)

    else:
        raise ValueError(f"不支持的文件类型: {ext}。支持的类型: .pdf, .docx")
