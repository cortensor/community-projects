"use client";
import React, { useEffect, useState } from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import CodeBlock from './CodeBlock';

interface ThinkingCollapsibleProps {
  htmlContent: string;
  isThinking: boolean;
}

const ThinkingCollapsible: React.FC<ThinkingCollapsibleProps> = ({ htmlContent, isThinking }) => {
  const [isOpen, setIsOpen] = useState(true);

  const formattedContent = ">" + htmlContent.trim().split('\n').join('\n>');

  useEffect(() => {
    setIsOpen(isThinking);
  }, [isThinking]);

  return (
    <div className="">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
      >
        <div className="flex items-center gap-3">
          <Sparkles size={16} className="text-brand-primary/80" />
          <span className="text-sm font-medium text-neutral-300">Way of Thinking</span>
        </div>
        <ChevronDown
          size={20}
          className={`text-neutral-400 translate-y-0.5 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>
      <div
        className={`overflow-hidden custom-scrollbar transition-max-height duration-500 ease-in-out ${isOpen ? 'max-h-[10000px]' : 'max-h-0'}`}
      >
        <div className="px-6 py-2 pb-3 my-3 border-t border-b border-neutral-700/20">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={{
            p: ({ node, ...props }) => <p className="mt-2 mb-2 leading-[1.9]" {...props} />,
            ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2" {...props} />,
            ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2" {...props} />,
            li: ({ node, ...props }) => <li className="pb-0 m-0" {...props} />,
            blockquote: ({ node, ...props }) => (
              <blockquote className="border-l-4 border-neutral-700 pl-4 my-0 mt-0 italic text-neutral-400" {...props} />
            ),
          }}>{formattedContent}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

export default ThinkingCollapsible;