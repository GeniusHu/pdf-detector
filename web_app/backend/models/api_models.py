#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 相似度检测服务的 API 数据模型

本模块定义了 PDF 相似度检测服务的所有请求和响应数据模型。
这些模型用于前后端之间的数据交换，确保数据结构的类型安全和一致性。

主要功能：
- 定义文档比对的请求参数
- 定义文件上传的响应格式
- 定义任务状态查询的响应格式
- 定义相似度检测结果的完整数据结构
- 定义错误响应和健康检查的数据模型

命名约定：
- 内部 Python 代码使用 snake_case（蛇形命名）
- API 响应使用 camelCase（驼峰命名）
- 通过 Pydantic 的 alias 参数实现自动转换
"""

# typing 模块：提供类型提示支持，用于定义复杂数据类型的注解
from typing import List, Optional, Dict, Any

# pydantic：数据验证和设置管理库，用于定义数据模型和自动验证
from pydantic import BaseModel, Field

# enum：枚举类型支持，用于定义固定的常量选项
from enum import Enum

# datetime：日期时间处理模块
from datetime import datetime


class ProcessingMode(str, Enum):
    """
    文档处理模式枚举

    定义不同的文档处理速度模式，根据文档大小和精度要求选择合适的处理方式。
    模式之间主要区别在于算法复杂度和处理精度的平衡。

    枚举值：
        STANDARD: 标准模式 - 使用最高精度的算法，处理速度较慢，适合小型文档或对精度要求极高的场景
        FAST: 快速模式 - 平衡速度和精度，适合大多数场景，为默认推荐选项
        ULTRA_FAST: 超快速模式 - 使用最快的算法，精度略有降低，适合大型文档或快速预览场景
    """
    STANDARD = "standard"          # 标准模式：最高精度，处理速度最慢
    FAST = "fast"                  # 快速模式：平衡速度和精度，默认选项
    ULTRA_FAST = "ultra_fast"      # 超快速模式：最快速度，精度略低


class ContentFilter(str, Enum):
    """
    内容过滤选项枚举

    定义文档内容提取和过滤的不同策略，控制哪些内容应该被包含在相似度分析中。
    这对于排除参考文献、目录等非正文内容非常重要。

    枚举值：
        ALL_CONTENT: 全部内容 - 提取文档中的所有文本内容，包括正文、参考文献、附录等
        MAIN_CONTENT_ONLY: 仅正文内容 - 只提取主要正文内容，过滤掉页眉页脚、目录、参考文献等（默认选项）
        INCLUDE_REFERENCES: 包含参考文献 - 正文内容加上参考文献部分
        INCLUDE_CITATIONS: 包含引用标记 - 正文内容加上引用标注和脚注
    """
    ALL_CONTENT = "all"                          # 全部内容：包含所有文本
    MAIN_CONTENT_ONLY = "main_content_only"      # 仅正文内容：过滤掉非正文部分（默认）
    INCLUDE_REFERENCES = "include_references"    # 包含参考文献：正文+参考文献
    INCLUDE_CITATIONS = "include_citations"      # 包含引用标记：正文+引用标注


class ExportFormat(str, Enum):
    """
    导出格式选项枚举

    定义相似度检测结果的不同导出格式，用户可以根据需求选择合适的输出格式。

    枚举值：
        TEXT: 纯文本格式 - 生成易读的文本报告，包含所有相似段落和统计信息
        JSON: JSON 格式 - 结构化数据格式，方便程序处理和二次分析
        CSV: CSV 格式 - 表格格式，方便在 Excel 等工具中打开和分析
        PDF_REPORT: PDF 报告 - 生成格式化的 PDF 报告文件，适合存档和打印
    """
    TEXT = "text"              # 纯文本格式：易读的文本报告
    JSON = "json"              # JSON 格式：结构化数据，方便程序处理
    CSV = "csv"                # CSV 格式：表格格式，适合 Excel 分析
    PDF_REPORT = "pdf_report"  # PDF 报告：格式化的 PDF 文件，适合存档


class TaskStatus(str, Enum):
    """
    任务状态枚举

    定义文档比对任务在处理生命周期中的各种状态。
    任务状态会随着处理进度自动更新，前端可以根据状态显示不同的 UI。

    枚举值：
        PENDING: 等待中 - 任务已创建，正在队列中等待处理
        PROCESSING: 处理中 - 任务正在执行，正在进行文档提取和相似度计算
        COMPLETED: 已完成 - 任务执行成功，结果已生成
        ERROR: 错误 - 任务执行过程中遇到错误，已终止
        CANCELLED: 已取消 - 任务被用户或系统主动取消
    """
    PENDING = "pending"        # 等待中：在队列中等待处理
    PROCESSING = "processing"  # 处理中：正在执行文档分析
    COMPLETED = "completed"    # 已完成：任务成功完成
    ERROR = "error"            # 错误：执行过程中遇到错误
    CANCELLED = "cancelled"    # 已取消：任务被主动取消


# ============================================================================
# 请求模型 (Request Models)
# ============================================================================

class ComparisonRequest(BaseModel):
    """
    文档比对请求模型

    这是启动文档相似度比对任务的请求参数模型。
    前端提交的请求参数将按照此模型进行验证，确保所有参数类型和范围正确。
    支持从 PDF 和 Word 文档中提取文本进行比对。

    属性说明：
        pdf1_path (str): 第一个文档的文件路径（必填）
                        支持格式：PDF (.pdf), Word (.docx, .doc)
                        示例："/uploads/document1.pdf"

        pdf2_path (str): 第二个文档的文件路径（必填）
                        支持格式：PDF (.pdf), Word (.docx, .doc)
                        示例："/uploads/document2.docx"

        similarity_threshold (float): 相似度阈值（默认：0.90，范围：0.0-1.0）
                                     只报告相似度高于此阈值的序列
                                     值越接近 1.0，匹配越严格
                                     推荐：0.85-0.95 之间

        sequence_length (int): 序列长度（默认：8，范围：4-20）
                              用于相似度检测的连续字符数量
                              较短值（4-6）检测更多片段相似性
                              较长值（15-20）检测大段复制
                              推荐默认值 8

        content_filter (ContentFilter): 内容过滤选项（默认：MAIN_CONTENT_ONLY）
                                       控制提取文档的哪些内容进行分析
                                       推荐使用 MAIN_CONTENT_ONLY 过滤参考文献

        processing_mode (ProcessingMode): 处理模式（默认：FAST）
                                         控制处理速度和精度的平衡
                                         大型文档推荐 ULTRA_FAST

        max_sequences (int): 每个文件的最大序列数（默认：5000，范围：100-100000）
                            防止结果过多导致性能问题
                            超过此数量将只返回最相似的前 N 个

        export_format (ExportFormat): 结果导出格式（默认：TEXT）
                                     选择结果文件的输出格式

        context_chars (int): 上下文字符数（默认：100，范围：50-500）
                            在相似序列周围显示的上下文文字数量
                            帮助理解相似片段的具体语境

        page_range1 (Optional[str]): 文档 1 的页码范围（可选）
                                    格式："1-146" 或 "1,3,5-10"
                                    None 表示处理全部页面

        page_range2 (Optional[str]): 文档 2 的页码范围（可选）
                                    格式："1-169" 或 "1,3,5-10"
                                    None 表示处理全部页面
    """
    pdf1_path: str = Field(..., description="第一个文档的文件路径，支持 PDF 和 Word 格式", alias="pdf1Path")
    pdf2_path: str = Field(..., description="第二个文档的文件路径，支持 PDF 和 Word 格式", alias="pdf2Path")
    similarity_threshold: float = Field(default=0.90, ge=0.0, le=1.0, description="相似度阈值，范围 0.0-1.0，只报告高于此阈值的相似序列", alias="similarityThreshold")
    sequence_length: int = Field(default=8, ge=4, le=20, description="用于相似度检测的连续字符序列长度，范围 4-20", alias="sequenceLength")
    content_filter: ContentFilter = Field(default=ContentFilter.MAIN_CONTENT_ONLY, description="内容过滤选项，控制提取哪些内容", alias="contentFilter")
    processing_mode: ProcessingMode = Field(default=ProcessingMode.FAST, description="处理模式，控制速度和精度平衡", alias="processingMode")
    max_sequences: int = Field(default=5000, ge=100, le=100000, description="每个文件的最大序列数，防止结果过多", alias="maxSequences")
    export_format: ExportFormat = Field(default=ExportFormat.TEXT, description="结果导出格式", alias="exportFormat")
    context_chars: int = Field(default=100, ge=50, le=500, description="相似序列周围显示的上下文字符数", alias="contextChars")
    page_range1: Optional[str] = Field(None, description="文档 1 的页码范围，格式如 '1-146' 或 '1,3,5-10'", alias="pageRange1")
    page_range2: Optional[str] = Field(None, description="文档 2 的页码范围，格式如 '1-169' 或 '1,3,5-10'", alias="pageRange2")

    class Config:
        populate_by_name = True  # 允许同时使用 camelCase 和 snake_case


class UploadResponse(BaseModel):
    """
    文件上传响应模型

    文件上传成功后返回给前端的信息，包含文件的基本属性和存储位置。

    属性说明：
        filename (str): 原始文件名
                       保持用户上传时的文件名
                       示例："thesis_final.pdf"

        file_path (str): 服务器保存的文件路径
                        文件在服务器上的实际存储路径
                        用于后续的比对任务
                        示例："/uploads/uuid-thesis_final.pdf"

        file_size (int): 文件大小（字节）
                        用于显示文件大小和预估处理时间
                        示例：2048576（约 2MB）

        uploaded_at (str): 上传时间戳（ISO 8601 格式）
                          记录文件上传的精确时间
                          示例："2025-01-03T10:30:45.123Z"
    """
    filename: str = Field(..., description="原始文件名", alias="fileName")
    file_path: str = Field(..., description="服务器保存的文件路径", alias="filePath")
    file_size: int = Field(..., description="文件大小（字节）", alias="fileSize")
    uploaded_at: str = Field(..., description="上传时间戳（ISO 8601 格式）", alias="uploadedAt")

    class Config:
        populate_by_name = True


# ============================================================================
# 响应模型 (Response Models)
# ============================================================================

class ComparisonResponse(BaseModel):
    """
    文档比对任务启动响应模型

    当提交文档比对请求后，立即返回的任务信息。
    前端可以使用 task_id 后续查询任务进度和结果。

    属性说明：
        task_id (str): 唯一任务标识符
                      用于后续查询任务状态和获取结果
                      格式：UUID 字符串
                      示例："550e8400-e29b-41d4-a716-446655440000"

        status (str): 任务状态
                     可能值：pending, processing, completed, error, cancelled
                     参见 TaskStatus 枚举

        message (str): 状态消息
                     提供任务状态的详细说明
                     示例："比对任务已创建，正在处理中..."
    """
    task_id: str = Field(..., description="唯一任务标识符，用于后续查询", alias="taskId")
    status: str = Field(..., description="任务当前状态")
    message: str = Field(..., description="状态说明消息")

    class Config:
        populate_by_name = True


class TaskStatusResponse(BaseModel):
    """
    任务状态查询响应模型

    用于查询任务当前的处理进度和状态信息。
    前端可以通过定期轮询此接口获取实时进度更新。

    属性说明：
        task_id (str): 任务标识符
                     查询的任务 ID

        status (str): 当前任务状态
                     可能值：pending, processing, completed, error, cancelled
                     用于前端显示不同的 UI 状态

        progress (float): 处理进度（范围：0.0-1.0）
                         0.0 表示刚开始，1.0 表示已完成
                         用于显示进度条
                         示例：0.65（表示 65% 完成）

        started_at (str): 任务开始时间（ISO 8601 格式）
                         记录任务实际开始处理的时间
                         示例："2025-01-03T10:30:45.123Z"

        completed_at (Optional[str]): 任务完成时间（ISO 8601 格式）
                                    仅在任务完成或出错时有值
                                    示例："2025-01-03T10:35:20.456Z"

        error (Optional[str]): 错误信息
                             如果任务出错，包含错误描述
                             示例："文档解析失败：文件已损坏"

        message (Optional[str]): 当前状态消息
                               提供更详细的进度说明
                               示例："正在提取第二个文档的文本内容..."
    """
    task_id: str = Field(..., description="任务标识符", alias="taskId")
    status: str = Field(..., description="当前任务状态")
    progress: float = Field(..., ge=0.0, le=1.0, description="处理进度，范围 0.0-1.0")
    started_at: str = Field(..., description="任务开始时间", alias="startedAt")
    completed_at: Optional[str] = Field(None, description="任务完成时间", alias="completedAt")
    error: Optional[str] = Field(None, description="错误信息（如果有）")
    message: Optional[str] = Field(None, description="当前状态的详细说明")

    class Config:
        populate_by_name = True


class SimilarSequence(BaseModel):
    """
    相似序列信息模型

    描述在两个文档中发现的相似文本序列。
    每个实例代表一对相似的文本段落。

    属性说明：
        sequence1 (str): 文档 1 中的文本序列
                        实际匹配到的文本内容
                        示例："本研究旨在探讨深度学习在图像识别领域的应用..."

        sequence2 (str): 文档 2 中的文本序列
                        与 sequence1 相似的文本内容
                        可能包含细微差异

        similarity (float): 相似度分数（范围：0.0-1.0）
                           1.0 表示完全相同
                           0.95 表示高度相似
                           计算基于编辑距离等算法

        position1 (Dict[str, Any]): 文档 1 中的位置信息
                                   包含页码、行号、字符偏移等
                                   示例：{"page": 15, "line": 42, "offset": 1234}

        position2 (Dict[str, Any]): 文档 2 中的位置信息
                                   包含页码、行号、字符偏移等
                                   示例：{"page": 23, "line": 18, "offset": 2345}

        context1 (Dict[str, str]): 文档 1 中序列周围的上下文
                                  包含 before 和 after 字段
                                  示例：{"before": "...前文", "after": "后文..."}

        context2 (Dict[str, str]): 文档 2 中序列周围的上下文
                                  包含 before 和 after 字段
                                  用于对比两个相似段落的语境

        differences (List[str]): 差异列表
                                列出两个序列之间的具体差异
                                示例：["字符 '深度' vs '浅层'", "标点符号差异"]
    """
    sequence1: str = Field(..., description="文档 1 中的文本序列内容")
    sequence2: str = Field(..., description="文档 2 中的文本序列内容")
    similarity: float = Field(..., ge=0.0, le=1.0, description="相似度分数，范围 0.0-1.0")
    position1: Dict[str, Any] = Field(..., description="文档 1 中的位置信息（页码、行号等）")
    position2: Dict[str, Any] = Field(..., description="文档 2 中的位置信息（页码、行号等）")
    context1: Dict[str, str] = Field(..., description="文档 1 中序列周围的上下文")
    context2: Dict[str, str] = Field(..., description="文档 2 中序列周围的上下文")
    differences: List[str] = Field(..., description="两个序列之间的差异列表")


class SimilarityStatistics(BaseModel):
    """
    相似度统计信息模型

    提供文档比对的整体统计指标，帮助快速了解相似度分布情况。

    属性说明：
        total_sequences_analyzed (int): 分析的总序列数
                                      从两个文档中提取并比对的序列总数
                                      用于评估比对规模

        similar_sequences_found (int): 发现的相似序列数
                                      相似度超过阈值的序列数量
                                      这是比对结果的核心指标

        high_similarity_count (int): 高相似度序列数量（相似度 > 0.9）
                                    表示几乎完全相同的内容
                                    可能存在抄袭或复制

        medium_similarity_count (int): 中等相似度序列数量（相似度 0.8-0.9）
                                      表示高度相似但有改写
                                      可能存在改写或借鉴

        low_similarity_count (int): 低相似度序列数量（相似度 0.75-0.8）
                                   表示部分相似
                                   可能是巧合或常见表达

        average_similarity (float): 平均相似度（范围：0.0-1.0）
                                   所有相似序列的平均相似度
                                   用于整体评估文档相似程度

        max_similarity (float): 最高相似度（范围：0.0-1.0）
                               所有相似序列中的最高相似度值
                               表示最相似的部分

        min_similarity (float): 最低相似度（范围：0.0-1.0）
                               所有相似序列中的最低相似度值
                               表示刚好达到阈值的相似度
    """
    total_sequences_analyzed: int = Field(..., description="分析的总序列数", alias="totalSequencesAnalyzed")
    similar_sequences_found: int = Field(..., description="发现的相似序列数量", alias="similarSequencesFound")
    high_similarity_count: int = Field(..., description="高相似度序列数量（>0.9）", alias="highSimilarityCount")
    medium_similarity_count: int = Field(..., description="中等相似度序列数量（0.8-0.9）", alias="mediumSimilarityCount")
    low_similarity_count: int = Field(..., description="低相似度序列数量（0.75-0.8）", alias="lowSimilarityCount")
    average_similarity: float = Field(..., ge=0.0, le=1.0, description="平均相似度", alias="averageSimilarity")
    max_similarity: float = Field(..., ge=0.0, le=1.0, description="最高相似度", alias="maxSimilarity")
    min_similarity: float = Field(..., ge=0.0, le=1.0, description="最低相似度", alias="minSimilarity")

    class Config:
        populate_by_name = True


class FileStatistics(BaseModel):
    """
    文件处理统计信息模型

    提供单个文档的详细处理统计，包括文件大小、页数、内容提取情况等。

    属性说明：
        file_path (str): 文件路径
                       被处理的文件路径
                       用于标识具体文档

        file_size_mb (float): 文件大小（MB）
                            用于评估文档规模
                            影响处理时间预估

        total_pages (int): 总页数
                          文档的总页数
                          PDF 文档的页面总数

        total_lines (int): 提取的总行数
                         从文档中提取的文本总行数
                         包括所有内容类型

        main_content_lines (int): 正文内容行数
                                 经过内容过滤后的正文行数
                                 排除了页眉页脚、目录等

        filtered_lines (int): 过滤掉的行数
                             被内容过滤器排除的行数
                             包括参考文献、目录等

        total_chars (int): 总字符数
                          提取的文本总字符数
                          用于评估文档篇幅

        processing_time_seconds (float): 处理时间（秒）
                                        文档提取和处理所用时间
                                        用于性能监控和优化
    """
    file_path: str = Field(..., description="文件路径", alias="filePath")
    file_size_mb: float = Field(..., description="文件大小（MB）", alias="fileSizeMb")
    total_pages: int = Field(..., description="总页数", alias="totalPages")
    total_lines: int = Field(..., description="提取的总行数", alias="totalLines")
    main_content_lines: int = Field(..., description="过滤后的正文行数", alias="mainContentLines")
    filtered_lines: int = Field(..., description="过滤掉的行数", alias="filteredLines")
    total_chars: int = Field(..., description="总字符数", alias="totalChars")
    processing_time_seconds: float = Field(..., description="处理时间（秒）", alias="processingTimeSeconds")

    class Config:
        populate_by_name = True


class SimilarityResult(BaseModel):
    """
    完整相似度检测结果模型

    这是文档比对任务完成后的完整结果，包含所有统计信息和相似序列详情。

    属性说明：
        task_id (str): 任务标识符
                     对应的比对任务 ID
                     用于关联任务和结果

        comparison_info (Dict[str, Any]): 比对配置信息
                                        记录本次比对使用的参数
                                        如相似度阈值、序列长度等

        file1_stats (FileStatistics): 文档 1 的统计信息
                                     包含文件大小、页数、处理时间等

        file2_stats (FileStatistics): 文档 2 的统计信息
                                     包含文件大小、页数、处理时间等

        similarity_stats (SimilarityStatistics): 相似度统计信息
                                               包含整体相似度指标和分布
                                               是结果的概览摘要

        similar_sequences (List[SimilarSequence]): 相似序列列表
                                                 所有检测到的相似序列详情
                                                 按相似度排序

        processing_time_seconds (float): 总处理时间（秒）
                                        整个比对任务的总耗时
                                        包括文档提取和相似度计算

        export_files (Dict[str, str]): 导出文件路径
                                      根据请求的导出格式生成的文件
                                      键为格式类型，值为文件路径
                                      示例：{"text": "/results/report.txt"}
    """
    task_id: str = Field(..., description="任务标识符", alias="taskId")
    comparison_info: Dict[str, Any] = Field(..., description="比对配置信息", alias="comparisonInfo")
    file1_stats: FileStatistics = Field(..., description="文档 1 的统计信息", alias="file1Stats")
    file2_stats: FileStatistics = Field(..., description="文档 2 的统计信息", alias="file2Stats")
    similarity_stats: SimilarityStatistics = Field(..., description="相似度统计信息", alias="similarityStats")
    similar_sequences: List[SimilarSequence] = Field(..., description="相似序列列表", alias="similarSequences")
    processing_time_seconds: float = Field(..., description="总处理时间（秒）", alias="processingTimeSeconds")
    export_files: Dict[str, str] = Field(..., description="导出文件路径映射", alias="exportFiles")

    class Config:
        populate_by_name = True


class ExportFile(BaseModel):
    """
    导出文件信息模型

    描述生成的导出文件的详细信息，便于用户下载。

    属性说明：
        format (ExportFormat): 导出格式
                             导出文件使用的格式类型
                             对应 ExportFormat 枚举

        file_path (str): 导出文件路径
                        文件在服务器上的存储位置
                        示例："/exports/result_20250103.txt"

        file_size (int): 文件大小（字节）
                        用于显示文件大小和预估下载时间

        download_url (str): 下载链接
                           用户可以通过此 URL 下载文件
                           示例："/api/v1/download/result_20250103.txt"
    """
    format: ExportFormat = Field(..., description="导出格式")
    file_path: str = Field(..., description="导出文件路径", alias="filePath")
    file_size: int = Field(..., description="文件大小（字节）", alias="fileSize")
    download_url: str = Field(..., description="下载链接", alias="downloadUrl")

    class Config:
        populate_by_name = True


# ============================================================================
# 错误模型 (Error Models)
# ============================================================================

class ErrorDetail(BaseModel):
    """
    错误详情模型

    描述错误的具体信息，帮助用户和开发者理解问题。

    属性说明：
        code (int): 错误代码
                  HTTP 状态码或自定义错误码
                  常见值：
                  - 400: 请求参数错误
                  - 404: 文件未找到
                  - 500: 服务器内部错误

        message (str): 错误消息
                      对错误的用户友好描述
                      示例："文件格式不支持，请上传 PDF 或 Word 文档"

        details (Optional[Dict[str, Any]]): 额外错误详情
                                          提供更多技术细节，用于调试
                                          可能包含堆栈跟踪、字段名等
    """
    code: int = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="额外的错误详情")


class ErrorResponse(BaseModel):
    """
    错误响应模型

    API 错误响应的标准格式，包含错误信息和请求追踪信息。

    属性说明：
        error (ErrorDetail): 错误详情
                           包含错误代码、消息和详细信息

        timestamp (str): 错误时间戳（ISO 8601 格式）
                        记录错误发生的时间
                        用于日志分析和调试

        request_id (Optional[str]): 请求标识符
                                  用于追踪请求的完整生命周期
                                  便于在日志中查找相关问题
                                  格式：UUID 字符串
    """
    error: ErrorDetail = Field(..., description="错误详情")
    timestamp: str = Field(..., description="错误时间戳")
    request_id: Optional[str] = Field(None, description="请求标识符", alias="requestId")

    class Config:
        populate_by_name = True


# ============================================================================
# 健康检查模型 (Health Check Models)
# ============================================================================

class ServiceStatus(BaseModel):
    """
    单个服务状态模型

    描述系统依赖服务的健康状态，如数据库、文件系统等。

    属性说明：
        name (str): 服务名称
                  服务的标识名称
                  示例："database", "file_storage", "document_processor"

        status (str): 服务状态
                     可能值：healthy, unhealthy, degraded
                     - healthy: 服务正常运行
                     - unhealthy: 服务不可用
                     - degraded: 服务可用但性能下降

        last_check (str): 最后检查时间（ISO 8601 格式）
                         上次健康检查的时间
                         用于评估状态的新鲜度

        details (Optional[Dict[str, Any]]): 额外服务详情
                                          包含响应时间、版本等信息
                                          示例：{"response_time_ms": 15, "version": "1.2.3"}
    """
    name: str = Field(..., description="服务名称")
    status: str = Field(..., description="服务状态")
    last_check: str = Field(..., description="最后检查时间", alias="lastCheck")
    details: Optional[Dict[str, Any]] = Field(None, description="额外的服务详情")

    class Config:
        populate_by_name = True


class HealthCheckResponse(BaseModel):
    """
    健康检查响应模型

    提供系统整体健康状态的概览，用于监控和运维。

    属性说明：
        status (str): 整体健康状态
                     可能值：healthy, unhealthy, degraded
                     基于所有依赖服务的状态综合判断

        timestamp (str): 检查时间戳（ISO 8601 格式）
                        执行健康检查的时间

        services (Dict[str, Any]): 服务状态字典
                                  包含所有依赖服务的状态信息
                                  键为服务名，值为状态详情
                                  示例：{"database": {...}, "storage": {...}}

        uptime_seconds (float): 服务运行时长（秒）
                              服务自启动以来的运行时间
                              用于计算服务可用性

        version (str): API 版本
                      当前部署的 API 版本号
                      格式：语义化版本号（如 "1.0.0"）
    """
    status: str = Field(..., description="整体健康状态")
    timestamp: str = Field(..., description="检查时间戳")
    services: Dict[str, Any] = Field(..., description="服务状态字典")
    uptime_seconds: float = Field(..., description="服务运行时长（秒）", alias="uptimeSeconds")
    version: str = Field(..., description="API 版本")

    class Config:
        populate_by_name = True


# ============================================================================
# WebSocket 模型 (WebSocket Models)
# ============================================================================

class WebSocketMessage(BaseModel):
    """
    WebSocket 消息模型

    WebSocket 通信的通用消息格式，用于实时推送任务更新。

    属性说明：
        type (str): 消息类型
                  标识消息的用途和内容格式
                  示例：progress, error, complete

        task_id (Optional[str]): 任务标识符
                               关联的任务 ID
                               用于将消息关联到具体任务

        data (Dict[str, Any]): 消息数据
                              根据消息类型包含不同数据
                              示例：{"progress": 0.5, "message": "处理中..."}

        timestamp (str): 消息时间戳（ISO 8601 格式）
                        消息发送的时间
                        用于排序和调试
    """
    type: str = Field(..., description="消息类型")
    task_id: Optional[str] = Field(None, description="任务标识符", alias="taskId")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: str = Field(..., description="消息时间戳")

    class Config:
        populate_by_name = True


class ProgressUpdate(BaseModel):
    """
    进度更新消息模型

    通过 WebSocket 实时推送任务进度更新的专用消息格式。

    属性说明：
        progress (float): 进度（范围：0.0-1.0）
                        0.0 表示刚开始，1.0 表示已完成
                        用于显示进度条和百分比
                        示例：0.65（表示 65% 完成）

        message (str): 进度消息
                      描述当前正在执行的操作
                      示例："正在提取文档文本..."

        current_step (str): 当前处理步骤
                           标识当前处于哪个处理阶段
                           示例："extracting_content", "calculating_similarity"

        estimated_remaining_seconds (Optional[int]): 预计剩余时间（秒）
                                                    基于当前进度预估的剩余时间
                                                    用于显示 ETA
                                                    示例：120（约 2 分钟）

        details (Optional[Dict[str, Any]]): 额外进度详情
                                          提供更多进度相关的信息
                                          示例：{"processed_pages": 50, "total_pages": 100}
    """
    progress: float = Field(..., ge=0.0, le=1.0, description="进度，范围 0.0-1.0")
    message: str = Field(..., description="进度说明消息")
    current_step: str = Field(..., description="当前处理步骤", alias="currentStep")
    estimated_remaining_seconds: Optional[int] = Field(None, description="预计剩余时间（秒）", alias="estimatedRemainingSeconds")
    details: Optional[Dict[str, Any]] = Field(None, description="额外的进度详情")

    class Config:
        populate_by_name = True
