/**
 * 文件上传组件
 *
 * 本组件提供拖放式文件上传功能，支持：
 * - 拖放文件上传
 * - 点击选择文件
 * - 文件类型和大小验证
 * - 上传进度显示
 * - 文件状态管理
 * - 错误提示
 *
 * @module FileUpload
 * @author Document Similarity Detection Team
 * @version 1.0.0
 */

// ============================================================================
// 导入依赖
// ============================================================================

/**
 * React 核心功能导入
 * - useCallback: 性能优化，缓存回调函数
 * - useState: 状态管理 Hook
 */
import React, { useCallback, useState } from 'react';

/**
 * React Dropzone 库
 * 提供拖放文件上传功能
 */
import { useDropzone } from 'react-dropzone';

/**
 * Framer Motion 动画库
 * - motion: 动画组件
 * - AnimatePresence: 动画过渡组件（用于元素的进入/退出动画）
 */
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Lucide React 图标库
 */
import {
  Upload,         // 上传图标
  X,             // 关闭/删除图标
  File,          // 文件图标
  AlertCircle,   // 警告图标
  CheckCircle,   // 成功图标
  Loader2,       // 加载图标
  FileText,      // 文本文档图标
} from 'lucide-react';

/**
 * 工具函数导入
 * - cn: 类名合并工具
 * - formatFileSize: 文件大小格式化工具
 * - isValidFileType: 文件类型验证工具
 * - isValidFileSize: 文件大小验证工具
 */
import { cn, formatFileSize, isValidFileType, isValidFileSize } from '@/lib/utils';

/**
 * 类型定义导入
 */
import { FileUpload } from '@/types';

// ============================================================================
// Props 接口定义
// ============================================================================

/**
 * 文件上传区域组件 Props
 *
 * @interface FileUploadZoneProps
 *
 * @property {function} onFilesChange - 文件列表变化回调
 *   - 参数: FileUpload[] - 更新后的文件列表
 * @property {FileUpload[]} files - 当前文件列表
 * @property {number} [maxFiles=2] - 最大文件数量（默认2）
 * @property {number} [maxSize] - 最大文件大小（字节）
 * @property {string[]} [acceptedTypes] - 接受的文件类型（如 ['.pdf', '.docx']）
 * @property {boolean} [disabled] - 是否禁用上传
 * @property {string} [className] - 自定义 CSS 类名
 */
interface FileUploadZoneProps {
  onFilesChange: (files: FileUpload[]) => void;
  files: FileUpload[];
  maxFiles?: number;
  maxSize?: number;
  acceptedTypes?: string[];
  disabled?: boolean;
  className?: string;
}

/**
 * 文件上传项组件 Props
 *
 * @interface FileUploadItemProps
 *
 * @property {FileUpload} file - 文件对象
 * @property {function} onRemove - 移除文件回调
 *   - 参数: string - 文件 ID
 * @property {boolean} [disabled] - 是否禁用操作（如上传中）
 */
interface FileUploadItemProps {
  file: FileUpload;
  onRemove: (id: string) => void;
  disabled?: boolean;
}

// ============================================================================
// 子组件：文件上传项
// ============================================================================

/**
 * 文件上传项组件
 *
 * 显示单个文件的信息、状态和操作按钮
 *
 * @param {FileUploadItemProps} props - 组件属性
 * @returns {JSX.Element} 文件上传项的 JSX 元素
 */
