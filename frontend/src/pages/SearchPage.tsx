import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, Clock, Zap } from 'lucide-react';
import SearchBar from '../components/SearchBar';
import { SearchResultCard } from '../components/SearchResultCard';
import { Pagination } from '../components/Pagination';
import { ThemeToggle } from '../components/ThemeToggle';
import { searchApi } from '../services/api';
import type { SearchResponse } from '../types';

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  const page = parseInt(searchParams.get('page') || '1', 10);
  
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchResults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await searchApi.search(query, page);
      setData(response);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      if (axiosError.response?.data?.detail?.includes('index_not_found')) {
        setError('No content has been indexed yet. Please run the crawler first to index some web pages.');
      } else {
        setError('Failed to fetch search results. Please try again.');
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [query, page]);

  useEffect(() => {
    if (query) {
      fetchResults();
    }
  }, [query, page, fetchResults]);

  const handleSearch = (newQuery: string) => {
    if (newQuery === query) return;
    navigate(`/search?q=${encodeURIComponent(newQuery)}&page=1`);
  };

  const handlePageChange = (newPage: number) => {
    navigate(`/search?q=${encodeURIComponent(query)}&page=${newPage}`);
    window.scrollTo(0, 0);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0a] flex flex-col transition-colors duration-500 relative overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-violet-200/20 blur-[100px] dark:bg-violet-900/10 animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-fuchsia-200/20 blur-[100px] dark:bg-fuchsia-900/10 animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-20 bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-gray-200/50 dark:border-gray-800/50 supports-[backdrop-filter]:bg-white/60 transition-all duration-300">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-4 md:gap-8">
          <Link to="/" className="flex-shrink-0 group mr-2">
            <span className="text-xl sm:text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-600 via-fuchsia-600 to-indigo-600 dark:from-violet-400 dark:via-fuchsia-400 dark:to-indigo-400 hidden md:block group-hover:opacity-80 transition-opacity">
              EchoSearch
            </span>
            <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-600 via-fuchsia-600 to-indigo-600 md:hidden">
              E
            </span>
          </Link>
          <div className="flex-1 flex justify-center max-w-3xl w-full">
            <SearchBar onSearch={handleSearch} initialQuery={query} isLoading={loading} />
          </div>
          <div className="flex-shrink-0 ml-2">
            <ThemeToggle />
          </div>
        </div>
        
        {/* Stats Bar */}
        {data && !loading && !error && (
          <div className="border-t border-gray-100 dark:border-gray-800/50 bg-white/50 dark:bg-[#0a0a0a]/50 backdrop-blur-sm">
            <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-2 flex items-center gap-6 text-xs font-medium text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5" />
                <span>{data.total.toLocaleString()} results</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>{(data.took_ms / 1000).toFixed(3)}s</span>
              </div>
              {data.cached && (
                <div className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                  <Zap className="w-3.5 h-3.5" />
                  <span>Cached</span>
                </div>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full relative z-10">
        <div className="flex gap-8">
          {/* Sidebar (Desktop) */}
          <aside className="hidden lg:block w-64 flex-shrink-0 space-y-6">
            <div className="sticky top-32">
              <div className="p-4 rounded-xl bg-white/50 dark:bg-gray-900/20 border border-gray-100 dark:border-gray-800/50 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">
                  <Filter className="w-4 h-4" />
                  <span>Filters</span>
                </div>
                <div className="space-y-2">
                  <div className="text-xs text-gray-500 dark:text-gray-400 uppercase font-bold tracking-wider mb-2">Time</div>
                  {['Any time', 'Past 24 hours', 'Past week', 'Past month', 'Past year'].map((filter) => (
                    <button key={filter} className="block w-full text-left px-2 py-1.5 text-sm rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                      {filter}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          {/* Results Column */}
          <div className="flex-1 max-w-3xl">
            {loading ? (
              <div className="space-y-6 animate-pulse">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="p-6 rounded-xl bg-white/50 dark:bg-gray-900/20 border border-gray-100 dark:border-gray-800/50">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-800"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-32"></div>
                    </div>
                    <div className="h-5 bg-gray-200 dark:bg-gray-800 rounded w-3/4 mb-3"></div>
                    <div className="space-y-2">
                      <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-full"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-5/6"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : error ? (
              <div className="p-6 bg-red-50/50 dark:bg-red-900/10 text-red-600 dark:text-red-400 rounded-2xl border border-red-100 dark:border-red-900/20 backdrop-blur-sm flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-full">
                  <Search className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-medium">Something went wrong</h3>
                  <p className="text-sm opacity-90">{error}</p>
                </div>
              </div>
            ) : data ? (
              <AnimatePresence mode="wait">
                <motion.div
                  key={query + page}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  {data.results.length === 0 ? (
                    <div className="text-center py-20 bg-white/30 dark:bg-gray-900/30 rounded-3xl border border-gray-100 dark:border-gray-800 backdrop-blur-sm">
                      <div className="inline-flex items-center justify-center p-6 rounded-full bg-violet-50 dark:bg-violet-900/20 mb-6 ring-1 ring-violet-100 dark:ring-violet-800/30">
                        <Search className="w-10 h-10 text-violet-500 dark:text-violet-400" />
                      </div>
                      <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                        No results found
                      </h3>
                      <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                        We couldn't find anything matching <span className="font-medium text-gray-900 dark:text-gray-100">"{query}"</span>. 
                        Try adjusting your search terms or filters.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {data.results.map((result, index) => (
                        <SearchResultCard key={index} result={result} />
                      ))}
                    </div>
                  )}

                  {data.total > 0 && (
                    <div className="mt-12 pt-8 border-t border-gray-200/50 dark:border-gray-800/50">
                      <Pagination
                        currentPage={page}
                        totalPages={data.total_pages}
                        onPageChange={handlePageChange}
                      />
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
};
