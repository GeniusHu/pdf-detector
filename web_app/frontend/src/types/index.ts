/**
 * 类型定义模块
 *
 * 本模块集中定义整个应用使用的 TypeScript 类型和接口
 * 包括：
 * - API 请求和响应数据结构
 * - 组件 Props 类型定义
 * - 状态管理类型
 * - 枚举类型定义
 *
 * @module types
 * @version 1.0.0
 */

// ============================================================================
// 文件上传相关类型
// ============================================================================

/**
 * 文件上传信息接口
 *
 * 表示用户上传的文件的完整信息，包括文件对象、上传状态和进度
 *
 * @interface FileUpload
 *
 * @property {string} id - 文件的唯一标识符（自动生成）
 * @property {File} file - 原始 File 对象（来自文件输入）
 * @property {string} name - 文件名
 * @property {number} size - 文件大小（字节）
 * @property {string} sizeFormatted - 格式化的文件大小显示字符串（如 "2.5 MB"）
 * @property {string} type - MIME 类型（如 "application/pdf"）
 * @property {Date} uploadedAt - 上传时间戳
 * @property {string} [filePath] - 服务器上的文件路径（上传成功后返回）
 * @property {'pending' | 'uploading' | 'completed' | 'error'} status - 上传状态
 *   - pending: 等待上传
 *   - uploading: 正在上传
 *   - completed: 上传完成
 *   - error: 上传失败
 * @property {string} [error] - 错误消息（状态为 error 时）
 * @property {number} [progress] - 上传进度（0-100，状态为 uploading 时）
 */
export interface FileUpload {
  id: string;
  file: File;
  name: string;
  size: number;
  sizeFormatted: string;
  type: string;
  uploadedAt: Date;
  filePath?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  progress?: number;
}

// ============================================================================
// 比对请求相关类型
// ============================================================================

/**
 * 比对请求参数接口
 *
 * 定义启动文档相似度比对任务所需的所有参数
 *
 * @interface ComparisonRequest
 *
 * @property {string} pdf1Path - 第一个文档的服务器文件路径
 * @property {string} pdf2Path - 第二个文档的服务器文件路径
 * @property {number} similarityThreshold - 相似度阈值（0-1），只有超过此值的序列才会被记录
 * @property {number} sequenceLength - 用于比对的序列长度（字符数）
 * @property {ContentFilter} contentFilter - 内容过滤器（决定哪些内容参与比对）
 * @property {ProcessingMode} processingMode - 处理模式（影响算法和速度）
 * @property {number} maxSequences - 最大返回序列数（防止结果过大）
 * @property {ExportFormat} exportFormat - 导出格式
 * @property {number} contextChars - 相似序列前后包含的上下文字符数
 * @property {string} [pageRange1] - 文件1的页码范围（可选，如 "1-146"）
 * @property {string} [pageRange2] - 文件2的页码范围（可选，如 "1-169"）
 *
 * @example
 * const request: ComparisonRequest = {
 *   pdf1Path: '/uploads/doc1.pdf',
 *   pdf2Path: '/uploads/doc2.pdf',
 *   similarityThreshold: 0.90,
 *   sequenceLength: 8,
 *   contentFilter: ContentFilter.MAIN_CONTENT_ONLY,
 *   processingMode: ProcessingMode.FAST,
 *   maxSequences: 5000,
 *   exportFormat: ExportFormat.JSON,
 *   contextChars: 100,
 *   pageRange1: '1-146',
 *   pageRange2: '1-169'
 * };
 */
export interface ComparisonRequest {
  pdf1Path: string;
  pdf2Path: string;
  similarityThreshold: number;
  sequenceLength: number;
  contentFilter: ContentFilter;
  processingMode: ProcessingMode;
  maxSequences: number;
  exportFormat: ExportFormat;
  contextChars: number;
  pageRange1?: string;    // 例如："1-146"
  pageRange2?: string;    // 例如："1-169"
}

// ============================================================================
// 任务状态相关类型
// ============================================================================

/**
 * 任务状态类型枚举
 *
 * 定义比对任务在生命周期中可能处于的所有状态
 *
 * @enum {string}
 */
export enum TaskStatusType {
  /** 任务已创建，等待开始处理 */
  PENDING = 'pending',
  /** 任务正在处理中 */
  PROCESSING = 'processing',
  /** 任务处理完成 */
  COMPLETED = 'completed',
  /** 任务处理出错 */
  ERROR = 'error',
  /** 任务被取消 */
  CANCELLED = 'cancelled',
}

