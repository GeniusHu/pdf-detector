#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档相似度检测 Web 后端服务
===================================

这是一个基于 FastAPI 的文档相似度检测 Web 应用后端服务。
主要功能：
1. 接收 PDF 和 Word (.docx) 文档的上传
2. 使用异步任务处理文档相似度检测
3. 提供基于轮询的任务状态查询机制
4. 支持多种导出格式的检测结果

技术特性：
- 使用异步任务处理长时间运行的文档比较操作
- 通过轮询机制向前端报告任务进度
- 支持跨域请求（CORS）
- 提供静态文件服务（上传的文档和导出的结果）
- 完整的错误处理和日志记录
"""

# ==================== 标准库导入 ====================
from contextlib import asynccontextmanager  # 用于管理应用程序生命周期上下文
import asyncio  # 异步编程支持，用于后台任务处理
import uuid  # 用于生成唯一的任务 ID
import json  # JSON 数据处理（虽然当前未使用，但保留备用）
import os  # 操作系统接口，用于文件路径操作和文件检查
from pathlib import Path  # 面向对象的文件系统路径操作
from typing import Dict, Optional  # 类型注解支持
import logging  # 日志记录
from datetime import datetime  # 日期时间处理

# ==================== FastAPI 核心导入 ====================
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
# FastAPI: 核心框架类
# File: 用于处理文件上传参数
# UploadFile: 上传文件的类型定义
# HTTPException: HTTP 异常处理
# BackgroundTasks: 后台任务支持（当前版本使用 asyncio.create_task 替代）
# Depends: 依赖注入装饰器

from fastapi.responses import JSONResponse  # JSON 响应处理
from fastapi.middleware.cors import CORSMiddleware  # 跨域资源共享中间件
from fastapi.staticfiles import StaticFiles  # 静态文件服务支持

# ==================== 自定义模块导入 ====================
from models.api_models import (
    ComparisonRequest, ComparisonResponse,
    TaskStatusResponse, ErrorResponse
)
# API 数据模型定义：
# - ComparisonRequest: 文档比较请求模型
# - ComparisonResponse: 文档比较响应模型
# - TaskStatusResponse: 任务状态查询响应模型
# - ErrorResponse: 错误响应模型

from utils.logger import setup_logger  # 日志配置工具
from utils.file_utils import save_upload_file, cleanup_files
# 文件工具函数：
# - save_upload_file: 保存上传的文件
# - cleanup_files: 清理临时文件

# ==================== 日志配置 ====================
# 初始化日志记录器，用于记录应用程序运行时的各种信息
logger = setup_logger(__name__)

# ==================== 全局状态管理 ====================
# 活跃任务字典：存储所有正在运行或已完成的任务信息
# 键：task_id (任务唯一标识符)
# 值：任务信息字典，包含状态、进度、结果等
active_tasks: Dict[str, Dict] = {}

# 应用程序启动时间：用于计算服务运行时长（uptime）
app_start_time = datetime.utcnow()

# 服务实例（将在 lifespan 函数中初始化）
# 使用延迟初始化模式，避免在模块导入时就创建服务实例
document_service_instance = None  # 文档处理服务实例
similarity_service_instance = None  # 相似度检测服务实例

# ==================== 依赖注入函数 ====================
def get_document_service():
    """
    获取文档服务实例的依赖注入函数

    Returns:
        DocumentService: 文档处理服务实例
    """
    return document_service_instance

def get_similarity_service():
    """
    获取相似度检测服务实例的依赖注入函数

    Returns:
        SimilarityService: 相似度检测服务实例
    """
    return similarity_service_instance

# ==================== 应用程序生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器

    这个异步上下文管理器负责应用程序的启动和关闭操作。
    FastAPI 会在应用程序启动时调用这个函数，在应用程序关闭时进行清理。

    Args:
        app: FastAPI 应用实例

    Yields:
        None: 在应用程序运行期间保持活动状态
    """
    global document_service_instance, similarity_service_instance
    # 使用 global 关键字修改全局变量

    logger.info("Starting Document Similarity Detection Service...")
    logger.info("正在启动文档相似度检测服务...")

    # ==================== 服务初始化 ====================
    # 导入并初始化服务模块
    # 注意：放在这里导入可以避免循环依赖问题
    from services.document_service import DocumentService  # 文档处理服务
    from services.similarity_service import SimilarityService  # 相似度检测服务

    # 创建服务实例
    document_service_instance = DocumentService()
    similarity_service_instance = SimilarityService()

    logger.info("Services initialized successfully")
    logger.info("服务初始化成功")

    # ==================== 应用程序运行阶段 ====================
    # yield 之前是启动代码，yield 之后是关闭代码
    # 在 yield 期间，应用程序正常运行并处理请求
    yield

    # ==================== 应用程序关闭清理 ====================
    logger.info("Shutting down Document Similarity Detection Service...")
    logger.info("正在关闭文档相似度检测服务...")

    # 清理所有正在运行的任务
    # 遍历所有活跃任务，取消未完成的任务
    for task_id, task_info in active_tasks.items():
        if not task_info.get('completed', True):
            # 如果任务未完成，取消任务
            task_info['task'].cancel()
            logger.info(f"任务 {task_id} 已取消")

    logger.info("Shutdown complete")
    logger.info("关闭完成")

