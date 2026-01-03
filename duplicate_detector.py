#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相似序列检测器模块
===================

本模块是PDF相似度检测系统的核心模块，整合了所有功能组件，
负责检测两个PDF文件中的相似8字序列并输出结果。

主要功能：
1. PDF文本提取与预处理
2. 8字序列生成与索引
3. 相似度计算与检测
4. 结果格式化与输出

核心类：
- SimilarSequenceDetector: 相似序列检测器，支持相似度检测
- DuplicateDetector: 重复检测器，兼容旧接口，支持完全匹配检测

作者：PDF检测系统开发团队
版本：2.0
"""

# ============================================================================
# 标准库导入
# ============================================================================

import time  # 时间模块，用于性能计时和生成时间戳

# ============================================================================
# 类型提示导入
# ============================================================================

from typing import List, Dict, Tuple, Optional
# List: 列表类型，用于存储序列集合
# Dict: 字典类型，用于构建序列查找表
# Tuple: 元组类型，用于返回多个值
# Optional: 可选类型，用于可空参数

# ============================================================================
# 自定义模块导入
# ============================================================================

from pdf_extractor import PDFTextExtractor
# PDF文本提取器：负责从PDF文件中提取文本及其位置信息

from text_processor import TextProcessor, CharInfo
# TextProcessor: 文本处理器，负责文本的分字、清洗等预处理
# CharInfo: 字符信息类，包含字符内容及其在PDF中的位置（页码、行号）

from sequence_generator import (SequenceGenerator, SequenceInfo,
                              SimilarSequenceInfo, SimilarityCalculator)
# SequenceGenerator: 序列生成器，负责生成8字序列和查找表
# SequenceInfo: 序列信息类，包含序列内容及其起止字符位置
# SimilarSequenceInfo: 相似序列信息类，包含两个序列及其相似度、差异分析
# SimilarityCalculator: 相似度计算器，负责计算序列间的相似度


class SimilarSequenceDetector:
    """
    相似序列检测器类
    =================

    这是系统的主要检测器类，负责完整的PDF相似度检测流程。

    工作流程：
    1. 初始化：设置PDF路径和相似度阈值，创建各个处理组件
    2. PDF处理：提取文本、分字、生成序列、构建查找表
    3. 相似检测：查找两个PDF中相似的8字序列
    4. 结果输出：格式化输出检测报告，支持保存到文件

    主要特性：
    - 支持可调节的相似度阈值（默认0.75）
    - 提供详细的统计信息（总数、平均相似度、高中低相似度分布等）
    - 显示每个相似序列的精确位置（页码、行号）
    - 分析并展示序列间的差异字符

    属性说明：
        pdf1_path (str): 第一个PDF文件的完整路径
        pdf2_path (str): 第二个PDF文件的完整路径
        min_similarity (float): 最小相似度阈值，范围0-1，默认0.75
        extractor1 (PDFTextExtractor): 第一个PDF的文本提取器
        extractor2 (PDFTextExtractor): 第二个PDF的文本提取器
        processor (TextProcessor): 文本处理器，用于分字和清洗
        generator (SequenceGenerator): 序列生成器，用于生成8字序列
        calculator (SimilarityCalculator): 相似度计算器

    使用示例：
        >>> detector = SimilarSequenceDetector(
        ...     "document1.pdf",
        ...     "document2.pdf",
        ...     min_similarity=0.8
        ... )
        >>> similar_sequences = detector.run_detection(save_to_file=True)
        >>> print(f"找到 {len(similar_sequences)} 个相似序列")
    """

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75):
        """
        初始化相似序列检测器

        创建检测器实例，设置PDF文件路径和相似度阈值，
        并初始化所有必要的处理组件（提取器、处理器、生成器等）。

        Args:
            pdf1_path (str): 第一个PDF文件的完整路径
            pdf2_path (str): 第二个PDF文件的完整路径
            min_similarity (float): 最小相似度阈值，范围0-1之间
                                 - 1.0 表示完全相同
                                 - 0.75 表示至少75%的字符相同（默认值）
                                 - 可根据检测严格程度调整

        Raises:
            FileNotFoundError: 当PDF文件不存在时（在PDFTextExtractor中抛出）
            ValueError: 当相似度阈值不在0-1范围内时

        Note:
            相似度阈值的选择建议：
            - 0.75-0.80: 宽松检测，会找到更多相似片段，可能有误报
            - 0.80-0.90: 中等检测，平衡准确率和召回率
            - 0.90-1.00: 严格检测，只找出高度相似的片段
        """
        # 保存PDF文件路径
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path

        # 保存相似度阈值
        self.min_similarity = min_similarity

        # 创建PDF文本提取器：负责从PDF中提取文本和位置信息
        self.extractor1 = PDFTextExtractor(pdf1_path)
        self.extractor2 = PDFTextExtractor(pdf2_path)

        # 创建文本处理器：负责文本的分字、清洗等预处理
        self.processor = TextProcessor()

        # 创建序列生成器：负责生成8字序列和相似序列检测
        # 将相似度阈值传递给生成器，用于后续的相似度判断
        self.generator = SequenceGenerator(min_similarity)

        # 创建相似度计算器：专门用于计算两个序列的相似度
        self.calculator = SimilarityCalculator(min_similarity)

    def process_pdf(self, extractor: PDFTextExtractor, pdf_name: str) -> Tuple[List[CharInfo], Dict[str, List[SequenceInfo]]]:
        """
        处理单个PDF文件

        该方法是PDF处理的核心流程，完成从PDF到序列查找表的全部转换工作。

        处理步骤：
        1. 文本提取：从PDF中提取文本及其位置信息
        2. 文本预处理：将文本分割成单个字符，记录每个字符的位置
        3. 序列生成：从字符列表中生成所有连续的8字序列
        4. 查找表构建：创建序列到其出现位置的映射表

        Args:
            extractor (PDFTextExtractor): PDF文本提取器实例
                                         该提取器已经关联了特定的PDF文件
            pdf_name (str): PDF文件的显示名称，用于日志输出
                           例如："文件1"、"文件2"或实际文件名

        Returns:
            Tuple[List[CharInfo], Dict[str, List[SequenceInfo]]]:
                返回一个元组，包含：
                - List[CharInfo]: 字符信息列表
                  包含PDF中的所有字符，每个字符记录了其内容和位置
                - Dict[str, List[SequenceInfo]]: 序列查找表
                  键：8字序列的字符串内容
                  值：该序列在PDF中所有出现位置的信息列表

        Example:
            >>> extractor = PDFTextExtractor("document.pdf")
            >>> chars, lookup_table = detector.process_pdf(extractor, "测试文档")
            >>> print(f"提取了 {len(chars)} 个字符")
            >>> print(f"生成了 {len(lookup_table)} 个唯一序列")

        Note:
            - 查找表的结构允许快速查找某个序列是否存在于PDF中
            - 每个序列可能出现多次，因此值是列表类型
            - 性能提示：对于大型PDF，此步骤可能耗时较长
        """
        # 输出处理开始标记
        print(f"\n=== 处理 {pdf_name} ===")

        # ====================================================================
        # 步骤1: 提取PDF文本
        # ====================================================================
        print("1. 提取PDF文本...")
        start_time = time.time()  # 记录开始时间，用于性能统计

        # 调用提取器提取文本，返回包含文本和位置信息的列表
        extracted_text = extractor.extract_text_with_positions()

        # 输出提取结果统计和耗时
        print(f"   提取了 {len(extracted_text)} 行文本，耗时 {time.time() - start_time:.2f} 秒")

        # ====================================================================
        # 步骤2: 文本预处理（分字）
        # ====================================================================
        print("2. 文本预处理（分字）...")
        start_time = time.time()  # 重置计时器

        # 将提取的文本行分割成单个字符，每个字符记录其位置（页码、行号）
        # 返回的是CharInfo对象列表，每个对象包含：char(字符)、page(页码)、line(行号)
        chars = self.processor.process_extracted_text(extracted_text)

        # 输出分字结果统计和耗时
        print(f"   生成了 {len(chars)} 个字符，耗时 {time.time() - start_time:.2f} 秒")

        # ====================================================================
        # 步骤3: 生成8字序列
        # ====================================================================
        print("3. 生成8字序列...")
        start_time = time.time()  # 重置计时器

        # 从字符列表中生成所有连续的8字序列
        # 例如："这是一个测试文档" 会生成 "这是一个测试"、"是一个测试文" 等序列
        sequences = self.generator.generate_sequences(chars)

        # 构建序列查找表：将序列内容作为键，其所有出现位置作为值
        # 这样可以快速查询某个序列是否存在以及出现的位置
        lookup_table = self.generator.create_sequence_lookup_table(sequences)

        # 输出序列生成结果统计和耗时
        print(f"   生成了 {len(sequences)} 个序列，{len(lookup_table)} 个唯一序列，"
              f"耗时 {time.time() - start_time:.2f} 秒")

        # 返回字符列表和查找表，供后续相似度检测使用
        return chars, lookup_table

    def detect_similar_sequences(self) -> List[SimilarSequenceInfo]:
        """
        检测相似序列

        这是检测流程的核心方法，负责找出两个PDF中所有相似的8字序列。

        工作原理：
        1. 分别处理两个PDF文件，生成各自的序列查找表
        2. 比较两个查找表，找出出现在两个PDF中的序列
        3. 对于每个共同序列，计算其相似度（考虑字符替换）
        4. 筛选出相似度达到阈值的序列

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息列表
                每个SimilarSequenceInfo对象包含：
                - sequence1: 文件1中的序列及其位置
                - sequence2: 文件2中的序列及其位置
                - similarity: 相似度分数（0-1之间）
                - differences: 差异分析，列出哪些位置的字符不同

        Example:
            >>> similar_sequences = detector.detect_similar_sequences()
            >>> for seq in similar_sequences:
            ...     print(f"相似度: {seq.similarity:.2f}")
            ...     print(f"文件1: {seq.sequence1.sequence}")
            ...     print(f"文件2: {seq.sequence2.sequence}")

        Note:
            - 相似度计算基于Levenshtein距离或字符替换检测
            - 返回的列表已按相似度从高到低排序
            - 性能取决于PDF大小和序列数量，可能需要几秒到几分钟
        """
        # 输出检测开始标记
        print("开始检测相似序列...")

        # ====================================================================
        # 处理两个PDF文件
        # ====================================================================
        # 处理第一个PDF：提取文本、生成序列、构建查找表
        # chars1 保存字符信息列表，lookup_table1 保存序列查找表
        chars1, lookup_table1 = self.process_pdf(self.extractor1, "文件1")

        # 处理第二个PDF：同样的流程
        chars2, lookup_table2 = self.process_pdf(self.extractor2, "文件2")

        # ====================================================================
        # 检测相似序列
        # ====================================================================
        print("\n=== 检测相似序列 ===")
        print(f"相似度阈值: {self.min_similarity:.2f}")  # 显示当前使用的相似度阈值
        start_time = time.time()  # 记录开始时间

        # 调用序列生成器的相似序列检测方法
        # 该方法会比较两个查找表，找出所有相似的序列对
        # 并计算每对序列的相似度和差异
        similar_sequences = self.generator.find_similar_sequences(lookup_table1, lookup_table2)

        # 输出检测结果统计和耗时
        print(f"检测完成，找到 {len(similar_sequences)} 个相似序列，"
              f"耗时 {time.time() - start_time:.2f} 秒")

        # 返回相似序列列表
        return similar_sequences

    def format_output(self, similar_sequences: List[SimilarSequenceInfo],
                      show_all_positions: bool = True, max_results: Optional[int] = None) -> str:
        """
        格式化输出结果

        将检测结果格式化为易读的报告文本，包含统计信息、详细列表等。

        报告结构：
        1. 基本信息：检测时间、文件路径、相似度阈值
        2. 统计摘要：总数、平均相似度、相似度分布等
        3. 详细列表：每个相似序列的具体信息和位置
        4. 差异分析：标出哪些字符不同

        Args:
            similar_sequences (List[SimilarSequenceInfo]): 相似序列信息列表
            show_all_positions (bool): 是否显示所有出现位置
                                      - True: 显示每个序列的所有出现位置
                                      - False: 只显示首次出现位置
            max_results (Optional[int]): 最大显示结果数量
                                        - None: 显示所有结果
                                        - 整数: 只显示前N个结果，避免输出过长

        Returns:
            str: 格式化的报告文本，可直接打印或保存到文件

        Example:
            >>> report = detector.format_output(similar_sequences, max_results=10)
            >>> print(report)
            >>> # 保存到文件
            >>> with open("report.txt", "w") as f:
            ...     f.write(report)

        Note:
            - 报告使用中文格式化，便于阅读
            - 相似度保留3位小数，便于精确比较
            - 位置信息包含页码和行号，便于定位
        """
        # 初始化输出列表
        output = []

        # ====================================================================
        # 报告头部
        # ====================================================================
        output.append("=" * 80)  # 分隔线
        output.append("PDF文件相似序列检测报告")  # 报告标题
        output.append("=" * 80)
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")  # 当前时间
        output.append(f"文件1: {self.pdf1_path}")  # 第一个PDF路径
        output.append(f"文件2: {self.pdf2_path}")  # 第二个PDF路径
        output.append(f"相似度阈值: {self.min_similarity:.2f}")  # 使用的相似度阈值
        output.append(f"相似序列总数: {len(similar_sequences)}")  # 找到的相似序列数量
        output.append("")  # 空行

        # ====================================================================
        # 无相似序列的情况
        # ====================================================================
        if not similar_sequences:
            # 如果没有找到相似序列，输出提示信息
            output.append(f"未发现相似度≥{self.min_similarity:.2f}的8字序列。")
            return "\n".join(output)  # 直接返回，不继续处理

        # ====================================================================
        # 限制显示结果数量
        # ====================================================================
        # 如果指定了最大显示数量，只取前N个结果
        # 这对于结果数量很大时很有用，可以避免输出过长
        display_sequences = similar_sequences[:max_results] if max_results else similar_sequences

        # ====================================================================
        # 统计信息
        # ====================================================================
        # 调用序列生成器的统计方法，计算各项统计指标
        summary = self.generator.get_sequence_summary(similar_sequences)

        output.append("统计信息:")
        output.append(f"- 相似序列总数: {summary['total_similar']}")
        output.append(f"- 高相似度(>0.9): {summary['high_similarity_count']} 个")
        output.append(f"- 中相似度(0.8-0.9): {summary['medium_similarity_count']} 个")
        output.append(f"- 低相似度(0.75-0.8): {summary['low_similarity_count']} 个")
        output.append(f"- 平均相似度: {summary['average_similarity']:.3f}")
        output.append(f"- 最高相似度: {summary['max_similarity']:.3f}")
        output.append(f"- 最低相似度: {summary['min_similarity']:.3f}")
        output.append("")  # 空行

        # ====================================================================
        # 详细结果列表
        # ====================================================================
        output.append("相似序列详情 (按相似度排序):")
        output.append("-" * 80)  # 分隔线

        # 遍历每个相似序列，输出详细信息
        for i, sim_seq in enumerate(display_sequences, 1):  # enumerate从1开始编号
            # 输出序列编号和相似度（保留3位小数）
            output.append(f"{i}. 相似度: {sim_seq.similarity:.3f}")

            # 输出文件1中的序列内容
            output.append(f"   文件1: '{sim_seq.sequence1.sequence}'")

            # 输出文件1中序列的位置信息（起止页码和行号）
            output.append(f"          位置: 页{sim_seq.sequence1.start_char.page}行{sim_seq.sequence1.start_char.line} - "
                        f"页{sim_seq.sequence1.end_char.page}行{sim_seq.sequence1.end_char.line}")

            # 输出文件2中的序列内容
            output.append(f"   文件2: '{sim_seq.sequence2.sequence}'")

            # 输出文件2中序列的位置信息
            output.append(f"          位置: 页{sim_seq.sequence2.start_char.page}行{sim_seq.sequence2.start_char.line} - "
                        f"页{sim_seq.sequence2.end_char.page}行{sim_seq.sequence2.end_char.line}")

            # ====================================================================
            # 差异分析
            # ====================================================================
            # 如果有差异且不是"完全相同"，则输出差异信息
            if sim_seq.differences and sim_seq.differences != ["完全相同"]:
                # differences是一个列表，包含所有差异的描述
                output.append(f"   差异: {', '.join(sim_seq.differences)}")
            else:
                output.append(f"   差异: 无")

            output.append("")  # 空行，分隔不同的序列

        # ====================================================================
        # 结果截断提示
        # ====================================================================
        # 如果限制了显示数量且实际结果更多，提示还有更多结果
        if max_results and len(similar_sequences) > max_results:
            output.append(f"... 还有 {len(similar_sequences) - max_results} 个相似序列未显示")
            output.append("完整结果请查看保存的文件。")

        # 将列表合并为字符串并返回
        return "\n".join(output)

    def save_results(self, similar_sequences: List[SimilarSequenceInfo],
                     output_file: str = "similar_sequences_results.txt"):
        """
        保存结果到文件

        将检测报告保存到文本文件中，便于后续查阅和分享。

        Args:
            similar_sequences (List[SimilarSequenceInfo]): 相似序列信息列表
            output_file (str): 输出文件的名称
                              默认为 "similar_sequences_results.txt"
                              可以包含相对路径或绝对路径

        Raises:
            IOError: 当文件写入失败时（如权限不足、磁盘空间不足等）
            Exception: 其他可能的异常

        Example:
            >>> detector.save_results(similar_sequences, "my_report.txt")
            >>> # 保存到指定目录
            >>> detector.save_results(similar_sequences, "/path/to/report.txt")

        Note:
            - 文件使用UTF-8编码，支持中文字符
            - 如果文件已存在，将被覆盖
            - 成功保存后会输出确认消息到控制台
        """
        # 调用format_output方法生成报告内容
        # show_all_positions=True 表示显示所有位置信息
        output = self.format_output(similar_sequences, show_all_positions=True)

        try:
            # 以写入模式打开文件（如果文件存在则覆盖）
            # encoding='utf-8' 确保中文字符正确保存
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)  # 将报告内容写入文件

            # 输出成功消息
            print(f"\n结果已保存到: {output_file}")

        except Exception as e:
            # 捕获并处理文件写入异常
            # 可能的原因：权限不足、磁盘空间不足、路径不存在等
            print(f"保存结果时出错: {e}")

    def run_detection(self, save_to_file: bool = True,
                     show_max_results: int = 50) -> List[SimilarSequenceInfo]:
        """
        运行完整的检测流程

        这是最常用的方法，整合了从PDF处理到结果输出的全部步骤。
        用户只需调用这一个方法即可完成整个检测过程。

        工作流程：
        1. 显示开始信息
        2. 检测相似序列
        3. 格式化并显示结果（控制台输出）
        4. 保存结果到文件（可选）
        5. 显示总耗时

        Args:
            save_to_file (bool): 是否将结果保存到文件
                               - True: 保存到文件（默认）
                               - False: 只在控制台显示
            show_max_results (int): 在控制台显示的最大结果数量
                                  默认为50，避免控制台输出过多
                                  文件中会保存所有结果

        Returns:
            List[SimilarSequenceInfo]: 相似序列信息列表
                                       可用于进一步的程序化处理

        Example:
            >>> # 基本用法：检测并保存结果
            >>> results = detector.run_detection()
            >>>
            >>> # 只在控制台显示，不保存文件
            >>> results = detector.run_detection(save_to_file=False)
            >>>
            >>> # 控制台显示更多结果
            >>> results = detector.run_detection(show_max_results=100)
            >>>
            >>> # 处理返回的结果
            >>> for seq in results:
            ...     if seq.similarity > 0.9:
            ...         print(f"高度相似: {seq.sequence1.sequence}")

        Note:
            - 整个过程可能需要几秒到几分钟，取决于PDF文件大小
            - 控制台输出和文件内容格式相同
            - 返回的结果列表可用于后续的数据分析或处理
        """
        # ====================================================================
        # 显示开始信息
        # ====================================================================
        print("=" * 80)  # 分隔线
        print("开始PDF文件相似序列检测")  # 标题
        print("=" * 80)

        # 记录总开始时间，用于计算总耗时
        start_time = time.time()

        # ====================================================================
        # 执行检测
        # ====================================================================
        # 调用detect_similar_sequences方法进行实际检测
        similar_sequences = self.detect_similar_sequences()

        # ====================================================================
        # 显示结果
        # ====================================================================
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)

        # 调用format_output格式化结果，并打印到控制台
        # show_all_positions=False: 只显示首次出现位置，避免输出过长
        # max_results=show_max_results: 限制显示数量
        print(self.format_output(similar_sequences, show_all_positions=False,
                               max_results=show_max_results))

        # ====================================================================
        # 保存结果
        # ====================================================================
        if save_to_file:
            # 如果save_to_file为True，调用save_results保存到文件
            # 使用默认文件名："similar_sequences_results.txt"
            self.save_results(similar_sequences)

        # ====================================================================
        # 显示总耗时
        # ====================================================================
        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        # 返回相似序列列表，供调用者进一步处理
        return similar_sequences


class DuplicateDetector:
    """
    重复检测器类（兼容旧接口）
    ==========================

    这是一个兼容性包装类，用于保持与旧版本API的兼容性。

    主要用途：
    - 为使用旧版本的代码提供向后兼容
    - 提供完全匹配检测功能（相似度=1.0）
    - 逐步引导用户迁移到新的相似度检测接口

    与SimilarSequenceDetector的区别：
    - DuplicateDetector: 只检测完全相同的序列（旧功能）
    - SimilarSequenceDetector: 检测相似的序列（新功能，推荐）

    设计模式：
    - 使用组合模式，内部持有SimilarSequenceDetector实例
    - 大部分方法委托给内部的SimilarSequenceDetector处理

    迁移建议：
    如果你的代码使用DuplicateDetector，建议迁移到SimilarSequenceDetector：
    ```python
    # 旧代码
    detector = DuplicateDetector(pdf1, pdf2)
    results = detector.run_detection()

    # 新代码（推荐）
    detector = SimilarSequenceDetector(pdf1, pdf2, min_similarity=0.8)
    results = detector.run_detection()
    ```

    Attributes:
        similarity_detector (SimilarSequenceDetector): 内部的相似序列检测器实例
    """

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75):
        """
        初始化检测器（兼容旧接口）

        创建检测器实例，内部创建SimilarSequenceDetector来处理实际工作。

        Args:
            pdf1_path (str): 第一个PDF文件的完整路径
            pdf2_path (str): 第二个PDF文件的完整路径
            min_similarity (float): 最小相似度阈值（默认0.75）
                                 虽然是兼容接口，但仍支持设置相似度

        Note:
            这个构造函数主要为了向后兼容。
            新代码建议直接使用SimilarSequenceDetector类。
        """
        # 创建内部的SimilarSequenceDetector实例
        # 所有实际的检测工作都由这个实例完成
        self.similarity_detector = SimilarSequenceDetector(pdf1_path, pdf2_path, min_similarity)

    def process_pdf(self, extractor: PDFTextExtractor, pdf_name: str) -> Tuple[List[CharInfo], Dict[str, List[SequenceInfo]]]:
        """
        处理PDF文件（兼容旧接口）

        这是一个委托方法，直接调用内部SimilarSequenceDetector的process_pdf方法。

        Args:
            extractor: PDF提取器
            pdf_name: PDF名称

        Returns:
            Tuple[字符列表, 序列查找表]

        Note:
            此方法仅为兼容旧接口保留，新代码无需调用。
        """
        # 直接委托给内部的SimilarSequenceDetector处理
        return self.similarity_detector.process_pdf(extractor, pdf_name)

    def detect_duplicates(self) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """
        检测重复序列（兼容旧接口）

        这是旧版本的核心检测方法，只找出完全相同的序列（相似度=1.0）。

        与新接口的区别：
        - 旧接口：只检测完全相同的序列
        - 新接口：检测相似度达到阈值的序列（更灵活）

        Returns:
            Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
                重复序列字典
                - 键：序列内容
                - 值：元组(文件1中的位置列表, 文件2中的位置列表)

        Note:
            新功能建议使用detect_similar_sequences()方法。
        """
        # 处理两个PDF文件
        chars1, lookup_table1 = self.process_pdf(self.similarity_detector.extractor1, "文件1")
        chars2, lookup_table2 = self.process_pdf(self.similarity_detector.extractor2, "文件2")

        # 调用SequenceGenerator的find_repeated_sequences方法
        # 该方法只找出完全相同的序列（相似度=1.0）
        return self.similarity_detector.generator.find_repeated_sequences(lookup_table1, lookup_table2)

    def format_output(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]],
                      show_all_positions: bool = True) -> str:
        """
        格式化输出（兼容旧接口）

        为完全匹配的序列生成格式化的报告文本。

        Args:
            repeated_sequences: 重复序列字典
            show_all_positions: 是否显示所有位置

        Returns:
            str: 格式化的报告文本

        Note:
            此方法会提示用户有新的相似度检测功能可用。
        """
        # 初始化输出列表
        output = []

        # 报告头部
        output.append("=" * 80)
        output.append("PDF文件序列检测报告")
        output.append("=" * 80)
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"文件1: {self.similarity_detector.pdf1_path}")
        output.append(f"文件2: {self.similarity_detector.pdf2_path}")
        output.append(f"完全匹配序列数: {len(repeated_sequences)}")
        output.append("")

        # 如果没有找到完全匹配的序列
        if not repeated_sequences:
            output.append("未发现完全相同的8字序列。")
            output.append("\n提示: 现在系统支持相似度检测，使用 detect_similar_sequences() 方法")
            output.append(f"可以找到相似度≥{self.similarity_detector.min_similarity:.2f}的序列。")
            return "\n".join(output)

        # 获取统计信息
        summary = self.similarity_detector.generator.get_exact_matches_summary(repeated_sequences)

        # 输出统计摘要
        output.append("完全匹配统计:")
        output.append(f"- 完全匹配序列数: {summary['total_repeated']}")
        output.append(f"- 文件1中出现总次数: {summary['file1_total_occurrences']}")
        output.append(f"- 文件2中出现总次数: {summary['file2_total_occurrences']}")
        output.append("")

        # 输出详细序列列表
        output.append("完全匹配的序列:")
        output.append("-" * 80)

        # 遍历每个重复序列
        for i, (sequence, (file1_infos, file2_infos)) in enumerate(repeated_sequences.items(), 1):
            output.append(f"{i}. 序列: '{sequence}'")

            # 输出在文件1中的出现位置
            output.append(f"   在文件1中出现 {len(file1_infos)} 次:")

            if show_all_positions:
                # 显示所有位置
                for j, seq_info in enumerate(file1_infos, 1):
                    output.append(f"     {j}. 页{seq_info.start_char.page}行{seq_info.start_char.line} - "
                                f"页{seq_info.end_char.page}行{seq_info.end_char.line}")
            else:
                # 只显示首次出现位置
                output.append(f"     首次出现: 页{file1_infos[0].start_char.page}行{file1_infos[0].start_char.line}")

            # 输出在文件2中的出现位置
            output.append(f"   在文件2中出现 {len(file2_infos)} 次:")

            if show_all_positions:
                # 显示所有位置
                for j, seq_info in enumerate(file2_infos, 1):
                    output.append(f"     {j}. 页{seq_info.start_char.page}行{seq_info.start_char.line} - "
                                f"页{seq_info.end_char.page}行{seq_info.end_char.line}")
            else:
                # 只显示首次出现位置
                output.append(f"     首次出现: 页{file2_infos[0].start_char.page}行{file2_infos[0].start_char.line}")

            output.append("")  # 空行

        # 提示有新的相似度检测功能
        output.append("\n提示: 现在系统支持相似度检测！")
        output.append(f"可以找到相似度≥{self.similarity_detector.min_similarity:.2f}的序列。")

        return "\n".join(output)

    def save_results(self, repeated_sequences: Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]],
                     output_file: str = "duplicate_results.txt"):
        """
        保存结果（兼容旧接口）

        将完全匹配的检测结果保存到文件。

        Args:
            repeated_sequences: 重复序列字典
            output_file: 输出文件名（默认为"duplicate_results.txt"）
        """
        # 生成报告内容
        output = self.format_output(repeated_sequences)

        try:
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果时出错: {e}")

    def run_detection(self, save_to_file: bool = True) -> Dict[str, Tuple[List[SequenceInfo], List[SequenceInfo]]]:
        """
        运行检测（兼容旧接口）

        执行完整的完全匹配检测流程。

        Args:
            save_to_file: 是否保存结果到文件

        Returns:
            重复序列字典

        Note:
            这是旧接口的主要入口方法。
            新代码建议使用run_similarity_detection()或直接使用SimilarSequenceDetector。
        """
        # 显示开始信息
        print("=" * 80)
        print("开始PDF文件完全匹配序列检测")
        print("=" * 80)

        start_time = time.time()

        # 执行检测
        repeated_sequences = self.detect_duplicates()

        # 显示结果
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)
        print(self.format_output(repeated_sequences, show_all_positions=False))

        # 保存结果
        if save_to_file:
            self.save_results(repeated_sequences)

        # 显示总耗时
        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        return repeated_sequences

    def run_similarity_detection(self, save_to_file: bool = True) -> List[SimilarSequenceInfo]:
        """
        运行相似度检测（新接口）

        这是推荐的检测方法，使用SimilarSequenceDetector进行相似度检测。

        Args:
            save_to_file: 是否保存结果到文件

        Returns:
            List[SimilarSequenceInfo]: 相似序列信息列表

        Example:
            >>> detector = DuplicateDetector(pdf1, pdf2)
            >>> # 使用旧接口（只检测完全相同）
            >>> old_results = detector.run_detection()
            >>> # 使用新接口（检测相似序列）
            >>> new_results = detector.run_similarity_detection()

        Note:
            此方法是连接旧接口和新接口的桥梁，
            允许旧代码用户逐步迁移到新的相似度检测功能。
        """
        # 直接委托给内部的SimilarSequenceDetector处理
        return self.similarity_detector.run_detection(save_to_file=save_to_file)


# ============================================================================
# 测试函数
# ============================================================================

def test_duplicate_detector():
    """
    测试重复检测器

    这是一个简单的测试函数，用于验证模块是否正常加载。

    注意：
    - 实际的PDF检测需要真实的PDF文件
    - 此函数只输出提示信息，不执行实际检测

    要运行完整的测试，需要：
    1. 准备两个PDF文件
    2. 创建SimilarSequenceDetector实例
    3. 调用run_detection方法

    Example:
        >>> detector = SimilarSequenceDetector("test1.pdf", "test2.pdf")
        >>> results = detector.run_detection()
    """
    # 输出模块加载成功信息
    print("相似序列检测器模块已创建")
    print("要测试功能，请运行主程序并提供实际的PDF文件路径")
    print("\n新功能:")
    print("- 支持8字序列检测")
    print("- 支持相似度检测（默认≥0.75）")
    print("- 可调节相似度阈值")
    print("- 显示详细差异信息")


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    """
    当直接运行此模块时，执行测试函数

    使用方式：
    1. 直接运行：python duplicate_detector.py
       会调用test_duplicate_detector()

    2. 作为模块导入：from duplicate_detector import SimilarSequenceDetector
       不会执行测试函数
    """
    test_duplicate_detector()
