/**
 * 主页面组件
 *
 * 文档相似度检测应用的主页面，负责：
 * - 文件上传管理
 * - 比对参数配置
 * - 任务状态监控和轮询
 * - 结果展示和导出
 * - 用户交互处理
 *
 * @component HomePage
 * @author Document Similarity Detection Team
 * @version 1.0.0
 */

// ============================================================================
// 导入依赖
// ============================================================================

/**
 * React 核心功能导入
 * - useState: 状态管理 Hook
 * - useEffect: 副作用处理 Hook
 * - useRef: 可变引用 Hook（用于定时器等）
 */
import React, { useState, useEffect, useRef } from 'react';

/**
 * Framer Motion 动画库
 * - motion: 动画组件，用于创建流畅的 UI 动画
 */
import { motion } from 'framer-motion';

/**
 * Lucide React 图标库
 * 提供轻量级、可定制的图标组件
 */
import {
  FileText,        // 文档图标
  BarChart3,       // 图表图标
  Settings,        // 设置图标
  Zap,             // 闪电图标（表示快速）
  Shield,          // 盾牌图标（表示安全/过滤）
  ArrowRight,      // 右箭头图标
} from 'lucide-react';

/**
 * 自定义组件导入
 * 使用 @ 别名路径（在 tsconfig.json 中配置）
 */
import FileUploadZone from '@/components/FileUpload';         // 文件上传组件
import ProcessingStatus from '@/components/ProcessingStatus'; // 处理状态组件
import SimilarityResults from '@/components/SimilarityResults'; // 结果展示组件

/**
 * 类型定义导入
 */
import {
  FileUpload,           // 文件上传类型
  TaskStatus,           // 任务状态类型
  SimilarityResult,     // 相似度结果类型
  ProcessingMode,       // 处理模式枚举
  ContentFilter,        // 内容过滤器枚举
  ExportFormat,         // 导出格式枚举
  TaskStatusType,       // 任务状态类型枚举
} from '@/types';

/**
 * API 函数导入
 */
import {
  uploadPdf,        // 文件上传 API
  startComparison,  // 启动比对 API
  getTaskStatus,    // 获取任务状态 API
  getTaskResult,    // 获取任务结果 API
} from '@/api';

/**
 * 工具函数导入
 * - cn: 类名合并工具（基于 clsx 和 tailwind-merge）
 */
import { cn } from '@/lib/utils';

/**
 * Toast 通知库
 * 用于显示成功、错误等提示消息
 */
import toast from 'react-hot-toast';

// ============================================================================
// 组件定义
// ============================================================================

/**
 * 主页面组件
 *
 * @returns {JSX.Element} 主页面的 JSX 元素
 */
