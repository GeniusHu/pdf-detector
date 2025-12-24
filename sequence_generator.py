#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8字序列生成模块
用于从字符序列中生成所有连续的8字序列，并检测相似序列
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
from text_processor import CharInfo
from dataclasses import dataclass
import difflib


@dataclass
class SequenceInfo:
    """8字序列信息类"""
    sequence: str                       # 8字序列内容
    start_index: int                    # 在字符序列中的起始位置
    start_char: CharInfo               # 起始字符的位置信息
    end_char: CharInfo                 # 结束字符的位置信息
    chars: List[CharInfo]              # 包含的8个字符信息

    def __str__(self):
        return f"'{self.sequence}' (页{self.start_char.page}行{self.start_char.line}-页{self.end_char.page}行{self.end_char.line})"


@dataclass
class SimilarSequenceInfo:
    """相似序列信息类"""
    sequence1: SequenceInfo             # 文件1中的序列
    sequence2: SequenceInfo             # 文件2中的序列
    similarity: float                   # 相似度 (0-1)
    differences: List[str]              # 差异描述

    def __str__(self):
        return (f"相似度: {self.similarity:.2f} | "
                f"'{self.sequence1.sequence}' ↔ '{self.sequence2.sequence}'")


class SimilarityCalculator:
    """相似度计算器"""

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化相似度计算器

        Args:
            min_similarity: 最小相似度阈值 (0-1)
        """
        self.min_similarity = min_similarity

    def calculate_similarity(self, seq1: str, seq2: str) -> float:
        """
        计算两个序列的相似度

        Args:
            seq1: 序列1
            seq2: 序列2

        Returns:
            float: 相似度 (0-1)
        """
        # 使用SequenceMatcher计算相似度
        return difflib.SequenceMatcher(None, seq1, seq2).ratio()

    def get_differences(self, seq1: str, seq2: str) -> List[str]:
        """
        获取两个序列的差异描述

        Args:
            seq1: 序列1
            seq2: 序列2

        Returns:
            List[str]: 差异描述列表
        """
        words1 = seq1.split()
        words2 = seq2.split()

        differences = []
        sm = difflib.SequenceMatcher(None, words1, words2)

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                differences.append(f"替换: {' '.join(words1[i1:i2])} → {' '.join(words2[j1:j2])}")
            elif tag == 'delete':
                differences.append(f"删除: {' '.join(words1[i1:i2])}")
            elif tag == 'insert':
                differences.append(f"插入: {' '.join(words2[j1:j2])}")

        return differences if differences else ["完全相同"]

    def is_similar(self, seq1: str, seq2: str) -> Tuple[bool, float, List[str]]:
        """
        判断两个序列是否相似

        Args:
            seq1: 序列1
            seq2: 序列2

        Returns:
            Tuple[bool, float, List[str]]: (是否相似, 相似度, 差异列表)
        """
        similarity = self.calculate_similarity(seq1, seq2)
        differences = self.get_differences(seq1, seq2)
        is_similar = similarity >= self.min_similarity

        return is_similar, similarity, differences


class SequenceGenerator:
    """8字序列生成器"""

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化序列生成器

        Args:
            min_similarity: 最小相似度阈值
        """
        self.min_similarity = min_similarity
        self.similarity_calculator = SimilarityCalculator(min_similarity)

    def generate_sequences(self, chars: List[CharInfo]) -> List[SequenceInfo]:
        """
        从字符列表中生成所有连续的8字序列

        Args:
            chars: 字符信息列表

        Returns:
            List[SequenceInfo]: 8字序列信息列表
        """
        sequences = []

        for i in range(len(chars) - 7):  # -7 因为需要8个字符
            # 取8个连续字符
            seq_chars = chars[i:i+8]
            sequence = " ".join([char.char for char in seq_chars])

            # 创建序列信息
            seq_info = SequenceInfo(
                sequence=sequence,
                start_index=i,
                start_char=seq_chars[0],
                end_char=seq_chars[7],
                chars=seq_chars
            )
            sequences.append(seq_info)

        return sequences

    def create_sequence_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """
        创建序列查找表，用于快速查找重复序列

        Args:
            sequences: 8字序列列表

        Returns:
            Dict[str, List[SequenceInfo]]: 序列到其所有出现位置的映射
        """
        lookup_table = defaultdict(list)

        for seq_info in sequences:
            lookup_table[seq_info.sequence].append(seq_info)

        return dict(lookup_table)

    def find_similar_sequences(self,
                              file1_sequences: Dict[str, List[SequenceInfo]],
                              file2_sequences: Dict[str, List[SequenceInfo]]) -> List[SimilarSequenceInfo]:
        """
        查找两个文件中相似的8字序列

        Args:
            file1_sequences: 文件1的序列查找表
            file2_sequences: 文件2的序列查找表

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息
        """
        similar_sequences = []
        processed_pairs = set()  # 避免重复处理同一对序列

        # 获取所有序列
        all_file1_seqs = []
        for seq_list in file1_sequences.values():
            all_file1_seqs.extend(seq_list)

        all_file2_seqs = []
        for seq_list in file2_sequences.values():
            all_file2_seqs.extend(seq_list)

        # 两两比较相似度
        for seq1_info in all_file1_seqs:
            for seq2_info in all_file2_seqs:
                # 创建唯一的配对标识（避免重复比较）
                pair_id = (id(seq1_info), id(seq2_info))
                if pair_id in processed_pairs:
                    continue
                processed_pairs.add(pair_id)

                # 计算相似度
                is_similar, similarity, differences = self.similarity_calculator.is_similar(
                    seq1_info.sequence, seq2_info.sequence
                )

                if is_similar:
                    similar_seq_info = SimilarSequenceInfo(
                        sequence1=seq1_info,
                        sequence2=seq2_info,
                        similarity=similarity,
                        differences=differences
                    )
                    similar_sequences.append(similar_seq_info)

        # 按相似度降序排序
        similar_sequences.sort(key=lambda x: x.similarity, reverse=True)

        return similar_sequences

    def find_repeated_sequences(self,
                                file1_sequences: Dict[str, List[SequenceInfo]],
                                file2_sequences: Dict[str, List[SequenceInfo]]) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """
        查找两个文件中完全重复的8字序列（兼容旧接口）

        Args:
            file1_sequences: 文件1的序列查找表
            file2_sequences: 文件2的序列查找表

        Returns:
            Dict: 重复序列的详细信息
        """
        repeated_sequences = {}

        # 找出在两个文件中都出现的序列
        common_sequences = set(file1_sequences.keys()) & set(file2_sequences.keys())

        for sequence in common_sequences:
            repeated_sequences[sequence] = (
                file1_sequences[sequence],
                file2_sequences[sequence]
            )

        return repeated_sequences

    def get_sequence_summary(self, similar_sequences: List[SimilarSequenceInfo]) -> Dict:
        """
        获取相似序列的统计信息

        Args:
            similar_sequences: 相似序列列表

        Returns:
            Dict: 统计信息
        """
        summary = {
            'total_similar': len(similar_sequences),
            'high_similarity_count': 0,  # 相似度 > 0.9
            'medium_similarity_count': 0,  # 相似度 0.8-0.9
            'low_similarity_count': 0,   # 相似度 0.75-0.8
            'average_similarity': 0.0,
            'max_similarity': 0.0,
            'min_similarity': 1.0 if similar_sequences else 0.0
        }

        if not similar_sequences:
            return summary

        similarities = [seq.similarity for seq in similar_sequences]

        summary['average_similarity'] = sum(similarities) / len(similarities)
        summary['max_similarity'] = max(similarities)
        summary['min_similarity'] = min(similarities)

        for seq_info in similar_sequences:
            if seq_info.similarity > 0.9:
                summary['high_similarity_count'] += 1
            elif seq_info.similarity > 0.8:
                summary['medium_similarity_count'] += 1
            else:
                summary['low_similarity_count'] += 1

        return summary

    def get_exact_matches_summary(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]) -> Dict:
        """
        获取完全匹配的统计信息（兼容旧接口）

        Args:
            repeated_sequences: 重复序列字典

        Returns:
            Dict: 统计信息
        """
        summary = {
            'total_repeated': len(repeated_sequences),
            'file1_total_occurrences': 0,
            'file2_total_occurrences': 0,
            'max_occurrences_file1': 0,
            'max_occurrences_file2': 0
        }

        for seq, (file1_infos, file2_infos) in repeated_sequences.items():
            summary['file1_total_occurrences'] += len(file1_infos)
            summary['file2_total_occurrences'] += len(file2_infos)
            summary['max_occurrences_file1'] = max(summary['max_occurrences_file1'], len(file1_infos))
            summary['max_occurrences_file2'] = max(summary['max_occurrences_file2'], len(file2_infos))

        return summary


