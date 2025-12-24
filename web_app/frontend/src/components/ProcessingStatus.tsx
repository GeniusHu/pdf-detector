import React from 'react';
import { motion } from 'framer-motion';
import {
  Loader2,
  FileText,
  Search,
  BarChart3,
  Download,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { cn, formatDuration, getSimilarityColor, getStatusColor } from '@/lib/utils';
import { TaskStatus, ProcessingMode } from '@/types';

interface ProcessingStatusProps {
  task: TaskStatus;
  currentStep?: string;
  estimatedTimeRemaining?: number;
  processingMode?: ProcessingMode;
  className?: string;
}

interface StepIndicatorProps {
  step: number;
  currentStep: number;
  label: string;
  icon: React.ReactNode;
  completed: boolean;
  active: boolean;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({
  step,
  currentStep,
  label,
  icon,
  completed,
  active,
}) => {
  return (
    <div className="flex items-center space-x-3">
      <div
        className={cn(
          'w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300',
          completed
            ? 'bg-success-600 text-white'
            : active
            ? 'bg-primary-600 text-white ring-4 ring-primary-100'
            : 'bg-secondary-200 text-secondary-600'
        )}
      >
        {completed ? (
          <CheckCircle className="w-5 h-5" />
        ) : (
          <div className="flex items-center justify-center">
            {icon}
          </div>
        )}
      </div>
      <div>
        <p
          className={cn(
            'text-sm font-medium',
            completed
              ? 'text-success-700'
              : active
              ? 'text-primary-700'
              : 'text-secondary-600'
          )}
        >
          Step {step}
        </p>
        <p
          className={cn(
            'text-xs',
            completed
              ? 'text-success-600'
              : active
              ? 'text-primary-600'
              : 'text-secondary-500'
          )}
        >
          {label}
        </p>
      </div>
    </div>
  );
};

const ProcessingModeBadge: React.FC<{ mode: ProcessingMode }> = ({ mode }) => {
  const getModeInfo = () => {
    switch (mode) {
      case ProcessingMode.ULTRA_FAST:
        return {
          label: 'Ultra Fast',
          icon: <Zap className="w-3 h-3" />,
          color: 'bg-warning-100 text-warning-800 border-warning-200',
        };
      case ProcessingMode.FAST:
        return {
          label: 'Fast',
          icon: <Zap className="w-3 h-3" />,
          color: 'bg-primary-100 text-primary-800 border-primary-200',
        };
      default:
        return {
          label: 'Standard',
          icon: <Clock className="w-3 h-3" />,
          color: 'bg-secondary-100 text-secondary-800 border-secondary-200',
        };
    }
  };

  const modeInfo = getModeInfo();

  return (
    <div className={cn('inline-flex items-center space-x-1 px-2 py-1 rounded-full border text-xs font-medium', modeInfo.color)}>
      {modeInfo.icon}
      <span>{modeInfo.label}</span>
    </div>
  );
};

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  task,
  currentStep,
  estimatedTimeRemaining,
  processingMode,
  className,
}) => {
  const getCurrentStepNumber = () => {
    if (task.status === 'pending') return 0;
    if (task.status === 'processing') {
      if (currentStep?.includes('Extracting')) return 1;
      if (currentStep?.includes('Detecting')) return 2;
      if (currentStep?.includes('Generating')) return 3;
      return 1;
    }
    if (task.status === 'completed') return 4;
    return 0;
  };

  const currentStepNumber = getCurrentStepNumber();

  const steps = [
    {
      step: 1,
      label: 'Extracting Content',
      icon: <FileText className="w-4 h-4" />,
    },
    {
      step: 2,
      label: 'Detecting Similarities',
      icon: <Search className="w-4 h-4" />,
    },
    {
      step: 3,
      label: 'Generating Results',
      icon: <BarChart3 className="w-4 h-4" />,
    },
    {
      step: 4,
      label: 'Completed',
      icon: <CheckCircle className="w-4 h-4" />,
    },
  ];

  const getStatusIcon = () => {
    switch (task.status) {
      case 'processing':
        return <Loader2 className="w-5 h-5 animate-spin text-primary-600" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-success-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-600" />;
      case 'cancelled':
        return <AlertCircle className="w-5 h-5 text-secondary-600" />;
      default:
        return <Clock className="w-5 h-5 text-secondary-600" />;
    }
  };

  const getStatusMessage = () => {
    if (task.status === 'processing') {
      return currentStep || 'Processing...';
    }
    if (task.status === 'completed') {
      return 'Analysis completed successfully!';
    }
    if (task.status === 'error') {
      return task.error || 'An error occurred during processing';
    }
    if (task.status === 'cancelled') {
      return 'Processing was cancelled';
    }
    return 'Waiting to start processing...';
  };

  return (
    <div className={cn('bg-white rounded-xl border border-secondary-200 p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-lg font-semibold text-secondary-900">
              Processing Status
            </h3>
            <p className="text-sm text-secondary-600">
              Task ID: {task.taskId}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {processingMode && <ProcessingModeBadge mode={processingMode} />}
          <div
            className={cn(
              'px-3 py-1 rounded-full border text-sm font-medium',
              getStatusColor(task.status)
            )}
          >
            {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-secondary-900">
            Progress
          </span>
          <span className="text-sm text-secondary-600">
            {task.progress.toFixed(1)}%
          </span>
        </div>
        <div className="relative w-full h-3 bg-secondary-100 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary-500 to-primary-600 rounded-full relative"
            initial={{ width: '0%' }}
            animate={{ width: `${task.progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            {task.status === 'processing' && (
              <motion.div
                className="absolute inset-0 bg-white opacity-30"
                animate={{
                  x: ['-100%', '100%'],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'linear',
                }}
                style={{ width: '50%' }}
              />
            )}
          </motion.div>
        </div>
      </div>

      {/* Current Status Message */}
      <div className="mb-6 p-4 bg-secondary-50 rounded-lg border border-secondary-200">
        <p className="text-sm text-secondary-800">{getStatusMessage()}</p>
        {estimatedTimeRemaining && task.status === 'processing' && (
          <p className="text-xs text-secondary-600 mt-1">
            Estimated time remaining: {formatDuration(estimatedTimeRemaining)}
          </p>
        )}
      </div>

      {/* Step Indicators */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium text-secondary-900">Processing Steps</h4>
        <div className="space-y-3">
          {steps.map((step) => (
            <StepIndicator
              key={step.step}
              step={step.step}
              currentStep={currentStepNumber}
              label={step.label}
              icon={step.icon}
              completed={currentStepNumber > step.step}
              active={currentStepNumber === step.step}
            />
          ))}
        </div>
      </div>

      {/* Processing Info */}
      {task.status === 'processing' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 bg-primary-50 rounded-lg border border-primary-200"
        >
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 animate-pulse" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-primary-900">
                Processing in Progress
              </p>
              <p className="text-xs text-primary-700 mt-1">
                This may take a few moments depending on file size and complexity.
                You can safely navigate away from this page; processing will continue in the background.
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default ProcessingStatus;