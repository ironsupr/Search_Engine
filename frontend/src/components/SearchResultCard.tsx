import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Copy, Check, MoreHorizontal } from 'lucide-react';
import type { SearchResult } from '../types';

interface SearchResultCardProps {
  result: SearchResult;
}

export const SearchResultCard: React.FC<SearchResultCardProps> = ({ result }) => {
  const [showActions, setShowActions] = useState(false);
  const [copied, setCopied] = useState(false);

  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  };

  const getBreadcrumbs = (url: string) => {
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname.split('/').filter(Boolean).slice(0, 2);
      return (
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 overflow-hidden">
          <span className="font-medium text-gray-700 dark:text-gray-300">{urlObj.hostname}</span>
          {path.map((segment, i) => (
            <React.Fragment key={i}>
              <span className="text-gray-300 dark:text-gray-600">›</span>
              <span className="truncate max-w-[100px]">{segment}</span>
            </React.Fragment>
          ))}
        </div>
      );
    } catch {
      return <span className="text-xs text-gray-500">{url}</span>;
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const handleCopyLink = (e: React.MouseEvent) => {
    e.preventDefault();
    navigator.clipboard.writeText(result.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const domain = getDomain(result.url);
  const faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.005 }}
      transition={{ duration: 0.2 }}
      className="mb-4 group relative p-4 sm:p-6 rounded-xl bg-white dark:bg-gray-900/40 border border-gray-100 dark:border-gray-800 hover:border-violet-200 dark:hover:border-violet-800/50 hover:shadow-lg hover:shadow-violet-500/5 transition-all duration-300"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Header: Icon + Breadcrumbs + Actions */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-50 dark:bg-gray-800 p-0.5 ring-1 ring-gray-100 dark:ring-gray-700">
            <img 
              src={faviconUrl} 
              alt="" 
              className="w-full h-full object-contain rounded-full opacity-80 group-hover:opacity-100 transition-opacity"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>';
              }}
            />
          </div>
          {getBreadcrumbs(result.url)}
        </div>
        
        <div className={`flex items-center gap-1 transition-opacity duration-200 ${showActions ? 'opacity-100' : 'opacity-0'}`}>
          <button 
            onClick={handleCopyLink}
            className="p-1.5 rounded-md text-gray-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20 transition-colors"
            title="Copy link"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
          <button className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Title */}
      <div className="mb-2">
        <a 
          href={result.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="group/link inline-block"
        >
          <h3 
            className="text-lg sm:text-xl font-semibold text-violet-700 dark:text-violet-400 group-hover/link:text-fuchsia-600 dark:group-hover/link:text-fuchsia-400 group-hover/link:underline decoration-2 decoration-fuchsia-200 dark:decoration-fuchsia-800 underline-offset-2 transition-colors"
            dangerouslySetInnerHTML={{ __html: result.title || 'Untitled Page' }}
          />
        </a>
      </div>
      
      {/* Snippet */}
      <div className="mb-3">
        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-2"
          dangerouslySetInnerHTML={{ __html: result.snippet || result.description || 'No description available' }}
        />
      </div>
      
      {/* Footer: Date + Score */}
      <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500">
        {result.crawled_at && (
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" />
            <span>{formatDate(result.crawled_at)}</span>
          </div>
        )}
        
        <div className="flex items-center gap-1.5" title={`Relevance Score: ${result.score.toFixed(4)}`}>
          <div className="w-16 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full"
              style={{ width: `${Math.min(result.score * 10, 100)}%` }}
            />
          </div>
          <span className="font-medium">{result.score.toFixed(2)}</span>
        </div>
      </div>
    </motion.div>
  );
};