const FileUploadItem: React.FC<FileUploadItemProps> = ({ file, onRemove, disabled }) => {
  /**
   * 判断文件类型
   * 根据文件扩展名确定是 PDF、Word 还是其他类型
   */
  const fileType = file.name.toLowerCase().endsWith('.pdf') ? 'pdf' :
                   file.name.toLowerCase().endsWith('.docx') ? 'word' : 'unknown';

  /**
   * 获取状态图标
   * 根据文件的上传状态返回对应的图标
   *
   * @returns {JSX.Element} 状态图标组件
   */
  const getStatusIcon = () => {
    switch (file.status) {
      case 'uploading':
        // 上传中：显示旋转的加载图标
        return <Loader2 className="w-4 h-4 animate-spin text-primary-600" />;
      case 'completed':
        // 已完成：显示绿色对勾图标
        return <CheckCircle className="w-4 h-4 text-success-600" />;
      case 'error':
        // 错误：显示红色警告图标
        return <AlertCircle className="w-4 h-4 text-error-600" />;
      default:
        // 其他状态：显示灰色文件图标
        return <File className="w-4 h-4 text-secondary-600" />;
    }
  };

  /**
   * 获取状态颜色样式
   * 根据文件状态返回对应的 Tailwind CSS 类名
   *
   * @returns {string} CSS 类名字符串
   */
  const getStatusColor = () => {
    switch (file.status) {
      case 'uploading':
        return 'border-primary-200 bg-primary-50';
      case 'completed':
        return 'border-success-200 bg-success-50';
      case 'error':
        return 'border-error-200 bg-error-50';
      default:
        return 'border-secondary-200 bg-secondary-50';
    }
  };

  /**
   * 获取文件类型标签文本
   *
   * @returns {string} 文件类型标签（'PDF' | 'Word' | 'Unknown'）
   */
  const getFileTypeLabel = () => {
    if (fileType === 'pdf') return 'PDF';
    if (fileType === 'word') return 'Word';
    return 'Unknown';
  };

  /**
   * 获取文件类型标签颜色样式
   *
   * @returns {string} CSS 类名字符串
   */
  const getFileTypeColor = () => {
    if (fileType === 'pdf') return 'bg-red-100 text-red-700';
    if (fileType === 'word') return 'bg-blue-100 text-blue-700';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        'flex items-center justify-between p-3 rounded-lg border transition-all duration-200',
        getStatusColor()  // 根据状态应用颜色样式
      )}
    >
      {/* 左侧：文件信息和状态图标 */}
      <div className="flex items-center space-x-3 flex-1 min-w-0">
        {/* 文档图标 */}
        <FileText className="w-5 h-5 text-secondary-500 flex-shrink-0" />
        {/* 状态图标 */}
        {getStatusIcon()}
        {/* 文件信息区域 */}
        <div className="flex-1 min-w-0">
          {/* 文件名和类型标签 */}
          <div className="flex items-center space-x-2">
            <p className="text-sm font-medium text-secondary-900 truncate">
              {file.name}
            </p>
            {/* 文件类型标签 */}
            <span className={cn(
              'text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0',
              getFileTypeColor()
            )}>
              {getFileTypeLabel()}
            </span>
          </div>
          {/* 文件大小、进度和错误信息 */}
          <div className="flex items-center space-x-2 mt-1">
            {/* 文件大小 */}
            <span className="text-xs text-secondary-600">
              {formatFileSize(file.size)}
            </span>
            {/* 上传进度（仅在上传中时显示） */}
            {file.status === 'uploading' && file.progress !== undefined && (
              <>
                <span className="text-xs text-secondary-400">•</span>
                <span className="text-xs text-primary-600">
                  {file.progress}%
                </span>
              </>
            )}
            {/* 错误消息（仅在错误状态时显示） */}
            {file.error && (
              <>
                <span className="text-xs text-secondary-400">•</span>
                <span className="text-xs text-error-600">
                  {file.error}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 右侧：删除按钮 */}
      {!disabled && (
        <motion.button
          whileHover={{ scale: 1.05 }}  // 悬停时放大
          whileTap={{ scale: 0.95 }}    // 点击时缩小
          onClick={() => onRemove(file.id)}
          className="p-1 rounded-md hover:bg-secondary-200 transition-colors"
          disabled={file.status === 'uploading'}  // 上传中禁用删除
        >
          <X className="w-4 h-4 text-secondary-600" />
        </motion.button>
      )}
    </motion.div>
  );
};

