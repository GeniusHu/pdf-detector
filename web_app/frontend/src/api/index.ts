/**
 * API 模块
 *
 * 本模块提供与后端 API 交互的所有功能，包括：
 * - HTTP 请求封装（基于 Axios）
 * - WebSocket 实时通信管理
 * - 文件上传（支持进度回调）
 * - 文档相似度比对任务管理
 * - 错误处理和重试机制
 *
 * @module api
 * @author Document Similarity Detection Team
 * @version 1.0.0
 */

// ============================================================================
// 导入依赖和类型定义
// ============================================================================

/**
 * 导入 Axios HTTP 客户端库及相关类型
 * Axios 是一个基于 Promise 的 HTTP 客户端，用于浏览器和 Node.js
 */
import axios, { AxiosResponse, AxiosError } from 'axios';

/**
 * 导入应用类型定义
 * 包含所有 API 请求和响应的数据结构
 */
import {
  ComparisonRequest,    // 比对请求参数类型
  TaskStatus,           // 任务状态类型
  SimilarityResult,     // 相似度分析结果类型
  HealthStatus,         // 健康检查状态类型
  ApiResponse,          // 通用 API 响应类型
  ExportFormat,         // 导出格式枚举
  ProcessingMode,       // 处理模式枚举
  ContentFilter,        // 内容过滤器枚举
  ExportFile,           // 导出文件信息类型
} from '@/types';

// ============================================================================
// API 配置常量
// ============================================================================

/**
 * API 基础 URL
 * 优先从环境变量读取，否则使用默认值（本地开发服务器）
 * 通过 NEXT_PUBLIC_ 前缀的变量可在客户端代码中访问
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * WebSocket 基础 URL
 * 用于建立实时双向通信连接
 * 使用 ws:// 或 wss:// 协议（非加密/加密）
 */
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// ============================================================================
// Axios 实例创建和配置
// ============================================================================

/**
 * 创建预配置的 Axios 实例
 *
 * 配置说明：
 * - baseURL: 所有请求的基础 URL
 * - timeout: 30秒超时（适用于大型文件上传和处理）
 * - headers: 默认 Content-Type 为 JSON
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 秒超时，适合处理大文件
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// 请求拦截器
// ============================================================================

/**
 * 请求拦截器
 *
 * 在每个请求发送前自动添加认证令牌（如果存在）
 *
 * 功能：
 * - 从 localStorage 读取认证令牌
 * - 将令牌添加到请求头的 Authorization 字段
 * - 格式：Bearer <token>
 *
 * @param config - Axios 请求配置对象
 * @returns 修改后的请求配置
 */
