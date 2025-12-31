import axios, { AxiosResponse, AxiosError } from 'axios';
import {
  ComparisonRequest,
  TaskStatus,
  SimilarityResult,
  HealthStatus,
  ApiResponse,
  ExportFormat,
  ProcessingMode,
  ContentFilter,
  ExportFile,
} from '@/types';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token (if implemented in future)
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle common error scenarios
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    } else if (error.response?.status === 429) {
      // Handle rate limiting
      console.warn('Rate limit exceeded. Please try again later.');
    }
    return Promise.reject(error);
  }
);

// API Error handling
export class ApiError extends Error {
  public status: number;
  public code: string;
  public details?: any;

  constructor(message: string, status: number, code: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Helper function to handle API responses
const handleResponse = <T>(response: AxiosResponse<T>): T => {
  return response.data;
};

// Helper function to handle API errors
const handleError = (error: AxiosError): never => {
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

  if (error.response) {
    const { status, data } = error.response;
    const errorData = data as any;
    throw new ApiError(
      errorData?.error?.message || errorData?.message || 'An error occurred',
      status,
      errorData?.error?.code || 'UNKNOWN_ERROR',
      errorData?.error?.details
    );
  } else if (error.request) {
    console.error('[API] Request made but no response received');
    throw new ApiError('Network error. Please check your connection.', 0, 'NETWORK_ERROR');
  } else {
    console.error('[API] Error setting up request:', error.message);
    throw new ApiError('An unexpected error occurred.', 0, 'UNEXPECTED_ERROR');
  }
};

// API Endpoints
export const apiEndpoints = {
  // Health and status
  health: '/',
  check: '/health',

  // File operations
  upload: '/api/v1/upload',

  // Comparison operations
  compare: '/api/v1/compare',
  taskStatus: (taskId: string) => `/api/v1/task/${taskId}/status`,
  taskResult: (taskId: string) => `/api/v1/task/${taskId}/result`,
  deleteTask: (taskId: string) => `/api/v1/task/${taskId}`,

  // WebSocket
  websocket: (taskId: string) => `${WS_BASE_URL}/ws/${taskId}`,
};

// API Functions

// Health check
export const checkHealth = async (): Promise<HealthStatus> => {
  try {
    const response = await api.get(apiEndpoints.check);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

// Upload PDF file
export const uploadPdf = async (file: File, onUploadProgress?: (progress: number) => void): Promise<{ filePath: string; filename: string; fileSize: number }> => {
  console.log('[API] Uploading file:', file.name, 'size:', file.size);
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(apiEndpoints.upload, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
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

// Start PDF comparison
export const startComparison = async (request: ComparisonRequest): Promise<{ taskId: string; status: string; message: string }> => {
  console.log('[API] Starting comparison:', request);
  try {
    const response = await api.post(apiEndpoints.compare, request);
    console.log('[API] Comparison started:', response.data);
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

// Get task status
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

// Get task result
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

// Delete task
export const deleteTask = async (taskId: string): Promise<{ message: string }> => {
  try {
    const response = await api.delete(apiEndpoints.deleteTask(taskId));
    return handleResponse(response);
  } catch (error) {
    throw handleError(error as AxiosError);
  }
};

// WebSocket connection for real-time updates
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: ((message: any) => void)[] = [];
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  constructor(taskId: string) {
    this.url = apiEndpoints.websocket(taskId);
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.connectionHandlers.forEach(handler => handler(true));
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.messageHandlers.forEach(handler => handler(message));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          this.connectionHandlers.forEach(handler => handler(false));
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  onMessage(handler: (message: any) => void): void {
    this.messageHandlers.push(handler);
  }

  onConnectionChange(handler: (connected: boolean) => void): void {
    this.connectionHandlers.push(handler);
  }

  removeMessageHandler(handler: (message: any) => void): void {
    const index = this.messageHandlers.indexOf(handler);
    if (index > -1) {
      this.messageHandlers.splice(index, 1);
    }
  }

  removeConnectionHandler(handler: (connected: boolean) => void): void {
    const index = this.connectionHandlers.indexOf(handler);
    if (index > -1) {
      this.connectionHandlers.splice(index, 1);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Utility functions for creating requests
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
  } = {}
): ComparisonRequest => {
  return {
    pdf1Path,
    pdf2Path,
    similarityThreshold: options.similarityThreshold ?? 0.90,
    sequenceLength: options.sequenceLength ?? 8,
    contentFilter: options.contentFilter ?? ContentFilter.MAIN_CONTENT_ONLY,
    processingMode: options.processingMode ?? ProcessingMode.FAST,
    maxSequences: options.maxSequences ?? 5000,
    exportFormat: options.exportFormat ?? ExportFormat.JSON,
    contextChars: options.contextChars ?? 100,
  };
};

// Export file download utility
export const downloadExportFile = async (fileUrl: string, filename: string): Promise<void> => {
  try {
    const response = await fetch(fileUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(url);
  } catch (error) {
    throw new ApiError(`Failed to download file: ${filename}`, 0, 'DOWNLOAD_ERROR', error);
  }
};

// Batch operations
export const batchUploadPdfs = async (
  files: File[],
  onProgress?: (completed: number, total: number, currentFile: string) => void
): Promise<Array<{ filePath: string; filename: string; fileSize: number }>> => {
  const results = [];

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

// Export all API functions and classes
export default {
  // Configuration
  API_BASE_URL,

  // API functions
  checkHealth,
  uploadPdf,
  startComparison,
  getTaskStatus,
  getTaskResult,
  deleteTask,
  downloadExportFile,

  // Utilities
  createComparisonRequest,
  batchUploadPdfs,

  // Error handling
  ApiError,
  apiEndpoints,
  api,
};