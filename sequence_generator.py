#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8字序列生成模块
用于从字符序列中生成所有连续的8字序列，并检测相似序列

主要功能：
1. 从文本字符序列中生成所有连续的8字序列
2. 计算两个序列之间的相似度
3. 查找两个文件中相似的8字序列
4. 提供详细的差异分析和统计信息
"""

# typing: 类型注解模块，用于声明函数参数和返回值的类型
from typing import List, Dict, Set, Tuple
# collections.defaultdict: 带默认值的字典，当访问不存在的键时会自动创建默认值
from collections import defaultdict
# text_processor.CharInfo: 字符信息类，包含字符内容及其在文档中的位置信息
from text_processor import CharInfo
# dataclasses.dataclass: 数据类装饰器，用于自动生成初始化方法等常用方法
from dataclasses import dataclass
# difflib: Python标准库，用于序列比较和相似度计算
import difflib


@dataclass
class SequenceInfo:
    """
    8字序列信息类

    用于存储一个8字序列的完整信息，包括序列内容、位置信息和字符详情。
    这个类是整个相似度检测系统的基础数据结构。

    Attributes:
        sequence (str): 8字序列的内容，字符之间用空格分隔
        start_index (int): 该序列在整个字符列表中的起始索引位置
        start_char (CharInfo): 序列起始字符的详细信息（页码、行号、列号等）
        end_char (CharInfo): 序列结束字符的详细信息
        chars (List[CharInfo]): 包含的8个字符的完整信息列表

    Example:
        >>> char1 = CharInfo('人', page=1, line=1, col=0)
        >>> char2 = CharInfo('工', page=1, line=1, col=1)
        >>> # ... 创建8个字符
        >>> seq_info = SequenceInfo(
        ...     sequence='人 工 智 能 技 术 发 展',
        ...     start_index=0,
        ...     start_char=char1,
        ...     end_char=char8,
        ...     chars=[char1, char2, ...]
        ... )
        >>> print(seq_info)
        '人 工 智 能 技 术 发 展' (页1行1-页1行1)
    """

    sequence: str                       # 8字序列的内容，字符间用空格分隔
    start_index: int                    # 该序列在原始字符列表中的起始索引位置
    start_char: CharInfo               # 序列第一个字符的位置信息（包含页码、行号等）
    end_char: CharInfo                 # 序列最后一个字符的位置信息
    chars: List[CharInfo]              # 包含的8个字符的完整信息列表

    def __str__(self):
        """
        返回序列的字符串表示

        Returns:
            str: 格式化的字符串，包含序列内容和位置信息
                  格式: "'序列内容' (页X行Y-页A行B)"
        """
        return f"'{self.sequence}' (页{self.start_char.page}行{self.start_char.line}-页{self.end_char.page}行{self.end_char.line})"


@dataclass
class SimilarSequenceInfo:
    """
    相似序列信息类

    用于存储两个文件中相似的8字序列对的完整信息，包括相似度分数和详细差异。

    Attributes:
        sequence1 (SequenceInfo): 文件1中的序列信息
        sequence2 (SequenceInfo): 文件2中的序列信息
        similarity (float): 相似度分数，范围0-1，1表示完全相同，0表示完全不同
        differences (List[str]): 两个序列之间的差异描述列表，包括替换、删除、插入操作

    Example:
        >>> sim_info = SimilarSequenceInfo(
        ...     sequence1=seq_info1,
        ...     sequence2=seq_info2,
        ...     similarity=0.875,
        ...     differences=['替换: 非常 → 极其', '删除: 2024']
        ... )
        >>> print(sim_info)
        相似度: 0.88 | '人 工 智 能 非 常 迅 速' ↔ '人 工 智 能 极 其 迅 速'
    """

    sequence1: SequenceInfo             # 文件1中的序列信息对象
    sequence2: SequenceInfo             # 文件2中的序列信息对象
    similarity: float                   # 相似度分数，范围在0到1之间，1表示完全相同
    differences: List[str]              # 两个序列差异的详细描述列表（替换、删除、插入）

    def __str__(self):
        """
        返回相似序列的字符串表示

        Returns:
            str: 格式化的字符串，包含相似度和两个序列的内容
                  格式: "相似度: X.XX | '序列1' ↔ '序列2'"
        """
        return (f"相似度: {self.similarity:.2f} | "
                f"'{self.sequence1.sequence}' ↔ '{self.sequence2.sequence}'")


class SimilarityCalculator:
    """
    相似度计算器类

    提供序列相似度计算、差异分析和相似性判断功能。
    使用difflib库的SequenceMatcher算法来计算序列相似度。

    Attributes:
        min_similarity (float): 最小相似度阈值，默认为0.75（75%）
                               只有相似度达到此阈值的序列才会被认为是相似的

    Example:
        >>> calculator = SimilarityCalculator(min_similarity=0.75)
        >>> is_sim, score, diffs = calculator.is_similar(
        ...     '人 工 智 能 技 术',
        ...     '人 工 智 能 技 术'
        ... )
        >>> print(f"相似度: {score}")  # 输出: 相似度: 1.0
    """

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化相似度计算器

        Args:
            min_similarity (float): 最小相似度阈值，范围0-1，默认为0.75
                                   用于判断两个序列是否被认为相似

        Example:
            >>> calculator = SimilarityCalculator(min_similarity=0.8)  # 设置80%为阈值
        """
        self.min_similarity = min_similarity  # 存储相似度阈值，用于后续判断

    def calculate_similarity(self, seq1: str, seq2: str) -> float:
        """
        计算两个序列的相似度

        使用difflib.SequenceMatcher的ratio()方法计算相似度。
        该算法基于最长公共子序列（LCS），返回值在0到1之间。

        Args:
            seq1 (str): 第一个序列，字符间用空格分隔
            seq2 (str): 第二个序列，字符间用空格分隔

        Returns:
            float: 相似度分数，范围0-1
                   - 1.0 表示完全相同
                   - 0.0 表示完全不同
                   - 中间值表示部分相似

        Example:
            >>> calc = SimilarityCalculator()
            >>> score = calc.calculate_similarity('人 工 智 能', '人 工 智 能')
            >>> print(score)  # 输出: 1.0
            >>> score = calc.calculate_similarity('人 工 智 能', '机 器 学 习')
            >>> print(score)  # 输出: 0.0
        """
        # 使用SequenceMatcher计算相似度，None表示不使用自定义的序列比较函数
        return difflib.SequenceMatcher(None, seq1, seq2).ratio()

    def get_differences(self, seq1: str, seq2: str) -> List[str]:
        """
        获取两个序列的差异描述

        使用difflib.SequenceMatcher的get_opcodes()方法来分析序列差异。
        能够识别三种类型的操作：替换、删除、插入。

        Args:
            seq1 (str): 第一个序列，作为比较的基准
            seq2 (str): 第二个序列，与seq1进行比较

        Returns:
            List[str]: 差异描述列表，每个元素描述一个差异操作
                      - 替换: "替换: 旧内容 → 新内容"
                      - 删除: "删除: 被删除的内容"
                      - 插入: "插入: 新插入的内容"
                      - 如果完全相同则返回 ["完全相同"]

        Example:
            >>> calc = SimilarityCalculator()
            >>> diffs = calc.get_differences(
            ...     '人 工 智 能 技 术',
            ...     '人 工 智 能 学 术'
            ... )
            >>> print(diffs)  # 输出: ['替换: 技 术 → 学 术']
        """
        # 将序列按空格分割成单词列表
        words1 = seq1.split()
        words2 = seq2.split()

        # 初始化差异列表
        differences = []
        # 创建SequenceMatcher对象用于比较两个序列
        sm = difflib.SequenceMatcher(None, words1, words2)

        # get_opcodes()返回操作码列表，描述如何将seq1转换为seq2
        # 每个操作码是 (tag, i1, i2, j1, j2) 元组
        # tag: 操作类型 ('replace', 'delete', 'insert', 'equal')
        # i1:i2: seq1中涉及的范围
        # j1:j2: seq2中涉及的范围
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                # 替换操作：seq1的words1[i1:i2]被替换为seq2的words2[j1:j2]
                differences.append(f"替换: {' '.join(words1[i1:i2])} → {' '.join(words2[j1:j2])}")
            elif tag == 'delete':
                # 删除操作：seq1的words1[i1:i2]被删除
                differences.append(f"删除: {' '.join(words1[i1:i2])}")
            elif tag == 'insert':
                # 插入操作：seq2的words2[j1:j2]被插入到seq1中
                differences.append(f"插入: {' '.join(words2[j1:j2])}")

        # 如果没有差异，返回"完全相同"；否则返回差异列表
        return differences if differences else ["完全相同"]

    def is_similar(self, seq1: str, seq2: str) -> Tuple[bool, float, List[str]]:
        """
        判断两个序列是否相似

        这是一个综合方法，计算相似度、分析差异，并根据阈值判断是否相似。
        返回的元组包含了完整的比较结果。

        Args:
            seq1 (str): 第一个序列
            seq2 (str): 第二个序列

        Returns:
            Tuple[bool, float, List[str]]: 包含三个元素的元组
                - bool: 是否相似（True表示相似度达到或超过阈值）
                - float: 相似度分数（0-1）
                - List[str]: 差异描述列表

        Example:
            >>> calc = SimilarityCalculator(min_similarity=0.75)
            >>> is_sim, score, diffs = calc.is_similar(
            ...     '人 工 智 能 技 术',
            ...     '人 工 智 能 技 术'
            ... )
            >>> print(f"相似: {is_sim}, 分数: {score}")
            相似: True, 分数: 1.0
        """
        # 计算两个序列的相似度分数
        similarity = self.calculate_similarity(seq1, seq2)
        # 获取详细的差异描述
        differences = self.get_differences(seq1, seq2)
        # 判断相似度是否达到阈值
        is_similar = similarity >= self.min_similarity

        return is_similar, similarity, differences


