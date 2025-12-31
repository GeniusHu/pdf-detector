// API and Application Types

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
}

export interface TaskStatus {
  taskId: string;
  status: TaskStatusType;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  message?: string;
}

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

export interface WebSocketMessage {
  type: string;
  taskId?: string;
  data: any;
  timestamp: number;
}

export interface ProgressUpdate {
  progress: number;
  message: string;
  currentStep: string;
  estimatedRemainingSeconds?: number;
  details?: Record<string, any>;
}

export interface ExportFile {
  format: ExportFormat;
  filePath: string;
  fileSize: number;
  downloadUrl: string;
}

export interface ProcessingOptions {
  similarityThreshold: number;
  sequenceLength: number;
  contentFilter: ContentFilter;
  processingMode: ProcessingMode;
  maxSequences: number;
  exportFormat: ExportFormat;
  contextChars: number;
}

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

// Enums
export enum ContentFilter {
  ALL_CONTENT = 'all',
  MAIN_CONTENT_ONLY = 'main_content_only',
  INCLUDE_REFERENCES = 'include_references',
  INCLUDE_CITATIONS = 'include_citations',
}

export enum ProcessingMode {
  STANDARD = 'standard',
  FAST = 'fast',
  ULTRA_FAST = 'ultra_fast',
}

export enum ExportFormat {
  TEXT = 'text',
  JSON = 'json',
  CSV = 'csv',
  PDF_REPORT = 'pdf_report',
}

export enum TaskStatusType {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  ERROR = 'error',
  CANCELLED = 'cancelled',
}

// UI State Types
export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  notifications: Notification[];
  loading: boolean;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  duration?: number;
  persistent?: boolean;
}

// Component Props Types
export interface FileUploadZoneProps {
  onFilesDrop: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number;
  acceptedTypes?: string[];
  disabled?: boolean;
  className?: string;
}

export interface ProgressBarProps {
  progress: number;
  showPercentage?: boolean;
  showLabel?: boolean;
  label?: string;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

export interface SimilarityChartProps {
  data: SimilarSequence[];
  height?: number;
  showDetails?: boolean;
  onSequenceClick?: (sequence: SimilarSequence) => void;
}

export interface ContextDisplayProps {
  sequence: SimilarSequence;
  contextChars?: number;
  showDifferences?: boolean;
  compact?: boolean;
}

export interface ExportOptionsProps {
  formats: ExportFormat[];
  selectedFormat: ExportFormat;
  onFormatChange: (format: ExportFormat) => void;
  onExport: (format: ExportFormat) => void;
  loading?: boolean;
  disabled?: boolean;
}

// Store Types
export interface AppState {
  files: FileUpload[];
  currentTask: TaskStatus | null;
  results: SimilarityResult | null;
  processing: boolean;
  error: string | null;
  settings: ProcessingOptions;
}

export interface FileState {
  uploads: FileUpload[];
  selectedFiles: string[];
  uploadProgress: Record<string, number>;
}

export interface TaskState {
  activeTasks: Record<string, TaskStatus>;
  completedTasks: TaskStatus[];
  currentTaskId: string | null;
}

export interface ResultState {
  currentResult: SimilarityResult | null;
  resultHistory: SimilarityResult[];
  exportHistory: ExportFile[];
}

// Hook Return Types
export interface UseFileUploadReturn {
  files: FileUpload[];
  uploadFile: (file: File) => Promise<string>;
  removeFile: (id: string) => void;
  clearFiles: () => void;
  uploadProgress: Record<string, number>;
  isUploading: boolean;
  error: string | null;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  disconnect: () => void;
  error: string | null;
}

export interface UseSimilarityDetectionReturn {
  startComparison: (request: ComparisonRequest) => Promise<string>;
  cancelTask: (taskId: string) => Promise<void>;
  getTaskStatus: (taskId: string) => Promise<TaskStatus>;
  getResults: (taskId: string) => Promise<SimilarityResult>;
  exportResults: (taskId: string, format: ExportFormat) => Promise<ExportFile>;
  isProcessing: boolean;
  error: string | null;
}