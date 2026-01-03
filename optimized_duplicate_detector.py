#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版相似序列检测器模块
使用多进程和智能算法大幅提升检测速度

本模块提供了一个高性能的PDF文档相似序列检测系统，主要用于：
1. 检测两个PDF文档之间的相似文本片段
2. 支持多种文档格式（PDF、Word等）
3. 使用多进程并行处理提升检测速度
4. 提供详细的上下文信息和统计报告

主要优化：
- 多进程并行处理相似度计算
- 智能哈希预筛选减少不必要的比较
- 可配置的序列数量限制以控制内存和速度
- 实时进度显示和性能监控

使用示例：
    detector = OptimizedSimilarSequenceDetector("doc1.pdf", "doc2.pdf")
    results = detector.run_detection_optimized()
"""

# ==================== 标准库导入 ====================
import time  # 用于时间测量和性能监控

# ==================== 类型注解导入 ====================
from typing import List, Dict, Tuple, Optional  # 类型提示，增强代码可读性和IDE支持

# ==================== 自定义模块导入 ====================
from pdf_extractor import PDFTextExtractor  # PDF文本提取器，用于从PDF文件中提取文本内容和位置信息
from text_processor import TextProcessor, CharInfo  # 文本处理器和字符信息类，用于文本预处理和字符管理
from optimized_sequence_generator import (  # 优化版序列生成器，提供高效的序列生成和相似度计算
    OptimizedSequenceGenerator,  # 优化版序列生成器主类
    SequenceInfo,  # 序列信息数据类，包含序列文本、位置、字符等信息
    SimilarSequenceInfo,  # 相似序列信息数据类，包含两个相似序列及其相似度
    FastSimilarityCalculator  # 快速相似度计算器，使用优化算法计算序列相似度
)


class OptimizedSimilarSequenceDetector:
    """
    优化版相似序列检测器主类

    该类负责协调整个相似序列检测流程，包括：
    1. 文档文本提取
    2. 文本预处理（分字、标准化）
    3. 序列生成
    4. 相似度计算
    5. 结果格式化和输出

    主要特性：
    - 支持多种文档格式（PDF、Word）
    - 多进程并行处理，大幅提升检测速度
    - 智能序列采样，平衡速度和准确性
    - 详细的进度显示和性能统计
    - 灵活的配置选项

    典型使用流程：
        detector = OptimizedSimilarSequenceDetector("file1.pdf", "file2.pdf", min_similarity=0.8)
        similar_sequences = detector.run_detection_optimized(save_to_file=True)

    属性说明：
        pdf1_path: 第一个文档的文件路径
        pdf2_path: 第二个文档的文件路径
        min_similarity: 相似度判断阈值（0-1之间的浮点数）
        max_sequences: 每个文档处理的最大序列数量限制
        sequence_length: 用于比较的序列长度（字数）
        chars1/chars2: 保存两个文档的完整字符列表，用于上下文显示
    """

    def __init__(self, pdf1_path: str, pdf2_path: str, min_similarity: float = 0.75,
                 num_processes: int = None, max_sequences: int = 10000, sequence_length: int = 8):
        """
        初始化优化版相似序列检测器

        该方法创建检测器实例并配置所有必要的组件，包括文本提取器、
        文本处理器、序列生成器和相似度计算器。

        Args:
            pdf1_path (str): 第一个PDF文件的完整路径，也可以是Word文档路径
            pdf2_path (str): 第二个PDF文件的完整路径，也可以是Word文档路径
            min_similarity (float): 最小相似度阈值，范围0-1，默认0.75
                - 0.75: 较宽松，会检测到更多相似片段
                - 0.85: 中等严格，平衡准确性和召回率
                - 0.95: 非常严格，只检测高度相似的片段
            num_processes (int, optional): 并行处理的进程数
                - None: 自动检测CPU核心数（推荐）
                - 1-4: 适用于内存较小的系统
                - 5-8: 适用于多核CPU系统
                - >8: 可能导致内存压力增大
            max_sequences (int): 每个文件处理的最大序列数量，默认10000
                - 较小值（5000-10000）: 处理速度快，但可能遗漏部分匹配
                - 较大值（20000-50000）: 检测更全面，但需要更多内存和时间
            sequence_length (int): 序列长度（字数），默认8
                - 较短（6-8）: 检测更灵活，但可能产生更多误匹配
                - 较长（10-15）: 检测更精确，但可能遗漏部分相似片段

        Raises:
            FileNotFoundError: 当指定的文件不存在时
            ValueError: 当参数超出有效范围时

        Example:
            >>> detector = OptimizedSimilarSequenceDetector(
            ...     "document1.pdf",
            ...     "document2.pdf",
            ...     min_similarity=0.85,
            ...     max_sequences=15000,
            ...     sequence_length=10
            ... )
            >>> results = detector.run_detection_optimized()
        """
        # 保存文档路径配置
        self.pdf1_path = pdf1_path  # 第一个文档的路径
        self.pdf2_path = pdf2_path  # 第二个文档的路径

        # 保存检测配置参数
        self.min_similarity = min_similarity  # 相似度阈值
        self.max_sequences = max_sequences  # 序列数量限制
        self.sequence_length = sequence_length  # 序列长度

        # 初始化文档提取器（支持PDF和Word文档）
        # 注意：这里创建标准提取器实例，后续可根据需要替换为增强版
        self.extractor1 = PDFTextExtractor(pdf1_path)  # 文档1的提取器
        self.extractor2 = PDFTextExtractor(pdf2_path)  # 文档2的提取器

        # 初始化文本处理器，用于文本分字和标准化
        self.processor = TextProcessor()

        # 初始化优化版序列生成器，使用多进程加速
        self.generator = OptimizedSequenceGenerator(
            min_similarity,  # 相似度阈值
            sequence_length,  # 序列长度
            num_processes  # 进程数配置
        )

        # 初始化快速相似度计算器
        self.calculator = FastSimilarityCalculator(min_similarity)

        # 初始化字符数据存储（用于后续显示匹配上下文）
        # 这些数据会在处理过程中填充
        self.chars1 = None  # 文档1的完整字符列表
        self.chars2 = None  # 文档2的完整字符列表

    def process_pdf_with_limit(self, extractor, pdf_name: str) -> Tuple[List[CharInfo], List[SequenceInfo]]:
        """
        处理单个PDF文件并限制序列数量

        该方法负责处理单个文档的完整流程：
        1. 从文档中提取文本内容
        2. 对文本进行预处理（分字、标准化）
        3. 生成固定长度的字符序列
        4. 如果序列数量超过限制，进行智能采样

        支持多种提取器类型：
        - PDFTextExtractor: 标准PDF提取器
        - EnhancedPDFTextExtractor: 增强版PDF提取器
        - WordExtractor: Word文档提取器

        Args:
            extractor: 文档提取器实例
                - EnhancedPDFTextExtractor: 增强版PDF提取器
                - PDFTextExtractor: 标准PDF提取器
                - WordExtractor: Word文档提取器
            pdf_name (str): PDF文档名称（用于显示进度信息）
                - "文件1": 表示第一个文档
                - "文件2": 表示第二个文档

        Returns:
            Tuple[List[CharInfo], List[SequenceInfo]]: 包含两个元素的元组
                - List[CharInfo]: 完整的字符列表，每个字符包含文本、页码、行号等信息
                - List[SequenceInfo]: 生成的序列列表，每个序列包含固定长度的字符序列

        Raises:
            Exception: 当文本提取或处理失败时

        Example:
            >>> extractor = PDFTextExtractor("document.pdf")
            >>> chars, sequences = detector.process_pdf_with_limit(extractor, "文件1")
            >>> print(f"处理了 {len(chars)} 个字符和 {len(sequences)} 个序列")
        """
        print(f"\n=== 处理 {pdf_name} ===")

        # ==================== 步骤1: 提取文本 ====================
        print("1. 提取文档文本...")
        start_time = time.time()

        # 根据提取器类型调用不同的提取方法
        # 这种设计模式称为"鸭子类型"（Duck Typing）- 根据对象的行为而非类型来判断

        if hasattr(extractor, 'extract_main_text_lines'):
            # 检查是否有 extract_main_text_lines 方法
            # 这表明是 EnhancedPDFTextExtractor（增强版PDF提取器）
            if pdf_name == "文件1":
                # 提取文件1的主体文本
                extracted_text = extractor.extract_main_text_lines(self.pdf1_path)
            elif pdf_name == "文件2":
                # 提取文件2的主体文本
                extracted_text = extractor.extract_main_text_lines(self.pdf2_path)
            else:
                # 未知的文件名，返回错误
                print(f"   错误: 未知的文件名 {pdf_name}")
                return [], []

        elif hasattr(extractor, '__class__') and extractor.__class__.__name__ == 'WordExtractor':
            # 检查是否是 WordExtractor（Word文档提取器）
            # Word文档需要传入文件路径参数
            if pdf_name == "文件1":
                extracted_text = extractor.extract_text_with_positions(self.pdf1_path)
            elif pdf_name == "文件2":
                extracted_text = extractor.extract_text_with_positions(self.pdf2_path)
            else:
                print(f"   错误: 未知的文件名 {pdf_name}")
                return [], []

        else:
            # 默认情况：PDFTextExtractor（标准PDF提取器）
            # 该提取器在初始化时已经绑定了文件路径，调用时不需要参数
            extracted_text = extractor.extract_text_with_positions()

        # 显示提取结果统计
        print(f"   提取了 {len(extracted_text):,} 行文本，耗时 {time.time() - start_time:.2f} 秒")

        # ==================== 步骤2: 文本预处理 ====================
        print("2. 文本预处理（分字）...")
        start_time = time.time()

        # 将提取的文本行分割成单个字符
        # TextProcessor 会处理每一行文本，将其转换为 CharInfo 对象列表
        # CharInfo 包含字符内容、页码、行号、位置等信息
        chars = self.processor.process_extracted_text(extracted_text)

        # 显示预处理结果统计
        print(f"   生成了 {len(chars):,} 个字符，耗时 {time.time() - start_time:.2f} 秒")

        # ==================== 步骤3: 生成序列 ====================
        print(f"3. 生成{self.sequence_length}字序列...")
        start_time = time.time()

        # 根据配置的序列长度，从字符列表中生成固定长度的序列
        # 例如，如果 sequence_length=8，则会生成 "今天天气真不错啊" 这样的8字序列
        sequences = self.generator.generate_sequences(chars)

        # ==================== 步骤4: 序列数量限制 ====================
        # 如果序列数量超过配置的最大值，进行智能采样
        # 这是为了在文档很长时控制处理时间和内存使用
        if len(sequences) > self.max_sequences:
            print(f"   序列数量 {len(sequences):,} 超过限制 {self.max_sequences:,}，进行采样...")

            # 计算采样步长
            # 例如：如果有50000个序列，限制为10000个，则step=5
            # 意味着每5个序列取1个，保证均匀分布
            step = len(sequences) // self.max_sequences

            # 使用切片进行均匀采样
            # [::step] 表示从开始到结束，每隔step个取一个
            # [:self.max_sequences] 确保最终数量不超过限制
            sequences = sequences[::step][:self.max_sequences]

        # 显示序列生成结果统计
        print(f"   处理 {len(sequences):,} 个序列，耗时 {time.time() - start_time:.2f} 秒")

        # 返回字符列表和序列列表
        return chars, sequences

    def detect_similar_sequences_optimized(self, show_progress: bool = True) -> List[SimilarSequenceInfo]:
        """
        检测相似序列（优化版）

        这是检测器的核心方法，执行完整的相似序列检测流程：
        1. 处理两个文档，生成字符序列
        2. 使用多进程并行计算相似度
        3. 筛选出满足阈值条件的相似序列
        4. 显示性能统计信息

        优化特性：
        - 多进程并行处理，充分利用多核CPU
        - 智能哈希预筛选，跳过明显不相似的序列对
        - 实时进度显示，包括预计剩余时间
        - 详细的性能统计（处理速度、总耗时等）

        Args:
            show_progress (bool): 是否显示进度信息
                - True: 显示实时进度和预计剩余时间（推荐用于长时间任务）
                - False: 静默执行，不显示进度信息（适用于批处理）

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息列表
                每个元素包含：
                - sequence1 (SequenceInfo): 文档1中的序列
                - sequence2 (SequenceInfo): 文档2中的序列
                - similarity (float): 相似度分数（0-1）
                - differences (List[str]): 差异描述列表

        Raises:
            Exception: 当文档处理或相似度计算失败时

        Example:
            >>> detector = OptimizedSimilarSequenceDetector("doc1.pdf", "doc2.pdf")
            >>> similar_sequences = detector.detect_similar_sequences_optimized(show_progress=True)
            >>> print(f"找到 {len(similar_sequences)} 个相似序列")
        """
        print("开始优化版相似序列检测...")
        total_start_time = time.time()  # 记录开始时间，用于计算总耗时

        # ==================== 阶段1: 处理两个文档 ====================
        # 分别处理两个文档，提取字符和生成序列
        chars1, sequences1 = self.process_pdf_with_limit(self.extractor1, "文件1")
        chars2, sequences2 = self.process_pdf_with_limit(self.extractor2, "文件2")

        # 保存字符列表到实例变量
        # 这些数据将用于后续显示匹配序列的上下文信息
        self.chars1 = chars1
        self.chars2 = chars2

        # ==================== 阶段2: 预估计算量 ====================
        # 计算理论上的最大比较次数（实际会比较少，因为有哈希预筛选）
        total_comparisons = len(sequences1) * len(sequences2)

        # 显示检测配置和统计信息
        print(f"\n=== 相似度检测 ===")
        print(f"相似度阈值: {self.min_similarity:.2f}")
        print(f"文件1序列数: {len(sequences1):,}")
        print(f"文件2序列数: {len(sequences2):,}")
        print(f"理论最大比较次数: {total_comparisons:,}")

        # ==================== 阶段3: 定义进度回调函数 ====================
        # 这个函数会在相似度计算过程中定期调用，用于显示进度
        def progress_callback(progress, completed, total):
            """
            进度回调函数

            Args:
                progress (float): 进度比例（0-1）
                completed (int): 已完成的比较次数
                total (int): 总比较次数
            """
            if show_progress:
                # 计算已用时间
                elapsed = time.time() - callback_start_time

                if completed > 0:
                    # 基于当前速度估算总时间
                    # 公式：总时间 = 已用时间 × 总次数 / 已完成次数
                    estimated_total = elapsed * total / completed

                    # 计算预计剩余时间
                    remaining = estimated_total - elapsed

                    # 显示进度信息
                    print(f"   进度: {completed}/{total} ({progress*100:.1f}%) - "
                          f"已用时: {elapsed:.1f}s, 预计剩余: {remaining:.1f}s")

        # 记录回调函数的开始时间
        callback_start_time = time.time()

        # ==================== 阶段4: 执行相似度检测 ====================
        # 使用多进程并行计算相似度
        start_time = time.time()
        similar_sequences = self.generator.find_similar_sequences_parallel(
            sequences1,  # 文档1的序列列表
            sequences2,  # 文档2的序列列表
            progress_callback if show_progress else None  # 进度回调函数
        )
        detection_time = time.time() - start_time  # 计算检测耗时

        # ==================== 阶段5: 性能统计 ====================
        total_time = time.time() - total_start_time  # 计算总耗时（包含文档处理）

        # 计算处理速度（每秒比较次数）
        # 这反映了算法的效率，数值越大表示处理越快
        comparisons_per_second = total_comparisons / detection_time if detection_time > 0 else 0

        # 显示完成信息和性能统计
        print(f"\n=== 检测完成 ===")
        print(f"找到 {len(similar_sequences):,} 个相似序列")
        print(f"检测耗时: {detection_time:.2f} 秒")
        print(f"总耗时: {total_time:.2f} 秒")
        print(f"处理速度: {comparisons_per_second:,.0f} 比较/秒")

        return similar_sequences

    def get_context(self, sequence: SequenceInfo, chars: List[CharInfo],
                    context_length: int = 50) -> str:
        """
        获取序列的上下文（前后各context_length个字符）

        该方法用于在显示相似序列时提供额外的上下文信息，帮助用户理解
        相似片段在文档中的具体位置和周围内容。这对于验证匹配的准确性和
        理解文档的语义上下文非常重要。

        上下文格式：
        ...前文[匹配序列]后文...
        - "..." 表示还有更多内容
        - "[]" 标记匹配的序列
        - 前文和后文各包含 context_length 个字符

        Args:
            sequence (SequenceInfo): 序列信息对象
                - start_index: 序列在文档中的起始索引
                - chars: 序列包含的字符列表
                - raw_sequence: 原始序列文本（包含标点符号）
                - sequence: 清理后的序列文本（不含标点）
            chars (List[CharInfo]): 文档的完整字符列表
                每个元素是一个 CharInfo 对象，包含字符内容、位置等信息
            context_length (int): 上下文长度（字符数），默认50
                - 较小值（20-30）: 适合紧凑显示
                - 中等值（50-100）: 平衡信息和可读性（推荐）
                - 较大值（150+）: 提供更多上下文，但显示较长

        Returns:
            str: 格式化的上下文字符串
                格式为："...前文[匹配序列]后文..."
                - 前文: 匹配序列之前的 context_length 个字符
                - 匹配序列: 原始序列文本（包含标点符号）
                - 后文: 匹配序列之后的 context_length 个字符

        Example:
            >>> sequence = SequenceInfo(...)
            >>> chars = [...]  # 完整字符列表
            >>> context = detector.get_context(sequence, chars, context_length=30)
            >>> print(context)
            ...这是前面的文本内容，用于提供上下文[今天天气真不错啊]这是后面的文本内容...
        """
        # 获取序列的起始索引
        start_idx = sequence.start_index

        # ==================== 获取前文 ====================
        # 计算前文的起始位置（不能小于0）
        before_start = max(0, start_idx - context_length)

        # 切片获取前文的所有字符
        # Python切片: [start:end] 包含start，不包含end
        before_chars = chars[before_start:start_idx]

        # 将字符列表拼接成字符串
        # 使用列表推导式提取每个字符的文本内容
        before_text = ''.join([c.char for c in before_chars])

        # ==================== 获取匹配序列 ====================
        # 优先使用原始序列（包含标点符号），如果没有则使用清理后的序列
        # 原始序列更能体现文档的原始内容
        match_text = sequence.raw_sequence if sequence.raw_sequence else sequence.sequence

        # ==================== 获取后文 ====================
        # 计算后文的结束位置（不能超过字符列表长度）
        # start_idx + len(sequence.chars) 是匹配序列结束的位置
        after_end = min(len(chars), start_idx + len(sequence.chars) + context_length)

        # 切片获取后文的所有字符
        # 从匹配序列结束位置开始，到 after_end 结束
        after_chars = chars[start_idx + len(sequence.chars):after_end]

        # 将字符列表拼接成字符串
        after_text = ''.join([c.char for c in after_chars])

        # ==================== 格式化输出 ====================
        # 返回格式化的上下文字符串
        # 使用方括号[]标记匹配的序列，便于识别
        return f"...{before_text}[{match_text}]{after_text}..."

    def format_output_optimized(self, similar_sequences: List[SimilarSequenceInfo],
                               show_all_positions: bool = True,
                               max_results: Optional[int] = None) -> str:
        """
        格式化输出结果（优化版）

        该方法将相似序列检测结果格式化为可读性强的报告文本，包括：
        1. 报告头部信息（时间、文件路径、配置参数等）
        2. 统计摘要（总数、相似度分布、平均值等）
        3. 详细结果列表（每个相似序列的具体信息和上下文）
        4. 分页提示（当结果过多时）

        报告格式设计原则：
        - 层次清晰：使用分隔线和标题区分不同部分
        - 信息完整：包含位置、相似度、上下文等关键信息
        - 易于阅读：使用缩进和格式化对齐
        - 适度详细：平衡详细程度和可读性

        Args:
            similar_sequences (List[SimilarSequenceInfo]): 相似序列列表
                每个元素包含两个匹配的序列及其相似度信息
            show_all_positions (bool): 是否显示所有位置信息，默认True
                - True: 显示完整的上下文和位置信息
                - False: 仅显示序列文本和基本位置（页码、行号）
            max_results (Optional[int]): 最大显示结果数量，默认None（显示全部）
                - None: 显示所有结果（适合结果较少的情况）
                - 10-50: 推荐范围（适合大多数情况）
                - 100+: 适合生成完整报告文件

        Returns:
            str: 格式化的输出结果字符串
                包含完整的报告文本，可直接打印或保存到文件

        Example:
            >>> results = detector.detect_similar_sequences_optimized()
            >>> report = detector.format_output_optimized(
            ...     results,
            ...     show_all_positions=True,
            ...     max_results=20
            ... )
            >>> print(report)
            >>> # 或保存到文件
            >>> with open("report.txt", "w", encoding="utf-8") as f:
            ...     f.write(report)
        """
        # ==================== 初始化输出列表 ====================
        output = []

        # ==================== 报告头部 ====================
        # 使用等宽分隔线创建清晰的视觉分隔
        output.append("=" * 80)
        output.append("PDF文件相似序列检测报告（优化版）")
        output.append("=" * 80)

        # 添加报告元数据
        output.append(f"检测完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")  # 当前时间
        output.append(f"文件1: {self.pdf1_path}")  # 第一个文件路径
        output.append(f"文件2: {self.pdf2_path}")  # 第二个文件路径
        output.append(f"相似度阈值: {self.min_similarity:.2f}")  # 相似度配置
        output.append(f"序列数量限制: {self.max_sequences:,}")  # 序列数量限制
        output.append(f"相似序列总数: {len(similar_sequences):,}")  # 检测到的相似序列数
        output.append("")  # 空行分隔

        # ==================== 处理空结果情况 ====================
        if not similar_sequences:
            # 如果没有找到相似序列，显示提示信息
            output.append(f"未发现相似度≥{self.min_similarity:.2f}的{self.sequence_length}字序列。")
            return "\n".join(output)

        # ==================== 限制显示数量 ====================
        # 如果指定了最大显示数量，只取前N个结果
        display_sequences = similar_sequences[:max_results] if max_results else similar_sequences

        # ==================== 统计信息部分 ====================
        # 生成统计摘要，提供整体概况
        summary = self.generator.get_sequence_summary(similar_sequences)

        output.append("统计信息:")
        output.append(f"- 相似序列总数: {summary['total_similar']:,}")  # 总数
        output.append(f"- 高相似度(>0.9): {summary['high_similarity_count']:,} 个")  # 高相似度数量
        output.append(f"- 中相似度(0.8-0.9): {summary['medium_similarity_count']:,} 个")  # 中相似度数量
        output.append(f"- 低相似度(0.75-0.8): {summary['low_similarity_count']:,} 个")  # 低相似度数量
        output.append(f"- 平均相似度: {summary['average_similarity']:.3f}")  # 平均相似度
        output.append(f"- 最高相似度: {summary['max_similarity']:.3f}")  # 最高相似度
        output.append(f"- 最低相似度: {summary['min_similarity']:.3f}")  # 最低相似度
        output.append("")  # 空行分隔

        # ==================== 详细结果部分 ====================
        output.append("相似序列详情 (按相似度排序):")
        output.append("-" * 80)

        # 遍历每个相似序列，生成详细信息
        for i, sim_seq in enumerate(display_sequences, 1):  # 从1开始编号
            # 显示序号和相似度
            output.append(f"{i}. 相似度: {sim_seq.similarity:.3f}")

            # ==================== 文件1的信息 ====================
            if self.chars1:
                # 如果有完整字符列表，显示带上下文的信息
                context1 = self.get_context(sim_seq.sequence1, self.chars1, 50)  # 获取上下文
                output.append(f"   文件1 (页{sim_seq.sequence1.start_char.page}行{sim_seq.sequence1.start_char.line}):")
                output.append(f"      {context1}")  # 显示上下文
            else:
                # 如果没有完整字符列表，仅显示基本信息
                output.append(f"   文件1: '{sim_seq.sequence1.sequence}'")
                output.append(f"          位置: 页{sim_seq.sequence1.start_char.page}行{sim_seq.sequence1.start_char.line}")

            # ==================== 文件2的信息 ====================
            if self.chars2:
                # 如果有完整字符列表，显示带上下文的信息
                context2 = self.get_context(sim_seq.sequence2, self.chars2, 50)  # 获取上下文
                output.append(f"   文件2 (页{sim_seq.sequence2.start_char.page}行{sim_seq.sequence2.start_char.line}):")
                output.append(f"      {context2}")  # 显示上下文
            else:
                # 如果没有完整字符列表，仅显示基本信息
                output.append(f"   文件2: '{sim_seq.sequence2.sequence}'")
                output.append(f"          位置: 页{sim_seq.sequence2.start_char.page}行{sim_seq.sequence2.start_char.line}")

            # ==================== 差异信息 ====================
            # 显示两个序列之间的差异
            if sim_seq.differences and sim_seq.differences != ["完全相同"]:
                # 如果有差异，显示差异列表
                output.append(f"   差异: {', '.join(sim_seq.differences)}")
            else:
                # 如果完全相同，显示"无"
                output.append(f"   差异: 无")

            output.append("")  # 空行分隔每个结果

        # ==================== 分页提示 ====================
        # 如果限制了显示数量且还有更多结果，显示提示信息
        if max_results and len(similar_sequences) > max_results:
            remaining = len(similar_sequences) - max_results
            output.append(f"... 还有 {remaining:,} 个相似序列未显示")
            output.append("完整结果请查看保存的文件。")

        # ==================== 返回完整报告 ====================
        # 将列表拼接成字符串，使用换行符连接
        return "\n".join(output)

    def save_results_optimized(self, similar_sequences: List[SimilarSequenceInfo],
                               output_file: str = "optimized_similar_sequences_results.txt"):
        """
        保存结果到文件（优化版）

        该方法将检测结果保存到文本文件，便于：
        1. 长期存档和查阅
        2. 与他人分享检测结果
        3. 后续分析和审计
        4. 避免终端输出过多导致的性能问题

        文件格式特点：
        - 使用UTF-8编码，支持中文
