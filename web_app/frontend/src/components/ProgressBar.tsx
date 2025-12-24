import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  progress: number;
  showPercentage?: boolean;
  showLabel?: boolean;
  label?: string;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  showPercentage = true,
  showLabel = false,
  label,
  color = 'primary',
  size = 'md',
  animated = true,
  className,
}) => {
  const getColorClasses = () => {
    const colors = {
      primary: {
        bg: 'bg-primary-100',
        fill: 'bg-primary-600',
        text: 'text-primary-600',
      },
      secondary: {
        bg: 'bg-secondary-100',
        fill: 'bg-secondary-600',
        text: 'text-secondary-600',
      },
      success: {
        bg: 'bg-success-100',
        fill: 'bg-success-600',
        text: 'text-success-600',
      },
      warning: {
        bg: 'bg-warning-100',
        fill: 'bg-warning-600',
        text: 'text-warning-600',
      },
      error: {
        bg: 'bg-error-100',
        fill: 'bg-error-600',
        text: 'text-error-600',
      },
    };
    return colors[color];
  };

  const getSizeClasses = () => {
    const sizes = {
      sm: {
        height: 'h-2',
        text: 'text-xs',
        radius: 'rounded-md',
      },
      md: {
        height: 'h-3',
        text: 'text-sm',
        radius: 'rounded-lg',
      },
      lg: {
        height: 'h-4',
        text: 'text-base',
        radius: 'rounded-xl',
      },
    };
    return sizes[size];
  };

  const colorClasses = getColorClasses();
  const sizeClasses = getSizeClasses();

  // Clamp progress between 0 and 100
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className={cn('w-full', className)}>
      {/* Label */}
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-2">
          {label && (
            <span className={cn('font-medium text-secondary-900', sizeClasses.text)}>
              {label}
            </span>
          )}
          {showPercentage && (
            <span className={cn('font-medium', colorClasses.text, sizeClasses.text)}>
              {clampedProgress.toFixed(1)}%
            </span>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div
        className={cn(
          'relative w-full overflow-hidden',
          colorClasses.bg,
          sizeClasses.height,
          sizeClasses.radius
        )}
      >
        {/* Background animation */}
        {animated && clampedProgress > 0 && clampedProgress < 100 && (
          <motion.div
            className="absolute inset-0 opacity-30"
            animate={{
              backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'linear',
            }}
            style={{
              background: `linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)`,
              backgroundSize: '200% 200%',
            }}
          />
        )}

        {/* Progress fill */}
        <motion.div
          className={cn(
            'h-full',
            colorClasses.fill,
            sizeClasses.radius,
            'relative'
          )}
          initial={{ width: '0%' }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{
            duration: 0.3,
            ease: 'easeOut',
          }}
        >
          {/* Shine effect for active progress */}
          {animated && clampedProgress > 0 && clampedProgress < 100 && (
            <motion.div
              className="absolute inset-0 opacity-60"
              animate={{
                x: ['-100%', '100%'],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'linear',
              }}
              style={{
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent)',
                width: '100%',
              }}
            />
          )}
        </motion.div>

        {/* Pulsing effect for indeterminate state */}
        {animated && (clampedProgress === 0 || clampedProgress === 100) && (
          <motion.div
            className={cn(
              'absolute inset-0',
              colorClasses.fill,
              'opacity-20',
              sizeClasses.radius
            )}
            animate={{
              opacity: [0.2, 0.5, 0.2],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </div>

      {/* Accessible progress text for screen readers */}
      <div className="sr-only" role="progressbar" aria-valuenow={clampedProgress} aria-valuemin={0} aria-valuemax={100}>
        Progress: {clampedProgress.toFixed(1)}%
      </div>
    </div>
  );
};

export default ProgressBar;