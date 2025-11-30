import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Clock, TrendingUp, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchBarProps {
  onSearch: (query: string) => void;
  initialQuery?: string;
  isLoading?: boolean;
  suggestions?: string[];
}

const HISTORY_KEY = 'search_history';
const MAX_HISTORY = 10;

export default function SearchBar({ onSearch, initialQuery = '', isLoading = false, suggestions = [] }: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const [isFocused, setIsFocused] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load search history from localStorage on mount
  const [historyLoaded, setHistoryLoaded] = useState(false);
  
  if (!historyLoaded) {
    const saved = localStorage.getItem(HISTORY_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setHistory(parsed);
        }
      } catch {
        // Invalid JSON, ignore
      }
    }
    setHistoryLoaded(true);
  }

  // Save search to history
  const saveToHistory = useCallback((searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (!trimmed) return;
    
    setHistory(prev => {
      const filtered = prev.filter(item => item.toLowerCase() !== trimmed.toLowerCase());
      const updated = [trimmed, ...filtered].slice(0, MAX_HISTORY);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  // Remove item from history
  const removeFromHistory = (item: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setHistory(prev => {
      const updated = prev.filter(h => h !== item);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  // Clear all history
  const clearHistory = (e: React.MouseEvent) => {
    e.stopPropagation();
    setHistory([]);
    localStorage.removeItem(HISTORY_KEY);
  };

  // Get dropdown items (combine suggestions and history)
  const getDropdownItems = useCallback(() => {
    const items: { type: 'suggestion' | 'history'; value: string }[] = [];
    
    // Add matching suggestions first
    if (query.trim()) {
      suggestions
        .filter(s => s.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 5)
        .forEach(s => items.push({ type: 'suggestion', value: s }));
    }
    
    // Add matching history items
    history
      .filter(h => !query.trim() || h.toLowerCase().includes(query.toLowerCase()))
      .filter(h => !items.some(item => item.value.toLowerCase() === h.toLowerCase()))
      .slice(0, query.trim() ? 3 : 5)
      .forEach(h => items.push({ type: 'history', value: h }));
    
    return items;
  }, [query, suggestions, history]);

  const dropdownItems = getDropdownItems();

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || dropdownItems.length === 0) {
      if (e.key === 'Enter') {
        handleSearch();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < dropdownItems.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : dropdownItems.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          selectItem(dropdownItems[selectedIndex].value);
        } else {
          handleSearch();
        }
        break;
      case 'Escape':
        setShowDropdown(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
      case 'Tab':
        if (selectedIndex >= 0) {
          e.preventDefault();
          setQuery(dropdownItems[selectedIndex].value);
        }
        break;
    }
  };

  // Select an item from dropdown
  const selectItem = (value: string) => {
    setQuery(value);
    setShowDropdown(false);
    setSelectedIndex(-1);
    saveToHistory(value);
    onSearch(value);
  };

  // Handle search submit
  const handleSearch = () => {
    if (query.trim()) {
      saveToHistory(query.trim());
      onSearch(query.trim());
      setShowDropdown(false);
    }
  };

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };

  // Clear input
  const clearInput = () => {
    setQuery('');
    setSelectedIndex(-1);
    inputRef.current?.focus();
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setShowDropdown(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Global keyboard shortcut (Ctrl/Cmd + K)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setShowDropdown(true);
      }
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  return (
    <div className="relative w-full max-w-2xl">
      <form onSubmit={handleSubmit}>
        <div
          className={`
            relative flex items-center transition-all duration-300
            ${isFocused 
              ? 'ring-2 ring-blue-500/50 shadow-lg shadow-blue-500/20' 
              : 'ring-1 ring-gray-200 dark:ring-gray-700 hover:ring-gray-300 dark:hover:ring-gray-600'
            }
            bg-white dark:bg-gray-800 rounded-2xl overflow-hidden
          `}
        >
          {/* Search Icon / Loader */}
          <div className="pl-4 pr-2">
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
            ) : (
              <Search className={`w-5 h-5 transition-colors duration-200 ${
                isFocused ? 'text-blue-500' : 'text-gray-400'
              }`} />
            )}
          </div>

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(-1);
              setShowDropdown(true);
            }}
            onFocus={() => {
              setIsFocused(true);
              setShowDropdown(true);
            }}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="Search the web..."
            className="flex-1 py-4 px-2 bg-transparent text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none text-lg"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck="false"
          />

          {/* Keyboard Shortcut Hint */}
          {!query && !isFocused && (
            <div className="hidden sm:flex items-center gap-1 pr-4">
              <kbd className="px-2 py-1 text-xs font-medium text-gray-400 bg-gray-100 dark:bg-gray-700 rounded">
                Ctrl
              </kbd>
              <span className="text-gray-400">+</span>
              <kbd className="px-2 py-1 text-xs font-medium text-gray-400 bg-gray-100 dark:bg-gray-700 rounded">
                K
              </kbd>
            </div>
          )}

          {/* Clear Button */}
          <AnimatePresence>
            {query && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                type="button"
                onClick={clearInput}
                className="p-2 mr-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </motion.button>
            )}
          </AnimatePresence>

          {/* Search Button */}
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className={`
              m-1.5 px-6 py-2.5 rounded-xl font-medium transition-all duration-200
              ${query.trim() && !isLoading
                ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md hover:shadow-lg'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            Search
          </button>
        </div>
      </form>

      {/* Dropdown */}
      <AnimatePresence>
        {showDropdown && (isFocused || dropdownItems.length > 0) && dropdownItems.length > 0 && (
          <motion.div
            ref={dropdownRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
          >
            {/* History Header */}
            {history.length > 0 && !query.trim() && (
              <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Recent Searches
                </span>
                <button
                  onClick={clearHistory}
                  className="text-xs text-blue-500 hover:text-blue-600 font-medium"
                >
                  Clear all
                </button>
              </div>
            )}

            {/* Dropdown Items */}
            <div className="max-h-64 overflow-y-auto">
              {dropdownItems.map((item, index) => (
                <button
                  key={`${item.type}-${item.value}`}
                  onClick={() => selectItem(item.value)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`
                    w-full flex items-center gap-3 px-4 py-3 text-left transition-colors
                    ${selectedIndex === index 
                      ? 'bg-blue-50 dark:bg-blue-900/30' 
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    }
                  `}
                >
                  {item.type === 'history' ? (
                    <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  ) : (
                    <TrendingUp className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  )}
                  <span className="flex-1 text-gray-700 dark:text-gray-200 truncate">
                    {query.trim() ? (
                      highlightMatch(item.value, query)
                    ) : (
                      item.value
                    )}
                  </span>
                  {item.type === 'history' && (
                    <button
                      onClick={(e) => removeFromHistory(item.value, e)}
                      className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    >
                      <X className="w-3 h-3 text-gray-400" />
                    </button>
                  )}
                </button>
              ))}
            </div>

            {/* Keyboard Hints */}
            <div className="flex items-center gap-4 px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-[10px]">↑↓</kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-[10px]">Tab</kbd>
                Complete
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-[10px]">Enter</kbd>
                Search
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-600 rounded text-[10px]">Esc</kbd>
                Close
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper function to highlight matching text
function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  
  const parts = text.split(new RegExp(`(${escapeRegExp(query)})`, 'gi'));
  
  return parts.map((part, index) => 
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={index} className="bg-yellow-200 dark:bg-yellow-800 text-inherit rounded px-0.5">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

// Helper function to escape regex special characters
function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
