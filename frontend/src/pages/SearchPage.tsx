import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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

  useEffect(() => {
    if (query) {
      fetchResults();
    }
  }, [query, page]);

  const fetchResults = async () => {
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
  };

  const handleSearch = (newQuery: string) => {
    if (newQuery === query) return;
    navigate(`/search?q=${encodeURIComponent(newQuery)}&page=1`);
  };

  const handlePageChange = (newPage: number) => {
    navigate(`/search?q=${encodeURIComponent(query)}&page=${newPage}`);
    window.scrollTo(0, 0);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 flex flex-col transition-colors duration-200">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center gap-4 md:gap-8">
          <Link to="/" className="flex-shrink-0">
            <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 hidden md:block">
              Search
            </span>
            <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 md:hidden">
              S
            </span>
          </Link>
          <div className="flex-1 max-w-2xl">
            <SearchBar onSearch={handleSearch} initialQuery={query} isLoading={loading} />
          </div>
          <div className="flex-shrink-0">
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        <div className="max-w-4xl">
          {loading ? (
            <div className="space-y-8 animate-pulse mt-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-800"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-32"></div>
                  </div>
                  <div className="h-6 bg-gray-200 dark:bg-gray-800 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-full"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg border border-red-100 dark:border-red-900/30">
              {error}
            </div>
          ) : data ? (
            <AnimatePresence mode="wait">
              <motion.div
                key={query + page}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-6 px-1">
                  Found {data.total} results ({data.time.toFixed(3)} seconds)
                </div>
                
                {data.results.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-gray-500 dark:text-gray-400 text-lg">
                      No results found for <span className="font-medium text-gray-900 dark:text-gray-100">"{query}"</span>
                    </p>
                    <p className="text-gray-400 dark:text-gray-500 mt-2">
                      Try checking your spelling or using different keywords.
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
                  <div className="mt-10 border-t border-gray-100 dark:border-gray-800 pt-6">
                    <Pagination
                      currentPage={page}
                      totalPages={Math.ceil(data.total / 10)}
                      onPageChange={handlePageChange}
                    />
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          ) : null}
        </div>
      </main>
    </div>
  );
};