const HomePage: React.FC = () => {
  // ==========================================================================
  // 状态定义
  // ==========================================================================

  /**
   * 文件列表状态
   * 存储用户上传的所有文件及其状态
   */
  const [files, setFiles] = useState<FileUpload[]>([]);

  /**
   * 当前任务状态
   * 存储正在执行的比对任务的状态信息
   */
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null);

  /**
   * 比对结果状态
   * 存储任务完成后的相似度分析结果
   */
  const [results, setResults] = useState<SimilarityResult | null>(null);

  /**
   * 处理中状态
   * 标识当前是否正在处理任务
   */
  const [processing, setProcessing] = useState(false);

  /**
   * 当前处理步骤
   * 显示当前正在执行的处理步骤描述
   */
  const [currentStep, setCurrentStep] = useState<string>('');

  /**
   * 轮询定时器引用
   * 用于存储任务状态轮询的定时器 ID，以便清理
   */
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // ==========================================================================
  // 处理选项状态
  // ==========================================================================

  /**
   * 处理模式
   * 控制比对算法的性能和准确度平衡
   */
  const [processingMode, setProcessingMode] = useState<ProcessingMode>(ProcessingMode.STANDARD);

  /**
   * 内容过滤器
   * 决定哪些文档内容参与比对
   */
  const [contentFilter, setContentFilter] = useState<ContentFilter>(ContentFilter.MAIN_CONTENT_ONLY);

  /**
   * 相似度阈值
   * 只有相似度超过此值的序列才会被记录（0-1）
   */
  const [similarityThreshold, setSimilarityThreshold] = useState(0.90);

  /**
   * 序列长度
   * 用于比对的连续字符数量
   */
  const [sequenceLength, setSequenceLength] = useState(8);

  /**
   * 导出格式
   * 结果文件的导出格式
   */
  const [exportFormat, setExportFormat] = useState<ExportFormat>(ExportFormat.JSON);

  /**
   * 文件1页码范围
   * 可选：指定第一个文档的比对页码范围（如 "1-146"）
   */
  const [pageRange1, setPageRange1] = useState('');

  /**
   * 文件2页码范围
   * 可选：指定第二个文档的比对页码范围（如 "1-169"）
   */
  const [pageRange2, setPageRange2] = useState('');

  // ==========================================================================
  // 事件处理函数
  // ==========================================================================

  /**
   * 处理文件列表变化
   *
   * 当文件列表更新时调用此函数
   * 如果文件数少于2个，清除之前的比对结果
   *
   * @param {FileUpload[]} newFiles - 新的文件列表
   */
  const handleFilesChange = (newFiles: FileUpload[]) => {
    setFiles(newFiles);
    // 如果文件数少于2个，清除结果（需要重新比对）
    if (newFiles.length < 2) {
      setResults(null);
    }
  };

  /**
   * 轮询任务状态
   *
   * 定期向服务器查询任务的执行状态和进度
   * 当任务完成或出错时停止轮询
   *
   * @async
   * @param {string} taskId - 要查询的任务 ID
   */
  const pollTaskStatus = async (taskId: string) => {
    try {
      console.log('[FRONTEND] Polling task status:', taskId);
      // 从服务器获取任务状态
      const status = await getTaskStatus(taskId);
      console.log('[FRONTEND] Task status response:', status);

      // 更新任务状态
      setCurrentTask(status);
      setCurrentStep(status.message || '');

      // 检查任务是否完成
      if (status.status === 'completed') {
        console.log('[FRONTEND] Task completed, fetching results...');
        // 清除轮询定时器
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
        setProcessing(false);

        // 获取任务结果
        const result = await getTaskResult(taskId);
        console.log('[FRONTEND] Results fetched:', result);
        setResults(result);
        toast.success('Analysis completed successfully!');
      }
      // 检查任务是否出错
      else if (status.status === 'error') {
        console.log('[FRONTEND] Task error:', status.error);
        // 清除轮询定时器
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
        setProcessing(false);
        // 显示错误消息
        toast.error(status.error || 'An error occurred during processing');
      }
    } catch (error) {
      console.error('[FRONTEND] Error polling status:', error);
    }
  };

  /**
   * 处理开始比对
   *
   * 验证文件上传状态，构建比对请求，启动比对任务
   * 并开始轮询任务状态
   *
   * @async
   */
  const handleStartComparison = async () => {
    // 验证：必须恰好选择2个文档
    if (files.length !== 2) {
      toast.error('Please select exactly 2 documents (PDF or Word) to compare');
      return;
    }

    // 验证：所有文件必须已上传完成
    const pendingFiles = files.filter(f => f.status === 'pending' || f.status === 'uploading');
    if (pendingFiles.length > 0) {
      toast.error('Please wait for all files to finish uploading');
      return;
    }

    try {
      console.log('[FRONTEND] Starting comparison...');
      setProcessing(true);
      setCurrentStep('Initializing comparison...');

      // 构建比对请求参数
      const comparisonRequest = {
        pdf1Path: files[0].filePath!,        // 第一个文件的服务器路径
        pdf2Path: files[1].filePath!,        // 第二个文件的服务器路径
        similarityThreshold,                  // 相似度阈值
        sequenceLength,                       // 序列长度
        contentFilter,                        // 内容过滤器
        processingMode,                       // 处理模式
        maxSequences: processingMode === ProcessingMode.ULTRA_FAST ? 2000 : 5000, // 根据模式调整最大序列数
        exportFormat,                         // 导出格式
        contextChars: 100,                    // 上下文字符数
        pageRange1: pageRange1 || undefined,  // 文件1页码范围（如果提供）
        pageRange2: pageRange2 || undefined,  // 文件2页码范围（如果提供）
      };

      console.log('[FRONTEND] Comparison request:', comparisonRequest);

      // 发送比对请求到服务器
      const response = await startComparison(comparisonRequest);
      console.log('[FRONTEND] Comparison response:', response);

      // 验证响应是否包含任务 ID
      if (!response || !response.taskId) {
        console.error('[FRONTEND] Invalid response:', response);
        toast.error('Invalid response from server');
        setProcessing(false);
        return;
      }

      // 初始化任务状态对象
      const taskStatus = {
        taskId: response.taskId,
        status: TaskStatusType.PROCESSING,
        progress: 0,
        startedAt: new Date().toISOString(),
        message: 'Processing started...',
      };
      console.log('[FRONTEND] Setting task status:', taskStatus);
      setCurrentTask(taskStatus);

      // 开始轮询任务状态（每2秒一次）
      console.log('[FRONTEND] Starting polling for task:', response.taskId);
      pollingRef.current = setInterval(() => {
        console.log('[FRONTEND] Polling task:', response.taskId);
        pollTaskStatus(response.taskId);
      }, 2000); // 轮询间隔：2秒（原来是10秒）

      toast.success('Comparison started successfully');

    } catch (error) {
      console.error('Error starting comparison:', error);
      toast.error('Failed to start comparison');
      setProcessing(false);
    }
  };

  /**
   * 处理导出结果
   *
   * 将比对结果导出为指定格式的文件并下载
   *
   * @async
   * @param {ExportFormat} format - 导出格式
   */
  const handleExport = async (format: ExportFormat) => {
    if (!results) return;

    try {
      // 将结果对象转换为 JSON 字符串
      const exportData = JSON.stringify(results, null, 2);
      // 创建 Blob 对象
      const blob = new Blob([exportData], { type: 'application/json' });
      // 创建临时 URL
      const url = URL.createObjectURL(blob);
      // 创建下载链接
      const a = document.createElement('a');
      a.href = url;
      a.download = `similarity-results-${results.taskId}.${format}`;
      document.body.appendChild(a);
      // 触发下载
      a.click();
      document.body.removeChild(a);
      // 释放临时 URL
      URL.revokeObjectURL(url);

      toast.success('Results exported successfully');
    } catch (error) {
      console.error('Error exporting results:', error);
      toast.error('Failed to export results');
    }
  };

  /**
   * 处理查看上下文
   *
   * 当用户点击查看某个相似序列的上下文时调用
   * （当前实现仅为占位符）
   *
   * @param {any} sequence - 相似序列对象
   */
  const handleViewContext = (sequence: any) => {
    toast.success('Context view opened');
  };

  /**
   * 处理重置
   *
   * 清除所有状态，准备新的比对任务
   * 停止轮询定时器
   */
  const handleReset = () => {
    // 停止轮询定时器
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    // 重置所有状态
    setFiles([]);
    setCurrentTask(null);
    setResults(null);
    setProcessing(false);
    setCurrentStep('');
  };

  // ==========================================================================
  // 副作用处理
  // ==========================================================================

  /**
   * 文件上传副作用
   *
   * 监听文件列表变化，自动上传处于 'pending' 状态的文件
   * 使用 useEffect 实现文件添加后自动触发上传
   */
  useEffect(() => {
    files.forEach(async (file) => {
      // 检查文件是否需要上传
      if (file.status === 'pending') {
        try {
          // 更新文件状态为 'uploading'
          setFiles(prev => prev.map(f =>
            f.id === file.id ? { ...f, status: 'uploading' } : f
          ));

          // 调用上传 API，传入进度回调
          const uploadResult = await uploadPdf(file.file, (progress) => {
            // 更新上传进度
            setFiles(prev => prev.map(f =>
              f.id === file.id ? { ...f, progress } : f
            ));
          });

          // 上传成功，更新文件状态
          setFiles(prev => prev.map(f =>
            f.id === file.id ? {
              ...f,
              status: 'completed',
              filePath: uploadResult.filePath,
              progress: 100
            } : f
          ));

        } catch (error) {
          console.error('Error uploading file:', error);
          // 上传失败，更新文件状态为 'error'
          setFiles(prev => prev.map(f =>
            f.id === file.id ? {
              ...f,
              status: 'error',
              error: 'Upload failed'
            } : f
          ));
          toast.error(`Failed to upload ${file.name}`);
        }
      }
    });
  }, [files]); // 依赖：文件列表

  /**
   * 清理副作用
   *
   * 组件卸载时清除轮询定时器，防止内存泄漏
   */
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []); // 仅在组件卸载时执行

  // ==========================================================================
  // 派生状态
  // ==========================================================================

  /**
   * 是否可以开始比对
   * 条件：恰好有2个文件且都已上传完成
   */
  const canStartComparison = files.length === 2 && files.every(f => f.status === 'completed');

  /**
   * 是否有比对结果
   */
  const hasResults = results !== null;

  // ==========================================================================
  // 渲染
  // ==========================================================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      {/* ==================== 页头 ==================== */}
      <header className="bg-white/80 backdrop-blur-md border-b border-secondary-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* 左侧：Logo 和标题 */}
            <div className="flex items-center space-x-3">
              {/* 图标容器 */}
              <div className="p-2 bg-primary-600 rounded-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
              {/* 标题和副标题 */}
              <div>
                <h1 className="text-xl font-bold text-secondary-900">Document Similarity Detector</h1>
                <p className="text-xs text-secondary-600">Advanced content analysis powered by AI (PDF & Word)</p>
              </div>
            </div>

            {/* 右侧：操作按钮 */}
            <div className="flex items-center space-x-4">
              {/* 仅在有结果时显示"新建比对"按钮 */}
              {hasResults && (
                <button
                  onClick={handleReset}
                  className="px-4 py-2 bg-secondary-600 text-white rounded-lg hover:bg-secondary-700 transition-colors text-sm font-medium"
                >
                  New Comparison
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ==================== 主内容区 ==================== */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* ==================== 欢迎区域 ==================== */}
          {/* 仅在非处理状态且无结果时显示 */}
          {!processing && !hasResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center space-y-4"
            >
              <h2 className="text-4xl font-bold text-secondary-900">
                Compare Documents with Precision
              </h2>
              <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
                Upload two PDF or Word documents to detect similar content with our advanced AI-powered analysis.
                Get detailed results with context, similarity scores, and comprehensive statistics.
              </p>

              {/* 功能特性展示 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                {[
                  {
                    icon: <Zap className="w-6 h-6" />,
                    title: 'Lightning Fast',
                    description: 'Optimized algorithms process large files in minutes',
                  },
                  {
                    icon: <Shield className="w-6 h-6" />,
                    title: 'Content Filtering',
                    description: 'Focus on main content by filtering references and metadata',
                  },
                  {
                    icon: <BarChart3 className="w-6 h-6" />,
                    title: 'Detailed Analytics',
                    description: 'Comprehensive statistics and similarity metrics',
                  },
                ].map((feature, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }} // 级联延迟动画
                    className="bg-white p-6 rounded-xl border border-secondary-200"
                  >
                    {/* 功能图标 */}
                    <div className="flex items-center justify-center w-12 h-12 bg-primary-100 text-primary-600 rounded-lg mb-4">
                      {feature.icon}
                    </div>
                    {/* 功能标题 */}
                    <h3 className="text-lg font-semibold text-secondary-900 mb-2">
                      {feature.title}
                    </h3>
                    {/* 功能描述 */}
                    <p className="text-secondary-600">
                      {feature.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ==================== 处理选项配置 ==================== */}
          {/* 仅在非处理状态且无结果时显示 */}
          {!processing && !hasResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl border border-secondary-200 p-6"
            >
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Processing Options</h3>

              {/* 第一行：页码范围配置 */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                {/* 文件1页码范围 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    File 1 Page Range (Optional)
                  </label>
                  <input
                    type="text"
                    value={pageRange1}
                    onChange={(e) => setPageRange1(e.target.value)}
                    placeholder="e.g., 1-146"
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-secondary-500 mt-1">Leave empty for all pages</p>
                </div>

                {/* 文件2页码范围 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    File 2 Page Range (Optional)
                  </label>
                  <input
                    type="text"
                    value={pageRange2}
                    onChange={(e) => setPageRange2(e.target.value)}
                    placeholder="e.g., 1-169"
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-secondary-500 mt-1">Leave empty for all pages</p>
                </div>
              </div>

              {/* 第二行：核心处理参数 */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mt-4">
                {/* 处理模式选择 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Processing Mode
                  </label>
                  <select
                    value={processingMode}
                    onChange={(e) => setProcessingMode(e.target.value as ProcessingMode)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={ProcessingMode.STANDARD}>Standard (Most Accurate)</option>
                    <option value={ProcessingMode.FAST}>Fast (Recommended)</option>
                    <option value={ProcessingMode.ULTRA_FAST}>Ultra Fast (Quick Results)</option>
                  </select>
                </div>

                {/* 内容过滤器选择 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Content Filter
                  </label>
                  <select
                    value={contentFilter}
                    onChange={(e) => setContentFilter(e.target.value as ContentFilter)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={ContentFilter.MAIN_CONTENT_ONLY}>Main Content Only</option>
                    <option value={ContentFilter.ALL_CONTENT}>All Content</option>
                    <option value={ContentFilter.INCLUDE_REFERENCES}>Include References</option>
                    <option value={ContentFilter.INCLUDE_CITATIONS}>Include Citations</option>
                  </select>
                </div>

                {/* 相似度阈值滑块 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Similarity: {(similarityThreshold * 100).toFixed(0)}%
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.05"
                    value={similarityThreshold}
                    onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-secondary-500 mt-1">
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                {/* 序列长度选择 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Sequence Length
                  </label>
                  <select
                    value={sequenceLength}
                    onChange={(e) => setSequenceLength(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={4}>4 characters</option>
                    <option value={5}>5 characters</option>
                    <option value={6}>6 characters</option>
                    <option value={7}>7 characters</option>
                    <option value={8}>8 characters</option>
                    <option value={9}>9 characters</option>
                    <option value={10}>10 characters</option>
                    <option value={12}>12 characters</option>
                    <option value={15}>15 characters</option>
                    <option value={20}>20 characters</option>
                  </select>
                  <p className="text-xs text-secondary-500 mt-1">Consecutive chars for matching</p>
                </div>

                {/* 导出格式选择 */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Export Format
                  </label>
                  <select
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={ExportFormat.JSON}>JSON</option>
                    <option value={ExportFormat.TEXT}>Text Report</option>
                    <option value={ExportFormat.CSV}>CSV</option>
                    <option value={ExportFormat.PDF_REPORT}>PDF Report</option>
                  </select>
                </div>
              </div>
            </motion.div>
          )}

          {/* ==================== 文件上传区域 ==================== */}
          {/* 仅在非处理状态且无结果时显示 */}
          {!processing && !hasResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <FileUploadZone
                files={files}
                onFilesChange={handleFilesChange}
                maxFiles={2}
              />
            </motion.div>
          )}

          {/* ==================== 开始比对按钮 ==================== */}
          {/* 仅在有文件、非处理状态且无结果时显示 */}
          {!processing && !hasResults && files.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-center"
            >
              <button
                onClick={handleStartComparison}
                disabled={!canStartComparison}
                className={cn(
                  'px-8 py-3 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2 mx-auto',
                  canStartComparison
                    ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-lg hover:shadow-xl'
                    : 'bg-secondary-300 text-secondary-500 cursor-not-allowed'
                )}
              >
                <span>Start Comparison</span>
                <ArrowRight className="w-5 h-5" />
              </button>
              {/* 按钮状态提示文本 */}
              <p className="text-sm text-secondary-600 mt-2">
                {files.length < 2
                  ? 'Please select 2 documents (PDF or Word)'
                  : !files.every(f => f.status === 'completed')
                  ? 'Please wait for files to finish uploading'
                  : 'Ready to compare your documents'}
              </p>
            </motion.div>
          )}

          {/* ==================== 处理状态显示 ==================== */}
          {/* 仅在处理状态时显示 */}
          {processing && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {currentTask ? (
                // 显示任务处理状态
                <ProcessingStatus
                  task={currentTask}
                  currentStep={currentStep}
                  estimatedTimeRemaining={undefined}
                  processingMode={processingMode}
                />
              ) : (
                // 显示初始化加载动画
                <div className="bg-white rounded-xl border border-secondary-200 p-6 text-center">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                    <h3 className="text-lg font-semibold text-secondary-900">Starting comparison...</h3>
                    <p className="text-sm text-secondary-600">Please wait while we initialize the task</p>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* ==================== 比对结果展示 ==================== */}
          {/* 仅在有结果时显示 */}
          {results && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <SimilarityResults
                result={results}
                onExport={handleExport}
                onViewContext={handleViewContext}
              />
            </motion.div>
          )}
        </div>
      </main>

      {/* ==================== 页脚 ==================== */}
      <footer className="mt-16 bg-white/80 backdrop-blur-md border-t border-secondary-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-secondary-600">
            <p>Document Similarity Detector - Advanced AI-powered document analysis (PDF & Word)</p>
            <p className="mt-2">Built with Next.js, FastAPI, and cutting-edge similarity detection algorithms</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
