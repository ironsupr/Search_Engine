import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Globe, Zap, Code, Search as SearchIcon } from 'lucide-react';
import SearchBar from '../components/SearchBar';
import { ThemeToggle } from '../components/ThemeToggle';

const Background = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {/* Light Mode Gradients */}
    <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-violet-200/30 blur-[100px] dark:hidden animate-pulse" />
    <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-fuchsia-200/30 blur-[100px] dark:hidden animate-pulse" style={{ animationDelay: '1s' }} />
    
    {/* Dark Mode Gradients */}
    <div className="hidden dark:block absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-violet-900/20 blur-[120px] animate-pulse" />
    <div className="hidden dark:block absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-fuchsia-900/20 blur-[120px] animate-pulse" style={{ animationDelay: '2s' }} />
    <div className="hidden dark:block absolute top-[40%] left-[40%] w-[30%] h-[30%] rounded-full bg-indigo-900/20 blur-[100px] animate-pulse" style={{ animationDelay: '4s' }} />
  </div>
);

const QuickLink = ({ icon: Icon, label, onClick }: { icon: React.ElementType, label: string, onClick: () => void }) => (
  <motion.button
    whileHover={{ scale: 1.05, y: -2 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className="
      flex items-center gap-2 px-4 py-2 rounded-full 
      bg-white/50 dark:bg-gray-800/50 
      border border-gray-200/50 dark:border-gray-700/50 
      backdrop-blur-sm shadow-sm hover:shadow-md 
      text-gray-600 dark:text-gray-300 
      hover:text-violet-600 dark:hover:text-violet-400 
      hover:border-violet-200 dark:hover:border-violet-800
      transition-all duration-300
    "
  >
    <Icon className="w-4 h-4" />
    <span className="text-sm font-medium">{label}</span>
  </motion.button>
);

export const Home: React.FC = () => {
  const navigate = useNavigate();

  const handleSearch = (query: string) => {
    navigate(`/search?q=${encodeURIComponent(query)}&page=1`);
  };

  const quickLinks = [
    { icon: Code, label: 'Programming', query: 'programming tutorials' },
    { icon: Globe, label: 'World News', query: 'latest world news' },
    { icon: Zap, label: 'Tech Trends', query: 'technology trends 2025' },
    { icon: Sparkles, label: 'AI Tools', query: 'artificial intelligence tools' },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-[#0a0a0a] transition-colors duration-500 relative selection:bg-violet-200 dark:selection:bg-violet-900 overflow-hidden">
      <Background />

      <header className="absolute top-0 right-0 p-6 z-20">
        <ThemeToggle />
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="w-full max-w-3xl flex flex-col items-center gap-10 -mt-10">
          
          {/* Logo / Title Section */}
          <motion.div
            initial={{ opacity: 0, y: -30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="text-center space-y-4"
          >
            <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 dark:from-violet-500/20 dark:to-fuchsia-500/20 mb-4 ring-1 ring-inset ring-violet-200/50 dark:ring-violet-800/50">
              <SearchIcon className="w-8 h-8 text-violet-600 dark:text-violet-400" />
            </div>
            <h1 className="text-5xl sm:text-7xl font-bold tracking-tight">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-600 via-fuchsia-600 to-indigo-600 dark:from-violet-400 dark:via-fuchsia-400 dark:to-indigo-400 animate-gradient-x">
                Echo
              </span>
              <span className="text-gray-800 dark:text-gray-100">
                Search
              </span>
            </h1>
            <p className="text-lg text-gray-500 dark:text-gray-400 max-w-lg mx-auto font-light">
              Your voice echoes through the web. Fast, private, intelligent search.
            </p>
          </motion.div>
          
          {/* Search Bar Section */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="w-full max-w-2xl relative group"
          >
            <div className="absolute -inset-1 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-indigo-500 rounded-2xl opacity-20 group-hover:opacity-40 blur transition duration-500"></div>
            <div className="relative">
              <SearchBar onSearch={handleSearch} />
            </div>
          </motion.div>

          {/* Quick Links */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-wrap justify-center gap-3 mt-2"
          >
            {quickLinks.map((link) => (
              <QuickLink 
                key={link.label}
                icon={link.icon}
                label={link.label}
                onClick={() => handleSearch(link.query)}
              />
            ))}
          </motion.div>
        </div>
      </main>

      <footer className="py-8 text-center relative z-10">
        <div className="flex items-center justify-center gap-6 text-sm text-gray-400 dark:text-gray-600 mb-4">
          <a href="#" className="hover:text-violet-500 transition-colors">About</a>
          <a href="#" className="hover:text-violet-500 transition-colors">Privacy</a>
          <a href="#" className="hover:text-violet-500 transition-colors">Terms</a>
        </div>
        <p className="text-xs text-gray-300 dark:text-gray-700">
          &copy; {new Date().getFullYear()} Search Engine. Crafted with React & FastAPI.
        </p>
      </footer>
    </div>
  );
};
