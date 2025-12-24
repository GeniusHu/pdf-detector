#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版8字序列生成模块
使用多进程和智能算法大幅提升相似度检测速度
"""

from typing import List, Dict, Tuple, Set
from collections import defaultdict
from text_processor import CharInfo
from dataclasses import dataclass
import difflib
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import hashlib
import time
import itertools


@dataclass
class SequenceInfo:
    """8字序列信息类"""
    sequence: str                       # 8字序列内容
    start_index: int                    # 在字符序列中的起始位置
    start_char: CharInfo               # 起始字符的位置信息
    end_char: CharInfo                 # 结束字符的位置信息
    chars: List[CharInfo]              # 包含的8个字符信息
    hash_signature: str               # 序列哈希签名（用于快速筛选）

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
        return (f"相似度: {self.similarity:.3f} | "
                f"'{self.sequence1.sequence}' ↔ '{self.sequence2.sequence}'")


class FastSimilarityCalculator:
    """快速相似度计算器"""

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化快速相似度计算器

        Args:
            min_similarity: 最小相似度阈值 (0-1)
        """
        self.min_similarity = min_similarity

    def calculate_similarity(self, seq1: str, seq2: str) -> float:
        """
        计算两个序列的相似度
        """
        # 快速长度检查
        if abs(len(seq1.split()) - len(seq2.split())) > 2:
            return 0.0

        # 使用快速相似度算法
        return difflib.SequenceMatcher(None, seq1, seq2).ratio()

    def get_differences(self, seq1: str, seq2: str) -> List[str]:
        """
        获取两个序列的差异描述
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
        """
        similarity = self.calculate_similarity(seq1, seq2)
        differences = self.get_differences(seq1, seq2)
        is_similar = similarity >= self.min_similarity

        return is_similar, similarity, differences


