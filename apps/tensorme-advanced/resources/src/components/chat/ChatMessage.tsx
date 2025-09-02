"use client";
import React, { useEffect, useState } from 'react';
import { Message } from '@/types';
import { Copy, Check, ChevronLeft, ChevronRight, Loader2, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import CodeBlock from './CodeBlock';
import ThinkingCollapsible from './ThinkingCollapsible';

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

  // useEffect(() => {
  //   console.log(message);
  // }, [message]);

  const isUser = message.role === 'user';
  const hasMultipleResponses = message.responses && message.responses.length > 1;

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
    <div className={`group flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in-slide-up`}>
      {isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 backdrop-blur-sm border border-white/10 flex items-center justify-center mt-1">
          <User size={18} className="text-blue-300" />
        </div>
      )}

      <div
        className={`prose prose-invert prose-sm max-w-full rounded-2xl backdrop-blur-md shadow-2xl relative ${isUser
          ? 'bg-white/10 border border-white/20 text-white rounded-br-none'
          : message.isError
            ? 'bg-red-500/10 backdrop-blur-md border border-red-400/30 text-red-200 rounded-bl-none'
            : 'bg-black/20 backdrop-blur-md border border-white/10 text-white/90 rounded-bl-none px-1 py-3 sm:px-2 sm:py-3'
          }`}
      >
        {message.role === 'assistant' && !message.isError && (
          <button onClick={handleCopy} className="absolute top-3 right-3 p-1.5 hover:cursor-pointer rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80 opacity-0 group-hover:opacity-100" aria-label="Copy message" title="Copy">
            {hasCopied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
          </button>
        )}
        {message.role === 'assistant' && message.thinking && (
          <ThinkingCollapsible htmlContent={message.thinking || ''} isThinking={message.isThinking || false} />
        )}
        <div className="px-4">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              h1: ({ node, ...props }) => <h1 className="text-xl font-bold mb-2 mt-3" {...props} />,
              h2: ({ node, ...props }) => <h2 className="text-lg font-semibold mb-2 mt-3" {...props} />,
              h3: ({ node, ...props }) => <h3 className="text-base font-semibold mb-2 mt-3" {...props} />,
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" className="text-brand-primary underline hover:text-brand-primary-hover" />
              ),
              p: ({ node, ...props }) => <p className="mt-2 mb-2 leading-[1.8]" {...props} />,
              ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2" {...props} />,
              ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2" {...props} />,
              li: ({ node, ...props }) => <li className="pb-0 m-0" {...props} />,
              blockquote: ({ node, ...props }) => (
                <blockquote className="border-l-4 border-white/20 pl-4 my-3 italic text-white/60" {...props} />
              ),
              code: ({ node, inline, className, children, ...props }: any) => {
                const match = /language-(\w+)/.exec(className || '');
                const value = String(children).replace(/\n$/, '');
                const multiLine = value.includes('\n');

                if (multiLine || match?.[1]) {
                  return <CodeBlock language={match?.[1]} value={value} />;
                }

                return (
                  <code
                    className="bg-white/10 backdrop-blur-sm text-blue-300 font-semibold px-1.5 mx-0.5 py-0.5 rounded text-xs font-mono"
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              pre: ({ node, ...props }) => <pre className="bg-transparent py-0 px-0 m-0" {...props} />,
              table: ({ node, ...props }) => <table className="w-full my-3 text-sm border-collapse" {...props} />,
              thead: ({ node, ...props }) => <thead className="border-b-2 border-white/20" {...props} />,
              tr: ({ node, ...props }) => <tr className="border-b border-white/10 last:border-0" {...props} />,
              th: ({ node, ...props }) => <th className="px-3 py-2 text-left font-semibold" {...props} />,
              td: ({ node, ...props }) => <td className="px-3 py-2" {...props} />,
              hr: ({ node, ...props }) => <hr className="my-4 border-white/20" {...props} />,
            }}
          >
            {message.content}
          </ReactMarkdown>

        </div>

        {message.role === 'assistant' && (
          <div className="pt-2 text-xs text-white/40">
            {hasMultipleResponses && (
              <div className="flex items-center justify-between mt-2 border-t border-white/10 pt-3 px-4">
                <span className="font-mono text-white/50">
                  Miner: {message.responses?.[message.selectedResponseIndex || 0]?.minerAddress.slice(0, 6)}...{message.responses?.[message.selectedResponseIndex || 0]?.minerAddress.slice(-4)}
                </span>
                <div className="flex items-center gap-2">
                  <button onClick={handlePrevResponse} className="p-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"><ChevronLeft size={14} /></button>
                  <span className="text-white/60">{(message.selectedResponseIndex || 0) + 1} of {message.responses?.length || 0}</span>
                  <button onClick={handleNextResponse} className="p-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"><ChevronRight size={14} /></button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
};

export default ChatMessage;