// ============================================================================
// 主组件：文件上传区域
// ============================================================================

/**
 * 文件上传区域组件
 *
 * 提供拖放和点击选择文件的功能，并管理文件列表
 *
 * @param {FileUploadZoneProps} props - 组件属性
 * @returns {JSX.Element} 文件上传区域的 JSX 元素
 */
export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onFilesChange,
  files,
  maxFiles = 2,
  maxSize = 100 * 1024 * 1024,  // 默认最大100MB
  acceptedTypes = ['.pdf', '.docx'],
  disabled = false,
  className,
}) => {
  /**
   * 拖放激活状态
   * 标识当前是否有文件正在拖放到区域上方
   */
  const [dragActive, setDragActive] = useState(false);

  /**
   * 错误消息列表
   * 存储当前显示的验证错误消息
   */
  const [errors, setErrors] = useState<string[]>([]);

  /**
   * 验证文件
   *
   * 检查文件的类型、大小和是否重复
   *
   * @param {File[]} newFiles - 待验证的文件列表
   * @returns {string[]} 错误消息列表（空数组表示无错误）
   */
  const validateFiles = useCallback((newFiles: File[]): string[] => {
    const newErrors: string[] = [];

    newFiles.forEach((file) => {
      // 检查文件类型
      if (!isValidFileType(file, acceptedTypes)) {
        newErrors.push(`Invalid file type: ${file.name}. Only ${acceptedTypes.join(', ')} files are allowed.`);
        return;
      }

      // 检查文件大小
      if (!isValidFileSize(file, maxSize)) {
        newErrors.push(`File too large: ${file.name}. Maximum size is ${formatFileSize(maxSize)}.`);
        return;
      }

      // 检查重复文件
      if (files.some((existingFile) => existingFile.name === file.name)) {
        newErrors.push(`Duplicate file: ${file.name}. This file has already been uploaded.`);
        return;
      }
    });

    return newErrors;
  }, [files, acceptedTypes, maxSize]);

  /**
   * 处理文件
   *
   * 验证文件并添加到文件列表
   *
   * @param {File[]} newFiles - 新添加的文件列表
   */
  const processFiles = useCallback((newFiles: File[]) => {
    // 验证文件
    const validationErrors = validateFiles(newFiles);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      // 5秒后自动清除错误消息
      setTimeout(() => setErrors([]), 5000);
      return;
    }

    // 创建文件上传对象
    const fileUploads: FileUpload[] = newFiles.map((file) => ({
      // 生成唯一 ID：随机字符串 + 时间戳
      id: Math.random().toString(36).substring(2) + Date.now().toString(36),
      file,
      name: file.name,
      size: file.size,
      sizeFormatted: formatFileSize(file.size),
      type: file.type,
      uploadedAt: new Date(),
      status: 'pending' as const,  // 初始状态为等待上传
    }));

    // 更新文件列表（限制最大文件数）
    const updatedFiles = [...files, ...fileUploads].slice(0, maxFiles);
    onFilesChange(updatedFiles);
    setErrors([]);
  }, [files, maxFiles, validateFiles, onFilesChange]);

  /**
   * 使用 react-dropzone 配置拖放区域
   */
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: processFiles,  // 文件放下时的回调
    accept: {
      // 接受的 MIME 类型和文件扩展名
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles,              // 最大文件数
    maxSize,              // 最大文件大小
    disabled: disabled || files.length >= maxFiles,  // 达到上限时禁用
    noClick: disabled || files.length >= maxFiles,   // 达到上限时禁用点击
    onDragEnter: () => setDragActive(true),          // 拖动进入
    onDragLeave: () => setDragActive(false),         // 拖动离开
    onDropAccepted: () => setDragActive(false),      // 成功放下
    onDropRejected: () => setDragActive(false),      // 放下被拒绝
  });

  /**
   * 处理移除文件
   *
   * 从文件列表中删除指定文件
   *
   * @param {string} id - 要移除的文件 ID
   */
  const handleRemoveFile = useCallback((id: string) => {
    const updatedFiles = files.filter((file) => file.id !== id);
    onFilesChange(updatedFiles);
  }, [files, onFilesChange]);

  /**
   * 是否可以添加更多文件
   */
  const canAddMore = files.length < maxFiles && !disabled;

  return (
    <div className={cn('w-full', className)}>
      {/* ==================== 上传区域 ==================== */}
      {canAddMore && (
        <motion.div
          {...getRootProps() as any}
          whileHover={{ scale: 1.01 }}   // 悬停时轻微放大
          whileTap={{ scale: 0.99 }}     // 点击时轻微缩小
          className={cn(
            'relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200',
            // 根据拖放状态应用不同样式
            isDragActive || dragActive
              ? 'border-primary-400 bg-primary-50'
              : 'border-secondary-300 bg-secondary-50 hover:bg-secondary-100',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          {/* 隐藏的文件输入 */}
          <input {...getInputProps()} />

          {/* 上传图标和提示文本 */}
          <div className="flex flex-col items-center space-y-4">
            {/* 上传图标（带动画） */}
            <motion.div
              animate={isDragActive || dragActive ? { scale: 1.1, rotate: 5 } : { scale: 1, rotate: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Upload className="w-12 h-12 text-primary-600" />
            </motion.div>
            {/* 提示文本 */}
            <div>
              <p className="text-lg font-medium text-secondary-900">
                {isDragActive || dragActive
                  ? 'Drop your files here'           // 拖放激活时
                  : 'Drop PDF or Word files here or click to browse'}  // 默认提示
              </p>
              <p className="text-sm text-secondary-600 mt-1">
                Maximum {formatFileSize(maxSize)} per file. Up to {maxFiles} files.
              </p>
              <p className="text-xs text-secondary-500 mt-1">
                Supported formats: PDF (.pdf), Word (.docx)
              </p>
            </div>
          </div>

          {/* ==================== 拖放时的背景动画 ==================== */}
          <AnimatePresence>
            {(isDragActive || dragActive) && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-primary-100 rounded-xl pointer-events-none"
                style={{ zIndex: -1 }}  // 置于底层
              />
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* ==================== 错误消息显示 ==================== */}
      <AnimatePresence>
        {errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 space-y-2"
          >
            {errors.map((error, index) => (
              <div
                key={index}
                className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg"
              >
                <AlertCircle className="w-4 h-4 text-error-600 flex-shrink-0" />
                <p className="text-sm text-error-800">{error}</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ==================== 文件列表 ==================== */}
      {files.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-secondary-900 mb-3">
            Uploaded Files ({files.length}/{maxFiles})
          </h3>
          <div className="space-y-2">
            <AnimatePresence>
              {files.map((file) => (
                <FileUploadItem
                  key={file.id}
                  file={file}
                  onRemove={handleRemoveFile}
                  disabled={disabled}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* ==================== 使用提示 ==================== */}
      {/* 仅在无文件且可添加时显示 */}
      {files.length === 0 && canAddMore && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start space-x-3">
            {/* 提示图标 */}
            <div className="flex-shrink-0">
              <div className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">i</span>
              </div>
            </div>
            {/* 提示内容 */}
            <div className="flex-1">
              <h4 className="text-sm font-medium text-blue-900">Tips for better results:</h4>
              <ul className="mt-2 text-sm text-blue-800 space-y-1">
                <li>• Use high-quality PDF or Word files with clear text</li>
                <li>• Files with structured content work best</li>
                <li>• Avoid scanned images or password-protected files</li>
                <li>• Larger files may take longer to process</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * 默认导出
 */
export default FileUploadZone;