class OptimizedSequenceGenerator:
    """优化版8字序列生成器"""

    def __init__(self, min_similarity: float = 0.75, num_processes: int = None):
        """
        初始化优化版序列生成器

        Args:
            min_similarity: 最小相似度阈值
            num_processes: 进程数（None=自动检测）
        """
        self.min_similarity = min_similarity
        self.num_processes = num_processes or min(8, mp.cpu_count())
        self.calculator = FastSimilarityCalculator(min_similarity)

    def generate_sequences(self, chars: List[CharInfo]) -> List[SequenceInfo]:
        """
        从字符列表中生成所有连续的8字序列
        """
        sequences = []

        for i in range(len(chars) - 7):  # -7 因为需要8个字符
            # 取8个连续字符
            seq_chars = chars[i:i+8]
            sequence = " ".join([char.char for char in seq_chars])

            # 生成哈希签名用于快速筛选
            hash_signature = self._generate_hash_signature(sequence)

            # 创建序列信息
            seq_info = SequenceInfo(
                sequence=sequence,
                start_index=i,
                start_char=seq_chars[0],
                end_char=seq_chars[7],
                chars=seq_chars,
                hash_signature=hash_signature
            )
            sequences.append(seq_info)

        return sequences

    def _generate_hash_signature(self, sequence: str) -> str:
        """
        生成序列的哈希签名用于快速筛选
        """
        # 取前3个词和后3个词的组合哈希
        words = sequence.split()
        if len(words) >= 6:
            key_part = " ".join(words[:3] + words[-3:])
        else:
            key_part = sequence

        return hashlib.md5(key_part.encode()).hexdigest()[:8]

    def create_hash_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """
        创建哈希查找表，用于快速预筛选相似序列
        """
        hash_table = defaultdict(list)

        for seq_info in sequences:
            # 为每个序列生成多个可能的哈希键
            words = seq_info.sequence.split()

            # 前4词哈希
            if len(words) >= 4:
                key1 = " ".join(words[:4])
                hash1 = hashlib.md5(key1.encode()).hexdigest()[:8]
                hash_table[hash1].append(seq_info)

            # 后4词哈希
            if len(words) >= 4:
                key2 = " ".join(words[-4:])
                hash2 = hashlib.md5(key2.encode()).hexdigest()[:8]
                hash_table[hash2].append(seq_info)

            # 间隔词哈希
            if len(words) >= 8:
                key3 = " ".join([words[i] for i in range(0, 8, 2)])
                hash3 = hashlib.md5(key3.encode()).hexdigest()[:8]
                hash_table[hash3].append(seq_info)

        return dict(hash_table)

    def _compare_sequences_chunk(self, chunk_data: Tuple) -> List[SimilarSequenceInfo]:
        """
        处理序列比较的一个数据块
        """
        file1_seqs_chunk, file2_sequences, min_similarity = chunk_data
        similar_sequences = []
        calculator = FastSimilarityCalculator(min_similarity)

        for seq1 in file1_seqs_chunk:
            for seq2 in file2_sequences:
                # 快速哈希预检查
                if seq1.hash_signature == seq2.hash_signature:
                    # 可能完全相同，详细检查
                    is_similar, similarity, differences = calculator.is_similar(
                        seq1.sequence, seq2.sequence
                    )
                    if is_similar:
                        similar_sequences.append(SimilarSequenceInfo(
                            sequence1=seq1,
                            sequence2=seq2,
                            similarity=similarity,
                            differences=differences
                        ))
                else:
                    # 快速相似度检查（限制比较次数）
                    is_similar, similarity, differences = calculator.is_similar(
                        seq1.sequence, seq2.sequence
                    )
                    if is_similar:
                        similar_sequences.append(SimilarSequenceInfo(
                            sequence1=seq1,
                            sequence2=seq2,
                            similarity=similarity,
                            differences=differences
                        ))

        return similar_sequences

    def find_similar_sequences_parallel(self,
                                       file1_sequences: List[SequenceInfo],
                                       file2_sequences: List[SequenceInfo],
                                       progress_callback=None) -> List[SimilarSequenceInfo]:
        """
        并行查找相似序列
        """
        print(f"开始并行相似度检测 (进程数: {self.num_processes})")
        print(f"文件1序列数: {len(file1_sequences):,}")
        print(f"文件2序列数: {len(file2_sequences):,}")

        # 使用哈希表预筛选
        print("生成哈希索引...")
        start_time = time.time()

        # 将文件2序列按哈希分组
        file2_hash_table = self.create_hash_lookup_table(file2_sequences)
        print(f"哈希索引创建完成，耗时 {time.time() - start_time:.2f} 秒")

        # 预筛选候选序列
        candidate_pairs = []
        for seq1 in file1_sequences[:10000]:  # 限制文件1的序列数量以提高速度
            # 为seq1生成可能的哈希键
            words = seq1.sequence.split()
            candidate_hashes = set()

            if len(words) >= 4:
                key1 = " ".join(words[:4])
                candidate_hashes.add(hashlib.md5(key1.encode()).hexdigest()[:8])
                key2 = " ".join(words[-4:])
                candidate_hashes.add(hashlib.md5(key2.encode()).hexdigest()[:8])

            if len(words) >= 8:
                key3 = " ".join([words[i] for i in range(0, 8, 2)])
                candidate_hashes.add(hashlib.md5(key3.encode()).hexdigest()[:8])

            # 找到所有候选序列
            candidates = []
            for hash_key in candidate_hashes:
                if hash_key in file2_hash_table:
                    candidates.extend(file2_hash_table[hash_key])

            # 去重（使用ID去重，因为SequenceInfo对象不是hashable）
            seen_ids = set()
            unique_candidates = []
            for candidate in candidates:
                if id(candidate) not in seen_ids:
                    seen_ids.add(id(candidate))
                    unique_candidates.append(candidate)
            candidates = unique_candidates

            # 添加候选对
            for seq2 in candidates:
                candidate_pairs.append((seq1, seq2))

        print(f"预筛选完成，从 {len(file1_sequences) * len(file2_sequences):,} 对中筛选出 {len(candidate_pairs):,} 对候选")

        # 分块处理候选对
        chunk_size = max(100, len(candidate_pairs) // self.num_processes)
        chunks = []

        for i in range(0, len(candidate_pairs), chunk_size):
            chunk = candidate_pairs[i:i+chunk_size]
            # 转换为适合并行处理的格式
            file1_chunk = [pair[0] for pair in chunk]
            chunks.append((file1_chunk, file2_sequences, self.min_similarity))

        # 并行处理
        print("开始并行比较...")
        all_similar_sequences = []

        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # 提交任务
            future_to_index = {
                executor.submit(self._compare_sequences_chunk, chunk): i
                for i, chunk in enumerate(chunks)
            }

            # 收集结果
            completed = 0
            for future in future_to_index:
                try:
                    result = future.result()
                    all_similar_sequences.extend(result)
                    completed += 1

                    # 进度回调
                    if progress_callback:
                        progress = completed / len(chunks)
                        progress_callback(progress, completed, len(chunks))

                    print(f"完成进度: {completed}/{len(chunks)} ({completed/len(chunks)*100:.1f}%)")

                except Exception as e:
                    print(f"处理块时出错: {e}")

        # 去重并排序
        unique_sequences = self._remove_duplicates(all_similar_sequences)
        unique_sequences.sort(key=lambda x: x.similarity, reverse=True)

        return unique_sequences

    def _remove_duplicates(self, sequences: List[SimilarSequenceInfo]) -> List[SimilarSequenceInfo]:
        """
        去除重复的相似序列
        """
        seen = set()
        unique_sequences = []

        for seq_info in sequences:
            # 创建唯一标识符
            identifier = (seq_info.sequence1.sequence, seq_info.sequence2.sequence)
            if identifier not in seen:
                seen.add(identifier)
                unique_sequences.append(seq_info)

        return unique_sequences

    # 保持向后兼容的接口
    def create_sequence_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """兼容旧接口"""
        lookup_table = defaultdict(list)
        for seq_info in sequences:
            lookup_table[seq_info.sequence].append(seq_info)
        return dict(lookup_table)

    def find_similar_sequences(self,
                              file1_sequences: Dict[str, List[SequenceInfo]],
                              file2_sequences: Dict[str, List[SequenceInfo]]) -> List[SimilarSequenceInfo]:
        """兼容旧接口的包装方法"""
        # 获取所有序列
        all_file1_seqs = []
        for seq_list in file1_sequences.values():
            all_file1_seqs.extend(seq_list)

        all_file2_seqs = []
        for seq_list in file2_sequences.values():
            all_file2_seqs.extend(seq_list)

        # 限制序列数量以提高速度
        if len(all_file1_seqs) > 10000:
            all_file1_seqs = all_file1_seqs[:10000]
            print(f"文件1序列数量限制为 {len(all_file1_seqs):,}（原数量超过限制）")

        if len(all_file2_seqs) > 10000:
            all_file2_seqs = all_file2_seqs[:10000]
            print(f"文件2序列数量限制为 {len(all_file2_seqs):,}（原数量超过限制）")

        # 使用并行方法
        return self.find_similar_sequences_parallel(all_file1_seqs, all_file2_seqs)

    def get_sequence_summary(self, similar_sequences: List[SimilarSequenceInfo]) -> Dict:
        """获取相似序列的统计信息"""
        summary = {
            'total_similar': len(similar_sequences),
            'high_similarity_count': 0,
            'medium_similarity_count': 0,
            'low_similarity_count': 0,
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
        """获取完全匹配的统计信息（兼容旧接口）"""
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

    def find_repeated_sequences(self,
                                file1_sequences: Dict[str, List[SequenceInfo]],
                                file2_sequences: Dict[str, List[SequenceInfo]]) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """查找两个文件中完全重复的8字序列（兼容旧接口）"""
        repeated_sequences = {}

        # 找出在两个文件中都出现的序列
        common_sequences = set(file1_sequences.keys()) & set(file2_sequences.keys())

        for sequence in common_sequences:
            repeated_sequences[sequence] = (
                file1_sequences[sequence],
                file2_sequences[sequence]
            )

        return repeated_sequences


def test_optimized_generator():
    """测试优化版序列生成器"""
    from text_processor import CharInfo

    print("=== 优化版8字序列生成测试 ===")

    # 创建更大的测试数据
    chars = []
    words = ['人工智能', '技术', '发展', '非常', '迅速', 'machine', 'learning', 'python', '2024', '年', '研究', '取得', '重要', '进展']

    for i in range(5000):  # 5000个字符
        word = words[i % len(words)]
        chars.append(CharInfo(word, 1 + i // 100, 1 + i % 100, i))

    generator = OptimizedSequenceGenerator(min_similarity=0.75, num_processes=4)

    # 测试序列生成
    print("\n1. 生成8字序列...")
    start_time = time.time()
    sequences = generator.generate_sequences(chars)
    generation_time = time.time() - start_time
    print(f"   生成 {len(sequences):,} 个序列，耗时 {generation_time:.2f} 秒")

    # 模拟第二个文件（部分相似）
    chars2 = chars.copy()
    for i in range(0, len(chars2), 100):  # 每100个字符改一个
        chars2[i] = CharInfo('深度学习', chars2[i].page, chars2[i].line, chars2[i].position)

    print("\n2. 生成第二个文件的序列...")
    start_time = time.time()
    sequences2 = generator.generate_sequences(chars2)
    generation_time2 = time.time() - start_time
    print(f"   生成 {len(sequences2):,} 个序列，耗时 {generation_time2:.2f} 秒")

    # 创建查找表
    print("\n3. 创建查找表...")
    start_time = time.time()
    lookup_table = generator.create_sequence_lookup_table(sequences)
    lookup_table2 = generator.create_sequence_lookup_table(sequences2)
    lookup_time = time.time() - start_time
    print(f"   创建查找表完成，耗时 {lookup_time:.2f} 秒")

    # 并行相似度检测
    print(f"\n4. 开始并行相似度检测 (进程数: {generator.num_processes})...")
    start_time = time.time()

    def progress_callback(progress, completed, total):
        print(f"   进度: {completed}/{total} ({progress*100:.1f}%)")

    similar_sequences = generator.find_similar_sequences_parallel(
        sequences[:1000], sequences2[:1000], progress_callback
    )
    comparison_time = time.time() - start_time

    print(f"\n5. 相似度检测完成:")
    print(f"   找到 {len(similar_sequences)} 个相似序列")
    print(f"   总耗时: {comparison_time:.2f} 秒")
    print(f"   平均每秒处理: {(1000*1000)/comparison_time:.0f} 对比较")

    # 显示前几个结果
    print(f"\n6. 前5个相似序列:")
    for i, sim_seq in enumerate(similar_sequences[:5]):
        print(f"   {i+1}. {sim_seq}")

    # 统计信息
    summary = generator.get_sequence_summary(similar_sequences)
    print(f"\n7. 统计信息: {summary}")


if __name__ == "__main__":
    test_optimized_generator()