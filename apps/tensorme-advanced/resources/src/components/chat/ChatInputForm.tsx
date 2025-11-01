"use client";
import React, { useState, useEffect } from 'react';
import { Send, Loader2, Search } from 'lucide-react';

interface ChatInputFormProps {
  inputValue: string;
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  isResearchMode?: boolean;
  onResearchToggle?: (enabled: boolean) => void;
  showResearchToggle?: boolean;
}

const ChatInputForm: React.FC<ChatInputFormProps> = ({
  inputValue,
  onInputChange,
  onSubmit,
  isLoading,
  inputRef,
  isResearchMode = false,
  onResearchToggle,
  showResearchToggle = false,
}) => {
  const [isOverflowing, setIsOverflowing] = useState(false)

  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;

      const maxHeight = 192;
      setIsOverflowing(textarea.scrollHeight > maxHeight);
    }
  }, [inputValue, inputRef]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form && !isLoading && inputValue.trim()) {
        form.requestSubmit();
      }
    }
  };

  return (
    <footer className="max-w-3xl mx-auto px-4 sm:px-0 pb-6 pt-4">
      <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-4 shadow-2xl">
        {showResearchToggle && onResearchToggle && (
          <div className="mb-2">
            <button
              type="button"
              onClick={() => onResearchToggle(!isResearchMode)}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg backdrop-blur-sm text-xs font-medium ${
                isResearchMode 
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-400/30' 
                  : 'bg-white/5 text-white/50 hover:bg-white/10 hover:text-white/70 border border-white/10'
              }`}
            >
              <Search size={12} />
              <span>{isResearchMode ? 'Deep Research On' : 'Deep Research'}</span>
              {isResearchMode && <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></div>}
            </button>
          </div>
        )}
        
        <form onSubmit={onSubmit} className="flex items-center gap-3">
          <div className="relative w-full">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={onInputChange}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder={isResearchMode ? "Ask a research question..." : "Send a message..."}
              disabled={isLoading}
              className={`w-full pl-5 pr-5 py-3.5 text-sm bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl focus:border-white/20 focus:bg-white/10 text-white placeholder-white/40 disabled:opacity-50 resize-none max-h-48 outline-none
                  ${isOverflowing ? 'overflow-y-auto custom-scrollbar' : 'overflow-hidden'}
                  ${isResearchMode ? 'border-blue-400/30 bg-blue-500/10' : ''}`}
              style={{
                lineHeight: '1.5rem',
              }}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="w-11 h-11 flex-shrink-0 flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed shadow-lg backdrop-blur-sm"
            aria-label="Send message"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>
        
        <div className="flex items-center justify-center mt-3 px-1">
          <p className="text-xs text-white/40">
            <kbd className="px-1.5 py-0.5 bg-white/10 border border-white/20 rounded text-white/60 font-mono text-xs">Shift + Enter</kbd> for new line
          </p>
        </div>
      </div>
    </footer>
  );
};

export default ChatInputForm;