/**
 * 任务状态信息接口
 *
 * 表示比对任务的当前执行状态和进度
 *
 * @interface TaskStatus
 *
 * @property {string} taskId - 任务唯一标识符
 * @property {TaskStatusType} status - 当前状态
 * @property {number} progress - 进度百分比（0-100）
 * @property {string} startedAt - 任务开始时间（ISO 8601 格式）
 * @property {string} [completedAt] - 任务完成时间（ISO 8601 格式，可选）
 * @property {string} [error] - 错误消息（状态为 error 时）
 * @property {string} [message] - 状态描述消息（可选）
 *
 * @example
 * const status: TaskStatus = {
 *   taskId: 'task-abc123',
 *   status: TaskStatusType.PROCESSING,
 *   progress: 45,
 *   startedAt: '2024-01-15T10:30:00Z',
 *   message: '正在分析文件2...'
 * };
 */
export interface TaskStatus {
  taskId: string;
  status: TaskStatusType;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  message?: string;
}

// ============================================================================
// 相似度结果相关类型
// ============================================================================

/**
 * 相似序列位置信息接口
 *
 * 标识相似序列在文档中的精确位置
 *
 * @interface Position
 * @property {number} page - 页码（从1开始）
 * @property {number} line - 行号
 * @property {number} charIndex - 字符索引（在行中的位置）
 */

/**
 * 上下文信息接口
 *
 * 相似序列前后的文本内容
 *
 * @interface Context
 * @property {string} before - 相似序列之前的文本
 * @property {string} after - 相似序列之后的文本
 */

/**
 * 相似序列信息接口
 *
 * 表示在两个文档中发现的相似文本序列
 *
 * @interface SimilarSequence
 *
 * @property {string} sequence1 - 文档1中的相似文本序列
 * @property {string} sequence2 - 文档2中的相似文本序列
 * @property {number} similarity - 相似度分数（0-1）
 * @property {Position} position1 - 在文档1中的位置
 *   - page: 页码
 *   - line: 行号
 *   - charIndex: 字符索引
 * @property {Position} position2 - 在文档2中的位置
 * @property {Context} context1 - 文档1中的上下文
 *   - before: 序列之前的文本
 *   - after: 序列之后的文本
 * @property {Context} context2 - 文档2中的上下文
 * @property {string[]} differences - 两个序列之间的差异列表
 */
export interface SimilarSequence {
  sequence1: string;
  sequence2: string;
  similarity: number;
  position1: {
    page: number;
    line: number;
    charIndex: number;
  };
  position2: {
    page: number;
    line: number;
    charIndex: number;
  };
  context1: {
    before: string;
    after: string;
  };
  context2: {
    before: string;
    after: string;
  };
  differences: string[];
}

/**
 * 文件统计信息接口
 *
 * 提供文档处理的详细统计信息
 *
 * @interface FileStatistics
 *
 * @property {string} filePath - 文件路径
 * @property {number} fileSizeMb - 文件大小（MB）
 * @property {number} totalPages - 总页数
 * @property {number} totalLines - 总行数
 * @property {number} mainContentLines - 主要内容的行数（过滤后）
 * @property {number} filteredLines - 被过滤掉的行数
 * @property {number} totalChars - 总字符数
 * @property {number} processingTimeSeconds - 处理耗时（秒）
 */
export interface FileStatistics {
  filePath: string;
  fileSizeMb: number;
  totalPages: number;
  totalLines: number;
  mainContentLines: number;
  filteredLines: number;
  totalChars: number;
  processingTimeSeconds: number;
}

/**
 * 相似度统计信息接口
 *
 * 提供比对结果的汇总统计数据
 *
 * @interface SimilarityStatistics
 *
 * @property {number} totalSequencesAnalyzed - 分析的总序列数
 * @property {number} similarSequencesFound - 发现的相似序列数
 * @property {number} highSimilarityCount - 高相似度序列数（>0.9）
 * @property {number} mediumSimilarityCount - 中等相似度序列数（0.7-0.9）
 * @property {number} lowSimilarityCount - 低相似度序列数（<0.7）
 * @property {number} averageSimilarity - 平均相似度
 * @property {number} maxSimilarity - 最高相似度
 * @property {number} minSimilarity - 最低相似度
 */
