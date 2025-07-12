"use client";
import React, { useEffect } from 'react';
import { Message } from '@/types';
import ChatMessage from './ChatMessage';
import ChatMessageSkeleton from './ChatMessageSkeleton';
import { Loader2 } from 'lucide-react';
import { useChatSessions } from '@/hooks/useChatSessions';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  handleSelectResponse: (messageId: string, newIndex: number) => void;
  loadingMessage: string | null;
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, messagesEndRef, handleSelectResponse, loadingMessage }) => {
  useEffect(() => {
    if (messagesEndRef?.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, messagesEndRef, loadingMessage]);

  return (
    <main className="absolute inset-0 p-4 sm:p-6 overflow-y-auto custom-scrollbar !pb-32">
      <div className="mx-auto max-w-4xl space-y-4">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} onSelectResponse={handleSelectResponse} />
        ))}
        {isLoading && (
          <div className="animate-fade-in-slide-up">
            <div className="flex items-center justify-start gap-2 text-sm text-neutral-text-secondary mb-2">
              <Loader2 size={16} className="animate-spin" />
              <span>{loadingMessage}</span>
            </div>
            <ChatMessageSkeleton />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </main>
  );
};

export default MessageList;