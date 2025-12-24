import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, File, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { cn, formatFileSize, isValidFileType, isValidFileSize } from '@/lib/utils';
import { FileUpload } from '@/types';

interface FileUploadZoneProps {
  onFilesChange: (files: FileUpload[]) => void;
  files: FileUpload[];
  maxFiles?: number;
  maxSize?: number;
  acceptedTypes?: string[];
  disabled?: boolean;
  className?: string;
}

interface FileUploadItemProps {
  file: FileUpload;
  onRemove: (id: string) => void;
  disabled?: boolean;
}

const FileUploadItem: React.FC<FileUploadItemProps> = ({ file, onRemove, disabled }) => {
  const getStatusIcon = () => {
    switch (file.status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin text-primary-600" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-success-600" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error-600" />;
      default:
        return <File className="w-4 h-4 text-secondary-600" />;
    }
  };

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

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        'flex items-center justify-between p-3 rounded-lg border transition-all duration-200',
        getStatusColor()
      )}
    >
      <div className="flex items-center space-x-3 flex-1 min-w-0">
        {getStatusIcon()}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-secondary-900 truncate">
            {file.name}
          </p>
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs text-secondary-600">
              {formatFileSize(file.size)}
            </span>
            {file.status === 'uploading' && file.progress !== undefined && (
              <>
                <span className="text-xs text-secondary-400">•</span>
                <span className="text-xs text-primary-600">
                  {file.progress}%
                </span>
              </>
            )}
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

      {!disabled && (
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => onRemove(file.id)}
          className="p-1 rounded-md hover:bg-secondary-200 transition-colors"
          disabled={file.status === 'uploading'}
        >
          <X className="w-4 h-4 text-secondary-600" />
        </motion.button>
      )}
    </motion.div>
  );
};

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onFilesChange,
  files,
  maxFiles = 2,
  maxSize = 100 * 1024 * 1024, // 100MB
  acceptedTypes = ['.pdf'],
  disabled = false,
  className,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validateFiles = useCallback((newFiles: File[]): string[] => {
    const newErrors: string[] = [];

    newFiles.forEach((file) => {
      // Check file type
      if (!isValidFileType(file, acceptedTypes)) {
        newErrors.push(`Invalid file type: ${file.name}. Only ${acceptedTypes.join(', ')} files are allowed.`);
        return;
      }

      // Check file size
      if (!isValidFileSize(file, maxSize)) {
        newErrors.push(`File too large: ${file.name}. Maximum size is ${formatFileSize(maxSize)}.`);
        return;
      }

      // Check for duplicates
      if (files.some((existingFile) => existingFile.name === file.name)) {
        newErrors.push(`Duplicate file: ${file.name}. This file has already been uploaded.`);
        return;
      }
    });

    return newErrors;
  }, [files, acceptedTypes, maxSize]);

  const processFiles = useCallback((newFiles: File[]) => {
    // Validate files
    const validationErrors = validateFiles(newFiles);
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      setTimeout(() => setErrors([]), 5000);
      return;
    }

    // Create file upload objects
    const fileUploads: FileUpload[] = newFiles.map((file) => ({
      id: Math.random().toString(36).substring(2) + Date.now().toString(36),
      file,
      name: file.name,
      size: file.size,
      sizeFormatted: formatFileSize(file.size),
      type: file.type,
      uploadedAt: new Date(),
      status: 'pending' as const,
    }));

    // Update files list
    const updatedFiles = [...files, ...fileUploads].slice(0, maxFiles);
    onFilesChange(updatedFiles);
    setErrors([]);
  }, [files, maxFiles, validateFiles, onFilesChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: processFiles,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles,
    maxSize,
    disabled: disabled || files.length >= maxFiles,
    noClick: disabled || files.length >= maxFiles,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    onDropAccepted: () => setDragActive(false),
    onDropRejected: () => setDragActive(false),
  });

  const handleRemoveFile = useCallback((id: string) => {
    const updatedFiles = files.filter((file) => file.id !== id);
    onFilesChange(updatedFiles);
  }, [files, onFilesChange]);

  const canAddMore = files.length < maxFiles && !disabled;

  return (
    <div className={cn('w-full', className)}>
      {/* Upload Zone */}
      {canAddMore && (
        <motion.div
          {...getRootProps()}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          className={cn(
            'relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200',
            isDragActive || dragActive
              ? 'border-primary-400 bg-primary-50'
              : 'border-secondary-300 bg-secondary-50 hover:bg-secondary-100',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center space-y-4">
            <motion.div
              animate={isDragActive || dragActive ? { scale: 1.1, rotate: 5 } : { scale: 1, rotate: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Upload className="w-12 h-12 text-primary-600" />
            </motion.div>
            <div>
              <p className="text-lg font-medium text-secondary-900">
                {isDragActive || dragActive
                  ? 'Drop your PDF files here'
                  : 'Drop PDF files here or click to browse'}
              </p>
              <p className="text-sm text-secondary-600 mt-1">
                Maximum {formatFileSize(maxSize)} per file. Up to {maxFiles} files.
              </p>
            </div>
          </div>

          {/* Animated background when dragging */}
          <AnimatePresence>
            {(isDragActive || dragActive) && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-primary-100 rounded-xl pointer-events-none"
                style={{ zIndex: -1 }}
              />
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Errors */}
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

      {/* File List */}
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

      {/* Tips */}
      {files.length === 0 && canAddMore && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">i</span>
              </div>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-blue-900">Tips for better results:</h4>
              <ul className="mt-2 text-sm text-blue-800 space-y-1">
                <li>• Use high-quality PDF files with clear text</li>
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

export default FileUploadZone;