export interface SimilarityStatistics {
  totalSequencesAnalyzed: number;
  similarSequencesFound: number;
  highSimilarityCount: number;
  mediumSimilarityCount: number;
  lowSimilarityCount: number;
  averageSimilarity: number;
  maxSimilarity: number;
  minSimilarity: number;
}

/**
 * 相似度比对结果接口
 *
 * 包含完整的比对结果，包括统计信息和所有相似序列
 *
 * @interface SimilarityResult
 *
 * @property {string} taskId - 任务 ID
 * @property {ComparisonInfo} comparisonInfo - 比对参数信息
 *   - similarityThreshold: 相似度阈值
 *   - maxSequences: 最大序列数
 *   - processingMode: 处理模式
 *   - contextChars: 上下文字符数
 *   - processedAt: 处理时间戳
 * @property {FileStatistics} file1Stats - 文件1的统计信息
 * @property {FileStatistics} file2Stats - 文件2的统计信息
 * @property {SimilarityStatistics} similarityStats - 相似度统计
 * @property {SimilarSequence[]} similarSequences - 所有相似序列列表
 * @property {number} processingTimeSeconds - 总处理耗时（秒）
 * @property {Record<string, string>} exportFiles - 导出文件路径映射
 *   - 键: 文件格式（如 'json', 'csv'）
 *   - 值: 文件路径
 */
export interface SimilarityResult {
  taskId: string;
  comparisonInfo: {
    similarityThreshold: number;
    maxSequences: number;
    processingMode: string;
    contextChars: number;
    processedAt: number;
  };
  file1Stats: FileStatistics;
  file2Stats: FileStatistics;
  similarityStats: SimilarityStatistics;
  similarSequences: SimilarSequence[];
  processingTimeSeconds: number;
  exportFiles: Record<string, string>;
}

// ============================================================================
// WebSocket 和进度相关类型
// ============================================================================

/**
 * WebSocket 消息接口
 *
 * 通过 WebSocket 接收的服务器消息格式
 *
 * @interface WebSocketMessage
 *
 * @property {string} type - 消息类型（如 'progress', 'complete', 'error'）
 * @property {string} [taskId] - 任务 ID（可选）
 * @property {any} data - 消息数据（根据类型不同而变化）
 * @property {number} timestamp - 消息时间戳（Unix 时间戳）
 */
export interface WebSocketMessage {
  type: string;
  taskId?: string;
  data: any;
  timestamp: number;
}

/**
 * 进度更新信息接口
 *
 * 任务执行过程中的进度更新
 *
 * @interface ProgressUpdate
 *
 * @property {number} progress - 进度百分比（0-100）
 * @property {string} message - 进度描述消息
 * @property {string} currentStep - 当前步骤名称
 * @property {number} [estimatedRemainingSeconds] - 预计剩余时间（秒，可选）
 * @property {Record<string, any>} [details] - 额外的详细信息（可选）
 */
export interface ProgressUpdate {
  progress: number;
  message: string;
  currentStep: string;
  estimatedRemainingSeconds?: number;
  details?: Record<string, any>;
}

// ============================================================================
// 导出相关类型
// ============================================================================

/**
 * 导出文件信息接口
 *
 * 描述可下载的导出文件
 *
 * @interface ExportFile
 *
 * @property {ExportFormat} format - 文件格式
 * @property {string} filePath - 文件路径
 * @property {number} fileSize - 文件大小（字节）
 * @property {string} downloadUrl - 下载 URL
 */
export interface ExportFile {
  format: ExportFormat;
  filePath: string;
  fileSize: number;
  downloadUrl: string;
}

/**
 * 处理选项接口
 *
 * 比对任务的处理参数集合
 *
 * @interface ProcessingOptions
 *
 * @property {number} similarityThreshold - 相似度阈值（0-1）
 * @property {number} sequenceLength - 序列长度（字符数）
 * @property {ContentFilter} contentFilter - 内容过滤器
 * @property {ProcessingMode} processingMode - 处理模式
 * @property {number} maxSequences - 最大序列数
 * @property {ExportFormat} exportFormat - 导出格式
 * @property {number} contextChars - 上下文字符数
 */