# ==================== FastAPI 应用初始化 ====================
# 创建 FastAPI 应用实例
app = FastAPI(
    title="Document Similarity Detection API",  # API 标题
    description="AI-powered PDF and Word document similarity detection",  # API 描述
    version="2.0.0",  # API 版本号
    lifespan=lifespan  # 应用程序生命周期管理器
)

# ==================== 请求日志中间件 ====================
@app.middleware("http")
async def log_requests(request, call_next):
    """
    HTTP 请求日志中间件

    记录所有传入的 HTTP 请求和响应，包括：
    - 请求方法和路径
    - 响应状态码
    - 请求处理时间（毫秒）

    Args:
        request: 传入的 HTTP 请求对象
        call_next: 下一个中间件或路由处理函数

    Returns:
        Response: HTTP 响应对象
    """
    import time  # 导入时间模块用于计算请求处理时间
    start_time = time.time()  # 记录请求开始时间

    # 记录请求信息
    logger.info(f"[REQUEST] {request.method} {request.url.path}")

    # 调用下一个中间件或路由处理器
    response = await call_next(request)

    # 计算请求处理时间（转换为毫秒）
    process_time = (time.time() - start_time) * 1000
    # 记录响应信息，包括状态码和处理时间
    logger.info(f"[RESPONSE] {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")

    return response  # 返回响应对象

# ==================== CORS 跨域配置 ====================
# 跨域资源共享（CORS）中间件配置
# 注意：当使用通配符 origin 时，allow_credentials 必须为 False
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境配置）- 生产环境应指定具体域名
    allow_credentials=False,  # 使用通配符 origin 时必须为 False
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET, POST, PUT, DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 允许客户端访问所有响应头
)

# ==================== 静态文件服务配置 ====================
# 挂载静态文件目录，提供文件访问服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# /uploads: 上传的文档文件访问路径

app.mount("/exports", StaticFiles(directory="exports"), name="exports")
# /exports: 导出的结果文件访问路径（HTML、Excel 等）

# ==================== API 路由定义 ====================

@app.get("/")
async def root():
    """
    根路径路由处理函数

    提供 API 基本信息，包括：
    - API 名称
    - 当前版本
    - 支持的文档格式
    - 服务状态
    - 当前时间戳

    Returns:
        dict: 包含 API 信息的字典
    """
    return {
        "message": "Document Similarity Detection API",  # API 名称
        "version": "2.0.0",  # 当前版本号
        "supportedFormats": ["pdf", "docx"],  # 支持的文档格式列表
        "status": "running",  # 服务运行状态
        "timestamp": datetime.utcnow().isoformat()  # 当前 UTC 时间（ISO 8601 格式）
    }

