import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Terminal, Play, CheckCircle, XCircle, Loader2, Shield, Lock } from 'lucide-react';
import { ThemeToggle } from '../components/ThemeToggle';

interface CrawlResult {
  url: string;
  success: boolean;
  title?: string;
  error?: string;
}

interface CrawlResponse {
  total: number;
  success: number;
  failed: number;
  took_ms: number;
  results: CrawlResult[];
}

export const AdminPage: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [urls, setUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<CrawlResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === 'echosearch') {
      setIsAuthenticated(true);
    } else {
      setError('Access Denied');
      setTimeout(() => setError(null), 2000);
    }
  };

  const handleCrawl = async () => {
    if (!urls.trim()) return;
    
    setLoading(true);
    setError(null);
    setResults(null);

    const urlList = urls.split('\n').map(u => u.trim()).filter(u => u);

    try {
      const response = await fetch('http://localhost:8000/crawl-index/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: urlList })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to start crawl');
      }

      const data = await response.json();
      setResults(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0a] flex items-center justify-center p-4 transition-colors duration-500">
        <div className="max-w-md w-full">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white dark:bg-gray-900/50 p-8 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xl backdrop-blur-sm"
          >
            <div className="flex justify-center mb-6">
              <div className="p-3 bg-violet-100 dark:bg-violet-900/30 rounded-full">
                <Lock className="w-8 h-8 text-violet-600 dark:text-violet-400" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-center mb-6 text-gray-900 dark:text-white">Restricted Access</h2>
            <form onSubmit={handleLogin} className="space-y-4">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter access code"
                className="w-full px-4 py-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-violet-500 outline-none transition-all text-gray-900 dark:text-white"
                autoFocus
              />
              {error && <p className="text-red-500 text-sm text-center">{error}</p>}
              <button
                type="submit"
                className="w-full py-3 rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-medium transition-colors"
              >
                Unlock Console
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0a] transition-colors duration-500">
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-6 h-6 text-violet-600 dark:text-violet-400" />
            <span className="font-bold text-lg text-gray-900 dark:text-white">EchoSearch Console</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Input Section */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-4"
          >
            <div className="bg-white dark:bg-gray-900/50 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-violet-500" />
                Instant Indexer
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Enter URLs to crawl and index immediately. One URL per line.
              </p>
              <textarea
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                placeholder="https://example.com&#10;https://another-site.org"
                className="w-full h-64 p-4 rounded-xl bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 focus:ring-2 focus:ring-violet-500 outline-none font-mono text-sm resize-none mb-4 text-gray-900 dark:text-gray-300"
              />
              <div className="flex justify-end">
                <button
                  onClick={handleCrawl}
                  disabled={loading || !urls.trim()}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-all shadow-lg shadow-violet-500/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Start Indexing
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>

          {/* Results Section */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-4"
          >
            {error && (
              <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400">
                {error}
              </div>
            )}

            {results && (
              <div className="bg-white dark:bg-gray-900/50 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Results</h3>
                  <div className="flex gap-3 text-sm">
                    <span className="px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium">
                      {results.success} Success
                    </span>
                    {results.failed > 0 && (
                      <span className="px-2.5 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 font-medium">
                        {results.failed} Failed
                      </span>
                    )}
                    <span className="px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                      {(results.took_ms / 1000).toFixed(2)}s
                    </span>
                  </div>
                </div>

                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                  {results.results.map((result, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`p-4 rounded-xl border ${
                        result.success 
                          ? 'bg-green-50/50 dark:bg-green-900/10 border-green-100 dark:border-green-900/30' 
                          : 'bg-red-50/50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {result.success ? (
                          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                            {result.title || result.url}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                            {result.url}
                          </div>
                          {result.error && (
                            <div className="text-xs text-red-500 mt-2 font-mono bg-red-100/50 dark:bg-red-900/20 p-2 rounded">
                              {result.error}
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </main>
    </div>
  );
};