export interface ProcessingOptions {
  similarityThreshold: number;
  sequenceLength: number;
  contentFilter: ContentFilter;
  processingMode: ProcessingMode;
  maxSequences: number;
  exportFormat: ExportFormat;
  contextChars: number;
}

// ============================================================================
// API 响应相关类型
// ============================================================================

/**
 * 通用 API 响应接口
 *
 * 标准化的 API 响应格式
 *
 * @interface ApiResponse
 * @template T - 响应数据类型
 *
 * @property {boolean} success - 请求是否成功
 * @property {T} [data] - 响应数据（成功时）
 * @property {ErrorInfo} [error] - 错误信息（失败时）
 *   - code: 错误代码
 *   - message: 错误消息
 *   - details: 错误详情
 * @property {string} timestamp - 响应时间戳（ISO 8601 格式）
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: number;
    message: string;
    details?: any;
  };
  timestamp: string;
}

/**
 * 健康检查状态接口
 *
 * 服务健康检查的响应信息
 *
 * @interface HealthStatus
 *
 * @property {string} status - 整体状态（'healthy' | 'unhealthy' | 'degraded'）
 * @property {string} timestamp - 检查时间戳（ISO 8601 格式）
 * @property {ServiceInfo} services - 各服务的状态信息
 *   - 键: 服务名称
 *   - 值: 服务详细信息
 *     - name: 服务名称
 *     - status: 服务状态
 *     - lastCheck: 最后检查时间
 *     - details: 额外详情
 * @property {number} uptimeSeconds - 服务运行时长（秒）
 * @property {string} version - 服务版本号
 */
export interface HealthStatus {
  status: string;
  timestamp: string;
  services: Record<string, {
    name: string;
    status: string;
    lastCheck: string;
    details?: any;
  }>;
  uptimeSeconds: number;
  version: string;
}

// ============================================================================
// 枚举类型定义
// ============================================================================

/**
 * 内容过滤器枚举
 *
 * 定义文档内容过滤选项，控制哪些内容参与比对
 *
 * @enum {string}
 */
export enum ContentFilter {
  /** 包含所有内容（包括页眉、页脚、参考文献等） */
  ALL_CONTENT = 'all',
  /** 仅包含主要内容（排除参考文献、引用等） */
  MAIN_CONTENT_ONLY = 'main_content_only',
  /** 包含主要内容和参考文献 */
  INCLUDE_REFERENCES = 'include_references',
  /** 包含主要内容和引用 */
  INCLUDE_CITATIONS = 'include_citations',
}

/**
 * 处理模式枚举
 *
 * 定义文档比对的处理模式，影响算法选择和性能
 *
 * @enum {string}
 */
export enum ProcessingMode {
  /** 标准模式：最准确但速度较慢（适合小文件） */
  STANDARD = 'standard',
  /** 快速模式：平衡准确度和速度（推荐） */
  FAST = 'fast',
  /** 超快速模式：速度最快但可能降低准确度（适合大文件） */
  ULTRA_FAST = 'ultra_fast',
}

/**
 * 导出格式枚举
 *
 * 定义支持的导出文件格式
 *
 * @enum {string}
 */
export enum ExportFormat {
  /** 纯文本格式 */
  TEXT = 'text',
  /** JSON 格式 */
  JSON = 'json',
  /** CSV 格式（适合电子表格） */
  CSV = 'csv',
  /** PDF 报告格式 */
  PDF_REPORT = 'pdf_report',
}

// ============================================================================
// UI 状态相关类型
// ============================================================================

/**
 * UI 状态接口
 *
 * 应用全局 UI 状态
 *
 * @interface UIState
 *
 * @property {'light' | 'dark'} theme - 主题模式
 * @property {boolean} sidebarOpen - 侧边栏是否打开
 * @property {Notification[]} notifications - 通知列表
 * @property {boolean} loading - 全局加载状态
 */
export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  notifications: Notification[];
  loading: boolean;
}

/**
 * 通知信息接口
 *
 * 应用通知/消息的数据结构
 *
 * @interface Notification
 *
 * @property {string} id - 通知唯一标识符
 * @property {'success' | 'error' | 'warning' | 'info'} type - 通知类型
 * @property {string} title - 通知标题
 * @property {string} message - 通知内容
 * @property {Date} timestamp - 通知时间
 * @property {number} [duration] - 显示时长（毫秒，可选）
 * @property {boolean} [persistent] - 是否持久显示（需要手动关闭）
 */
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  duration?: number;
  persistent?: boolean;
}