- 包含完整的检测结果和上下文
- 格式化输出，便于阅读
- 可在任何文本编辑器中打开

        Args:
            similar_sequences (List[SimilarSequenceInfo]): 相似序列列表
                检测到的所有相似序列及其详细信息
            output_file (str): 输出文件名，默认"optimized_similar_sequences_results.txt"
                - 可以包含相对路径或绝对路径
                - 示例: "results.txt", "output/report.txt", "/tmp/full_report.txt"
                - 如果目录不存在，会报错

        Raises:
            IOError: 当文件写入失败时（如权限不足、磁盘已满等）
            Exception: 其他写入错误

        Example:
            >>> detector = OptimizedSimilarSequenceDetector("doc1.pdf", "doc2.pdf")
            >>> results = detector.detect_similar_sequences_optimized()
            >>> detector.save_results_optimized(results, "my_report.txt")
            结果已保存到: my_report.txt

        Note:
            - 文件使用UTF-8编码，确保中文正确显示
            - 如果文件已存在，会被覆盖
            - 建议使用有意义的文件名，如包含日期或文档名称
        """
        # ==================== 生成格式化输出 ====================
        # 使用 format_output_optimized 方法生成完整的报告文本
        # show_all_positions=True 表示包含所有位置信息和上下文
        output = self.format_output_optimized(similar_sequences, show_all_positions=True)

        # ==================== 写入文件 ====================
        try:
            # 使用 with 语句自动管理文件资源
            # encoding='utf-8' 确保中文字符正确保存
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)  # 写入完整的报告内容

            # 显示成功消息
            print(f"\n结果已保存到: {output_file}")

        except Exception as e:
            # 捕获并显示错误信息
            # 常见错误：权限不足、磁盘已满、路径不存在等
            print(f"保存结果时出错: {e}")

    def run_detection_optimized(self, save_to_file: bool = True,
                                show_max_results: int = 50,
                                show_progress: bool = True) -> List[SimilarSequenceInfo]:
        """
        运行完整的检测流程（优化版）

        这是检测器的主要入口方法，封装了完整的检测流程：
        1. 显示配置信息
        2. 执行相似序列检测
        3. 格式化并显示结果摘要
        4. 保存完整结果到文件（可选）
        5. 显示总耗时统计

        这是用户最常调用的方法，提供了一站式的检测体验。

        典型使用场景：
        - 快速检测两个文档的相似性
        - 生成详细的相似序列报告
        - 批量处理多个文档对
        - 集成到自动化工作流中

        Args:
            save_to_file (bool): 是否保存结果到文件，默认True
                - True: 保存完整结果到默认文件名（推荐）
                - False: 仅在屏幕显示结果，不保存文件
            show_max_results (int): 屏幕显示的最大结果数量，默认50
                - 控制屏幕输出的详细程度
                - 设置较小值（10-20）适合快速查看
                - 设置较大值（50-100）适合详细审查
                - 无论此值如何，保存的文件都包含完整结果
            show_progress (bool): 是否显示进度信息，默认True
                - True: 显示实时进度和预计剩余时间
                - False: 静默执行，适用于脚本或批处理

        Returns:
            List[SimilarSequenceInfo]: 相似序列的详细信息列表
                包含所有检测到的相似序列，可用于进一步处理

        Raises:
            Exception: 当文档处理失败或检测过程出错时

        Example:
            >>> # 基本使用
            >>> detector = OptimizedSimilarSequenceDetector("doc1.pdf", "doc2.pdf")
            >>> results = detector.run_detection_optimized()
            >>>
            >>> # 自定义配置
            >>> results = detector.run_detection_optimized(
            ...     save_to_file=True,
            ...     show_max_results=20,
            ...     show_progress=True
            ... )
            >>>
            >>> # 不保存文件，仅快速查看
            >>> results = detector.run_detection_optimized(
            ...     save_to_file=False,
            ...     show_max_results=10
            ... )

        Note:
            - 完整结果会保存到文件，屏幕仅显示摘要
            - 建议保存文件以便后续查阅和分析
            - 进度显示对于长时间运行的任务很有帮助
        """
        # ==================== 显示配置信息 ====================
        print("=" * 80)
        print("开始PDF文件相似序列检测（优化版）")
        # 显示关键配置参数
        print(f"配置: 相似度≥{self.min_similarity:.2f}, 最大序列数={self.max_sequences:,}")
        print("=" * 80)

        # 记录开始时间，用于计算总耗时
        start_time = time.time()

        # ==================== 执行检测 ====================
        # 调用核心检测方法，获取所有相似序列
        similar_sequences = self.detect_similar_sequences_optimized(show_progress=show_progress)

        # ==================== 显示结果摘要 ====================
        print("\n" + "=" * 80)
        print("检测结果")
        print("=" * 80)

        # 格式化并显示结果摘要
        # show_all_positions=False: 不显示完整上下文（避免屏幕输出过多）
        # max_results=show_max_results: 仅显示前N个结果
        print(self.format_output_optimized(
            similar_sequences,
            show_all_positions=False,
            max_results=show_max_results
        ))

        # ==================== 保存完整结果 ====================
        if save_to_file:
            # 保存包含所有结果和完整上下文的报告到文件
            self.save_results_optimized(similar_sequences)

        # ==================== 显示总耗时 ====================
        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")

        # 返回完整的结果列表，供调用者进一步处理
        return similar_sequences


# ==================== 模块级辅助函数 ====================

def fast_similarity_detection(pdf1_path: str, pdf2_path: str,
                            min_similarity: float = 0.8,
                            max_sequences: int = 5000,
                            num_processes: int = None) -> List[SimilarSequenceInfo]:
    """
    快速相似度检测函数（便捷接口）

    这是一个便捷函数，用于快速执行相似度检测，无需手动创建检测器实例。
    它使用预设的优化参数，适合大多数常见场景。

    与完整API相比，该函数：
    - 使用更严格的相似度阈值（0.8 vs 0.75）
    - 限制序列数量以提高速度（5000 vs 10000）
    - 不保存结果文件（仅返回数据）
    - 仅显示前20个结果（避免屏幕输出过多）

    适用场景：
    - 快速验证两个文档的相似性
    - 交互式探索和测试
    - 集成到其他脚本中
    - 批量处理多个文档对

    Args:
        pdf1_path (str): 第一个PDF/Word文件的完整路径
        pdf2_path (str): 第二个PDF/Word文件的完整路径
        min_similarity (float): 相似度阈值，默认0.8（更严格）
            - 较高值（0.85-0.95）: 只检测高度相似的片段
            - 中等值（0.75-0.85）: 平衡准确性和召回率
            - 较低值（0.65-0.75）: 检测更多相似片段，可能包含误报
        max_sequences (int): 每个文件的最大序列数，默认5000（更快）
            - 较小值（3000-5000）: 处理速度快，适合快速检测
            - 较大值（10000-20000）: 检测更全面，但需要更多时间
        num_processes (int, optional): 并行处理的进程数
            - None: 自动检测CPU核心数（推荐）
            - 1-4: 适用于内存较小的系统
            - 5-8: 适用于多核CPU系统

    Returns:
        List[SimilarSequenceInfo]: 相似序列列表
            每个元素包含两个匹配的序列及其相似度信息
            返回结果最多显示前20个，但包含所有检测到的相似序列

    Raises:
        FileNotFoundError: 当指定的文件不存在时
        Exception: 当文档处理或检测过程出错时

    Example:
        >>> # 基本使用
        >>> results = fast_similarity_detection("doc1.pdf", "doc2.pdf")
        >>> print(f"找到 {len(results)} 个相似序列")
        >>>
        >>> # 自定义参数
        >>> results = fast_similarity_detection(
        ...     "file1.pdf",
        ...     "file2.pdf",
        ...     min_similarity=0.85,
        ...     max_sequences=10000
        ... )
        >>>
        >>> # 遍历结果
        >>> for seq_info in results[:10]:
        ...     print(f"相似度: {seq_info.similarity:.2f}")
        ...     print(f"序列1: {seq_info.sequence1.sequence}")
        ...     print(f"序列2: {seq_info.sequence2.sequence}")

    Note:
        - 该函数不保存结果文件，如需保存请使用 OptimizedSimilarSequenceDetector 类
        - 仅显示前20个结果，但返回的列表包含所有检测到的相似序列
        - 适合快速检测和探索，不适合生成详细报告
    """
    # 创建检测器实例，使用传入的参数
    detector = OptimizedSimilarSequenceDetector(
        pdf1_path,  # 第一个文档路径
        pdf2_path,  # 第二个文档路径
        min_similarity,  # 相似度阈值
        num_processes,  # 进程数配置
        max_sequences  # 序列数量限制
    )

    # 运行检测并返回结果
    # save_to_file=False: 不保存文件（仅返回数据）
    # show_max_results=20: 屏幕显示前20个结果
    # show_progress=True: 显示进度信息
    return detector.run_detection_optimized(
        save_to_file=False,
        show_max_results=20,
        show_progress=True
    )


def test_optimized_detector():
    """
    测试优化版检测器

    这是一个简单的测试函数，用于验证检测器是否正确安装和配置。
    它显示了优化版检测器的主要特性和优势。

    通常用于：
    - 验证模块导入是否正确
    - 展示检测器的功能特性
    - 作为快速参考示例

    Example:
        >>> python optimized_duplicate_detector.py
        优化版相似序列检测器已创建
        主要优化:
        - 多进程并行处理
        - 智能哈希预筛选
        - 序列数量限制
        - 实时进度显示
        - 性能监控
    """
    print("优化版相似序列检测器已创建")
    print("主要优化:")
    print("- 多进程并行处理")  # 利用多核CPU加速计算
    print("- 智能哈希预筛选")  # 快速跳过明显不相似的序列
    print("- 序列数量限制")  # 控制内存使用和处理时间
    print("- 实时进度显示")  # 显示进度和预计剩余时间
    print("- 性能监控")  # 统计处理速度和总耗时


# ==================== 主程序入口 ====================
# 当直接运行该模块时，执行测试函数
# 这允许将模块作为脚本运行，用于测试和演示
if __name__ == "__main__":
    test_optimized_detector()