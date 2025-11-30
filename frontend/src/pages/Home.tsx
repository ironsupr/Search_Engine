import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import SearchBar from '../components/SearchBar';
import { ThemeToggle } from '../components/ThemeToggle';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  const handleSearch = (query: string) => {
    navigate(`/search?q=${encodeURIComponent(query)}&page=1`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-gray-900 transition-colors duration-200 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-50 via-transparent to-transparent dark:from-blue-900/20 dark:via-transparent dark:to-transparent opacity-70 pointer-events-none"></div>

      <header className="absolute top-0 right-0 p-4 z-10">
        <ThemeToggle />
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 relative z-0">
        <div className="w-full max-w-2xl flex flex-col items-center gap-8 -mt-20">
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-6xl sm:text-7xl font-bold tracking-tight text-center"
          >
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
              Search
            </span>
          </motion.h1>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="w-full max-w-xl"
          >
            <SearchBar onSearch={handleSearch} />
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-wrap justify-center gap-4 text-sm text-gray-500 dark:text-gray-400 mt-4"
          >
            <span>Try searching for:</span>
            {['Python', 'React', 'Machine Learning', 'Docker'].map((term) => (
              <button
                key={term}
                onClick={() => handleSearch(term)}
                className="px-3 py-1 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              >
                {term}
              </button>
            ))}
          </motion.div>
        </div>
      </main>

      <footer className="py-6 text-center text-sm text-gray-400 dark:text-gray-600 relative z-10">
        <p>&copy; {new Date().getFullYear()} Mini Search Engine. Built for SDE Portfolio.</p>
      </footer>
    </div>
  );
};
