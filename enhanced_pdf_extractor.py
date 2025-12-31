#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版PDF文本提取模块
只提取正文内容，过滤引用、批注、页眉页脚等非正文内容
"""

import pdfplumber
import re
import os
from typing import List, Tuple, Set, Dict
from dataclasses import dataclass
import logging


@dataclass
class TextExtractionConfig:
    """文本提取配置"""
    include_references: bool = False          # 是否包含引用
    include_footnotes: bool = False           # 是否包含脚注
    include_citations: bool = False           # 是否包含引文
    include_page_numbers: bool = False       # 是否包含页码
    include_headers_footers: bool = False    # 是否包含页眉页脚
    include_annotations: bool = False        # 是否包含批注
    min_line_length: int = 10                 # 最小行长度（过滤短行）
    remove_duplicate_lines: bool = True       # 是否去除重复行
    page_range: Tuple[int, int] = None       # 页码范围 (start, end)，例如 (1, 146) 表示只提取1-146页


class EnhancedPDFTextExtractor:
    """增强版PDF文本提取器"""

    def __init__(self, config: TextExtractionConfig = None, pdf_path: str = None):
        """
        初始化增强版PDF提取器

        Args:
            config: 文本提取配置
            pdf_path: PDF文件路径（可选）
        """
        self.config = config or TextExtractionConfig()
        self.logger = logging.getLogger(__name__)
        self.pdf_path = pdf_path

        # 常见的引用、脚注、引文模式
        self.reference_patterns = [
            r'^\[\d+\]',                     # [1], [2] 等
            r'^\(\d+\)',                    # (1), (2) 等
            r'^References$',                # References
            r'^参考文献$',                   # 参考文献
            r'^Bibliography$',              # Bibliography
        ]

        # 中文脚注/引用模式 - 增强检测
        self.footnote_patterns = [
            r'参见.*第\d+页',               # 参见...第XX页
            r'详见.*第\d+页',               # 详见...第XX页
            r'出版社.*年版第\d+页',        # 出版社...年版第XX页
            r'人民出版社.*年版',           # 人民出版社...年版
            r'中央文献出版社.*年版',       # 中央文献出版社...年版
            r'文献出版社.*年版',           # 文献出版社...年版
            r'学习出版社.*年版',           # 学习出版社...年版
            r'第\d+卷.*第\d+页',            # 第X卷...第X页
            r'Vol\.\d+.*No\.\d+',          # Vol.X No.X
            r'pp\.\d+',                     # pp.XXX
            r'\d{4}年.*版',                 # 20XX年...版
            r'年版.*第\d+页',               # 年版...第XX页
            r'\[\d+\].*页',                 # [X]...页
            r'ISBN',                        # ISBN
            r'ISSN',                        # ISSN
            r'DOI:',                        # DOI:
        ]

        self.citation_patterns = [
            r'\[.*?\]',                     # [...]
            r'\(.*?\d{4}.*?\)',            # (年份)
            r'et al\.',                    # et al.
            r'Fig\.\d+',                    # Fig.1
            r'Table \d+',                   # Table 1
            r'Equation \d+',                # Equation 1
        ]

        self.page_header_footer_patterns = [
            r'^\d+$',                       # 单独的数字（页码）
            r'Page \d+',                    # Page 1
            r'第\d+页',                      # 第1页
            r'^\s*$',                       # 空行
            r'^-{5,}$',                     # 多个横线
        ]

    def is_reference_line(self, text: str) -> bool:
        """判断是否为引用行"""
        text_lower = text.lower().strip()
        for pattern in self.reference_patterns:
            if re.match(pattern, text_lower):
                return True
        return False

    def is_citation_line(self, text: str) -> bool:
        """判断是否包含大量引文"""
        citation_count = 0
        words = text.split()

        for pattern in self.citation_patterns:
            matches = re.findall(pattern, text)
            citation_count += len(matches)

        # 如果引文数量超过单词数的30%，认为是引文行
        return len(words) > 0 and (citation_count / len(words)) > 0.3

    def is_page_header_footer(self, text: str) -> bool:
        """判断是否为页眉页脚"""
        text_stripped = text.strip()
        for pattern in self.page_header_footer_patterns:
            if re.match(pattern, text_stripped):
                return True
        return False

    def is_footnote_line(self, text: str) -> bool:
        """判断是否为脚注/参考文献行"""
        for pattern in self.footnote_patterns:
            if re.search(pattern, text):
                return True
        return False

    def is_short_or_empty(self, text: str) -> bool:
        """判断是否为短行或空行"""
        text_stripped = text.strip()
        if not text_stripped:
            return True
        return len(text_stripped) < self.config.min_line_length

    def normalize_text(self, text: str) -> str:
        """标准化文本"""
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空格
        text = text.strip()
        return text

    def extract_main_text_lines(self, pdf_path: str) -> List[Tuple[str, int, int]]:
        """
        提取PDF正文内容

        Args:
            pdf_path: PDF文件路径

        Returns:
            List[Tuple[str, int, int]]: (文本, 页码, 行号) 的列表
        """
        main_text_lines = []

        try:
            import os
            pdf_name = os.path.basename(pdf_path)
            print(f"\n{'='*60}")
            print(f"[PDF] ===== STARTING EXTRACTION: {pdf_name} =====")
            print(f"{'='*60}")

            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                # 应用页码范围限制
                page_start, page_end = 1, total_pages
                if self.config.page_range:
                    page_start, page_end = self.config.page_range
                    page_end = min(page_end, total_pages)
                    print(f"[PDF] {pdf_name} - Page range: {page_start}-{page_end} (total: {total_pages} pages)")
                else:
                    print(f"[PDF] {pdf_name} - Total pages: {total_pages}")

                for page_num, page in enumerate(pdf.pages, 1):
                    # 跳过范围外的页面
                    if page_num < page_start or page_num > page_end:
                        continue
                    try:
                        # 提取当前页的文本
                        page_text = page.extract_text()
                        if not page_text:
                            print(f"[PDF] {pdf_name} - Page {page_num}/{total_pages}: EMPTY (skipped)")
                            continue

                        # 按行分割
                        lines = page_text.split('\n')

                        for line_num, line in enumerate(lines, 1):
                            line_stripped = line.strip()

                            # 跳过空行
                            if not line_stripped:
                                continue

                            # 应用各种过滤规则
                            if self.should_skip_line(line_stripped, page_num, line_num):
                                continue

                            # 标准化文本
                            normalized_line = self.normalize_text(line_stripped)

                            if normalized_line:
                                main_text_lines.append((normalized_line, page_num, line_num))

                    except Exception as e:
                        print(f"[PDF] {pdf_name} - ERROR on page {page_num}/{total_pages}: {e}")
                        continue

                    # 每50页报告一次进度
                    if page_num % 50 == 0 or page_num == total_pages:
                        print(f"[PDF] {pdf_name} - Processed {page_num}/{total_pages} pages, {len(main_text_lines)} lines extracted so far")

            print(f"[PDF] {pdf_name} - COMPLETED: {total_pages} pages processed, {len(main_text_lines)} lines extracted (before dedup)")
            print(f"{'='*60}\n")

            # 去除重复行
            if self.config.remove_duplicate_lines:
                main_text_lines = self.remove_duplicate_lines(main_text_lines)

            return main_text_lines

        except Exception as e:
            self.logger.error(f"提取PDF文本时出错: {e}")
            return []

    def should_skip_line(self, text: str, page_num: int, line_num: int) -> bool:
        """
        判断是否应该跳过该行

        Args:
            text: 文本内容
            page_num: 页码
            line_num: 行号

        Returns:
            bool: 是否跳过
        """
        # 检查各种过滤条件
        if self.is_short_or_empty(text):
            return True

        if not self.config.include_references and self.is_reference_line(text):
            return True

        if not self.config.include_citations and self.is_citation_line(text):
            return True

        # 检测脚注（默认不包含）
        if not self.config.include_footnotes and self.is_footnote_line(text):
            return True

        if not self.config.include_page_numbers and self.is_page_header_footer(text):
            return True

        # 检查是否在页面顶部或底部（可能是页眉页脚）
        if not self.config.include_headers_footers:
            if line_num <= 3 or line_num >= 45:  # 假设每页最多50行
                if self.is_likely_header_footer(text):
                    return True

        return False

    def is_likely_header_footer(self, text: str) -> bool:
        """判断是否可能是页眉页脚"""
        text_stripped = text.strip()

        # Must be very short to be header/footer
        if len(text_stripped) > 15:  # Increased from 20 to allow more content
            return False

        # Single number or very short line is likely header/footer
        if len(text_stripped) <= 5:
            return True

        # 包含页码模式
        if re.search(r'页\s*\d+|page\s*\d+|\d+\s*/\s*\d+', text, re.IGNORECASE):
            return True

        # 包含会议信息、期刊名称等
        header_footer_keywords = [
            'conference', 'proceedings', 'journal', 'volume', 'issue',
            'doi:', 'isbn:', 'issn:', 'copyright', '©'
        ]

        text_lower = text.lower()
        for keyword in header_footer_keywords:
            if keyword in text_lower:
                return True

        return False

    def remove_duplicate_lines(self, lines: List[Tuple[str, int, int]]) -> List[Tuple[str, int, int]]:
        """去除重复行"""
        seen_texts = set()
        unique_lines = []

        for text, page_num, line_num in lines:
            if text not in seen_texts:
                seen_texts.add(text)
                unique_lines.append((text, page_num, line_num))

        return unique_lines

    def extract_raw_text(self, pdf_path: str) -> str:
        """提取原始文本（兼容性方法）"""
        lines = self.extract_main_text_lines(pdf_path)
        return "\n".join([line[0] for line in lines])

    def extract_text_with_positions(self) -> List[Tuple[str, int, int]]:
        """
        提取PDF文本并保留位置信息（兼容PDFTextExtractor接口）

        Returns:
            List[Tuple[str, int, int]]: (文本, 页码, 行号) 的列表
        """
        # 如果已经设置了PDF路径，直接提取
        if hasattr(self, 'pdf_path') and self.pdf_path and os.path.exists(self.pdf_path):
            return self.extract_main_text_lines(self.pdf_path)

        # 如果没有设置路径或文件不存在，返回空列表
        return []

    def extract_raw_text_from_path(self, pdf_path: str) -> str:
        """
        从指定路径提取原始文本

        Args:
            pdf_path: PDF文件路径

        Returns:
            str: 提取的文本内容
        """
        lines = self.extract_main_text_lines(pdf_path)
        return "\n".join([line[0] for line in lines])

    def get_extraction_stats(self, pdf_path: str) -> Dict:
        """获取提取统计信息"""
        # 先尝试提取所有文本
        all_lines = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        all_lines.extend(lines)
        except Exception as e:
            return {"error": str(e)}

        # 提取正文
        main_lines = self.extract_main_text_lines(pdf_path)

        stats = {
            "total_pages": 0,
            "total_lines": len(all_lines),
            "main_content_lines": len(main_lines),
            "filtered_lines": len(all_lines) - len(main_lines),
            "filtering_ratio": (len(all_lines) - len(main_lines)) / len(all_lines) if all_lines else 0,
            "total_chars": sum(len(line[0]) for line in main_lines),
            "config": {
                "include_references": self.config.include_references,
                "include_footnotes": self.config.include_footnotes,
                "include_citations": self.config.include_citations,
                "include_page_numbers": self.config.include_page_numbers,
                "include_headers_footers": self.config.include_headers_footers,
                "include_annotations": self.config.include_annotations,
                "min_line_length": self.config.min_line_length,
            }
        }

        return stats


def create_default_main_content_extractor() -> EnhancedPDFTextExtractor:
    """创建默认的正文提取器（只提取正文，过滤其他内容）"""
    config = TextExtractionConfig(
        include_references=False,      # 不包含引用
        include_footnotes=False,        # 不包含脚注
        include_citations=False,        # 不包含引文
        include_page_numbers=False,    # 不包含页码
        include_headers_footers=False,  # 不包含页眉页脚
        include_annotations=False,     # 不包含批注
        min_line_length=10,             # 最小行长度10字符
        remove_duplicate_lines=True    # 去除重复行
    )
    return EnhancedPDFTextExtractor(config)


def test_enhanced_extractor():
    """测试增强版提取器"""
    print("=== 增强版PDF提取器测试 ===")

    # 创建测试配置
    config = TextExtractionConfig(
        include_references=False,
        include_citations=False,
        include_page_numbers=False,
        include_headers_footers=False,
        min_line_length=10,
        remove_duplicate_lines=True
    )

    extractor = EnhancedPDFTextExtractor(config)

    # 测试过滤规则
    test_lines = [
        "This is a normal line of text content.",
        "[1]",
        "References",
        "Page 123",
        "et al. (2020)",
        "123",
        "",
        "Short line",
        "这是一个正常的正文内容，包含足够的字数来进行测试。",
        "Table 1 shows the results.",
        "© 2024 All rights reserved"
    ]

    print("测试行过滤:")
    for i, line in enumerate(test_lines, 1):
        should_skip = extractor.should_skip_line(line, 1, i)
        status = "跳过" if should_skip else "保留"
        print(f"  {i}. '{line}' → {status}")

    # 测试统计功能
    print(f"\n默认配置:")
    for key, value in config.__dict__.items():
        print(f"  {key}: {value}")

    print("\n✅ 增强版PDF提取器创建成功！")


if __name__ == "__main__":
    test_enhanced_extractor()