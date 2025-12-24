import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { FileText, BarChart3, Settings, Zap, Shield, ArrowRight } from 'lucide-react';
import FileUploadZone from '@/components/FileUpload';
import ProcessingStatus from '@/components/ProcessingStatus';
import SimilarityResults from '@/components/SimilarityResults';
import { FileUpload, TaskStatus, SimilarityResult, ProcessingMode, ContentFilter, ExportFormat } from '@/types';
import { uploadPdf, startComparison, getTaskStatus, getTaskResult } from '@/api';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

const HomePage: React.FC = () => {
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null);
  const [results, setResults] = useState<SimilarityResult | null>(null);
  const [processing, setProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('');
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Processing options
  const [processingMode, setProcessingMode] = useState<ProcessingMode>(ProcessingMode.FAST);
  const [contentFilter, setContentFilter] = useState<ContentFilter>(ContentFilter.MAIN_CONTENT_ONLY);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.75);
  const [exportFormat, setExportFormat] = useState<ExportFormat>(ExportFormat.JSON);

  const handleFilesChange = (newFiles: FileUpload[]) => {
    setFiles(newFiles);
    if (newFiles.length < 2) {
      setResults(null);
    }
  };

  // Poll task status
  const pollTaskStatus = async (taskId: string) => {
    try {
      const status = await getTaskStatus(taskId);
      setCurrentTask(status);
      setCurrentStep(status.message || '');

      // Check if task is completed
      if (status.status === 'completed') {
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
        setProcessing(false);
        // Fetch results
        const result = await getTaskResult(taskId);
        setResults(result);
        toast.success('Analysis completed successfully!');
      } else if (status.status === 'error') {
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
        setProcessing(false);
        toast.error(status.error || 'An error occurred during processing');
      }
    } catch (error) {
      console.error('Error polling status:', error);
    }
  };

  const handleStartComparison = async () => {
    if (files.length !== 2) {
      toast.error('Please select exactly 2 PDF files to compare');
      return;
    }

    // Check if all files are uploaded
    const pendingFiles = files.filter(f => f.status === 'pending' || f.status === 'uploading');
    if (pendingFiles.length > 0) {
      toast.error('Please wait for all files to finish uploading');
      return;
    }

    try {
      setProcessing(true);
      setCurrentStep('Initializing comparison...');

      // Start comparison
      const comparisonRequest = {
        pdf1Path: files[0].filePath!,
        pdf2Path: files[1].filePath!,
        similarityThreshold,
        contentFilter,
        processingMode,
        maxSequences: processingMode === ProcessingMode.ULTRA_FAST ? 2000 : 5000,
        exportFormat,
        contextChars: 100,
      };

      const response = await startComparison(comparisonRequest);

      // Set initial task status
      setCurrentTask({
        taskId: response.taskId,
        status: 'processing',
        progress: 0,
        startedAt: new Date().toISOString(),
        message: 'Processing started...',
      });

      // Start polling
      pollingRef.current = setInterval(() => {
        pollTaskStatus(response.taskId);
      }, 1000); // Poll every second

      toast.success('Comparison started successfully');

    } catch (error) {
      console.error('Error starting comparison:', error);
      toast.error('Failed to start comparison');
      setProcessing(false);
    }
  };

  const handleExport = async (format: ExportFormat) => {
    if (!results) return;

    try {
      const exportData = JSON.stringify(results, null, 2);
      const blob = new Blob([exportData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `similarity-results-${results.taskId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast.success('Results exported successfully');
    } catch (error) {
      console.error('Error exporting results:', error);
      toast.error('Failed to export results');
    }
  };

  const handleViewContext = (sequence: any) => {
    toast.success('Context view opened');
  };

  const handleReset = () => {
    // Stop polling if active
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setFiles([]);
    setCurrentTask(null);
    setResults(null);
    setProcessing(false);
    setCurrentStep('');
  };

  // Upload files as they are added
  useEffect(() => {
    files.forEach(async (file) => {
      if (file.status === 'pending') {
        try {
          setFiles(prev => prev.map(f =>
            f.id === file.id ? { ...f, status: 'uploading' } : f
          ));

          const uploadResult = await uploadPdf(file.file, (progress) => {
            setFiles(prev => prev.map(f =>
              f.id === file.id ? { ...f, progress } : f
            ));
          });

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
  }, [files]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const canStartComparison = files.length === 2 && files.every(f => f.status === 'completed');
  const hasResults = results !== null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-secondary-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-600 rounded-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-secondary-900">PDF Similarity Detector</h1>
                <p className="text-xs text-secondary-600">Advanced content analysis powered by AI</p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Welcome Section */}
          {!processing && !hasResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center space-y-4"
            >
              <h2 className="text-4xl font-bold text-secondary-900">
                Compare PDF Documents with Precision
              </h2>
              <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
                Upload two PDF files to detect similar content with our advanced AI-powered analysis.
                Get detailed results with context, similarity scores, and comprehensive statistics.
              </p>

              {/* Features */}
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
                    transition={{ delay: index * 0.1 }}
                    className="bg-white p-6 rounded-xl border border-secondary-200"
                  >
                    <div className="flex items-center justify-center w-12 h-12 bg-primary-100 text-primary-600 rounded-lg mb-4">
                      {feature.icon}
                    </div>
                    <h3 className="text-lg font-semibold text-secondary-900 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-secondary-600">
                      {feature.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Processing Options */}
          {!processing && !hasResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl border border-secondary-200 p-6"
            >
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Processing Options</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Processing Mode */}
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

                {/* Content Filter */}
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

                {/* Similarity Threshold */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Similarity Threshold: {(similarityThreshold * 100).toFixed(0)}%
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

                {/* Export Format */}
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

          {/* File Upload */}
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

          {/* Start Button */}
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
              <p className="text-sm text-secondary-600 mt-2">
                {files.length < 2
                  ? 'Please select 2 PDF files'
                  : !files.every(f => f.status === 'completed')
                  ? 'Please wait for files to finish uploading'
                  : 'Ready to compare your documents'}
              </p>
            </motion.div>
          )}

          {/* Processing Status */}
          {processing && currentTask && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <ProcessingStatus
                task={currentTask}
                currentStep={currentStep}
                estimatedTimeRemaining={undefined}
                processingMode={processingMode}
              />
            </motion.div>
          )}

          {/* Results */}
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

      {/* Footer */}
      <footer className="mt-16 bg-white/80 backdrop-blur-md border-t border-secondary-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-secondary-600">
            <p>PDF Similarity Detector - Advanced AI-powered document analysis</p>
            <p className="mt-2">Built with Next.js, FastAPI, and cutting-edge similarity detection algorithms</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