@app.get("/health")
async def health_check():
    """
    健康检查路由处理函数

    用于监控服务健康状态，返回：
    - 整体服务状态
    - 各子服务状态
    - 服务运行时长（秒）
    - 最后检查时间

    注意：使用驼峰命名法（camelCase）以匹配前端预期

    Returns:
        dict: 包含健康状态信息的字典
    """
    now = datetime.utcnow()  # 获取当前 UTC 时间
    # 计算服务运行时长（秒）
    uptime_seconds = (now - app_start_time).total_seconds()

    return {
        "status": "healthy",  # 整体服务状态
        "timestamp": now.isoformat(),  # 检查时间
        "services": {  # 各子服务状态
            "document_processor": {
                "name": "Document Processor",  # 服务名称
                "status": "operational",  # 运行状态
                "lastCheck": now.isoformat()  # 最后检查时间
            },
            "similarity_detector": {
                "name": "Similarity Detector",  # 服务名称
                "status": "operational",  # 运行状态
                "lastCheck": now.isoformat()  # 最后检查时间
            }
        },
        "uptimeSeconds": uptime_seconds,  # 服务运行时长（秒）
        "version": "2.0.0"  # API 版本
    }

@app.post("/api/v1/compare")
async def compare_documents(
    request: ComparisonRequest,
    document_service = Depends(get_document_service),
    similarity_service = Depends(get_similarity_service)
):
    """
    文档比较路由处理函数

    启动文档相似度比较任务，支持以下功能：
    - 内容过滤（仅主文本 vs 完整内容）
    - 相似度阈值调整
    - 处理速度选项（快速/标准）
    - 页面范围选择
    - 导出格式选择（HTML/Excel）

    工作流程：
    1. 生成唯一的任务 ID
    2. 验证输入文件路径
    3. 初始化任务状态
    4. 创建后台异步任务执行比较
    5. 立即返回任务 ID 给客户端

    Args:
        request: 文档比较请求对象（ComparisonRequest）
        document_service: 文档处理服务（通过依赖注入获取）
        similarity_service: 相似度检测服务（通过依赖注入获取）

    Returns:
        dict: 包含任务 ID 和初始状态的信息

    Raises:
        HTTPException: 当文件不存在或发生服务器错误时抛出
    """
    # 记录请求开始日志
    logger.info(f"[COMPARE] ========== REQUEST RECEIVED ==========")
    logger.info(f"[COMPARE] Received compare request: doc1={request.pdf1_path}, doc2={request.pdf2_path}")
    logger.info(f"[COMPARE] Page ranges: range1={request.page_range1}, range2={request.page_range2}")

    try:
        # ==================== 生成任务 ID ====================
        # 使用 UUID4 生成全局唯一标识符
        task_id = str(uuid.uuid4())

        # ==================== 输入验证 ====================
        # 检查是否提供了两个文档路径
        if not request.pdf1_path or not request.pdf2_path:
            logger.warning("[COMPARE] Missing file paths")
            raise HTTPException(status_code=400, detail="Both document file paths are required")

        # 记录详细的文件路径信息用于调试
        logger.info(f"[COMPARE] Checking file paths:")
        logger.info(f"[COMPARE]   pdf1_path: {request.pdf1_path}")
        logger.info(f"[COMPARE]   pdf2_path: {request.pdf2_path}")
        logger.info(f"[COMPARE]   doc1 exists: {os.path.exists(request.pdf1_path)}")
        logger.info(f"[COMPARE]   doc2 exists: {os.path.exists(request.pdf2_path)}")
        logger.info(f"[COMPARE]   Current working directory: {os.getcwd()}")

        # 验证文件是否存在
        if not os.path.exists(request.pdf1_path) or not os.path.exists(request.pdf2_path):
            logger.warning(f"[COMPARE] Files not found: doc1 exists={os.path.exists(request.pdf1_path)}, doc2 exists={os.path.exists(request.pdf2_path)}")
            raise HTTPException(status_code=404, detail="One or both document files not found")

        # ==================== 初始化任务状态 ====================
        # 在全局任务字典中创建任务记录
        active_tasks[task_id] = {
            "taskId": task_id,  # 任务唯一标识符
            "status": "pending",  # 初始状态：等待中
            "progress": 0,  # 初始进度：0%
            "startedAt": datetime.utcnow().isoformat(),  # 任务开始时间
            "completedAt": None,  # 任务完成时间（初始为 None）
            "completed": False,  # 是否完成（初始为 False）
            "result": None,  # 任务结果（初始为 None）
            "error": None,  # 错误信息（初始为 None）
            "message": "Task initialized"  # 初始消息
        }

        # ==================== 创建后台任务 ====================
        # 使用 asyncio.create_task 创建异步后台任务
        # 这样可以立即返回响应，而不等待比较完成
        task = asyncio.create_task(
            process_document_comparison(
                task_id, request, document_service, similarity_service
            )
        )
        # 将任务对象存储到任务信息中，用于后续取消或查询
        active_tasks[task_id]["task"] = task

        logger.info(f"[COMPARE] Task created: {task_id}")
        logger.info(f"[COMPARE] Sending response...")

        # ==================== 构造响应 ====================
        response_data = {
            "taskId": task_id,  # 返回任务 ID 供客户端查询状态
            "status": "pending",  # 当前状态
            "message": "Comparison task started successfully"  # 提示消息
        }
        logger.info(f"[COMPARE] Response data: {response_data}")

        return response_data  # 立即返回响应，任务在后台执行

    except HTTPException:
        # 如果是 HTTP 异常，直接抛出（保持原有的 HTTP 状态码）
        raise
    except Exception as e:
        # 捕获所有其他异常并记录日志
        logger.error(f"[COMPARE] Error starting document comparison: {str(e)}", exc_info=True)
        # 返回 500 内部服务器错误
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    文档上传路由处理函数

    接收 PDF 或 Word (.docx) 文档的上传，保存到服务器。

    工作流程：
    1. 验证文件类型（只允许 pdf 和 docx）
    2. 保存文件到上传目录
    3. 返回文件信息（路径、大小、类型等）

    注意：使用驼峰命名法（camelCase）以匹配前端预期

    Args:
        file: 上传的文件对象（UploadFile）

    Returns:
        dict: 包含文件名、路径、大小、类型和上传时间的字典

    Raises:
        HTTPException: 当文件类型不支持或上传失败时抛出
    """
    logger.info(f"[UPLOAD] Received upload request: filename={file.filename}")

    try:
        # ==================== 文件类型验证 ====================
        # 提取文件扩展名并转换为小写
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        # 检查文件类型是否支持
        if file_ext not in ['pdf', 'docx']:
            logger.warning(f"[UPLOAD] Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF and Word (DOCX) files are allowed"
            )

        # ==================== 保存文件 ====================
        # 调用工具函数保存上传的文件
        file_path = await save_upload_file(file)

        # ==================== 获取文件信息 ====================
        # 获取文件大小（字节）
        file_size = os.path.getsize(file_path)

        # 确定文件类型标识
        file_type = "pdf" if file_ext == 'pdf' else "docx"

        logger.info(f"[UPLOAD] File saved successfully: {file_path} ({file_size} bytes, type={file_type})")

        # ==================== 返回文件信息 ====================
        return {
            "filename": file.filename,  # 原始文件名
            "filePath": file_path,  # 服务器上的文件路径
            "fileSize": file_size,  # 文件大小（字节）
            "fileType": file_type,  # 文件类型标识
            "uploadedAt": datetime.utcnow().isoformat()  # 上传时间
        }

    except HTTPException:
        # 如果是 HTTP 异常，直接抛出
        raise
    except Exception as e:
        # 捕获所有其他异常并记录日志
        logger.error(f"[UPLOAD] Error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/api/v1/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    任务状态查询路由处理函数

    查询指定任务的执行状态和进度信息。

    返回的信息包括：
    - 任务 ID
    - 当前状态（pending/processing/completed/error）
    - 进度百分比（0-100）
    - 开始时间和完成时间
    - 错误信息（如果有）
    - 当前状态消息

    Args:
        task_id: 任务唯一标识符

    Returns:
        dict: 包含任务状态信息的字典

    Raises:
        HTTPException: 当任务不存在时抛出 404 错误
    """
    logger.info(f"[STATUS] Checking status for task: {task_id}")

    # 检查任务是否存在
    if task_id not in active_tasks:
        logger.warning(f"[STATUS] Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    # 获取任务信息
    task_info = active_tasks[task_id]
    logger.info(f"[STATUS] Task {task_id}: status={task_info.get('status')}, progress={task_info.get('progress')}")

    # 返回任务状态信息
    return {
        "taskId": task_info.get("taskId", task_id),  # 任务 ID
        "status": task_info.get("status", "unknown"),  # 当前状态
        "progress": task_info.get("progress", 0),  # 进度百分比
        "startedAt": task_info.get("startedAt", ""),  # 开始时间
        "completedAt": task_info.get("completedAt"),  # 完成时间（可能为 None）
        "error": task_info.get("error"),  # 错误信息（可能为 None）
        "message": task_info.get("message", "")  # 状态消息
    }

@app.get("/api/v1/task/{task_id}/result")
async def get_task_result(task_id: str):
    """
    任务结果查询路由处理函数

    获取已完成任务的比较结果。

    返回的数据包括：
    - 相似序列列表
    - 总体相似度统计
    - 导出文件信息（HTML、Excel 等）
    - 文档元数据

    Args:
        task_id: 任务唯一标识符

    Returns:
        dict: 包含相似度比较结果的字典

    Raises:
        HTTPException: 当任务不存在或任务未完成时抛出
    """
    logger.info(f"[RESULT] Getting result for task: {task_id}")

    # 检查任务是否存在
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    # 获取任务信息
    task_info = active_tasks[task_id]

    # 验证任务是否已完成
    if task_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current status: {task_info.get('status')}"
        )

    # ==================== 提取结果数据 ====================
    # 从嵌套结构中提取相似度结果
    result_data = task_info.get("result", {})
    similarity_result = result_data.get("similarity_result", {})
    export_files = result_data.get("export_files", {})

    # 记录调试信息
    logger.info(f"[RESULT] similarSequences type: {type(similarity_result.get('similarSequences'))}")
    logger.info(f"[RESULT] similarSequences length: {len(similarity_result.get('similarSequences', []))}")
    logger.info(f"[RESULT] Keys in similarity_result: {list(similarity_result.keys())}")

    # 将导出文件信息合并到相似度结果中
    similarity_result["exportFiles"] = export_files

    return similarity_result  # 返回完整的比较结果

