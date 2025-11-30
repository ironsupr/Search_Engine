import React from 'react';
import { motion } from 'framer-motion';
import type { SearchResult } from '../types';

interface SearchResultCardProps {
  result: SearchResult;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({ result }) => {
  // Extract domain for display
  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01, x: 4 }}
      transition={{ duration: 0.2 }}
      className="mb-8 group p-4 -mx-4 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-500 dark:text-gray-400 uppercase">
          {getDomain(result.url).charAt(0)}
        </div>
        <div className="flex flex-col">
          <span className="text-sm text-gray-900 dark:text-gray-200 font-medium">{getDomain(result.url)}</span>
          <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[300px]">{result.url}</span>
        </div>
      </div>
      
      <a href={result.url} target="_blank" rel="noopener noreferrer" className="block">
        <h3 className="text-xl text-blue-600 dark:text-blue-400 hover:underline visited:text-purple-600 dark:visited:text-purple-400 font-normal mb-1">
          {result.title || 'Untitled Page'}
        </h3>
      </a>
      
      <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed line-clamp-2 mb-2">
        {result.content}
      </p>
      
      <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
        <span className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">Score: {result.score.toFixed(2)}</span>
        {result.pagerank !== undefined && (
          <span className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">PR: {result.pagerank.toFixed(2)}</span>
        )}
      </div>
    </motion.div>
  );
};
