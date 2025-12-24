import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  Download,
  Eye,
  Copy,
  ChevronDown,
  ChevronUp,
  FileText,
  BarChart3,
  ArrowRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { cn, formatSimilarity, getSimilarityColor, formatDate, truncateText } from '@/lib/utils';
import { SimilarSequence, SimilarityResult, ExportFormat } from '@/types';

interface SimilarityResultsProps {
  result: SimilarityResult;
  onExport?: (format: ExportFormat) => void;
  onViewContext?: (sequence: SimilarSequence) => void;
  className?: string;
}

interface SimilarityCardProps {
  sequence: SimilarSequence;
  index: number;
  onViewContext?: (sequence: SimilarSequence) => void;
  expanded?: boolean;
  onToggleExpanded?: () => void;
}

const SimilarityCard: React.FC<SimilarityCardProps> = ({
  sequence,
  index,
  onViewContext,
  expanded = false,
  onToggleExpanded,
}) => {
  const similarityColor = getSimilarityColor(sequence.similarity);
  const similarityPercentage = formatSimilarity(sequence.similarity);

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // Could add toast notification here
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const getSimilarityIcon = () => {
    if (sequence.similarity >= 0.9) {
      return <CheckCircle className="w-4 h-4 text-error-600" />;
    } else if (sequence.similarity >= 0.8) {
      return <AlertTriangle className="w-4 h-4 text-warning-600" />;
    } else {
      return <XCircle className="w-4 h-4 text-primary-600" />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="bg-white border border-secondary-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow duration-200"
    >
      {/* Header */}
      <div
        className={cn(
          'p-4 border-b cursor-pointer transition-colors',
          expanded ? 'bg-secondary-50' : 'hover:bg-secondary-50'
        )}
        onClick={onToggleExpanded}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            <div className="flex-shrink-0">
              <span className="inline-flex items-center justify-center w-8 h-8 bg-primary-100 text-primary-800 rounded-full text-sm font-medium">
                {index + 1}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3 mb-2">
                {getSimilarityIcon()}
                <span className={cn('inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border', similarityColor)}>
                  {similarityPercentage} Similar
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-secondary-600 mb-1">File 1</p>
                  <p className="text-sm font-mono bg-secondary-100 p-2 rounded border">
                    {truncateText(sequence.sequence1, 50)}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">
                    Page {sequence.position1.page}, Line {sequence.position1.line}
                  </p>
                </div>

                <div className="min-w-0">
                  <p className="text-xs font-medium text-secondary-600 mb-1">File 2</p>
                  <p className="text-sm font-mono bg-secondary-100 p-2 rounded border">
                    {truncateText(sequence.sequence2, 50)}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">
                    Page {sequence.position2.page}, Line {sequence.position2.line}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewContext?.(sequence);
              }}
              className="p-2 text-secondary-600 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors"
              title="View full context"
            >
              <Eye className="w-4 h-4" />
            </button>

            <button
              className="p-2 text-secondary-600 hover:rotate-180 transition-transform duration-200"
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="p-4 bg-secondary-50 border-t space-y-4">
              {/* Context Display */}
              <div>
                <h4 className="text-sm font-medium text-secondary-900 mb-3">Context</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-secondary-600 mb-2">File 1 Context</p>
                    <div className="bg-white p-3 rounded border text-sm">
                      <p className="font-mono text-secondary-700">
                        <span className="text-secondary-500">...</span>
                        <span className="text-primary-600 font-bold">
                          {sequence.context1.before.slice(-30)}
                        </span>
                        <span className="bg-primary-100 text-primary-800 font-bold px-1">
                          {sequence.sequence1}
                        </span>
                        <span className="text-primary-600 font-bold">
                          {sequence.context2.after.slice(0, 30)}
                        </span>
                        <span className="text-secondary-500">...</span>
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-secondary-600 mb-2">File 2 Context</p>
                    <div className="bg-white p-3 rounded border text-sm">
                      <p className="font-mono text-secondary-700">
                        <span className="text-secondary-500">...</span>
                        <span className="text-primary-600 font-bold">
                          {sequence.context2.before.slice(-30)}
                        </span>
                        <span className="bg-primary-100 text-primary-800 font-bold px-1">
                          {sequence.sequence2}
                        </span>
                        <span className="text-primary-600 font-bold">
                          {sequence.context2.after.slice(0, 30)}
                        </span>
                        <span className="text-secondary-500">...</span>
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Differences */}
              {sequence.differences && sequence.differences.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-secondary-900 mb-2">Differences</h4>
                  <div className="bg-white p-3 rounded border">
                    <ul className="space-y-1">
                      {sequence.differences.map((difference, idx) => (
                        <li key={idx} className="text-sm text-secondary-700 flex items-start space-x-2">
                          <ArrowRight className="w-3 h-3 text-primary-600 mt-0.5 flex-shrink-0" />
                          <span>{difference}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-secondary-500">
                  Similarity score: {sequence.similarity.toFixed(3)}
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => copyToClipboard(sequence.sequence1, 'Copy File 1 sequence')}
                    className="text-xs text-secondary-600 hover:text-primary-600 transition-colors"
                  >
                    Copy File 1
                  </button>
                  <button
                    onClick={() => copyToClipboard(sequence.sequence2, 'Copy File 2 sequence')}
                    className="text-xs text-secondary-600 hover:text-primary-600 transition-colors"
                  >
                    Copy File 2
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const SimilarityResults: React.FC<SimilarityResultsProps> = ({
  result,
  onExport,
  onViewContext,
  className,
}) => {
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [similarityFilter, setSimilarityFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<'similarity' | 'position'>('similarity');

  const toggleExpandedCard = (index: number) => {
    setExpandedCards((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const filteredAndSortedSequences = useMemo(() => {
    let filtered = result.similarSequences;

    // Apply similarity filter
    if (similarityFilter !== 'all') {
      filtered = filtered.filter((seq) => {
        if (similarityFilter === 'high') return seq.similarity >= 0.9;
        if (similarityFilter === 'medium') return seq.similarity >= 0.8 && seq.similarity < 0.9;
        if (similarityFilter === 'low') return seq.similarity >= 0.75 && seq.similarity < 0.8;
        return true;
      });
    }

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((seq) =>
        seq.sequence1.toLowerCase().includes(term) ||
        seq.sequence2.toLowerCase().includes(term)
      );
    }

    // Apply sorting
    if (sortBy === 'similarity') {
      filtered = [...filtered].sort((a, b) => b.similarity - a.similarity);
    } else {
      filtered = [...filtered].sort((a, b) => a.position1.page - b.position1.page);
    }

    return filtered;
  }, [result.similarSequences, similarityFilter, searchTerm, sortBy]);

  const getStatsBadge = (label: string, value: number, color: string) => (
    <div className={cn('px-3 py-2 rounded-lg border', color)}>
      <p className="text-xs text-secondary-600">{label}</p>
      <p className="text-lg font-semibold text-secondary-900">{value.toLocaleString()}</p>
    </div>
  );

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="bg-white rounded-xl border border-secondary-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-secondary-900">Similarity Analysis Results</h2>
            <p className="text-secondary-600 mt-1">
              Completed on {formatDate(result.comparisonInfo.processedAt)}
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'similarity' | 'position')}
              className="px-3 py-2 border border-secondary-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="similarity">Sort by Similarity</option>
              <option value="position">Sort by Position</option>
            </select>

            {onExport && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => onExport(ExportFormat.TEXT)}
                  className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Export</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {getStatsBadge('Total Found', result.similarityStats.similarSequencesFound, 'bg-primary-50 border-primary-200 text-primary-900')}
          {getStatsBadge('High Similarity', result.similarityStats.highSimilarityCount, 'bg-error-50 border-error-200 text-error-900')}
          {getStatsBadge('Medium Similarity', result.similarityStats.mediumSimilarityCount, 'bg-warning-50 border-warning-200 text-warning-900')}
          {getStatsBadge('Low Similarity', result.similarityStats.lowSimilarityCount, 'bg-primary-50 border-primary-200 text-primary-900')}
        </div>

        {/* Additional Stats */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 bg-secondary-50 rounded-lg">
            <p className="text-xs text-secondary-600">Average Similarity</p>
            <p className="text-lg font-semibold text-secondary-900">
              {formatSimilarity(result.similarityStats.averageSimilarity)}
            </p>
          </div>
          <div className="p-3 bg-secondary-50 rounded-lg">
            <p className="text-xs text-secondary-600">Highest Similarity</p>
            <p className="text-lg font-semibold text-secondary-900">
              {formatSimilarity(result.similarityStats.maxSimilarity)}
            </p>
          </div>
          <div className="p-3 bg-secondary-50 rounded-lg">
            <p className="text-xs text-secondary-600">Processing Time</p>
            <p className="text-lg font-semibold text-secondary-900">
              {result.processingTimeSeconds.toFixed(1)}s
            </p>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-xl border border-secondary-200 p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-secondary-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search sequences..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-sm text-secondary-600">Filter:</span>
            <div className="flex items-center space-x-2">
              {[
                { key: 'all', label: 'All', count: result.similarityStats.similarSequencesFound },
                { key: 'high', label: 'High', count: result.similarityStats.highSimilarityCount },
                { key: 'medium', label: 'Medium', count: result.similarityStats.mediumSimilarityCount },
                { key: 'low', label: 'Low', count: result.similarityStats.lowSimilarityCount },
              ].map(({ key, label, count }) => (
                <button
                  key={key}
                  onClick={() => setSimilarityFilter(key as any)}
                  className={cn(
                    'px-3 py-1 rounded-full text-sm font-medium transition-colors',
                    similarityFilter === key
                      ? 'bg-primary-600 text-white'
                      : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
                  )}
                >
                  {label} ({count})
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {filteredAndSortedSequences.length > 0 ? (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-secondary-600">
                Showing {filteredAndSortedSequences.length} of {result.similarSequences.length} similar sequences
              </p>
              <button
                onClick={() => setExpandedCards(expandedCards.size === filteredAndSortedSequences.length ? new Set() : new Set(filteredAndSortedSequences.map((_, i) => i)))}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                {expandedCards.size === filteredAndSortedSequences.length ? 'Collapse All' : 'Expand All'}
              </button>
            </div>

            <div className="space-y-4">
              {filteredAndSortedSequences.map((sequence, index) => (
                <SimilarityCard
                  key={index}
                  sequence={sequence}
                  index={index}
                  onViewContext={onViewContext}
                  expanded={expandedCards.has(index)}
                  onToggleExpanded={() => toggleExpandedCard(index)}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="bg-white rounded-xl border border-secondary-200 p-8 text-center">
            <div className="w-16 h-16 bg-secondary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-secondary-400" />
            </div>
            <h3 className="text-lg font-medium text-secondary-900 mb-2">No results found</h3>
            <p className="text-secondary-600">
              {searchTerm || similarityFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'No similar sequences were found between these files.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimilarityResults;