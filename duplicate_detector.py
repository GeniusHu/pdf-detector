#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相似序列检测器模块
整合所有功能，检测两个PDF文件中的相似8字序列并输出结果
"""

import time
from typing import List, Dict, Tuple, Optional
from pdf_extractor import PDFTextExtractor
from text_processor import TextProcessor, CharInfo
from sequence_generator import (SequenceGenerator, SequenceInfo,
                              SimilarSequenceInfo, SimilarityCalculator)


class SimilarSequenceDetector:
    """相似序列检测器"""

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75):
        """
        初始化相似序列检测器

        Args:
            pdf1_path: 第一个PDF文件路径
            pdf2_path: 第二个PDF文件路径
            min_similarity: 最小相似度阈值 (0-1)
        """
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path
        self.min_similarity = min_similarity
        self.extractor1 = PDFTextExtractor(pdf1_path)
        self.extractor2 = PDFTextExtractor(pdf2_path)
        self.processor = TextProcessor()
        self.generator = SequenceGenerator(min_similarity)
        self.calculator = SimilarityCalculator(min_similarity)

    def process_pdf(self, extractor: PDFTextExtractor, pdf_name: str) -> Tuple[List[CharInfo], Dict[str, List[SequenceInfo]]]:
        """
        处理单个PDF文件

        Args:
            extractor: PDF提取器
            pdf_name: PDF名称（用于显示）

        Returns:
            Tuple[字符列表, 序列查找表]
        """
        print(f"\n=== 处理 {pdf_name} ===")

        # 1. 提取文本
        print("1. 提取PDF文本...")
        start_time = time.time()
        extracted_text = extractor.extract_text_with_positions()
        print(f"   提取了 {len(extracted_text)} 行文本，耗时 {time.time() - start_time:.2f} 秒")

        # 2. 文本预处理
        print("2. 文本预处理（分字）...")
        start_time = time.time()
        chars = self.processor.process_extracted_text(extracted_text)
        print(f"   生成了 {len(chars)} 个字符，耗时 {time.time() - start_time:.2f} 秒")

        # 3. 生成序列
        print("3. 生成8字序列...")
        start_time = time.time()
        sequences = self.generator.generate_sequences(chars)
        lookup_table = self.generator.create_sequence_lookup_table(sequences)
        print(f"   生成了 {len(sequences)} 个序列，{len(lookup_table)} 个唯一序列，耗时 {time.time() - start_time:.2f} 秒")

        return chars, lookup_table

    def detect_similar_sequences(self) -> List[SimilarSequenceInfo]:
        """
        检测相似序列

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息
        """
        print("开始检测相似序列...")

        # 处理两个文件
        chars1, lookup_table1 = self.process_pdf(self.extractor1, "文件1")
        chars2, lookup_table2 = self.process_pdf(self.extractor2, "文件2")

        # 检测相似序列
        print("\n=== 检测相似序列 ===")
        print(f"相似度阈值: {self.min_similarity:.2f}")
        start_time = time.time()

        similar_sequences = self.generator.find_similar_sequences(lookup_table1, lookup_table2)
        print(f"检测完成，找到 {len(similar_sequences)} 个相似序列，耗时 {time.time() - start_time:.2f} 秒")

        return similar_sequences

    def format_output(self, similar_sequences: List[SimilarSequenceInfo],
                      show_all_positions: bool = True, max_results: Optional[int] = None) -> str:
        """
        格式化输出结果

        Args:
            similar_sequences: 相似序列列表
            show_all_positions: 是否显示所有位置
            max_results: 最大显示结果数量

        Returns:
            str: 格式化的输出结果
        """
        output = []
        output.append("=" * 80)
        output.append("PDF文件相似序列检测报告")
        output.append("=" * 80)
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"文件1: {self.pdf1_path}")
        output.append(f"文件2: {self.pdf2_path}")
        output.append(f"相似度阈值: {self.min_similarity:.2f}")
        output.append(f"相似序列总数: {len(similar_sequences)}")
        output.append("")

        if not similar_sequences:
            output.append(f"未发现相似度≥{self.min_similarity:.2f}的8字序列。")
            return "\n".join(output)

        # 限制显示结果数量
        display_sequences = similar_sequences[:max_results] if max_results else similar_sequences

        # 统计信息
        summary = self.generator.get_sequence_summary(similar_sequences)
        output.append("统计信息:")
        output.append(f"- 相似序列总数: {summary['total_similar']}")
        output.append(f"- 高相似度(>0.9): {summary['high_similarity_count']} 个")
        output.append(f"- 中相似度(0.8-0.9): {summary['medium_similarity_count']} 个")
        output.append(f"- 低相似度(0.75-0.8): {summary['low_similarity_count']} 个")
        output.append(f"- 平均相似度: {summary['average_similarity']:.3f}")
        output.append(f"- 最高相似度: {summary['max_similarity']:.3f}")
        output.append(f"- 最低相似度: {summary['min_similarity']:.3f}")
        output.append("")

        # 详细结果
        output.append("相似序列详情 (按相似度排序):")
        output.append("-" * 80)

        for i, sim_seq in enumerate(display_sequences, 1):
            output.append(f"{i}. 相似度: {sim_seq.similarity:.3f}")
            output.append(f"   文件1: '{sim_seq.sequence1.sequence}'")
            output.append(f"          位置: 页{sim_seq.sequence1.start_char.page}行{sim_seq.sequence1.start_char.line} - "
                        f"页{sim_seq.sequence1.end_char.page}行{sim_seq.sequence1.end_char.line}")
            output.append(f"   文件2: '{sim_seq.sequence2.sequence}'")
            output.append(f"          位置: 页{sim_seq.sequence2.start_char.page}行{sim_seq.sequence2.start_char.line} - "
                        f"页{sim_seq.sequence2.end_char.page}行{sim_seq.sequence2.end_char.line}")

            # 显示差异
            if sim_seq.differences and sim_seq.differences != ["完全相同"]:
                output.append(f"   差异: {', '.join(sim_seq.differences)}")
            else:
                output.append(f"   差异: 无")

            output.append("")

        # 如果限制了显示数量，提示还有更多结果
        if max_results and len(similar_sequences) > max_results:
            output.append(f"... 还有 {len(similar_sequences) - max_results} 个相似序列未显示")
            output.append("完整结果请查看保存的文件。")

        return "\n".join(output)

    def save_results(self, similar_sequences: List[SimilarSequenceInfo],
                     output_file: str = "similar_sequences_results.txt"):
        """
        保存结果到文件

        Args:
            similar_sequences: 相似序列列表
            output_file: 输出文件名
        """
        output = self.format_output(similar_sequences, show_all_positions=True)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果时出错: {e}")

    def run_detection(self, save_to_file: bool = True,
                     show_max_results: int = 50) -> List[SimilarSequenceInfo]:
        """
        运行完整的检测流程

        Args:
            save_to_file: 是否保存结果到文件
            show_max_results: 屏幕显示的最大结果数量

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息
        """
        print("=" * 80)
        print("开始PDF文件相似序列检测")
        print("=" * 80)

        start_time = time.time()

        # 检测相似序列
        similar_sequences = self.detect_similar_sequences()

        # 显示结果
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)
        print(self.format_output(similar_sequences, show_all_positions=False,
                               max_results=show_max_results))

        # 保存结果
        if save_to_file:
            self.save_results(similar_sequences)

        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        return similar_sequences


class DuplicateDetector:
    """
    兼容旧接口的重复检测器
    """

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75):
        """
        初始化检测器

        Args:
            pdf1_path: 第一个PDF文件路径
            pdf2_path: 第二个PDF文件路径
            min_similarity: 最小相似度阈值 (默认0.75)
        """
        self.similarity_detector = SimilarSequenceDetector(pdf1_path, pdf2_path, min_similarity)

    def process_pdf(self, extractor: PDFTextExtractor, pdf_name: str) -> Tuple[List[CharInfo], Dict[str, List[SequenceInfo]]]:
        """兼容旧接口"""
        return self.similarity_detector.process_pdf(extractor, pdf_name)

    def detect_duplicates(self) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """兼容旧接口，返回完全匹配的序列"""
        chars1, lookup_table1 = self.process_pdf(self.similarity_detector.extractor1, "文件1")
        chars2, lookup_table2 = self.process_pdf(self.similarity_detector.extractor2, "文件2")
        return self.similarity_detector.generator.find_repeated_sequences(lookup_table1, lookup_table2)

    def format_output(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]],
                      show_all_positions: bool = True) -> str:
        """兼容旧接口"""
        output = []
        output.append("=" * 80)
        output.append("PDF文件序列检测报告")
        output.append("=" * 80)
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"文件1: {self.similarity_detector.pdf1_path}")
        output.append(f"文件2: {self.similarity_detector.pdf2_path}")
        output.append(f"完全匹配序列数: {len(repeated_sequences)}")
        output.append("")

        if not repeated_sequences:
            output.append("未发现完全相同的8字序列。")
            output.append("\n提示: 现在系统支持相似度检测，使用 detect_similar_sequences() 方法")
            output.append(f"可以找到相似度≥{self.similarity_detector.min_similarity:.2f}的序列。")
            return "\n".join(output)

        # 显示完全匹配的结果
        summary = self.similarity_detector.generator.get_exact_matches_summary(repeated_sequences)
        output.append("完全匹配统计:")
        output.append(f"- 完全匹配序列数: {summary['total_repeated']}")
        output.append(f"- 文件1中出现总次数: {summary['file1_total_occurrences']}")
        output.append(f"- 文件2中出现总次数: {summary['file2_total_occurrences']}")
        output.append("")

        output.append("完全匹配的序列:")
        output.append("-" * 80)

        for i, (sequence, (file1_infos, file2_infos)) in enumerate(repeated_sequences.items(), 1):
            output.append(f"{i}. 序列: '{sequence}'")
            output.append(f"   在文件1中出现 {len(file1_infos)} 次:")

            if show_all_positions:
                for j, seq_info in enumerate(file1_infos, 1):
                    output.append(f"     {j}. 页{seq_info.start_char.page}行{seq_info.start_char.line} - "
                                f"页{seq_info.end_char.page}行{seq_info.end_char.line}")
            else:
                output.append(f"     首次出现: 页{file1_infos[0].start_char.page}行{file1_infos[0].start_char.line}")

            output.append(f"   在文件2中出现 {len(file2_infos)} 次:")

            if show_all_positions:
                for j, seq_info in enumerate(file2_infos, 1):
                    output.append(f"     {j}. 页{seq_info.start_char.page}行{seq_info.start_char.line} - "
                                f"页{seq_info.end_char.page}行{seq_info.end_char.line}")
            else:
                output.append(f"     首次出现: 页{file2_infos[0].start_char.page}行{file2_infos[0].start_char.line}")

            output.append("")

        output.append("\n提示: 现在系统支持相似度检测！")
        output.append(f"可以找到相似度≥{self.similarity_detector.min_similarity:.2f}的序列。")

        return "\n".join(output)

    def save_results(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]],
                     output_file: str = "duplicate_results.txt"):
        """兼容旧接口"""
        output = self.format_output(repeated_sequences)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果时出错: {e}")

    def run_detection(self, save_to_file: bool = True) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """兼容旧接口，运行完全匹配检测"""
        print("=" * 80)
        print("开始PDF文件完全匹配序列检测")
        print("=" * 80)

        start_time = time.time()

        # 检测重复
        repeated_sequences = self.detect_duplicates()

        # 显示结果
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)
        print(self.format_output(repeated_sequences, show_all_positions=False))

        # 保存结果
        if save_to_file:
            self.save_results(repeated_sequences)

        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        return repeated_sequences

    def run_similarity_detection(self, save_to_file: bool = True) -> List[SimilarSequenceInfo]:
        """新接口：运行相似度检测"""
        return self.similarity_detector.run_detection(save_to_file=save_to_file)


def test_duplicate_detector():
    """测试重复检测器（需要实际的PDF文件）"""
    # 这里需要实际的PDF文件路径进行测试
    print("相似序列检测器模块已创建")
    print("要测试功能，请运行主程序并提供实际的PDF文件路径")
    print("\n新功能:")
    print("- 支持8字序列检测")
    print("- 支持相似度检测（默认≥0.75）")
    print("- 可调节相似度阈值")
    print("- 显示详细差异信息")


if __name__ == "__main__":
    test_duplicate_detector()