// ============================================================================
// 组件 Props 类型定义
// ============================================================================

/**
 * 文件上传区域组件 Props
 *
 * @interface FileUploadZoneProps
 *
 * @property {function} onFilesDrop - 文件拖放/选择回调
 *   - 参数: File[] - 选中的文件列表
 * @property {number} [maxFiles=2] - 最大文件数
 * @property {number} [maxSize] - 最大文件大小（字节）
 * @property {string[]} [acceptedTypes] - 接受的文件类型（如 ['.pdf', '.docx']）
 * @property {boolean} [disabled] - 是否禁用
 * @property {string} [className] - 自定义类名
 */
export interface FileUploadZoneProps {
  onFilesDrop: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number;
  acceptedTypes?: string[];
  disabled?: boolean;
  className?: string;
}

/**
 * 进度条组件 Props
 *
 * @interface ProgressBarProps
 *
 * @property {number} progress - 进度值（0-100）
 * @property {boolean} [showPercentage] - 是否显示百分比
 * @property {boolean} [showLabel] - 是否显示标签
 * @property {string} [label] - 标签文本
 * @property {'primary' | 'secondary' | 'success' | 'warning' | 'error'} [color] - 颜色主题
 * @property {'sm' | 'md' | 'lg'} [size] - 尺寸
 * @property {boolean} [animated] - 是否启用动画
 */
