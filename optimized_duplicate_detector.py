#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版相似序列检测器模块
使用多进程和智能算法大幅提升检测速度
"""

import time
from typing import List, Dict, Tuple, Optional
from pdf_extractor import PDFTextExtractor
from text_processor import TextProcessor, CharInfo
from optimized_sequence_generator import (OptimizedSequenceGenerator, SequenceInfo,
                                       SimilarSequenceInfo, FastSimilarityCalculator)


class OptimizedSimilarSequenceDetector:
    """优化版相似序列检测器"""

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75,
                 num_processes: int = None, max_sequences: int = 10000):
        """
        初始化优化版相似序列检测器

        Args:
            pdf1_path: 第一个PDF文件路径
            pdf2_path: 第二个PDF文件路径
            min_similarity: 最小相似度阈值 (0-1)
            num_processes: 进程数（None=自动检测）
            max_sequences: 每个文件的最大序列数（限制以提高速度）
        """
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path
        self.min_similarity = min_similarity
        self.max_sequences = max_sequences

        # 初始化为标准提取器（后续可以替换为增强版）
        self.extractor1 = PDFTextExtractor(pdf1_path)
        self.extractor2 = PDFTextExtractor(pdf2_path)

        self.processor = TextProcessor()
        self.generator = OptimizedSequenceGenerator(min_similarity, num_processes)
        self.calculator = FastSimilarityCalculator(min_similarity)

    def process_pdf_with_limit(self, extractor, pdf_name: str) -> Tuple[List[CharInfo], List[SequenceInfo]]:
        """
        处理单个PDF文件并限制序列数量

        Args:
            extractor: PDF提取器（EnhancedPDFTextExtractor 或 PDFTextExtractor）
            pdf_name: PDF名称（用于显示）

        Returns:
            Tuple[字符列表, 序列列表]
        """
        print(f"\n=== 处理 {pdf_name} ===")

        # 1. 提取文本
        print("1. 提取PDF文本...")
        start_time = time.time()

        # 根据提取器类型调用不同的方法
        if hasattr(extractor, 'extract_main_text_lines'):
            # EnhancedPDFTextExtractor
            if pdf_name == "文件1":
                extracted_text = extractor.extract_main_text_lines(self.pdf1_path)
            elif pdf_name == "文件2":
                extracted_text = extractor.extract_main_text_lines(self.pdf2_path)
            else:
                print(f"   错误: 未知的文件名 {pdf_name}")
                return [], []
        else:
            # PDFTextExtractor
            extracted_text = extractor.extract_text_with_positions()

        print(f"   提取了 {len(extracted_text):,} 行文本，耗时 {time.time() - start_time:.2f} 秒")

        # 2. 文本预处理
        print("2. 文本预处理（分字）...")
        start_time = time.time()
        chars = self.processor.process_extracted_text(extracted_text)
        print(f"   生成了 {len(chars):,} 个字符，耗时 {time.time() - start_time:.2f} 秒")

        # 3. 生成序列
        print("3. 生成8字序列...")
        start_time = time.time()
        sequences = self.generator.generate_sequences(chars)

        # 限制序列数量以控制性能
        if len(sequences) > self.max_sequences:
            print(f"   序列数量 {len(sequences):,} 超过限制 {self.max_sequences:,}，进行采样...")
            # 均匀采样以保持代表性
            step = len(sequences) // self.max_sequences
            sequences = sequences[::step][:self.max_sequences]

        print(f"   处理 {len(sequences):,} 个序列，耗时 {time.time() - start_time:.2f} 秒")

        return chars, sequences

    def detect_similar_sequences_optimized(self, show_progress: bool = True) -> List[SimilarSequenceInfo]:
        """
        检测相似序列（优化版）

        Args:
            show_progress: 是否显示进度

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息
        """
        print("开始优化版相似序列检测...")
        total_start_time = time.time()

        # 处理两个文件
        chars1, sequences1 = self.process_pdf_with_limit(self.extractor1, "文件1")
        chars2, sequences2 = self.process_pdf_with_limit(self.extractor2, "文件2")

        # 预估计算量
        total_comparisons = len(sequences1) * len(sequences2)
        print(f"\n=== 相似度检测 ===")
        print(f"相似度阈值: {self.min_similarity:.2f}")
        print(f"文件1序列数: {len(sequences1):,}")
        print(f"文件2序列数: {len(sequences2):,}")
        print(f"理论最大比较次数: {total_comparisons:,}")

        # 进度回调函数
        def progress_callback(progress, completed, total):
            if show_progress:
                elapsed = time.time() - callback_start_time
                if completed > 0:
                    estimated_total = elapsed * total / completed
                    remaining = estimated_total - elapsed
                    print(f"   进度: {completed}/{total} ({progress*100:.1f}%) - "
                          f"已用时: {elapsed:.1f}s, 预计剩余: {remaining:.1f}s")

        callback_start_time = time.time()

        # 执行优化的相似度检测
        start_time = time.time()
        similar_sequences = self.generator.find_similar_sequences_parallel(
            sequences1, sequences2, progress_callback if show_progress else None
        )
        detection_time = time.time() - start_time

        # 性能统计
        total_time = time.time() - total_start_time
        comparisons_per_second = total_comparisons / detection_time if detection_time > 0 else 0

        print(f"\n=== 检测完成 ===")
        print(f"找到 {len(similar_sequences):,} 个相似序列")
        print(f"检测耗时: {detection_time:.2f} 秒")
        print(f"总耗时: {total_time:.2f} 秒")
        print(f"处理速度: {comparisons_per_second:,.0f} 比较/秒")

        return similar_sequences

    def format_output_optimized(self, similar_sequences: List[SimilarSequenceInfo],
                               show_all_positions: bool = True,
                               max_results: Optional[int] = None) -> str:
        """
        格式化输出结果（优化版）

        Args:
            similar_sequences: 相似序列列表
            show_all_positions: 是否显示所有位置
            max_results: 最大显示结果数量

        Returns:
            str: 格式化的输出结果
        """
        output = []
        output.append("=" * 80)
        output.append("PDF文件相似序列检测报告（优化版）")
        output.append("=" * 80)
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"文件1: {self.pdf1_path}")
        output.append(f"文件2: {self.pdf2_path}")
        output.append(f"相似度阈值: {self.min_similarity:.2f}")
        output.append(f"序列数量限制: {self.max_sequences:,}")
        output.append(f"相似序列总数: {len(similar_sequences):,}")
        output.append("")

        if not similar_sequences:
            output.append(f"未发现相似度≥{self.min_similarity:.2f}的8字序列。")
            return "\n".join(output)

        # 限制显示结果数量
        display_sequences = similar_sequences[:max_results] if max_results else similar_sequences

        # 统计信息
        summary = self.generator.get_sequence_summary(similar_sequences)
        output.append("统计信息:")
        output.append(f"- 相似序列总数: {summary['total_similar']:,}")
        output.append(f"- 高相似度(>0.9): {summary['high_similarity_count']:,} 个")
        output.append(f"- 中相似度(0.8-0.9): {summary['medium_similarity_count']:,} 个")
        output.append(f"- 低相似度(0.75-0.8): {summary['low_similarity_count']:,} 个")
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
            output.append(f"... 还有 {len(similar_sequences) - max_results:,} 个相似序列未显示")
            output.append("完整结果请查看保存的文件。")

        return "\n".join(output)

    def save_results_optimized(self, similar_sequences: List[SimilarSequenceInfo],
                               output_file: str = "optimized_similar_sequences_results.txt"):
        """
        保存结果到文件（优化版）

        Args:
            similar_sequences: 相似序列列表
            output_file: 输出文件名
        """
        output = self.format_output_optimized(similar_sequences, show_all_positions=True)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果时出错: {e}")

    def run_detection_optimized(self, save_to_file: bool = True,
                                show_max_results: int = 50,
                                show_progress: bool = True) -> List[SimilarSequenceInfo]:
        """
        运行完整的检测流程（优化版）

        Args:
            save_to_file: 是否保存结果到文件
            show_max_results: 屏幕显示的最大结果数量
            show_progress: 是否显示进度

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息
        """
        print("=" * 80)
        print("开始PDF文件相似序列检测（优化版）")
        print(f"配置: 相似度≥{self.min_similarity:.2f}, 最大序列数={self.max_sequences:,}")
        print("=" * 80)

        start_time = time.time()

        # 检测相似序列
        similar_sequences = self.detect_similar_sequences_optimized(show_progress=show_progress)

        # 显示结果
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)
        print(self.format_output_optimized(similar_sequences, show_all_positions=False,
                                         max_results=show_max_results))

        # 保存结果
        if save_to_file:
            self.save_results_optimized(similar_sequences)

        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        return similar_sequences


# 创建一个快速便捷的函数
def fast_similarity_detection(pdf1_path: str, pdf2_path: str,
                            min_similarity: float = 0.8,
                            max_sequences: int = 5000,
                            num_processes: int = None) -> List[SimilarSequenceInfo]:
    """
    快速相似度检测函数

    Args:
        pdf1_path: 第一个PDF文件路径
        pdf2_path: 第二个PDF文件路径
        min_similarity: 相似度阈值（默认0.8，更严格）
        max_sequences: 每个文件最大序列数（默认5000，更快）
        num_processes: 进程数（None=自动检测）

    Returns:
        List[SimilarSequenceInfo]: 相似序列列表
    """
    detector = OptimizedSimilarSequenceDetector(
        pdf1_path, pdf2_path, min_similarity, num_processes, max_sequences
    )
    return detector.run_detection_optimized(
        save_to_file=False,
        show_max_results=20,
        show_progress=True
    )


def test_optimized_detector():
    """测试优化版检测器"""
    print("优化版相似序列检测器已创建")
    print("主要优化:")
    print("- 多进程并行处理")
    print("- 智能哈希预筛选")
    print("- 序列数量限制")
    print("- 实时进度显示")
    print("- 性能监控")


if __name__ == "__main__":
    test_optimized_detector()