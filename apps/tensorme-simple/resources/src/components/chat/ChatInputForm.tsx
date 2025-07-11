"use client";
import React, { useState, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputFormProps {
  inputValue: string;
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}

const ChatInputForm: React.FC<ChatInputFormProps> = ({
  inputValue,
  onInputChange,
  onSubmit,
  isLoading,
  inputRef,
}) => {
  const [isOverflowing, setIsOverflowing] = useState(false)

  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      // 1. Adjust height to content
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;

      // 2. Check if content height exceeds max-height
      // The `max-h-48` class corresponds to 12rem or 192px.
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
    <footer className="max-w-full px-4 sm:px-0 sm:max-w-4xl mx-auto !pb-4 !pt-3 bg-transparent">
      <form onSubmit={onSubmit} className="flex items-end gap-2.5">
        <textarea
          ref={inputRef}
          value={inputValue}
          onChange={onInputChange}
          onKeyDown={handleKeyDown}
          rows={2}
          placeholder="Send a message..."
          disabled={isLoading}
          className={`w-full pl-4 pr-4 py-2.5 bg-neutral-surface border border-neutral-border rounded-xl focus:ring-2 focus:ring-brand-primary focus:border-transparent text-neutral-text-primary placeholder-neutral-text-secondary disabled:opacity-60 resize-none max-h-32
              ${isOverflowing ? 'overflow-y-auto custom-scrollbar' : 'overflow-hidden'}`}
          style={{
            lineHeight: '1.5rem',
            boxShadow: '0 -10px 30px -5px rgba(0, 0, 0, 0.5)',
          }}
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="w-10 h-10 mb-0.5 flex-shrink-0 flex items-center justify-center bg-brand-primary text-black rounded-full hover:bg-brand-primary-hover focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2 focus:ring-offset-neutral-base disabled:bg-neutral-surface disabled:text-neutral-text-tertiary disabled:cursor-not-allowed transition-all duration-200"
          aria-label="Send message"
        >
          {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={16} />}
        </button>
      </form>
    </footer>
  );
};

export default ChatInputForm;