class SequenceGenerator:
    """
    8字序列生成器类

    这是整个系统的核心类，负责从文本中生成8字序列，并检测相似序列。
    主要功能包括：
    1. 从字符列表生成所有连续的8字序列
    2. 创建序列查找表以优化查找性能
    3. 比较两个文件中的相似序列
    4. 生成详细的统计信息

    Attributes:
        min_similarity (float): 最小相似度阈值
        similarity_calculator (SimilarityCalculator): 相似度计算器实例

    Example:
        >>> generator = SequenceGenerator(min_similarity=0.75)
        >>> sequences = generator.generate_sequences(char_list)
        >>> similar = generator.find_similar_sequences(table1, table2)
    """

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化序列生成器

        Args:
            min_similarity (float): 最小相似度阈值，范围0-1，默认为0.75
                                   用于过滤不相似的序列对

        Example:
            >>> generator = SequenceGenerator(min_similarity=0.8)
        """
        self.min_similarity = min_similarity  # 存储相似度阈值
        # 创建相似度计算器实例，用于后续的相似度计算
        self.similarity_calculator = SimilarityCalculator(min_similarity)

    def generate_sequences(self, chars: List[CharInfo]) -> List[SequenceInfo]:
        """
        从字符列表中生成所有连续的8字序列

        使用滑动窗口算法，每次从字符列表中取8个连续字符。
        如果字符列表长度为N，将生成N-7个序列（每个序列包含8个字符）。

        Args:
            chars (List[CharInfo]): 字符信息列表，按文档顺序排列
                                   每个CharInfo包含字符内容和位置信息

        Returns:
            List[SequenceInfo]: 8字序列信息列表，每个元素包含：
                               - 序列内容（8个字符，空格分隔）
                               - 起始和结束位置信息
                               - 包含的8个字符的完整信息

        Example:
            >>> chars = [
            ...     CharInfo('人', 1, 1, 0),
            ...     CharInfo('工', 1, 1, 1),
            ...     # ... 更多字符
            ... ]
            >>> generator = SequenceGenerator()
            >>> sequences = generator.generate_sequences(chars)
            >>> print(f"生成了 {len(sequences)} 个8字序列")
        """
        sequences = []  # 用于存储所有生成的8字序列

        # 遍历字符列表，每次取8个连续字符
        # len(chars) - 7 确保能够取到完整的8个字符
        # 例如：如果有10个字符，索引范围是0-9，最后一个序列从索引2开始（2-9）
        for i in range(len(chars) - 7):
            # 使用切片获取8个连续字符（从索引i到i+7）
            seq_chars = chars[i:i+8]
            # 将8个字符的内容用空格连接成字符串
            sequence = " ".join([char.char for char in seq_chars])

            # 创建SequenceInfo对象存储序列的完整信息
            seq_info = SequenceInfo(
                sequence=sequence,      # 序列内容
                start_index=i,          # 起始索引
                start_char=seq_chars[0],  # 起始字符信息
                end_char=seq_chars[7],    # 结束字符信息（第8个字符，索引为7）
                chars=seq_chars         # 包含的8个字符的完整列表
            )
            sequences.append(seq_info)  # 将生成的序列添加到结果列表

        return sequences  # 返回所有生成的8字序列

    def create_sequence_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """
        创建序列查找表，用于快速查找重复序列

        创建一个哈希表（字典），键是序列内容，值是该序列出现的所有位置列表。
        这个查找表可以快速判断某个序列是否存在，以及它的所有出现位置。

        Args:
            sequences (List[SequenceInfo]): 8字序列列表，通常由generate_sequences()生成

        Returns:
            Dict[str, List[SequenceInfo]]: 序列查找表，结构为：
                                          {
                                              '序列1': [SequenceInfo1, SequenceInfo2, ...],
                                              '序列2': [SequenceInfo3, ...],
                                              ...
                                          }
                                          值为列表是因为同一序列可能在文档中多次出现

        Example:
            >>> sequences = generator.generate_sequences(chars)
            >>> lookup_table = generator.create_sequence_lookup_table(sequences)
            >>> # 查找某个序列的所有出现位置
            >>> positions = lookup_table.get('人 工 智 能 技 术')
            >>> print(f"该序列出现了 {len(positions)} 次")
        """
        # 使用defaultdict(list)创建字典，当访问不存在的键时自动创建空列表
        lookup_table = defaultdict(list)

        # 遍历所有序列，将相同内容的序列分组存储
        for seq_info in sequences:
            # 将序列信息添加到对应序列内容的列表中
            lookup_table[seq_info.sequence].append(seq_info)

        # 将defaultdict转换为普通dict后返回
        return dict(lookup_table)

    def find_similar_sequences(self,
                              file1_sequences: Dict[str, List[SequenceInfo]],
                              file2_sequences: Dict[str, List[SequenceInfo]]) -> List[SimilarSequenceInfo]:
        """
        查找两个文件中相似的8字序列

        对两个文件的序列进行两两比较，找出所有相似度达到阈值的序列对。
        使用嵌套循环进行比较，使用set避免重复比较。

        Args:
            file1_sequences (Dict[str, List[SequenceInfo]]): 文件1的序列查找表
                                                             由create_sequence_lookup_table()生成
            file2_sequences (Dict[str, List[SequenceInfo]]): 文件2的序列查找表
                                                             由create_sequence_lookup_table()生成

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息列表，按相似度降序排列
                                      每个元素包含：
                                      - 两个文件的序列信息
                                      - 相似度分数
                                      - 差异描述

        Example:
            >>> table1 = generator.create_sequence_lookup_table(sequences1)
            >>> table2 = generator.create_sequence_lookup_table(sequences2)
            >>> similar = generator.find_similar_sequences(table1, table2)
            >>> for sim_seq in similar:
            ...     print(f"{sim_seq.similarity:.2%}: {sim_seq}")
        """
        similar_sequences = []  # 存储找到的所有相似序列对
        processed_pairs = set()  # 使用集合记录已处理的序列对，避免重复比较

        # 将文件1的所有序列展平成一个列表
        # file1_sequences是字典{序列: [出现位置列表]}，需要取出所有序列对象
        all_file1_seqs = []
        for seq_list in file1_sequences.values():
            all_file1_seqs.extend(seq_list)  # 将每个序列的所有出现位置添加到列表

        # 将文件2的所有序列展平成一个列表
        all_file2_seqs = []
        for seq_list in file2_sequences.values():
            all_file2_seqs.extend(seq_list)

        # 双重循环：对文件1的每个序列，与文件2的所有序列进行比较
        for seq1_info in all_file1_seqs:
            for seq2_info in all_file2_seqs:
                # 使用对象id创建唯一的配对标识符
                # id()返回对象的内存地址，可以唯一标识一个对象
                pair_id = (id(seq1_info), id(seq2_info))
                if pair_id in processed_pairs:
                    continue  # 如果这对序列已经比较过，跳过
                processed_pairs.add(pair_id)  # 标记这对序列已处理

                # 计算这对序列的相似度
                is_similar, similarity, differences = self.similarity_calculator.is_similar(
                    seq1_info.sequence,  # 文件1的序列内容
                    seq2_info.sequence   # 文件2的序列内容
                )

                # 如果相似度达到阈值，保存结果
                if is_similar:
                    similar_seq_info = SimilarSequenceInfo(
                        sequence1=seq1_info,      # 文件1的序列完整信息
                        sequence2=seq2_info,      # 文件2的序列完整信息
                        similarity=similarity,    # 相似度分数
                        differences=differences   # 差异描述
                    )
                    similar_sequences.append(similar_seq_info)

        # 按相似度降序排序，最相似的序列对排在前面
        # key函数指定按similarity字段排序，reverse=True表示降序
        similar_sequences.sort(key=lambda x: x.similarity, reverse=True)

        return similar_sequences

    def find_repeated_sequences(self,
                                file1_sequences: Dict[str, List[SequenceInfo]],
                                file2_sequences: Dict[str, List[SequenceInfo]]) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """
        查找两个文件中完全重复的8字序列（兼容旧接口）

        这个方法查找两个文件中**完全相同**的序列（不考虑相似度）。
        使用集合交集操作来高效找出共同的序列。

        Args:
            file1_sequences (Dict[str, List[SequenceInfo]]): 文件1的序列查找表
            file2_sequences (Dict[str, List[SequenceInfo]]): 文件2的序列查找表

        Returns:
            Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]: 重复序列的字典
                键: 序列内容
                值: 元组(文件1中的位置列表, 文件2中的位置列表)

        Note:
            此方法只查找完全相同的序列，不考虑相似度。
            如果需要查找相似但不完全相同的序列，请使用find_similar_sequences()方法。

        Example:
            >>> repeated = generator.find_repeated_sequences(table1, table2)
            >>> for seq, (pos1, pos2) in repeated.items():
            ...     print(f"序列 '{seq}' 在文件1出现{len(pos1)}次，文件2出现{len(pos2)}次")
        """
        repeated_sequences = {}  # 存储完全重复的序列

        # 使用集合的交集操作找出在两个文件中都出现的序列
        # & 运算符返回两个集合的交集
        common_sequences = set(file1_sequences.keys()) & set(file2_sequences.keys())

        # 遍历所有共同的序列，记录它们在两个文件中的出现位置
        for sequence in common_sequences:
            repeated_sequences[sequence] = (
                file1_sequences[sequence],  # 该序列在文件1中的所有出现位置
                file2_sequences[sequence]   # 该序列在文件2中的所有出现位置
            )

        return repeated_sequences

    def get_sequence_summary(self, similar_sequences: List[SimilarSequenceInfo]) -> Dict:
        """
        获取相似序列的统计信息

        计算相似序列的数量、相似度分布、平均相似度等统计指标。
        相似度分为三个等级：
        - 高相似度: > 0.9 (90%以上)
        - 中等相似度: 0.8 - 0.9 (80%-90%)
        - 低相似度: 0.75 - 0.8 (75%-80%)

        Args:
            similar_sequences (List[SimilarSequenceInfo]): 相似序列列表
                                                           由find_similar_sequences()返回

        Returns:
            Dict: 统计信息字典，包含以下字段：
                - total_similar (int): 相似序列总数
                - high_similarity_count (int): 高相似度序列数量（>0.9）
                - medium_similarity_count (int): 中等相似度序列数量（0.8-0.9）
                - low_similarity_count (int): 低相似度序列数量（0.75-0.8）
                - average_similarity (float): 平均相似度
                - max_similarity (float): 最高相似度
                - min_similarity (float): 最低相似度

        Example:
            >>> similar = generator.find_similar_sequences(table1, table2)
            >>> summary = generator.get_sequence_summary(similar)
            >>> print(f"找到{summary['total_similar']}个相似序列")
            >>> print(f"平均相似度: {summary['average_similarity']:.2%}")
        """
        # 初始化统计字典，设置默认值
        summary = {
            'total_similar': len(similar_sequences),  # 相似序列总数
            'high_similarity_count': 0,  # 高相似度计数（>0.9）
            'medium_similarity_count': 0,  # 中等相似度计数（0.8-0.9）
            'low_similarity_count': 0,   # 低相似度计数（0.75-0.8）
            'average_similarity': 0.0,   # 平均相似度
            'max_similarity': 0.0,       # 最高相似度
            'min_similarity': 1.0 if similar_sequences else 0.0  # 最低相似度
        }

        # 如果没有相似序列，直接返回空统计
        if not similar_sequences:
            return summary

        # 提取所有相似度分数
        similarities = [seq.similarity for seq in similar_sequences]

        # 计算基本统计指标
        summary['average_similarity'] = sum(similarities) / len(similarities)  # 平均值
        summary['max_similarity'] = max(similarities)  # 最大值
        summary['min_similarity'] = min(similarities)  # 最小值

        # 按相似度区间分类统计
        for seq_info in similar_sequences:
            if seq_info.similarity > 0.9:
                # 高相似度：> 90%
                summary['high_similarity_count'] += 1
            elif seq_info.similarity > 0.8:
                # 中等相似度：80% - 90%
                summary['medium_similarity_count'] += 1
            else:
                # 低相似度：75% - 80%
                summary['low_similarity_count'] += 1

        return summary

    def get_exact_matches_summary(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]) -> Dict:
        """
        获取完全匹配的统计信息（兼容旧接口）

        统计两个文件中完全相同的序列的数量和出现次数。
        这是对find_repeated_sequences()方法的补充统计。

        Args:
            repeated_sequences (Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]):
                重复序列字典，由find_repeated_sequences()返回

        Returns:
            Dict: 统计信息字典，包含以下字段：
                - total_repeated (int): 重复的序列总数（不同序列的数量）
                - file1_total_occurrences (int): 文件1中重复序列的总出现次数
                - file2_total_occurrences (int): 文件2中重复序列的总出现次数
                - max_occurrences_file1 (int): 文件1中单个序列的最大出现次数
                - max_occurrences_file2 (int): 文件2中单个序列的最大出现次数

        Example:
            >>> repeated = generator.find_repeated_sequences(table1, table2)
            >>> summary = generator.get_exact_matches_summary(repeated)
            >>> print(f"文件1中重复序列共出现{summary['file1_total_occurrences']}次")
            >>> print(f"单个序列在文件1中最多出现{summary['max_occurrences_file1']}次")
        """
        # 初始化统计字典
        summary = {
            'total_repeated': len(repeated_sequences),  # 重复序列的种类数
            'file1_total_occurrences': 0,  # 文件1中所有重复序列的出现总次数
            'file2_total_occurrences': 0,  # 文件2中所有重复序列的出现总次数
            'max_occurrences_file1': 0,  # 文件1中单个序列的最大出现次数
            'max_occurrences_file2': 0   # 文件2中单个序列的最大出现次数
        }

        # 遍历所有重复序列，统计出现次数
        for seq, (file1_infos, file2_infos) in repeated_sequences.items():
            # file1_infos是该序列在文件1中的所有出现位置列表
            # file2_infos是该序列在文件2中的所有出现位置列表

            # 累加总出现次数
            summary['file1_total_occurrences'] += len(file1_infos)
            summary['file2_total_occurrences'] += len(file2_infos)

            # 更新最大出现次数（取当前值和新值中的较大者）
            summary['max_occurrences_file1'] = max(summary['max_occurrences_file1'], len(file1_infos))
            summary['max_occurrences_file2'] = max(summary['max_occurrences_file2'], len(file2_infos))

        return summary


def test_sequence_generator():
    """
    测试序列生成器

    这是一个测试函数，用于验证SequenceGenerator类的各项功能。
    包括：
    1. 从字符列表生成8字序列
    2. 创建序列查找表
    3. 查找相似序列
    4. 显示统计信息

    Example:
        直接运行此文件即可执行测试：
        $ python sequence_generator.py
    """
    from text_processor import CharInfo

    # 创建测试字符列表（模拟文档1的字符）
    # CharInfo参数：字符内容、页码、行号、列号
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
        CharInfo('极其', 1, 1, 13),  # 与上面不同的词（"极其" vs "非常"）
        CharInfo('迅速', 1, 1, 14),
        CharInfo('machine', 1, 1, 15),
        CharInfo('learning', 1, 1, 16),
    ]

    # 创建序列生成器实例，设置最小相似度阈值为75%
    generator = SequenceGenerator(min_similarity=0.75)

    # ========== 测试1：生成8字序列 ==========
    sequences = generator.generate_sequences(chars)

    print("=== 8字序列生成测试 ===")
    print(f"总字符数: {len(chars)}")
    print(f"生成的8字序列数: {len(sequences)}")
    print("\n前5个序列:")
    for i, seq in enumerate(sequences[:5]):
        print(f"{i+1}. {seq}")

    # ========== 测试2：创建序列查找表 ==========
    lookup_table = generator.create_sequence_lookup_table(sequences)
    print(f"\n唯一序列数: {len(lookup_table)}")

    # ========== 测试3：模拟第二个文件 ==========
    # 创建第二个字符列表（模拟文档2的字符）
    # 与文档1相比，有几个字符不同（用于测试相似度检测）
    chars2 = [
        CharInfo('人工智能', 2, 1, 0),
        CharInfo('技术', 2, 1, 1),
        CharInfo('发展', 2, 1, 2),
        CharInfo('非常', 2, 1, 3),
        CharInfo('迅速', 2, 1, 4),
        CharInfo('machine', 2, 1, 5),
        CharInfo('learning', 2, 1, 6),
        CharInfo('python', 2, 1, 7),
        CharInfo('2025', 2, 1, 8),  # 年份不同（2025 vs 2024）
        CharInfo('年', 2, 1, 9),
    ]

    sequences2 = generator.generate_sequences(chars2)
    lookup_table2 = generator.create_sequence_lookup_table(sequences2)

    # ========== 测试4：查找相似序列 ==========
    similar_sequences = generator.find_similar_sequences(lookup_table, lookup_table2)
    print(f"\n相似序列数: {len(similar_sequences)}")

    print("\n相似的序列:")
    for i, sim_seq in enumerate(similar_sequences[:5]):
        print(f"{i+1}. {sim_seq}")
        print(f"   差异: {', '.join(sim_seq.differences)}")

    # ========== 测试5：显示统计信息 ==========
    summary = generator.get_sequence_summary(similar_sequences)
    print(f"\n统计信息:")
    print(f"  总相似序列数: {summary['total_similar']}")
    print(f"  高相似度(>90%): {summary['high_similarity_count']}")
    print(f"  中等相似度(80-90%): {summary['medium_similarity_count']}")
    print(f"  低相似度(75-80%): {summary['low_similarity_count']}")
    print(f"  平均相似度: {summary['average_similarity']:.2%}")
    print(f"  最高相似度: {summary['max_similarity']:.2%}")
    print(f"  最低相似度: {summary['min_similarity']:.2%}")


if __name__ == "__main__":
    """
    主程序入口

    当直接运行此文件时（而不是作为模块导入时），执行测试函数。
    这是Python的常见模式，用于分离可执行代码和模块代码。

    Example:
        $ python sequence_generator.py
        或者
        >>> from sequence_generator import SequenceGenerator  # 不运行测试
        >>> import sequence_generator  # 不运行测试
    """
    test_sequence_generator()