def test_sequence_generator():
    """测试序列生成器"""
    from text_processor import CharInfo

    # 创建测试字符
    chars = [
        CharInfo('人工智能', 1, 1, 0),
        CharInfo('技术', 1, 1, 1),
        CharInfo('发展', 1, 1, 2),
        CharInfo('非常', 1, 1, 3),
        CharInfo('迅速', 1, 1, 4),
        CharInfo('machine', 1, 1, 5),
        CharInfo('learning', 1, 1, 6),
        CharInfo('python', 1, 1, 7),
        CharInfo('2024', 1, 1, 8),
        CharInfo('年', 1, 1, 9),
        CharInfo('人工智能', 1, 1, 10),
        CharInfo('技术', 1, 1, 11),
        CharInfo('发展', 1, 1, 12),
        CharInfo('极其', 1, 1, 13),  # 与上面不同的词
        CharInfo('迅速', 1, 1, 14),
        CharInfo('machine', 1, 1, 15),
        CharInfo('learning', 1, 1, 16),
    ]

    generator = SequenceGenerator(min_similarity=0.75)

    # 测试序列生成
    sequences = generator.generate_sequences(chars)

    print("=== 8字序列生成测试 ===")
    print(f"总字符数: {len(chars)}")
    print(f"生成的8字序列数: {len(sequences)}")
    print("\n前5个序列:")
    for i, seq in enumerate(sequences[:5]):
        print(f"{i+1}. {seq}")

    # 测试查找表
    lookup_table = generator.create_sequence_lookup_table(sequences)
    print(f"\n唯一序列数: {len(lookup_table)}")

    # 模拟第二个文件的序列（有一些相似但不完全相同）
    chars2 = [
        CharInfo('人工智能', 2, 1, 0),
        CharInfo('技术', 2, 1, 1),
        CharInfo('发展', 2, 1, 2),
        CharInfo('非常', 2, 1, 3),
        CharInfo('迅速', 2, 1, 4),
        CharInfo('machine', 2, 1, 5),
        CharInfo('learning', 2, 1, 6),
        CharInfo('python', 2, 1, 7),
        CharInfo('2025', 2, 1, 8),  # 年份不同
        CharInfo('年', 2, 1, 9),
    ]

    sequences2 = generator.generate_sequences(chars2)
    lookup_table2 = generator.create_sequence_lookup_table(sequences2)

    # 测试相似度检测
    similar_sequences = generator.find_similar_sequences(lookup_table, lookup_table2)
    print(f"\n相似序列数: {len(similar_sequences)}")

    print("\n相似的序列:")
    for i, sim_seq in enumerate(similar_sequences[:5]):
        print(f"{i+1}. {sim_seq}")
        print(f"   差异: {', '.join(sim_seq.differences)}")

    # 显示统计信息
    summary = generator.get_sequence_summary(similar_sequences)
    print(f"\n统计信息: {summary}")


if __name__ == "__main__":
    test_sequence_generator()