#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 相似度检测服务 - 文件工具模块

本模块提供文件操作的实用工具函数，主要功能包括：
1. 文件上传和保存（支持异步IO）
2. 文件清理和删除
3. 文件信息获取
4. 文件名安全处理
5. PDF文件验证

设计特点：
- 使用异步IO提升性能
- 完善的错误处理和日志记录
- 文件大小和类型验证
- 自动生成唯一文件名避免冲突
"""

# 标准库导入
import os  # 操作系统接口，用于文件路径操作
import uuid  # UUID生成，用于创建唯一文件名
import shutil  # 高级文件操作
import aiofiles  # 异步文件操作库
from pathlib import Path  # 面向对象的文件系统路径操作
from typing import List, Optional  # 类型注解支持
from fastapi import UploadFile  # FastAPI的文件上传类型
import logging  # 日志记录

# 模块日志记录器
logger = logging.getLogger(__name__)


async def save_upload_file(
    upload_file: UploadFile,
    upload_dir: str = "uploads",
    max_size: int = 100 * 1024 * 1024  # 100MB
) -> str:
    """
    保存上传的文件到磁盘（异步函数）

    这是文件上传的核心函数，处理从FastAPI接收的文件对象：
    1. 创建上传目录（如果不存在）
    2. 验证文件类型（只允许PDF和DOCX）
    3. 生成唯一文件名（使用UUID）
    4. 分块读取和写入文件，同时监控文件大小
    5. 超过大小限制时自动清理

    Args:
        upload_file: FastAPI的UploadFile对象，包含文件内容和元数据
        upload_dir: 上传目录路径，默认为"uploads"
        max_size: 最大允许的文件大小（字节），默认为100MB

    Returns:
        str: 保存文件的绝对路径

    Raises:
        ValueError: 当文件类型不支持或文件大小超过限制时抛出
        IOError: 当文件保存失败时抛出

    Note:
        - 使用异步IO避免阻塞事件循环
        - 文件大小限制在上传过程中实时检查，避免写入超大文件
        - 生成唯一的UUID文件名避免文件名冲突
        - 返回绝对路径确保后续操作能正确找到文件
    """
    try:
        # 创建上传目录（如果不存在）
        # 使用resolve()获取绝对路径，避免相对路径导致的问题
        upload_path = Path(upload_dir).resolve()
        upload_path.mkdir(parents=True, exist_ok=True)

        # 验证并获取文件扩展名
        file_extension = Path(upload_file.filename).suffix.lower()
        # 只允许PDF和Word文档格式
        if file_extension not in ['.pdf', '.docx']:
            raise ValueError("Only PDF and Word (DOCX) files are allowed")

        # 生成唯一文件名（UUID + 原始扩展名）
        # UUID确保即使同时上传同名文件也不会冲突
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_path / unique_filename

        # 分块读取和写入文件，同时监控文件大小
        file_size = 0  # 累计已写入的字节数
        # 使用aiofiles进行异步文件操作
        async with aiofiles.open(file_path, 'wb') as f:
            # 每次读取8KB的块
            while chunk := await upload_file.read(8192):
                file_size += len(chunk)
                # 实时检查文件大小，超过限制立即停止
                if file_size > max_size:
                    # 关闭文件
                    await f.close()
                    # 删除部分写入的文件（missing_ok=True避免文件不存在时报错）
                    file_path.unlink(missing_ok=True)
                    # 抛出异常，说明文件过大
                    raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
                # 写入文件块
                await f.write(chunk)

        # 记录成功保存的日志
        logger.info(f"Saved uploaded file: {file_path} ({file_size} bytes)")
        # 返回绝对路径，确保后续操作能正确找到文件
        return str(file_path.resolve())

    except ValueError:
        # ValueError是我们主动抛出的（类型错误或大小超限），直接重新抛出
        raise
    except Exception as e:
        # 捕获其他所有异常，记录错误日志后包装为IOError抛出
        logger.error(f"Error saving upload file: {str(e)}")
        raise IOError(f"Failed to save file: {str(e)}")


async def cleanup_files(file_paths: List[str]) -> None:
    """
    清理临时文件（异步函数）

    批量删除指定的文件列表，用于清理处理过程中产生的临时文件。
    即使某个文件删除失败，也会继续尝试删除其他文件。

    Args:
        file_paths: 需要删除的文件路径列表

    Note:
        - 文件不存在时不会报错（静默跳过）
        - 删除失败的文件会记录警告日志但不会中断流程
        - 使用异步操作提升性能
    """
    # 遍历所有需要删除的文件路径
    for file_path in file_paths:
        try:
            # 检查文件是否存在
            if os.path.exists(file_path):
                # 删除文件
                os.remove(file_path)
                # 记录调试日志
                logger.debug(f"Deleted file: {file_path}")
        except Exception as e:
            # 删除失败时记录警告日志，但继续处理其他文件
            logger.warning(f"Failed to delete file {file_path}: {str(e)}")


def get_file_info(file_path: str) -> dict:
    """
    获取文件的详细信息

    提取文件的各种元数据信息，包括大小、创建时间、修改时间等

    Args:
        file_path: 文件路径

    Returns:
        dict: 包含文件信息的字典，包含以下字段：
            - path: 文件完整路径
            - name: 文件名（不含路径）
            - size: 文件大小（字节）
            - size_mb: 文件大小（MB）
            - created_at: 创建时间戳
            - modified_at: 修改时间戳

    Raises:
        FileNotFoundError: 当文件不存在时抛出

    Examples:
        >>> info = get_file_info("/path/to/file.pdf")
        >>> print(info['size_mb'])
        2.45
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 获取文件状态信息
    stat = os.stat(file_path)

    # 构建并返回文件信息字典
    return {
        "path": file_path,
        "name": Path(file_path).name,  # 只取文件名部分
        "size": stat.st_size,  # 文件大小（字节）
        "size_mb": round(stat.st_size / (1024 * 1024), 2),  # 文件大小（MB，保留2位小数）
        "created_at": stat.st_ctime,  # 创建时间（Unix时间戳）
        "modified_at": stat.st_mtime  # 修改时间（Unix时间戳）
    }


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建

    这是一个便捷函数，用于在写入文件前确保目标目录存在

    Args:
        directory: 目录路径

    Note:
        - 如果目录已存在，不会报错
        - parents=True表示会创建所有必需的父目录
        - exist_ok=True表示目录已存在时不报错
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名

    移除或替换文件名中可能导致问题的字符，确保文件名在文件系统中是安全的

    Args:
        filename: 原始文件名

    Returns:
        str: 处理后的安全文件名

    Note:
        - 替换的字符包括：路径分隔符、通配符、引号、控制字符等
        - 移除首尾的空格和点（避免隐藏文件问题）
        - 如果处理结果为空字符串，返回默认文件名"unnamed_file"

    Examples:
        >>> safe_filename("my/file:name.pdf")
        'my_file_name.pdf'
        >>> safe_filename("  ..test..  ")
        'test'
    """
    # 定义需要替换的字符映射
    # 这些字符在文件名中可能引起问题：路径分隔符、通配符、特殊字符等
    replacements = {
        '/': '_',   # Unix路径分隔符
        '\\': '_',  # Windows路径分隔符
        ':': '_',   # Windows驱动器分隔符
        '*': '_',   # 通配符
        '?': '_',   # 通配符
        '"': "'",   # 双引号改为单引号
        '<': '_',   # 重定向符
        '>': '_',   # 重定向符
        '|': '_',   # 管道符
        '\n': '',   # 换行符（删除）
        '\r': ''    # 回车符（删除）
    }

    # 遍历替换规则，逐个处理
    for old, new in replacements.items():
        filename = filename.replace(old, new)

    # 移除首尾的空格和点
    # 首尾的点可能导致文件被识别为隐藏文件或特殊文件
    filename = filename.strip('. ')

    # 确保文件名不为空（如果原文件名只包含特殊字符）
    if not filename:
        filename = "unnamed_file"

    return filename


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写）

    提取文件名中的扩展名部分，并转换为小写

    Args:
        filename: 文件名

    Returns:
        str: 文件扩展名（包含点号），如 ".pdf"，如果没有扩展名返回空字符串

    Examples:
        >>> get_file_extension("document.PDF")
        '.pdf'
        >>> get_file_extension("archive.tar.gz")
        '.gz'
        >>> get_file_extension("filename")
        ''
    """
    # Path.suffix会自动提取最后一个点之后的部分
    return Path(filename).suffix.lower()