api.interceptors.request.use(
  (config) => {
    // 尝试从本地存储获取认证令牌
    const token = localStorage.getItem('auth_token');
    if (token) {
      // 如果存在令牌，添加到请求头
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // 请求配置错误处理
    return Promise.reject(error);
  }
);

// ============================================================================
// 响应拦截器
// ============================================================================

/**
 * 响应拦截器
 *
 * 统一处理常见的 HTTP 错误状态码
 *
 * 功能：
 * - 401 未授权：清除本地令牌并跳转到登录页
 * - 429 请求过于频繁：显示警告提示
 * - 其他错误：传递给错误处理函数
 *
 * @param response - 成功的响应对象（直接返回）
 * @param error - Axios 错误对象
 * @returns Promise 对象，成功返回响应，失败返回拒绝的 Promise
 */
api.interceptors.response.use(
  (response) => response,  // 成功响应直接通过
  (error: AxiosError) => {
    // 处理特定状态码
    if (error.response?.status === 401) {
      // 处理未授权访问
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    } else if (error.response?.status === 429) {
      // 处理请求频率限制
      console.warn('Rate limit exceeded. Please try again later.');
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// 自定义错误类
// ============================================================================

/**
 * API 错误类
 *
 * 扩展标准 Error 类，提供更详细的 API 错误信息
 *
 * @class ApiError
 * @extends Error
 *
 * @property {number} status - HTTP 状态码
 * @property {string} code - 错误代码（用于国际化或错误分类）
 * @property {any} details - 额外的错误详情（可选）
 */
export class ApiError extends Error {
  /** HTTP 状态码 */
  public status: number;

  /** 错误代码 */
  public code: string;

  /** 错误详情（可选） */
  public details?: any;

  /**
   * 创建 API 错误实例
   *
   * @param message - 错误消息
   * @param status - HTTP 状态码
   * @param code - 错误代码
   * @param details - 额外的错误详情（可选）
   */
  constructor(message: string, status: number, code: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// ============================================================================
// 响应处理辅助函数
// ============================================================================

/**
 * 处理 API 响应
 *
 * 提取响应数据，简化调用方代码
 *
 * @template T - 响应数据类型
 * @param response - Axios 响应对象
 * @returns 响应数据部分
 */
const handleResponse = <T>(response: AxiosResponse<T>): T => {
  return response.data;
};

/**
 * 处理 API 错误
 *
 * 统一处理各类 API 错误，转换为 ApiError 对象
 *
 * 功能：
 * - 记录详细错误日志（包括请求配置）
 * - 根据错误类型生成对应的 ApiError
 * - 区分网络错误、服务器错误和客户端错误
 *
 * @param error - Axios 错误对象
 * @returns never - 总是抛出错误
 * @throws {ApiError} 包含详细错误信息的 API 错误对象
 */
const handleError = (error: AxiosError): never => {
  // 记录详细的错误日志
  console.error('[API Error]', {
    message: error.message,
    code: error.code,
    status: error.response?.status,
    data: error.response?.data,
    config: {
      url: error.config?.url,
      method: error.config?.method,
      baseURL: error.config?.baseURL,
    }
  });

  // 服务器返回了响应（非网络错误）
  if (error.response) {
    const { status, data } = error.response;
    const errorData = data as any;
    throw new ApiError(
      errorData?.error?.message || errorData?.message || 'An error occurred',
      status,
      errorData?.error?.code || 'UNKNOWN_ERROR',
      errorData?.error?.details
    );
  }
  // 请求已发出但无响应（网络问题）
  else if (error.request) {
    console.error('[API] Request made but no response received');
    throw new ApiError('Network error. Please check your connection.', 0, 'NETWORK_ERROR');
  }
  // 请求配置错误
  else {
    console.error('[API] Error setting up request:', error.message);
    throw new ApiError('An unexpected error occurred.', 0, 'UNEXPECTED_ERROR');
  }
};

// ============================================================================
// API 端点定义
// ============================================================================

/**
 * API 端点配置对象
 *
 * 集中管理所有 API 端点路径，便于维护和修改
 */
export const apiEndpoints = {
  // 健康检查相关
  health: '/',                              // 根路径健康检查
  check: '/health',                         // 详细健康检查

  // 文件操作
  upload: '/api/v1/upload',                 // 文件上传端点

  // 比对操作
  compare: '/api/v1/compare',               // 启动比对任务
  taskStatus: (taskId: string) =>           // 获取任务状态（动态路径）
    `/api/v1/task/${taskId}/status`,
  taskResult: (taskId: string) =>           // 获取任务结果（动态路径）
    `/api/v1/task/${taskId}/result`,
  deleteTask: (taskId: string) =>           // 删除任务（动态路径）
    `/api/v1/task/${taskId}`,

  // WebSocket 连接
  websocket: (taskId: string) =>            // WebSocket 端点（动态路径）
    `${WS_BASE_URL}/ws/${taskId}`,
};

// ============================================================================
// 核心 API 函数
// ============================================================================

/**
 * 健康检查
 *
 * 检查后端服务是否正常运行
 *
 * @async
 * @returns {Promise<HealthStatus>} 服务健康状态信息
 * @throws {ApiError} 服务不可用时抛出错误
 *
 * @example
 * const health = await checkHealth();
 * console.log(health.status); // 'healthy'
 */
export const checkHealth = async (): Promise<HealthStatus> => {
  try {
    const response = await api.get(apiEndpoints.check);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

/**
 * 上传 PDF 文件
 *
 * 上传单个 PDF 或 Word 文件到服务器
 *
 * @async
 * @param {File} file - 要上传的文件对象（来自文件输入）
 * @param {function} [onUploadProgress] - 上传进度回调函数（0-100）
 * @returns {Promise<{ filePath: string; filename: string; fileSize: number }>} 上传结果
 *   - filePath: 服务器上的文件路径
 *   - filename: 原始文件名
 *   - fileSize: 文件大小（字节）
 * @throws {ApiError} 上传失败时抛出错误
 *
 * @example
 * const file = document.querySelector('input[type="file"]').files[0];
 * const result = await uploadPdf(file, (progress) => {
 *   console.log(`上传进度: ${progress}%`);
 * });
 * console.log(result.filePath); // '/uploads/file-abc123.pdf'
 */
export const uploadPdf = async (
  file: File,
  onUploadProgress?: (progress: number) => void
): Promise<{ filePath: string; filename: string; fileSize: number }> => {
  console.log('[API] Uploading file:', file.name, 'size:', file.size);
  try {
    // 创建 FormData 对象用于文件上传
    const formData = new FormData();
    formData.append('file', file);

    // 发送 POST 请求上传文件
    const response = await api.post(apiEndpoints.upload, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',  // 多部分表单数据
      },
      // 上传进度回调
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(progress);
        }
      },
    });

    console.log('[API] Upload response:', response.data);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

/**
 * 启动 PDF 比对任务
 *
 * 创建并启动一个文档相似度比对任务
 *
 * @async
 * @param {ComparisonRequest} request - 比对请求参数
 * @returns {Promise<{ taskId: string; status: string; message: string }>} 任务启动结果
 *   - taskId: 任务唯一标识符
 *   - status: 任务状态
 *   - message: 状态消息
 * @throws {ApiError} 任务创建失败时抛出错误
 *
 * @example
 * const request = {
 *   pdf1Path: '/uploads/file1.pdf',
 *   pdf2Path: '/uploads/file2.pdf',
 *   similarityThreshold: 0.90,
 *   sequenceLength: 8,
 *   // ... 其他参数
 * };
 * const { taskId } = await startComparison(request);
 * console.log('任务 ID:', taskId);
 */
export const startComparison = async (
  request: ComparisonRequest
): Promise<{ taskId: string; status: string; message: string }> => {
  console.log('[API] Starting comparison:', request);
  try {
    const response = await api.post(apiEndpoints.compare, request);
    console.log('[API] Comparison started:', response.data);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

/**
 * 获取任务状态
 *
 * 查询比对任务的当前状态和进度
 *
 * @async
 * @param {string} taskId - 任务 ID
 * @returns {Promise<TaskStatus>} 任务状态信息
 *   - taskId: 任务 ID
 *   - status: 状态（pending/processing/completed/error）
 *   - progress: 进度百分比（0-100）
 *   - startedAt: 开始时间
 *   - completedAt: 完成时间（可选）
 *   - error: 错误信息（可选）
 *   - message: 状态消息
 * @throws {ApiError} 查询失败时抛出错误
 *
 * @example
 * const status = await getTaskStatus('task-abc123');
 * console.log(`进度: ${status.progress}%`);
 */
export const getTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  console.log('[API] Getting status for task:', taskId);
  try {
    const response = await api.get(apiEndpoints.taskStatus(taskId));
    console.log('[API] Task status:', response.data);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

/**
 * 获取任务结果
 *
 * 获取已完成的比对任务的详细结果
 *
 * @async
 * @param {string} taskId - 任务 ID
 * @returns {Promise<SimilarityResult>} 相似度分析结果
 *   - taskId: 任务 ID
 *   - comparisonInfo: 比对参数信息
 *   - file1Stats/file2Stats: 文件统计信息
 *   - similarityStats: 相似度统计
 *   - similarSequences: 相似序列列表
 *   - processingTimeSeconds: 处理耗时
 *   - exportFiles: 导出文件信息
 * @throws {ApiError} 获取失败时抛出错误
 *
 * @example
 * const result = await getTaskResult('task-abc123');
 * console.log('相似序列数:', result.similarityStats.similarSequencesFound);
 */
export const getTaskResult = async (taskId: string): Promise<SimilarityResult> => {
  console.log('[API] Getting result for task:', taskId);
  try {
    const response = await api.get(apiEndpoints.taskResult(taskId));
    console.log('[API] Task result received');
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

/**
 * 删除任务
 *
 * 删除指定任务及其相关数据
 *
 * @async
 * @param {string} taskId - 任务 ID
 * @returns {Promise<{ message: string }>} 删除结果消息
 * @throws {ApiError} 删除失败时抛出错误
 *
 * @example
 * await deleteTask('task-abc123');
 * console.log('任务已删除');
 */
export const deleteTask = async (taskId: string): Promise<{ message: string }> => {
  try {
    const response = await api.delete(apiEndpoints.deleteTask(taskId));
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

// ============================================================================
// WebSocket 管理类
// ============================================================================

/**
 * WebSocket 连接管理器
 *
 * 负责管理与服务器的 WebSocket 连接，实现实时通信
 *
 * 功能：
 * - 自动重连机制（最多 5 次，指数退避）
 * - 消息事件处理（支持多个监听器）
 * - 连接状态监控
 * - 优雅的连接关闭
 *
 * @class WebSocketManager
 *
 * @example
 * const ws = new WebSocketManager('task-abc123');
 * await ws.connect();
 * ws.onMessage((msg) => console.log(msg));
 * ws.send({ type: 'ping' });
 * ws.disconnect();
 */
export class WebSocketManager {
  /** WebSocket 连接实例 */
  private ws: WebSocket | null = null;

  /** WebSocket 服务器 URL */
  private url: string;

  /** 当前重连尝试次数 */
  private reconnectAttempts = 0;

  /** 最大重连尝试次数 */
  private maxReconnectAttempts = 5;

  /** 重连延迟（毫秒） */
  private reconnectDelay = 1000;

  /** 消息处理器列表 */
  private messageHandlers: ((message: any) => void)[] = [];

  /** 连接状态变化处理器列表 */
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  /**
   * 创建 WebSocket 管理器实例
   *
   * @param taskId - 任务 ID（用于构建 WebSocket URL）
   */
  constructor(taskId: string) {
    this.url = apiEndpoints.websocket(taskId);
  }

  /**
   * 建立 WebSocket 连接
   *
   * 创建 WebSocket 连接并设置事件处理器
   * 成功连接后触发连接状态处理器
   *
   * @async
   * @returns {Promise<void>} 连接成功时 resolve，失败时 reject
   *
   * @example
   * await ws.connect();
   * console.log('已连接');
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // 创建 WebSocket 连接
        this.ws = new WebSocket(this.url);

        /**
         * 连接成功事件处理器
         * 重置重连计数器并通知所有连接状态处理器
         */
        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.connectionHandlers.forEach(handler => handler(true));
          resolve();
        };

        /**
         * 消息接收事件处理器
         * 解析 JSON 消息并分发给所有消息处理器
         */
        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.messageHandlers.forEach(handler => handler(message));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        /**
         * 连接关闭事件处理器
         * 通知连接状态处理器并尝试重连
         */
        this.ws.onclose = () => {
          this.connectionHandlers.forEach(handler => handler(false));
          this.attemptReconnect();
        };

        /**
         * 连接错误事件处理器
         * 记录错误并拒绝连接 Promise
         */
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 断开 WebSocket 连接
   *
   * 关闭连接并清理资源
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 发送消息到服务器
   *
   * @param message - 要发送的消息对象（会自动转换为 JSON）
   *
   * @example
   * ws.send({ type: 'ping', data: {} });
   */
  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * 注册消息处理器
   *
   * 当收到消息时，所有注册的处理器都会被调用
   *
   * @param handler - 消息处理函数
   *
   * @example
   * ws.onMessage((msg) => {
   *   console.log('收到消息:', msg);
   * });
   */
  onMessage(handler: (message: any) => void): void {
    this.messageHandlers.push(handler);
  }

  /**
   * 注册连接状态变化处理器
   *
   * @param handler - 状态处理函数，参数为是否已连接
   *
   * @example
   * ws.onConnectionChange((connected) => {
   *   console.log(connected ? '已连接' : '已断开');
   * });
   */
  onConnectionChange(handler: (connected: boolean) => void): void {
    this.connectionHandlers.push(handler);
  }

  /**
   * 移除消息处理器
   *
   * @param handler - 要移除的处理函数
   */
  removeMessageHandler(handler: (message: any) => void): void {
    const index = this.messageHandlers.indexOf(handler);
    if (index > -1) {
      this.messageHandlers.splice(index, 1);
    }
  }

  /**
   * 移除连接状态处理器
   *
   * @param handler - 要移除的处理函数
   */
  removeConnectionHandler(handler: (connected: boolean) => void): void {
    const index = this.connectionHandlers.indexOf(handler);
    if (index > -1) {
      this.connectionHandlers.splice(index, 1);
    }
  }

  /**
   * 尝试重新连接
   *
   * 使用指数退避策略进行重连
   * 延迟时间 = reconnectDelay * reconnectAttempts
   *
   * @private
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  /**
   * 检查连接状态
   *
   * @returns {boolean} 如果连接处于打开状态返回 true
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 创建比对请求对象
 *
 * 构建一个符合 ComparisonRequest 接口的比对请求
 * 使用默认值填充未提供的参数
 *
 * @param {string} pdf1Path - 第一个 PDF 文件的服务器路径
 * @param {string} pdf2Path - 第二个 PDF 文件的服务器路径
 * @param {object} options - 可选的比对参数
 * @param {number} [options.similarityThreshold=0.90] - 相似度阈值（0-1）
 * @param {number} [options.sequenceLength=8] - 序列长度（字符数）
 * @param {ContentFilter} [options.contentFilter=ContentFilter.MAIN_CONTENT_ONLY] - 内容过滤器
 * @param {ProcessingMode} [options.processingMode=ProcessingMode.FAST] - 处理模式
 * @param {number} [options.maxSequences=5000] - 最大序列数
 * @param {ExportFormat} [options.exportFormat=ExportFormat.JSON] - 导出格式
 * @param {number} [options.contextChars=100] - 上下文字符数
 * @param {string} [options.pageRange1] - 文件1的页码范围（如 "1-146"）
 * @param {string} [options.pageRange2] - 文件2的页码范围（如 "1-169"）
 * @returns {ComparisonRequest} 完整的比对请求对象
 *
 * @example
 * const request = createComparisonRequest(
 *   '/uploads/file1.pdf',
 *   '/uploads/file2.pdf',
 *   { similarityThreshold: 0.95 }
 * );
 */
export const createComparisonRequest = (
  pdf1Path: string,
  pdf2Path: string,
  options: {
    similarityThreshold?: number;
    sequenceLength?: number;
    contentFilter?: ContentFilter;
    processingMode?: ProcessingMode;
    maxSequences?: number;
    exportFormat?: ExportFormat;
    contextChars?: number;
    pageRange1?: string;
    pageRange2?: string;
  } = {}
): ComparisonRequest => {
  return {
    pdf1Path,
    pdf2Path,
    // 使用 ?? 运算符提供默认值（null 或 undefined 时使用默认值）
    similarityThreshold: options.similarityThreshold ?? 0.90,
    sequenceLength: options.sequenceLength ?? 8,
    contentFilter: options.contentFilter ?? ContentFilter.MAIN_CONTENT_ONLY,
    processingMode: options.processingMode ?? ProcessingMode.FAST,
    maxSequences: options.maxSequences ?? 5000,
    exportFormat: options.exportFormat ?? ExportFormat.JSON,
    contextChars: options.contextChars ?? 100,
    pageRange1: options.pageRange1,
    pageRange2: options.pageRange2,
  };
};

/**
 * 下载导出文件
 *
 * 从指定 URL 下载文件并触发浏览器下载
 *
 * @async
 * @param {string} fileUrl - 文件的完整 URL
 * @param {string} filename - 保存时使用的文件名
 * @returns {Promise<void>}
 * @throws {ApiError} 下载失败时抛出错误
 *
 * @example
 * await downloadExportFile(
 *   'http://localhost:8000/exports/result-abc123.json',
 *   'similarity-results.json'
 * );
 */
export const downloadExportFile = async (fileUrl: string, filename: string): Promise<void> => {
  try {
    // 使用 fetch API 下载文件
    const response = await fetch(fileUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 创建 Blob 对象
    const blob = await response.blob();
    // 创建临时 URL
    const url = window.URL.createObjectURL(blob);

    // 创建隐藏的 <a> 标签并触发点击
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 释放临时 URL 对象
    window.URL.revokeObjectURL(url);
  } catch (error) {
    throw new ApiError(`Failed to download file: ${filename}`, 0, 'DOWNLOAD_ERROR', error);
  }
};

/**
 * 批量上传 PDF 文件
 *
 * 顺序上传多个文件，提供进度回调
 *
 * @async
 * @param {File[]} files - 要上传的文件数组
 * @param {function} [onProgress] - 进度回调函数
 *   - completed: 已完成文件数
 *   - total: 总文件数
 *   - currentFile: 当前文件名
 * @returns {Promise<Array<{ filePath: string; filename: string; fileSize: number }>>} 上传结果数组
 * @throws {Error} 任一文件上传失败时抛出错误
 *
 * @example
 * const results = await batchUploadPdfs(
 *   [file1, file2, file3],
 *   (completed, total, currentFile) => {
 *     console.log(`正在上传 ${currentFile} (${completed}/${total})`);
 *   }
 * );
 */
export const batchUploadPdfs = async (
  files: File[],
  onProgress?: (completed: number, total: number, currentFile: string) => void
): Promise<Array<{ filePath: string; filename: string; fileSize: number }>> => {
  const results = [];

  // 顺序处理每个文件
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    try {
      const result = await uploadPdf(file, (progress) => {
        if (onProgress) {
          onProgress(i, files.length, file.name);
        }
      });
      results.push(result);
    } catch (error) {
      console.error(`Failed to upload ${file.name}:`, error);
      throw error;
    }
  }

  return results;
};

// ============================================================================
// 默认导出
// ============================================================================

/**
 * 导出所有 API 功能和配置
 *
 * 提供统一访问点，便于导入使用
 */
export default {
  // 配置
  API_BASE_URL,

  // API 函数
  checkHealth,
  uploadPdf,
  startComparison,
  getTaskStatus,
  getTaskResult,
  deleteTask,
  downloadExportFile,

  // 工具函数
  createComparisonRequest,
  batchUploadPdfs,

  // 错误处理和配置
  ApiError,
  apiEndpoints,
  api,
};