@app.delete("/api/v1/task/{task_id}")
async def delete_task(task_id: str):
    """
    任务删除路由处理函数

    删除指定任务及其关联的文件。

    操作包括：
    1. 如果任务正在运行，取消任务
    2. 清理任务产生的临时文件
    3. 从活跃任务列表中移除

    Args:
        task_id: 任务唯一标识符

    Returns:
        dict: 包含操作结果的字典

    Raises:
        HTTPException: 当任务不存在时抛出 404 错误
    """
    # 检查任务是否存在
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    # 获取任务信息
    task_info = active_tasks[task_id]

    # ==================== 取消运行中的任务 ====================
    # 如果任务未完成且存在任务对象，取消任务
    if not task_info.get("completed", False) and task_info.get("task"):
        task_info["task"].cancel()  # 取消异步任务
        logger.info(f"任务 {task_id} 已取消")

    # ==================== 清理关联文件 ====================
    # 如果任务结果存在且包含需要清理的文件列表，进行清理
    if task_info.get("result") and "files_to_cleanup" in task_info["result"]:
        await cleanup_files(task_info["result"]["files_to_cleanup"])
        logger.info(f"任务 {task_id} 的关联文件已清理")

    # ==================== 从活跃任务中移除 ====================
    del active_tasks[task_id]

    logger.info(f"Deleted task: {task_id}")

    return {"message": "Task deleted successfully"}  # 返回成功消息

# ==================== 后台任务处理函数 ====================

async def process_document_comparison(
    task_id: str,
    request: ComparisonRequest,
    document_service,
    similarity_service
):
    """
    文档比较后台任务处理函数（使用流水线架构）

    通过标准化的流水线执行文档比较，包含7个处理阶段：
    1. 输入验证 - 验证文件路径和参数
    2. 文档提取 - 提取PDF/Word内容
    3. 内容预处理 - 清理和规范化
    4. 序列生成 - 生成N字序列
    5. 相似度检测 - 匹配和计算相似度
    6. 结果后处理 - 统计和格式化
    7. 结果导出 - 生成导出文件

    Args:
        task_id: 任务唯一标识符
        request: 文档比较请求对象
        document_service: 文档处理服务实例
        similarity_service: 相似度检测服务实例
    """
    logger.info(f"[TASK {task_id}] ========== BACKGROUND TASK STARTED ==========")
    logger.info(f"[TASK {task_id}] Request: pdf1={request.pdf1_path}, pdf2={request.pdf2_path}")

    # ==================== 使用流水线架构执行 ====================
    from services.pipeline import create_pipeline

    # 创建流水线实例
    pipeline = create_pipeline(mode="standard")

    # 定义进度回调函数（将流水线进度同步到active_tasks）
    def pipeline_progress_callback(progress: float, message: str = ""):
        """
        流水线进度回调函数

        Args:
            progress: 全局进度（0.0-1.0）
            message: 当前操作消息
        """
        active_tasks[task_id]["progress"] = progress
        if message:
            active_tasks[task_id]["message"] = message
        logger.info(f"[TASK {task_id}] [{progress*100:.1f}%] {message}")

    try:
        # 执行流水线
        result = await pipeline.execute(
            request=request,
            task_id=task_id,
            progress_callback=pipeline_progress_callback,
            document_service=document_service,
            similarity_service=similarity_service
        )

        # ==================== 处理执行结果 ====================
        if result['success']:
            # 任务成功完成
            similarity_result = result.get('result')

            # 在结果中设置任务 ID
            if similarity_result:
                if hasattr(similarity_result, 'task_id'):
                    similarity_result.task_id = task_id
                elif hasattr(similarity_result, 'model_dump'):
                    similarity_result.task_id = task_id

            # 序列化结果对象为字典
            if similarity_result:
                if hasattr(similarity_result, 'model_dump'):
                    # Pydantic v2
                    result_dict = similarity_result.model_dump(by_alias=True)
                elif hasattr(similarity_result, 'dict'):
                    # Pydantic v1
                    result_dict = similarity_result.dict(by_alias=True)
                else:
                    result_dict = similarity_result
            else:
                result_dict = {}

            # 更新任务状态为完成
            active_tasks[task_id]["status"] = "completed"
            active_tasks[task_id]["progress"] = 1.0
            active_tasks[task_id]["completedAt"] = datetime.utcnow().isoformat()
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["message"] = "Comparison completed successfully"

            # 保存任务结果
            active_tasks[task_id]["result"] = {
                "similarity_result": result_dict,
                "export_files": result.get('export_files', {}),
                "stats": result.get('stats', {}),
                "files_to_cleanup": [request.pdf1_path, request.pdf2_path],
            }

            logger.info(f"[TASK {task_id}] Completed successfully in {result.get('processing_time', 0):.2f}s")

        else:
            # 任务失败
            error_msg = result.get('error', 'Unknown error')
            failed_at = result.get('failed_at_stage', 'unknown')

            active_tasks[task_id]["status"] = "error"
            active_tasks[task_id]["error"] = error_msg
            active_tasks[task_id]["message"] = f"Error in {failed_at}: {error_msg}"
            active_tasks[task_id]["completed"] = True

            logger.error(f"[TASK {task_id}] Failed at stage {failed_at}: {error_msg}")

    except Exception as e:
        # ==================== 错误处理 ====================
        # 捕获所有异常并记录
        logger.error(f"[TASK {task_id}] Error processing: {str(e)}", exc_info=True)

        # 更新任务状态为错误
        active_tasks[task_id]["status"] = "error"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["message"] = f"Error: {str(e)}"
        active_tasks[task_id]["completed"] = True

# ==================== 全局异常处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器

    捕获所有未处理的异常，返回统一的错误响应格式。
    这是应用程序的最后一道防线，处理所有未被路由处理器捕获的异常。

    Args:
        request: 导致异常的 HTTP 请求对象
        exc: 抛出的异常对象

    Returns:
        JSONResponse: 标准化的错误响应，包含错误码和消息
    """
    # 记录完整的异常堆栈信息，便于调试
    logger.error(f"[ERROR] Unhandled exception: {str(exc)}", exc_info=True)

    # 返回标准化的错误响应
    # 使用统一的错误格式，避免向客户端暴露敏感的服务器内部信息
    return JSONResponse(
        status_code=500,  # HTTP 500 内部服务器错误
        content={
            "error": {
                "code": 500,  # 错误码
                "message": "Internal server error"  # 错误消息（通用描述）
            }
        }
    )