export interface ProgressBarProps {
  progress: number;
  showPercentage?: boolean;
  showLabel?: boolean;
  label?: string;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

/**
 * 相似度图表组件 Props
 *
 * @interface SimilarityChartProps
 *
 * @property {SimilarSequence[]} data - 相似序列数据
 * @property {number} [height] - 图表高度（像素）
 * @property {boolean} [showDetails] - 是否显示详细信息
 * @property {function} [onSequenceClick] - 序列点击回调
 *   - 参数: SimilarSequence - 被点击的序列
 */
export interface SimilarityChartProps {
  data: SimilarSequence[];
  height?: number;
  showDetails?: boolean;
  onSequenceClick?: (sequence: SimilarSequence) => void;
}

/**
 * 上下文显示组件 Props
 *
 * @interface ContextDisplayProps
 *
 * @property {SimilarSequence} sequence - 要显示的相似序列
 * @property {number} [contextChars] - 上下文字符数
 * @property {boolean} [showDifferences] - 是否高亮显示差异
 * @property {boolean} [compact] - 是否使用紧凑模式
 */
export interface ContextDisplayProps {
  sequence: SimilarSequence;
  contextChars?: number;
  showDifferences?: boolean;
  compact?: boolean;
}

/**
 * 导出选项组件 Props
 *
 * @interface ExportOptionsProps
 *
 * @property {ExportFormat[]} formats - 可用的导出格式列表
 * @property {ExportFormat} selectedFormat - 当前选中的格式
 * @property {function} onFormatChange - 格式变更回调
 *   - 参数: ExportFormat - 新的格式
 * @property {function} onExport - 导出回调
 *   - 参数: ExportFormat - 要导出的格式
 * @property {boolean} [loading] - 是否正在导出
 * @property {boolean} [disabled] - 是否禁用
 */
export interface ExportOptionsProps {
  formats: ExportFormat[];
  selectedFormat: ExportFormat;
  onFormatChange: (format: ExportFormat) => void;
  onExport: (format: ExportFormat) => void;
  loading?: boolean;
  disabled?: boolean;
}

// ============================================================================
// 状态管理类型（Store Types）
// ============================================================================

/**
 * 应用状态接口
 *
 * 全局应用状态管理
 *
 * @interface AppState
 *
 * @property {FileUpload[]} files - 文件列表
 * @property {TaskStatus | null} currentTask - 当前任务状态
 * @property {SimilarityResult | null} results - 比对结果
 * @property {boolean} processing - 是否正在处理
 * @property {string | null} error - 错误消息
 * @property {ProcessingOptions} settings - 处理设置
 */
export interface AppState {
  files: FileUpload[];
  currentTask: TaskStatus | null;
  results: SimilarityResult | null;
  processing: boolean;
  error: string | null;
  settings: ProcessingOptions;
}

/**
 * 文件状态接口
 *
 * 文件上传相关的状态
 *
 * @interface FileState
 *
 * @property {FileUpload[]} uploads - 上传中的文件列表
 * @property {string[]} selectedFiles - 选中的文件 ID 列表
 * @property {Record<string, number>} uploadProgress - 上传进度映射
 *   - 键: 文件 ID
 *   - 值: 进度（0-100）
 */
export interface FileState {
  uploads: FileUpload[];
  selectedFiles: string[];
  uploadProgress: Record<string, number>;
}

/**
 * 任务状态接口
 *
 * 任务管理相关的状态
 *
 * @interface TaskState
 *
 * @property {Record<string, TaskStatus>} activeTasks - 活跃任务映射
 *   - 键: 任务 ID
 *   - 值: 任务状态
 * @property {TaskStatus[]} completedTasks - 已完成任务列表
 * @property {string | null} currentTaskId - 当前任务 ID
 */
export interface TaskState {
  activeTasks: Record<string, TaskStatus>;
  completedTasks: TaskStatus[];
  currentTaskId: string | null;
}

/**
 * 结果状态接口
 *
 * 比对结果相关的状态
 *
 * @interface ResultState
 *
 * @property {SimilarityResult | null} currentResult - 当前结果
 * @property {SimilarityResult[]} resultHistory - 结果历史记录
 * @property {ExportFile[]} exportHistory - 导出历史记录
 */
export interface ResultState {
  currentResult: SimilarityResult | null;
  resultHistory: SimilarityResult[];
  exportHistory: ExportFile[];
}

// ============================================================================
// Hook 返回类型
// ============================================================================

/**
 * 文件上传 Hook 返回类型
 *
 * @interface UseFileUploadReturn
 *
 * @property {FileUpload[]} files - 文件列表
 * @property {function} uploadFile - 上传单个文件
 *   - 参数: File - 文件对象
 *   - 返回: Promise<string> - 文件路径
 * @property {function} removeFile - 移除文件
 *   - 参数: string - 文件 ID
 * @property {function} clearFiles - 清空所有文件
 * @property {Record<string, number>} uploadProgress - 上传进度映射
 * @property {boolean} isUploading - 是否正在上传
 * @property {string | null} error - 错误消息
 */
export interface UseFileUploadReturn {
  files: FileUpload[];
  uploadFile: (file: File) => Promise<string>;
  removeFile: (id: string) => void;
  clearFiles: () => void;
  uploadProgress: Record<string, number>;
  isUploading: boolean;
  error: string | null;
}

/**
 * WebSocket Hook 返回类型
 *
 * @interface UseWebSocketReturn
 *
 * @property {boolean} isConnected - 是否已连接
 * @property {WebSocketMessage | null} lastMessage - 最后接收的消息
 * @property {function} sendMessage - 发送消息
 *   - 参数: any - 消息对象
 * @property {function} disconnect - 断开连接
 * @property {string | null} error - 错误消息
 */
export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  disconnect: () => void;
  error: string | null;
}

/**
 * 相似度检测 Hook 返回类型
 *
 * @interface UseSimilarityDetectionReturn
 *
 * @property {function} startComparison - 开始比对
 *   - 参数: ComparisonRequest - 比对请求
 *   - 返回: Promise<string> - 任务 ID
 * @property {function} cancelTask - 取消任务
 *   - 参数: string - 任务 ID
 * @property {function} getTaskStatus - 获取任务状态
 *   - 参数: string - 任务 ID
 *   - 返回: Promise<TaskStatus>
 * @property {function} getResults - 获取结果
 *   - 参数: string - 任务 ID
 *   - 返回: Promise<SimilarityResult>
 * @property {function} exportResults - 导出结果
 *   - 参数: (string, ExportFormat) - 任务 ID 和格式
 *   - 返回: Promise<ExportFile>
 * @property {boolean} isProcessing - 是否正在处理
 * @property {string | null} error - 错误消息
 */
export interface UseSimilarityDetectionReturn {
  startComparison: (request: ComparisonRequest) => Promise<string>;
  cancelTask: (taskId: string) => Promise<void>;
  getTaskStatus: (taskId: string) => Promise<TaskStatus>;
  getResults: (taskId: string) => Promise<SimilarityResult>;
  exportResults: (taskId: string, format: ExportFormat) => Promise<ExportFile>;
  isProcessing: boolean;
  error: string | null;
}
