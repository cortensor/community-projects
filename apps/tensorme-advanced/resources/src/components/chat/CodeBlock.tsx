"use client";
import React,
{ useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  language: string | undefined;
  value: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, value }) => {
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    });
  };

  return (
    <div className="relative bg-[#1E1E1E] rounded-lg">
      <div className="flex items-center justify-between px-3 py-1.5 bg-neutral-800/60 rounded-t-lg border-b border-neutral-700">
        <span className="text-xs font-sans text-neutral-400">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex hover:cursor-pointer items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
        >
          {hasCopied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          {hasCopied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{ margin: 0, padding: '1rem', backgroundColor: 'transparent' }}
        codeTagProps={{ style: { fontFamily: 'var(--font-geist-mono)' } }}
        wrapLongLines={true}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeBlock;