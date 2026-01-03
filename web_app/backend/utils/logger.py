#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 相似度检测服务 - 日志配置模块

本模块提供统一的日志配置功能，主要特性：
1. 支持多种日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
2. 同时输出到控制台和文件
3. 自动日志文件轮转，防止单个文件过大
4. 灵活的日志格式配置
5. 线程安全的日志记录

使用场景：
- 开发环境：使用DEBUG级别查看详细信息
- 生产环境：使用INFO或WARNING级别减少日志量
- 故障排查：临时启用DEBUG级别获取详细日志

典型用法：
    >>> logger = setup_logger("my_app", "INFO", "app.log")
    >>> logger.info("Application started")
    >>> logger.error("An error occurred", exc_info=True)
"""

# 标准库导入
import logging  # Python日志模块
import logging.handlers  # 日志处理器（如轮转文件处理器）
import sys  # 系统相关操作
from pathlib import Path  # 文件路径操作
from typing import Optional  # 类型注解


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    设置并配置一个日志记录器

    创建一个功能完善的日志记录器，支持同时输出到控制台和文件。
    文件日志支持自动轮转，防止单个日志文件过大。

    Args:
        name: 日志记录器的名称，通常使用__name__或模块名
        level: 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL），默认为INFO
        log_file: 日志文件路径（可选），如果不指定则只输出到控制台
        max_bytes: 单个日志文件的最大大小（字节），默认为10MB
                  超过此大小后会创建新文件
        backup_count: 保留的备份日志文件数量，默认为5
                     例如：app.log、app.log.1、app.log.2等

    Returns:
        logging.Logger: 配置好的日志记录器对象

    Note:
        - 控制台输出使用简单格式（时间-级别-消息）
        - 文件输出使用详细格式（时间-名称-级别-文件位置-消息）
        - 日志级别设置后会过滤掉低于此级别的日志
        - 多次调用此函数会清除之前的处理器（避免重复输出）

    Examples:
        >>> # 基本用法：只输出到控制台
        >>> logger = setup_logger("my_app")
        >>> logger.info("This will be printed to console")

        >>> # 输出到控制台和文件
        >>> logger = setup_logger("my_app", "DEBUG", "app.log")
        >>> logger.debug("Detailed debug information")

        >>> # 自定义日志文件大小和备份数量
        >>> logger = setup_logger(
        ...     "my_app",
        ...     "INFO",
        ...     "app.log",
        ...     max_bytes=50*1024*1024,  # 50MB
        ...     backup_count=10
        ... )

    Log Levels:
        - DEBUG: 详细的调试信息，通常只在开发时使用
        - INFO: 一般信息，确认程序正常运行
        - WARNING: 警告信息，表示发生了意外但程序可以继续
        - ERROR: 错误信息，表示发生了严重问题
        - CRITICAL: 严重错误，表示程序可能无法继续运行
    """
    # 获取或创建指定名称的日志记录器
    logger = logging.getLogger(name)

    # 设置日志级别
    # getattr用于获取logging模块中的日志级别常量（如logging.INFO）
    # 如果传入的level字符串无效，默认使用INFO级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # 清除现有的处理器
    # 避免重复调用setup_logger时产生重复的日志输出
    logger.handlers.clear()

    # ========== 创建日志格式化器 ==========
    # 格式化器定义了日志消息的显示格式

    # 详细格式：用于文件日志
    # 包含：时间、日志器名称、级别、文件名、行号、消息
    # 格式：2024-01-01 12:00:00 - my_module - INFO - main.py:42 - Something happened
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # 简单格式：用于控制台输出
    # 只包含：时间、级别、消息
    # 格式：2024-01-01 12:00:00 - INFO - Something happened
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # ========== 添加控制台处理器 ==========
    # 将日志输出到标准输出（通常是终端）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)  # 控制台也使用相同的日志级别
    console_handler.setFormatter(simple_formatter)  # 使用简单格式
    logger.addHandler(console_handler)

    # ========== 添加文件处理器（可选）==========
    if log_file:
        # 如果指定了日志文件，创建文件路径对象
        log_path = Path(log_file)

        # 确保日志文件的目录存在
        # parents=True表示创建所有必需的父目录
        # exist_ok=True表示目录已存在时不报错
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建轮转文件处理器
        # RotatingFileHandler会自动管理日志文件大小：
        # - 当文件达到max_bytes时，会重命名为app.log.1
        # - 创建新的app.log文件继续写入
        # - 当备份文件数量超过backup_count时，删除最旧的备份
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,                    # 日志文件路径
            maxBytes=max_bytes,          # 单个文件最大大小
            backupCount=backup_count,    # 保留的备份文件数量
            encoding='utf-8'             # 文件编码
        )
        file_handler.setLevel(numeric_level)  # 文件也使用相同的日志级别
        file_handler.setFormatter(detailed_formatter)  # 使用详细格式
        logger.addHandler(file_handler)

    # 返回配置好的日志记录器
    return logger
