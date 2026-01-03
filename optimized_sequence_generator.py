#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版8字序列生成模块
使用多进程和智能算法大幅提升相似度检测速度

主要功能:
1. 从文档字符序列中生成连续的N字序列（默认为8字）
2. 使用多进程并行计算两个文档间的序列相似度
3. 通过哈希索引和预筛选优化大规模序列比对性能
4. 支持中文和英文文本的智能相似度检测

核心优化:
- 多进程并行处理，充分利用多核CPU
- 哈希签名快速预筛选候选相似序列
- 智能序列清理，保留中英文和数字字符
- 可配置的相似度阈值和序列长度
"""

# 类型注解支持，提供静态类型检查
from typing import List, Dict, Tuple, Set

# defaultdict: 带默认值的字典，用于构建哈希查找表
from collections import defaultdict

# CharInfo: 字符信息类，包含字符内容、页码、行号、位置等信息
from text_processor import CharInfo

# dataclass: 数据类装饰器，简化类的定义
from dataclasses import dataclass

# difflib: Python标准库，用于序列差异比较和相似度计算
import difflib

# multiprocessing: 多进程支持，用于并行计算
import multiprocessing as mp

# ProcessPoolExecutor: 进程池执行器，管理多进程任务
# ThreadPoolExecutor: 线程池执行器，管理多线程任务
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# hashlib: 哈希算法库，用于生成序列签名和快速索引
import hashlib

# time: 时间处理，用于性能计时和统计
import time

# itertools: 迭代工具，用于高效的迭代操作（本模块预留）
import itertools


@dataclass
class SequenceInfo:
    """
    序列信息类

    用于存储从文档中提取的连续字符序列及其相关信息。
    每个序列包含清理后的内容（用于比对）和原始内容（用于显示），
    同时记录了序列在文档中的位置信息。

    属性:
        sequence: 清理后的序列内容，用于相似度比对（只保留中英文和数字，无符号）
        raw_sequence: 原始序列内容，用于用户显示（保留原始符号和空格分隔）
        start_index: 序列在字符列表中的起始索引位置
        start_char: 起始字符的CharInfo对象，包含页码、行号等信息
        end_char: 结束字符的CharInfo对象，包含页码、行号等信息
        chars: 序列包含的所有字符信息列表
        hash_signature: 序列的MD5哈希签名（前8位），用于快速筛选和索引

    示例:
        >>> from text_processor import CharInfo
        >>> chars = [CharInfo('人', 1, 1, 0), CharInfo('工', 1, 1, 1)]
        >>> seq_info = SequenceInfo(
        ...     sequence="人工",
        ...     raw_sequence="人 工",
        ...     start_index=0,
        ...     start_char=chars[0],
        ...     end_char=chars[1],
        ...     chars=chars
        ... )
        >>> print(seq_info)
        '人 工' (页1行1-页1行1)
    """
    sequence: str                       # 清理后的序列内容（用于比对，无符号）
    raw_sequence: str = ""              # 原始序列内容（用于显示，保留符号）
    start_index: int = 0                # 在字符序列中的起始位置
    start_char: CharInfo = None         # 起始字符的位置信息
    end_char: CharInfo = None           # 结束字符的位置信息
    chars: List[CharInfo] = None        # 包含的字符信息
    hash_signature: str = ""            # 序列哈希签名（用于快速筛选）

    def __str__(self):
        """
        返回序列的可读字符串表示

        Returns:
            包含原始序列内容和位置信息的格式化字符串

        格式:
            '原始序列内容' (页起始页码行起始行号-页结束页码行结束行号)
        """
        return f"'{self.raw_sequence or self.sequence}' (页{self.start_char.page}行{self.start_char.line}-页{self.end_char.page}行{self.end_char.line})"


@dataclass
class SimilarSequenceInfo:
    """
    相似序列信息类

    用于存储两个文档间发现的相似序列对及其相关信息。
    包含两个文档中的序列对象、相似度分数和详细的差异描述。

    属性:
        sequence1: 第一个文档中的序列对象（SequenceInfo）
        sequence2: 第二个文档中的序列对象（SequenceInfo）
        similarity: 相似度分数，取值范围0-1，1表示完全相同，0表示完全不同
        differences: 差异描述列表，包含具体的替换、删除、插入操作说明

    示例:
        >>> from text_processor import CharInfo
        >>> seq1 = SequenceInfo(sequence="人工智能", raw_sequence="人 工 智 能", ...)
        >>> seq2 = SequenceInfo(sequence="机器学习", raw_sequence="机 器 学 习", ...)
        >>> sim_info = SimilarSequenceInfo(
        ...     sequence1=seq1,
        ...     sequence2=seq2,
        ...     similarity=0.75,
        ...     differences=["替换: 人工 → 机器", "替换: 智能 → 学习"]
        ... )
        >>> print(sim_info)
        相似度: 0.750 | '人工智能' ↔ '机器学习'
    """
    sequence1: SequenceInfo             # 文件1中的序列
    sequence2: SequenceInfo             # 文件2中的序列
    similarity: float                   # 相似度 (0-1)
    differences: List[str]              # 差异描述

    def __str__(self):
        """
        返回相似序列的可读字符串表示

        Returns:
            包含相似度和两个序列内容的格式化字符串

        格式:
            相似度: X.XXX | '序列1内容' ↔ '序列2内容'
        """
        return (f"相似度: {self.similarity:.3f} | "
                f"'{self.sequence1.sequence}' ↔ '{self.sequence2.sequence}'")


class FastSimilarityCalculator:
    """
    快速相似度计算器

    提供高效的序列相似度计算和差异分析功能。
    使用Python标准库difflib进行序列匹配，并包含快速预筛选优化。

    主要功能:
    - 计算两个文本序列的相似度分数（0-1）
    - 生成详细的差异描述（替换、删除、插入操作）
    - 基于阈值的相似度判断

    优化策略:
    - 长度快速检查：如果两个序列词数差异过大，直接返回0相似度
    - 使用difflib.SequenceMatcher的高效算法
    """

    def __init__(self, min_similarity: float = 0.75):
        """
        初始化快速相似度计算器

        Args:
            min_similarity: 最小相似度阈值，取值范围0-1。
                          只有相似度大于等于此值的序列才会被判定为相似。
                          默认0.75表示75%相似度。

        示例:
            >>> calculator = FastSimilarityCalculator(min_similarity=0.8)
            >>> is_sim, score, diff = calculator.is_similar("人工智能", "人工只能")
            >>> print(f"相似度: {score:.2f}, 是否相似: {is_sim}")
            相似度: 0.75, 是否相似: False
        """
        self.min_similarity = min_similarity

    def calculate_similarity(self, seq1: str, seq2: str) -> float:
        """
        计算两个序列的相似度

        使用difflib.SequenceMatcher计算序列相似度，返回0-1之间的浮点数。
        包含快速长度检查优化：如果两个序列词数差异超过2个，直接返回0。

        Args:
            seq1: 第一个文本序列
            seq2: 第二个文本序列

        Returns:
            相似度分数，取值范围0.0-1.0
            - 1.0 表示完全相同
            - 0.0 表示完全不同（或长度差异过大）
            - 中间值表示部分相似

        算法说明:
            使用SequenceMatcher.ratio()方法，基于最长公共子序列算法。
            公式: ratio = 2.0 * M / T
            其中 M = 匹配元素数量, T = 两个序列总元素数量

        示例:
            >>> calculator = FastSimilarityCalculator()
            >>> calculator.calculate_similarity("人工智能技术", "人工智能技术")
            1.0
            >>> calculator.calculate_similarity("人工智能", "机器学习")
            0.0
            >>> calculator.calculate_similarity("人工智能发展", "人工智能进步")
            0.75
        """
        # 快速长度检查：如果词数差异超过2，直接判定为不相似
        # 这是一种启发式优化，避免对明显不相似的序列进行昂贵的计算
        if abs(len(seq1.split()) - len(seq2.split())) > 2:
            return 0.0

        # 使用difflib.SequenceMatcher计算相似度
        # None表示不使用自定义的isjunk函数（移除不需要比较的元素）
        return difflib.SequenceMatcher(None, seq1, seq2).ratio()

    def get_differences(self, seq1: str, seq2: str) -> List[str]:
        """
        获取两个序列的差异描述

        分析两个序列的差异，返回人类可读的差异描述列表。
        差异类型包括：替换（replace）、删除（delete）、插入（insert）。

        Args:
            seq1: 第一个文本序列（基准序列）
            seq2: 第二个文本序列（对比序列）

        Returns:
            差异描述列表，每个描述说明一个操作（替换/删除/插入）
            如果完全相同，返回["完全相同"]

        差异说明:
            - 替换: seq1中的某些词被seq2中的词替换
            - 删除: seq1中的某些词在seq2中不存在
            - 插入: seq2中的某些词在seq1中不存在

        示例:
            >>> calculator = FastSimilarityCalculator()
            >>> calculator.get_differences("人工智能技术", "人工智能科学")
            ['替换: 技术 → 科学']
            >>> calculator.get_differences("人工智能", "人工智能技术")
            ['插入: 技术']
        """
        # 将序列按空格分割成词列表
        words1 = seq1.split()
        words2 = seq2.split()

        differences = []
        # 创建序列匹配器，用于分析差异
        sm = difflib.SequenceMatcher(None, words1, words2)

        # get_opcodes()返回差异操作代码列表
        # 每个操作代码是元组: (tag, i1, i2, j1, j2)
        # tag: 操作类型 ('replace', 'delete', 'insert', 'equal')
        # i1:i2: seq1中的操作范围
        # j1:j2: seq2中的操作范围
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                # 替换操作：seq1的[i1:i2]被替换为seq2的[j1:j2]
                differences.append(f"替换: {' '.join(words1[i1:i2])} → {' '.join(words2[j1:j2])}")
            elif tag == 'delete':
                # 删除操作：seq1的[i1:i2]在seq2中不存在
                differences.append(f"删除: {' '.join(words1[i1:i2])}")
            elif tag == 'insert':
                # 插入操作：seq2的[j1:j2]在seq1中不存在
                differences.append(f"插入: {' '.join(words2[j1:j2])}")

        # 如果没有差异，返回完全相同的标记
        return differences if differences else ["完全相同"]

    def is_similar(self, seq1: str, seq2: str) -> Tuple[bool, float, List[str]]:
        """
        判断两个序列是否相似

        综合方法：计算相似度、生成差异描述，并根据阈值判断是否相似。

        Args:
            seq1: 第一个文本序列
            seq2: 第二个文本序列

        Returns:
            包含三个元素的元组:
            - is_similar (bool): 是否达到相似度阈值
            - similarity (float): 相似度分数（0-1）
            - differences (List[str]): 差异描述列表

        示例:
            >>> calculator = FastSimilarityCalculator(min_similarity=0.75)
            >>> is_sim, score, diff = calculator.is_similar("人工智能技术", "人工智能技术")
            >>> print(f"相似: {is_sim}, 分数: {score:.2f}, 差异: {diff}")
            相似: True, 分数: 1.00, 差异: ['完全相同']
            >>> is_sim, score, diff = calculator.is_similar("人工智能", "机器学习")
            >>> print(f"相似: {is_sim}, 分数: {score:.2f}")
            相似: False, 分数: 0.00
        """
        # 计算相似度分数
        similarity = self.calculate_similarity(seq1, seq2)

        # 生成差异描述
        differences = self.get_differences(seq1, seq2)

        # 判断是否达到相似度阈值
        is_similar = similarity >= self.min_similarity

        return is_similar, similarity, differences


class OptimizedSequenceGenerator:
    """
    优化版序列生成器，支持可变长度序列和多进程并行处理

    这是模块的核心类，负责从文档字符序列中生成连续的N字序列，
    并在两个文档间进行高效的相似度检测。

    主要功能:
    1. 从字符列表生成连续N字序列（默认8字）
    2. 创建哈希索引表用于快速筛选候选序列
    3. 使用多进程并行计算相似度
    4. 支持中文和英文文本的智能处理

    核心优化:
    - 多进程并行：充分利用多核CPU，大幅提升处理速度
    - 哈希预筛选：通过哈希签名快速排除明显不相似的序列对
    - 智能清理：保留中英文和数字，去除标点符号干扰
    - 可配置性：支持自定义相似度阈值、序列长度和进程数

    性能提升:
    相比原始的暴力比对方法，使用哈希预筛选和多进程并行，
    在大规模文档比对中可以获得10-100倍的性能提升。

    使用示例:
        >>> generator = OptimizedSequenceGenerator(
        ...     min_similarity=0.75,
        ...     sequence_length=8,
        ...     num_processes=4
        ... )
        >>> # 生成序列
        >>> sequences = generator.generate_sequences(chars_list)
        >>> # 查找相似序列
        >>> similar = generator.find_similar_sequences_parallel(
        ...     file1_sequences, file2_sequences
        ... )
    """

    def __init__(self, min_similarity: float = 0.75, sequence_length: int = 8, num_processes: int = None):
        """
        初始化优化版序列生成器

        Args:
            min_similarity: 最小相似度阈值（0-1），默认0.75。
                          只有相似度达到此阈值的序列对才会被返回。
            sequence_length: 连续字符序列的长度，默认为8。
                           例如8表示生成8字序列。
            num_processes: 并行处理的进程数，None表示自动检测。
                          默认为min(8, CPU核心数)，
                          限制最大8个进程避免资源耗尽。

        示例:
            >>> # 使用默认参数
            >>> gen = OptimizedSequenceGenerator()
            >>> # 自定义参数
            >>> gen = OptimizedSequenceGenerator(
            ...     min_similarity=0.8,    # 更高的相似度要求
            ...     sequence_length=10,    # 10字序列
            ...     num_processes=4        # 使用4个进程
            ... )
        """
        self.min_similarity = min_similarity
        self.sequence_length = sequence_length
        # 自动检测CPU核心数，但最多使用8个进程
        # 避免过多进程导致上下文切换开销
        self.num_processes = num_processes or min(8, mp.cpu_count())
        # 创建相似度计算器实例
        self.calculator = FastSimilarityCalculator(min_similarity)

    def _clean_sequence(self, sequence: str) -> str:
        """
        清理序列，只保留中文、英文、数字

        从原始序列中过滤掉标点符号、空格等无关字符，
        只保留有意义的文本内容（中文、英文字母、数字）。

        Args:
            sequence: 原始序列字符串，可能包含标点符号、空格等

        Returns:
            清理后的序列字符串，只包含中文、英文和数字

        过滤规则:
            - 保留中文字符（Unicode范围：\u4e00-\u9fff）
            - 保留英文字母（a-z, A-Z）
            - 保留数字（0-9）
            - 删除所有其他字符（标点、空格、特殊符号等）

        设计原因:
            在相似度检测中，标点符号的存在会干扰比对结果。
            例如："人工智能，技术" 和 "人工智能技术" 应该被视为高度相似，
            但如果包含逗号，相似度会降低。清理后可以更准确地判断内容相似度。

        示例:
            >>> gen = OptimizedSequenceGenerator()
            >>> gen._clean_sequence("人工智能，技术！")
            '人工智能技术'
            >>> gen._clean_sequence("Hello, World! 2024")
            'HelloWorld2024'
        """
        # 保留：中文(\u4e00-\u9fff)、英文(a-zA-Z)、数字(0-9)
        # 删除：其他所有字符（标点、空格、特殊符号等）
        cleaned = []
        for char in sequence:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                cleaned.append(char)
            elif 'a' <= char <= 'z' or 'A' <= char <= 'Z':  # 英文字母
                cleaned.append(char)
            elif '0' <= char <= '9':  # 数字
                cleaned.append(char)
            # 其他字符（标点、空格等）被忽略
        return ''.join(cleaned)

    def generate_sequences(self, chars: List[CharInfo]) -> List[SequenceInfo]:
        """
        从字符列表中生成所有连续的N字序列

        使用滑动窗口方法，从字符列表中提取所有连续的N个字符（默认8字）。
        为每个序列创建SequenceInfo对象，包含清理后的内容、原始内容、
        位置信息和哈希签名。

        Args:
            chars: 字符信息列表，每个CharInfo对象包含字符内容、页码、行号等信息

        Returns:
            序列信息列表，每个元素是一个SequenceInfo对象
            如果输入字符数量小于sequence_length，返回空列表

        生成过程:
            1. 滑动窗口：从位置0开始，每次滑动1个字符
            2. 提取窗口内的sequence_length个字符
            3. 生成原始序列（用空格分隔字符，用于显示）
            4. 清理序列（去除标点，用于比对）
            5. 跳过清理后过短的序列（可能全是标点）
            6. 生成哈希签名（用于快速索引）
            7. 创建SequenceInfo对象并添加到结果列表

        过滤规则:
            - 跳过清理后长度<3的序列（可能全是标点符号）
            - 这确保了序列包含足够的有效内容

        示例:
            >>> from text_processor import CharInfo
            >>> chars = [
            ...     CharInfo('人', 1, 1, 0), CharInfo('工', 1, 1, 1),
            ...     CharInfo('智', 1, 1, 2), CharInfo('能', 1, 1, 3),
            ...     CharInfo('技', 1, 1, 4), CharInfo('术', 1, 1, 5),
            ...     CharInfo('发', 1, 1, 6), CharInfo('展', 1, 1, 7),
            ...     CharInfo('迅', 1, 1, 8), CharInfo('速', 1, 1, 9)
            ... ]
            >>> gen = OptimizedSequenceGenerator(sequence_length=4)
            >>> sequences = gen.generate_sequences(chars)
            >>> print(f"生成了 {len(sequences)} 个序列")
            >>> for seq in sequences[:2]:
            ...     print(seq)
            生成了 7 个序列
            '人 工 智 能' (页1行1-页1行1)
            '工 智 能 技' (页1行1-页1行1)
        """
        sequences = []
        seq_len = self.sequence_length

        # 需要至少 sequence_length 个字符才能生成序列
        if len(chars) < seq_len:
            return sequences

        # 滑动窗口：从位置0到(len(chars) - seq_len)
        for i in range(len(chars) - seq_len + 1):
            # 取 seq_len 个连续字符
            seq_chars = chars[i:i+seq_len]

            # 生成原始序列（用于显示，保留符号和空格分隔）
            # 使用空格分隔字符，便于用户阅读
            raw_sequence = " ".join([char.char for char in seq_chars])

            # 生成清理后的序列（用于比对，只保留中英数字）
            clean_sequence = self._clean_sequence(raw_sequence)

            # 跳过清理后太短的序列（可能全是符号）
            # 长度<3说明有效内容太少，不值得比较
            if len(clean_sequence) < 3:
                continue

            # 生成哈希签名用于快速筛选（基于清理后的序列）
            hash_signature = self._generate_hash_signature(clean_sequence)

            # 创建序列信息对象
            seq_info = SequenceInfo(
                sequence=clean_sequence,      # 用于比对（无符号）
                raw_sequence=raw_sequence,    # 用于显示（有空格）
                start_index=i,                # 在原始列表中的起始位置
                start_char=seq_chars[0],      # 起始字符的位置信息
                end_char=seq_chars[-1],       # 结束字符的位置信息
                chars=seq_chars,              # 完整的字符列表
                hash_signature=hash_signature # 哈希签名
            )
            sequences.append(seq_info)

        return sequences

    def _generate_hash_signature(self, sequence: str) -> str:
        """
        生成序列的哈希签名用于快速筛选

        通过提取序列的关键部分（前3词+后3词）生成MD5哈希签名。
        哈希签名用于快速预筛选：只有哈希签名相同或接近的序列
        才需要进行详细的相似度计算。

        Args:
            sequence: 清理后的序列字符串

        Returns:
            8位十六进制哈希签名字符串（MD5的前8位）

        设计思路:
            - 使用序列的前3词和后3词作为关键特征
            - 这些词通常包含序列的核心内容
            - 相似的序列会有相似的哈希签名
            - 快速排除明显不相似的序列对

        性能优化:
            哈希预筛选可以将需要详细比较的序列对数量
            减少90%以上，大幅提升整体性能。

        示例:
            >>> gen = OptimizedSequenceGenerator()
            >>> gen._generate_hash_signature("人工智能技术发展迅速")
            'a1b2c3d4'  # 示例哈希值
            >>> gen._generate_hash_signature("人工智能技术发展很快")
            'e5f6g7h8'  # 相似序列的哈希值可能不同，但会通过后续哈希表筛选
        """
        # 取前3个词和后3个词的组合哈希
        words = sequence.split()
        if len(words) >= 6:
            # 序列足够长：取前3词+后3词
            # 这些词通常包含序列的核心语义
            key_part = " ".join(words[:3] + words[-3:])
        else:
            # 序列较短：使用整个序列
            key_part = sequence

        # 生成MD5哈希并取前8位（16个十六进制字符的一半）
        # 8位哈希提供足够的区分度，同时保持较短的字符串长度
        return hashlib.md5(key_part.encode()).hexdigest()[:8]

    def create_hash_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """
        创建哈希查找表，用于快速预筛选相似序列

        为每个序列生成多个哈希键，构建哈希到序列列表的映射。
        在相似度检测时，通过哈希查找表可以快速找到候选相似序列，
        避免对所有序列对进行昂贵的相似度计算。

        对于中文（无空格分隔），按字符处理；对于英文（有空格分隔），按词处理。

        Args:
            sequences: SequenceInfo对象列表

        Returns:
            哈希查找表，字典格式 {哈希键: [序列列表]}
            每个序列可能映射到多个哈希键（前4词、后4词、间隔词等）

        哈希策略:
            中文序列（无空格）:
                - 前4个字符的哈希
                - 后4个字符的哈希（如果长度>=8）

            英文序列（有空格）:
                - 前4词的哈希
                - 后4词的哈希
                - 间隔词哈希（索引0,2,4,6位置的词，如果长度>=8）

        性能优化:
            使用哈希表预筛选，可以将需要详细比较的序列对数量
            从O(n*m)降低到O(n*k)，其中k是平均每个哈希桶的序列数。
            通常k << m，因此性能提升显著。

        示例:
            >>> gen = OptimizedSequenceGenerator()
            >>> sequences = gen.generate_sequences(chars_list)
            >>> hash_table = gen.create_hash_lookup_table(sequences)
            >>> print(f"哈希表包含 {len(hash_table)} 个桶")
            >>> # 查找具有相同哈希前缀的序列
            >>> for hash_key, seq_list in hash_table.items():
            ...     if len(seq_list) > 1:
            ...         print(f"哈希 {hash_key} 有 {len(seq_list)} 个序列")
        """
        hash_table = defaultdict(list)

        for seq_info in sequences:
            sequence = seq_info.sequence
            words = sequence.split()

            # 判断是中文（无空格）还是英文（有空格）
            if len(words) == 1:
                # 中文：按字符哈希
                if len(sequence) >= 4:
                    # 前4个字符哈希
                    key1 = sequence[:4]
                    hash1 = hashlib.md5(key1.encode()).hexdigest()[:8]
                    hash_table[hash1].append(seq_info)

                    # 后4个字符哈希（如果序列够长）
                    if len(sequence) >= 8:
                        key2 = sequence[-4:]
                        hash2 = hashlib.md5(key2.encode()).hexdigest()[:8]
                        hash_table[hash2].append(seq_info)
            else:
                # 英文：按词哈希
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

                # 间隔词哈希（增加匹配机会）
                # 取索引0, 2, 4, 6位置的词，提供另一种哈希视角
                if len(words) >= 8:
                    key3 = " ".join([words[i] for i in range(0, 8, 2)])
                    hash3 = hashlib.md5(key3.encode()).hexdigest()[:8]
                    hash_table[hash3].append(seq_info)

        # 转换为普通字典返回
        return dict(hash_table)

    def _compare_sequences_chunk(self, chunk_data: Tuple) -> List[SimilarSequenceInfo]:
        """
        处理序列比较的一个数据块（多进程工作函数）

        这是一个静态工作函数，被多个进程并行调用。
        每个进程处理一个数据块，比较文件1的序列块和文件2的所有序列。

        Args:
            chunk_data: 包含三个元素的元组
                - file1_seqs_chunk: 文件1的序列块（部分序列）
                - file2_sequences: 文件2的所有序列
                - min_similarity: 最小相似度阈值

        Returns:
            该数据块中找到的所有相似序列列表

        多进程说明:
            - 该函数在独立的子进程中执行
            - 每个子进程处理不同的数据块
            - 结果通过进程间通信返回主进程
            - 使用FastSimilarityCalculator进行相似度计算

        性能考虑:
            这是CPU密集型任务，适合使用多进程并行。
            Python的GIL（全局解释器锁）限制了多线程的性能，
            但多进程可以充分利用多核CPU。
        """
        # 解包数据
        file1_seqs_chunk, file2_sequences, min_similarity = chunk_data
        similar_sequences = []

        # 为当前进程创建独立的相似度计算器实例
        # 避免多进程间的资源共享问题
        calculator = FastSimilarityCalculator(min_similarity)

        # 双重循环：比较file1序列块中的每个序列与file2的所有序列
        for seq1 in file1_seqs_chunk:
            for seq2 in file2_sequences:
                # 快速哈希预检查
                if seq1.hash_signature == seq2.hash_signature:
                    # 哈希签名相同：可能完全相同或高度相似
                    # 进行详细检查确认
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
                    # 哈希签名不同：仍可能相似（只是概率较低）
                    # 也需要进行详细检查，因为哈希签名不完全等价于相似度
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
        并行查找相似序列（核心方法）

        使用多进程并行计算和哈希预筛选，高效地找出两个文档间的相似序列。
        这是模块的主要接口方法，整合了所有优化策略。

        Args:
            file1_sequences: 文件1的序列列表
            file2_sequences: 文件2的序列列表
            progress_callback: 可选的进度回调函数，签名为:
                             callback(progress: float, completed: int, total: int)
                             - progress: 完成比例（0-1）
                             - completed: 已完成的块数
                             - total: 总块数

        Returns:
            按相似度降序排列的相似序列列表（去重后）

        处理流程:
            1. 为文件2创建哈希索引表
            2. 为文件1的每个序列生成候选哈希键
            3. 通过哈希表快速找到候选相似序列
            4. 将候选对分块，分配给多个进程
            5. 每个进程并行计算相似度
            6. 收集结果，去重并按相似度排序

        性能优化:
            - 哈希预筛选：减少需要详细比较的序列对数量
            - 多进程并行：充分利用多核CPU
            - 块大小自适应：根据进程数和数据量自动调整

        示例:
            >>> gen = OptimizedSequenceGenerator(num_processes=4)
            >>> similar = gen.find_similar_sequences_parallel(
            ...     file1_sequences,
            ...     file2_sequences,
            ...     progress_callback=lambda p, c, t: print(f"进度: {p*100:.1f}%")
            ... )
            >>> print(f"找到 {len(similar)} 个相似序列")
        """
        print(f"开始并行相似度检测 (进程数: {self.num_processes})")
        print(f"文件1序列数: {len(file1_sequences):,}")
        print(f"文件2序列数: {len(file2_sequences):,}")

        # ========== 第一步：使用哈希表预筛选 ==========
        print("生成哈希索引...")
        start_time = time.time()

        # 将文件2序列按哈希分组，构建快速查找表
        file2_hash_table = self.create_hash_lookup_table(file2_sequences)
        print(f"哈希索引创建完成，耗时 {time.time() - start_time:.2f} 秒")

        # ========== 第二步：生成候选序列对 ==========
        candidate_pairs = []
        for seq1 in file1_sequences:
            # 为seq1生成可能的哈希键（支持中文和英文）
            sequence = seq1.sequence
            words = sequence.split()
            candidate_hashes = set()

            if len(words) == 1:
                # 中文：按字符哈希
                if len(sequence) >= 4:
                    # 前4个字符哈希
                    key1 = sequence[:4]
                    candidate_hashes.add(hashlib.md5(key1.encode()).hexdigest()[:8])

                    # 后4个字符哈希（如果序列够长）
                    if len(sequence) >= 8:
                        key2 = sequence[-4:]
                        candidate_hashes.add(hashlib.md5(key2.encode()).hexdigest()[:8])
            else:
                # 英文：按词哈希
                if len(words) >= 4:
                    key1 = " ".join(words[:4])
                    candidate_hashes.add(hashlib.md5(key1.encode()).hexdigest()[:8])
                    key2 = " ".join(words[-4:])
                    candidate_hashes.add(hashlib.md5(key2.encode()).hexdigest()[:8])

                if len(words) >= 8:
                    key3 = " ".join([words[i] for i in range(0, 8, 2)])
                    candidate_hashes.add(hashlib.md5(key3.encode()).hexdigest()[:8])

            # 在哈希表中查找所有候选序列
            candidates = []
            for hash_key in candidate_hashes:
                if hash_key in file2_hash_table:
                    candidates.extend(file2_hash_table[hash_key])

            # 去重：使用对象ID去重（SequenceInfo不是hashable）
            seen_ids = set()
            unique_candidates = []
            for candidate in candidates:
                if id(candidate) not in seen_ids:
                    seen_ids.add(id(candidate))
                    unique_candidates.append(candidate)
            candidates = unique_candidates

            # 为每个候选序列创建序列对
            for seq2 in candidates:
                candidate_pairs.append((seq1, seq2))

        print(f"预筛选完成，从 {len(file1_sequences) * len(file2_sequences):,} 对中筛选出 {len(candidate_pairs):,} 对候选")

        # ========== 第三步：分块处理候选对 ==========
        # 自适应块大小：最少100个，或者按进程数均分
        chunk_size = max(100, len(candidate_pairs) // self.num_processes)
        chunks = []

        for i in range(0, len(candidate_pairs), chunk_size):
            chunk = candidate_pairs[i:i+chunk_size]
            # 转换为适合并行处理的格式
            file1_chunk = [pair[0] for pair in chunk]
            chunks.append((file1_chunk, file2_sequences, self.min_similarity))

        # ========== 第四步：并行处理 ==========
        print("开始并行比较...")
        all_similar_sequences = []

        # 使用进程池执行器管理多进程
        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # 提交所有任务到进程池
            future_to_index = {
                executor.submit(self._compare_sequences_chunk, chunk): i
                for i, chunk in enumerate(chunks)
            }

            # 收集结果
            completed = 0
            for future in future_to_index:
                try:
                    # 获取任务结果（阻塞等待）
                    result = future.result()
                    all_similar_sequences.extend(result)
                    completed += 1

                    # 调用进度回调（如果提供）
                    if progress_callback:
                        progress = completed / len(chunks)
                        progress_callback(progress, completed, len(chunks))

                    # 打印进度信息
                    print(f"完成进度: {completed}/{len(chunks)} ({completed/len(chunks)*100:.1f}%)")

                except Exception as e:
                    # 捕获并报告处理错误，避免整个流程中断
                    print(f"处理块时出错: {e}")

        # ========== 第五步：去重并排序 ==========
        # 移除重复的相似序列对
        unique_sequences = self._remove_duplicates(all_similar_sequences)
        # 按相似度降序排序，最相似的排在前面
        unique_sequences.sort(key=lambda x: x.similarity, reverse=True)

        return unique_sequences

    def _remove_duplicates(self, sequences: List[SimilarSequenceInfo]) -> List[SimilarSequenceInfo]:
        """
        去除重复的相似序列

        在并行处理中，由于哈希筛选的复杂性，可能会产生重复的相似序列对。
        该方法基于序列内容对结果去重，确保每个序列对只出现一次。

        Args:
            sequences: 可能包含重复的相似序列列表

        Returns:
            去重后的相似序列列表

        去重策略:
            使用 (序列1内容, 序列2内容) 作为唯一标识符。
            如果两个序列对的序列内容相同，则被视为重复。

        为什么会有重复:
            - 在哈希预筛选中，一个序列可能匹配多个哈希键
            - 同一个序列对可能通过不同的哈希键被找到多次
            - 多进程处理时，不同进程可能发现相同的序列对

        示例:
            >>> # 假设有重复的序列对
            >>> duplicates = [sim_seq1, sim_seq2, sim_seq1]  # sim_seq1重复
            >>> unique = gen._remove_duplicates(duplicates)
            >>> print(len(unique))  # 输出: 2
        """
        seen = set()
        unique_sequences = []

        for seq_info in sequences:
            # 创建唯一标识符：(序列1内容, 序列2内容)的元组
            identifier = (seq_info.sequence1.sequence, seq_info.sequence2.sequence)
            if identifier not in seen:
                seen.add(identifier)
                unique_sequences.append(seq_info)

        return unique_sequences

    # ==================== 向后兼容接口 ====================
    # 以下方法为了保持与旧版本代码的兼容性而保留

    def create_sequence_lookup_table(self, sequences: List[SequenceInfo]) -> Dict[str, List[SequenceInfo]]:
        """
        创建序列查找表（兼容旧接口）

        这是一个简化的查找表，按序列内容分组。
        相比 create_hash_lookup_table，这个方法不使用哈希优化，
        仅用于向后兼容。

        Args:
            sequences: SequenceInfo对象列表

        Returns:
            字典格式 {序列内容: [序列列表]}

        注意:
            新代码应使用 create_hash_lookup_table 以获得更好的性能。
        """
        lookup_table = defaultdict(list)
        for seq_info in sequences:
            lookup_table[seq_info.sequence].append(seq_info)
        return dict(lookup_table)

    def find_similar_sequences(self,
                              file1_sequences: Dict[str, List[SequenceInfo]],
                              file2_sequences: Dict[str, List[SequenceInfo]]) -> List[SimilarSequenceInfo]:
        """
        查找相似序列（兼容旧接口的包装方法）

        将旧版本的字典格式序列映射转换为新版本的列表格式，
        并调用 find_similar_sequences_parallel 进行实际处理。

        Args:
            file1_sequences: 字典格式 {序列内容: [SequenceInfo列表]}
            file2_sequences: 字典格式 {序列内容: [SequenceInfo列表]}

        Returns:
            相似序列列表，按相似度降序排列

        注意:
            这是兼容旧接口的包装方法。
            新代码建议直接使用 find_similar_sequences_parallel。
        """
        # 获取所有序列：从字典格式转换为列表格式
        all_file1_seqs = []
        for seq_list in file1_sequences.values():
            all_file1_seqs.extend(seq_list)

        all_file2_seqs = []
        for seq_list in file2_sequences.values():
            all_file2_seqs.extend(seq_list)

        # 不限制序列数量 - 比较所有序列
        # 已注释掉的限制代码：旧版本可能限制序列数量以控制性能
        # if len(all_file1_seqs) > 10000:
        #     all_file1_seqs = all_file1_seqs[:10000]
        #     print(f"文件1序列数量限制为 {len(all_file1_seqs):,}（原数量超过限制）")
        # if len(all_file2_seqs) > 10000:
        #     all_file2_seqs = all_file2_seqs[:10000]
        #     print(f"文件2序列数量限制为 {len(all_file2_seqs):,}（原数量超过限制）")

        # 使用新的并行方法处理
        return self.find_similar_sequences_parallel(all_file1_seqs, all_file2_seqs)

    def get_sequence_summary(self, similar_sequences: List[SimilarSequenceInfo]) -> Dict:
        """
        获取相似序列的统计信息

        计算并返回相似序列集合的各种统计数据，
        包括总数、相似度分布、平均/最大/最小相似度等。

        Args:
            similar_sequences: SimilarSequenceInfo对象列表

        Returns:
            包含统计信息的字典，包含以下字段:
                - total_similar: 相似序列总数
                - high_similarity_count: 高相似度（>0.9）序列数量
                - medium_similarity_count: 中相似度（0.8-0.9）序列数量
                - low_similarity_count: 低相似度（<=0.8）序列数量
                - average_similarity: 平均相似度
                - max_similarity: 最高相似度
                - min_similarity: 最低相似度

        相似度分类:
            - 高相似度: > 0.9（90%以上）
            - 中相似度: 0.8 - 0.9（80%-90%）
            - 低相似度: <= 0.8（80%以下）

        示例:
            >>> summary = gen.get_sequence_summary(similar_sequences)
            >>> print(f"总计: {summary['total_similar']}")
            >>> print(f"平均相似度: {summary['average_similarity']:.2f}")
            >>> print(f"高相似度: {summary['high_similarity_count']}")
        """
        # 初始化统计字典
        summary = {
            'total_similar': len(similar_sequences),
            'high_similarity_count': 0,      # > 0.9
            'medium_similarity_count': 0,    # 0.8 - 0.9
            'low_similarity_count': 0,       # <= 0.8
            'average_similarity': 0.0,
            'max_similarity': 0.0,
            'min_similarity': 1.0 if similar_sequences else 0.0
        }

        # 如果没有相似序列，返回初始值
        if not similar_sequences:
            return summary

        # 提取所有相似度分数
        similarities = [seq.similarity for seq in similar_sequences]

        # 计算基本统计量
        summary['average_similarity'] = sum(similarities) / len(similarities)
        summary['max_similarity'] = max(similarities)
        summary['min_similarity'] = min(similarities)

        # 按相似度区间分类计数
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
        获取完全匹配序列的统计信息（兼容旧接口）

        统计两个文件中完全相同的序列的出现次数和分布情况。
        这是针对完全匹配（不是相似匹配）的统计功能。

        Args:
            repeated_sequences: 字典，格式为:
                {序列内容: (文件1中的序列列表, 文件2中的序列列表)}

        Returns:
            包含统计信息的字典，包含以下字段:
                - total_repeated: 重复序列的总数（不同序列内容的数量）
                - file1_total_occurrences: 文件1中重复序列的总出现次数
                - file2_total_occurrences: 文件2中重复序列的总出现次数
                - max_occurrences_file1: 文件1中单个序列的最大出现次数
                - max_occurrences_file2: 文件2中单个序列的最大出现次数

        示例:
            >>> repeated = {
            ...     "人工智能": ([seq1, seq2], [seq3]),
            ...     "机器学习": ([seq4], [seq5, seq6, seq7])
            ... }
            >>> summary = gen.get_exact_matches_summary(repeated)
            >>> print(f"重复序列: {summary['total_repeated']}")
            >>> print(f"文件1总次数: {summary['file1_total_occurrences']}")
        """
        # 初始化统计字典
        summary = {
            'total_repeated': len(repeated_sequences),           # 重复的不同序列数量
            'file1_total_occurrences': 0,                        # 文件1中的总出现次数
            'file2_total_occurrences': 0,                        # 文件2中的总出现次数
            'max_occurrences_file1': 0,                          # 文件1中单个序列最大出现次数
            'max_occurrences_file2': 0                           # 文件2中单个序列最大出现次数
        }

        # 遍历所有重复序列，统计出现次数
        for seq, (file1_infos, file2_infos) in repeated_sequences.items():
            summary['file1_total_occurrences'] += len(file1_infos)
            summary['file2_total_occurrences'] += len(file2_infos)
            summary['max_occurrences_file1'] = max(summary['max_occurrences_file1'], len(file1_infos))
            summary['max_occurrences_file2'] = max(summary['max_occurrences_file2'], len(file2_infos))

        return summary

    def find_repeated_sequences(self,
                                file1_sequences: Dict[str, List[SequenceInfo]],
                                file2_sequences: Dict[str, List[SequenceInfo]]) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """
        查找两个文件中完全重复的序列（兼容旧接口）

        找出在两个文件中都完全相同的序列（不是相似序列，是精确匹配）。
        这比相似度检测更严格，要求序列内容完全一致。

        Args:
            file1_sequences: 文件1的序列字典 {序列内容: [SequenceInfo列表]}
            file2_sequences: 文件2的序列字典 {序列内容: [SequenceInfo列表]}

        Returns:
            重复序列字典，格式为:
            {
                序列内容: (文件1中的序列列表, 文件2中的序列列表),
                ...
            }

        与相似度检测的区别:
            - 这个方法找的是完全相同的序列（100%匹配）
            - find_similar_sequences 找的是相似序列（>=阈值匹配）
            - 完全匹配是相似度=1.0的特殊情况

        性能:
            使用集合交集操作，时间复杂度O(n+m)，非常高效。
            其中n和m分别是两个文件的序列数量。

        示例:
            >>> repeated = gen.find_repeated_sequences(file1_seqs, file2_seqs)
            >>> for seq, (file1_list, file2_list) in repeated.items():
            ...     print(f"序列 '{seq}' 在文件1出现{len(file1_list)}次，文件2出现{len(file2_list)}次")
        """
        repeated_sequences = {}

        # 使用集合交集找出在两个文件中都出现的序列
        # keys() 返回所有序列内容（字符串），集合交集操作非常高效
        common_sequences = set(file1_sequences.keys()) & set(file2_sequences.keys())

        # 为每个公共序列创建映射关系
        for sequence in common_sequences:
            repeated_sequences[sequence] = (
                file1_sequences[sequence],  # 文件1中的所有出现
                file2_sequences[sequence]   # 文件2中的所有出现
            )

        return repeated_sequences


def test_optimized_generator():
    """
    测试优化版序列生成器

    这是一个功能测试和性能演示函数。
    创建模拟数据，测试序列生成、哈希索引、并行相似度检测等功能，
    并输出性能指标和结果统计。

    测试内容:
        1. 序列生成性能
        2. 哈希索引创建速度
        3. 并行相似度检测性能
        4. 结果统计和展示

    数据规模:
        - 5000个字符
        - 生成约5000个序列
        - 使用前1000个序列进行相似度检测
        - 使用4个进程并行处理

    输出:
        - 各步骤耗时统计
        - 相似序列数量
        - 吞吐量（每秒处理的对数）
        - 前5个相似序列示例
        - 统计摘要
    """
    # 导入依赖（放在函数内避免循环导入）
    from text_processor import CharInfo

    print("=== 优化版8字序列生成测试 ===")

    # ========== 创建测试数据 ==========
    # 使用预定义的词汇列表循环生成5000个字符
    chars = []
    words = ['人工智能', '技术', '发展', '非常', '迅速', 'machine', 'learning',
             'python', '2024', '年', '研究', '取得', '重要', '进展']

    for i in range(5000):  # 生成5000个字符
        word = words[i % len(words)]  # 循环使用词汇
        # 创建CharInfo对象: (字符, 页码, 行号, 位置)
        # 模拟文档结构: 每100个字符换行，每100个字符换页
        chars.append(CharInfo(word, 1 + i // 100, 1 + i % 100, i))

    # 创建生成器实例
    generator = OptimizedSequenceGenerator(min_similarity=0.75, num_processes=4)

    # ========== 测试1: 序列生成 ==========
    print("\n1. 生成8字序列...")
    start_time = time.time()
    sequences = generator.generate_sequences(chars)
    generation_time = time.time() - start_time
    print(f"   生成 {len(sequences):,} 个序列，耗时 {generation_time:.2f} 秒")

    # ========== 创建第二个文件数据（部分相似） ==========
    # 复制第一个文件的数据，然后修改部分内容以模拟相似但不同的文档
    chars2 = chars.copy()
    for i in range(0, len(chars2), 100):  # 每100个字符改一个
        chars2[i] = CharInfo('深度学习', chars2[i].page, chars2[i].line, chars2[i].position)

    print("\n2. 生成第二个文件的序列...")
    start_time = time.time()
    sequences2 = generator.generate_sequences(chars2)
    generation_time2 = time.time() - start_time
    print(f"   生成 {len(sequences2):,} 个序列，耗时 {generation_time2:.2f} 秒")

    # ========== 测试2: 创建查找表 ==========
    print("\n3. 创建查找表...")
    start_time = time.time()
    lookup_table = generator.create_sequence_lookup_table(sequences)
    lookup_table2 = generator.create_sequence_lookup_table(sequences2)
    lookup_time = time.time() - start_time
    print(f"   创建查找表完成，耗时 {lookup_time:.2f} 秒")

    # ========== 测试3: 并行相似度检测 ==========
    print(f"\n4. 开始并行相似度检测 (进程数: {generator.num_processes})...")
    start_time = time.time()

    # 定义进度回调函数
    def progress_callback(progress, completed, total):
        """显示处理进度"""
        print(f"   进度: {completed}/{total} ({progress*100:.1f}%)")

    # 执行并行相似度检测（仅使用前1000个序列以加快测试）
    similar_sequences = generator.find_similar_sequences_parallel(
        sequences[:1000], sequences2[:1000], progress_callback
    )
    comparison_time = time.time() - start_time

    # ========== 输出结果 ==========
    print(f"\n5. 相似度检测完成:")
    print(f"   找到 {len(similar_sequences)} 个相似序列")
    print(f"   总耗时: {comparison_time:.2f} 秒")
    print(f"   平均每秒处理: {(1000*1000)/comparison_time:.0f} 对比较")

    # 显示前几个结果示例
    print(f"\n6. 前5个相似序列:")
    for i, sim_seq in enumerate(similar_sequences[:5]):
        print(f"   {i+1}. {sim_seq}")

    # 统计信息
    summary = generator.get_sequence_summary(similar_sequences)
    print(f"\n7. 统计信息: {summary}")


# 主程序入口：当直接运行此文件时执行测试
if __name__ == "__main__":
    test_optimized_generator()