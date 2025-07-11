"use client";
import React, { useState } from 'react';
import { Message } from '@/types';
import { Copy, Check, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import ChatMessageSkeleton from './ChatMessageSkeleton';

interface ChatMessageProps {
  message: Message;
  onSelectResponse: (messageId: string, newIndex: number) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSelectResponse }) => {
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    navigator.clipboard.writeText(message.content).then(() => {
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
    });
  };

  const isUser = message.role === 'user';
  const hasMultipleResponses = message.responses && message.responses.length > 1;

  const getStatusText = (status: Message['status']) => {
    switch (status) {
      case 'sending': return 'Sending...';
      case 'submitted': return 'Task Submitted...';
      case 'assigned': return 'Task Assigned...';
      default: return null;
    }
  };

  const handlePrevResponse = () => {
    if (!message.responses || message.selectedResponseIndex === undefined) return;
    const newIndex = message.selectedResponseIndex > 0
      ? message.selectedResponseIndex - 1
      : message.responses.length - 1;
    onSelectResponse(message.id, newIndex);
  };

  const handleNextResponse = () => {
    if (!message.responses || message.selectedResponseIndex === undefined) return;
    const newIndex = message.selectedResponseIndex < message.responses.length - 1
      ? message.selectedResponseIndex + 1
      : 0;
    onSelectResponse(message.id, newIndex);
  };

  return (
    <div className={`group flex items-start gap-2.5 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in-slide-up`}>
      <div
        className={`max-w-xs md:max-w-md lg:max-w-xl xl:max-w-3xl px-4 py-2.5 rounded-xl shadow-md transition-all ${isUser
          ? 'bg-slate-700 text-white rounded-br-none'
          : message.isError
            ? 'bg-red-800 text-red-100 rounded-bl-none border border-red-700'
            : 'bg-neutral-800 text-gray-200 rounded-bl-none'
          }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>

        {message.role === 'assistant' && (
          <div className="pt-2 text-xs text-neutral-400">
            {hasMultipleResponses && (
              <div className="flex items-center justify-between mt-2 border-t border-neutral-700/50 pt-2">
                <span className="font-mono text-neutral-500 hover:underline">
                  Miner: {message.responses?.[message.selectedResponseIndex || 0]?.minerAddress.slice(0, 6)}...{message.responses?.[message.selectedResponseIndex || 0]?.minerAddress.slice(-4)}
                </span>
                <div className="flex items-center gap-2">
                  <button onClick={handlePrevResponse} className="p-1 rounded-full hover:bg-neutral-700"><ChevronLeft size={16} /></button>
                  <span>{(message.selectedResponseIndex || 0) + 1} of {message.responses?.length || 0}</span>
                  <button onClick={handleNextResponse} className="p-1 rounded-full hover:bg-neutral-700"><ChevronRight size={16} /></button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {message.role === 'assistant' && !message.isError && (
        <button onClick={handleCopy} className="p-1.5 rounded-md text-neutral-500 hover:bg-neutral-700 hover:text-neutral-300 transition-all duration-150 opacity-70 md:opacity-0 md:group-hover:opacity-100" aria-label="Copy message" title="Copy">
          {hasCopied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
        </button>
      )}
    </div>
  );
};

export default ChatMessage;