def is_valid_pdf(file_path: str) -> bool:
    """
    检查文件是否为有效的PDF

    尝试打开和解析PDF文件，验证其是否为有效的PDF格式

    Args:
        file_path: PDF文件路径

    Returns:
        bool: 如果是有效的PDF返回True，否则返回False

    Note:
        - 使用PyPDF2库进行验证
        - 尝试读取第一页的文本作为基本验证
        - 验证失败时会记录警告日志
        - 不会抛出异常，所有错误都返回False

    Examples:
        >>> is_valid_pdf("/path/to/file.pdf")
        True
        >>> is_valid_pdf("/path/to/corrupted.pdf")
        False
    """
    try:
        # 导入PyPDF2库
        import PyPDF2

        # 以二进制模式打开文件
        with open(file_path, 'rb') as f:
            # 创建PDF阅读器对象
            reader = PyPDF2.PdfReader(f)

            # 尝试读取第一页的内容作为基本验证
            # 如果PDF文件损坏，这里会抛出异常
            if len(reader.pages) > 0:
                reader.pages[0].extract_text()

            # 没有抛出异常，说明PDF是有效的
            return True

    except Exception as e:
        # 捕获所有异常（文件损坏、权限问题、不是PDF等）
        logger.warning(f"Invalid PDF file {file_path}: {str(e)}")
        return False
