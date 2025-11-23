'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '@/lib/utils'
import { CheckIcon, CopyIcon, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface MarkdownRendererProps {
  content: string
  className?: string
}

interface CodeBlockProps {
  children: React.ReactNode
  className?: string
  inline?: boolean
}

const CodeBlock: React.FC<CodeBlockProps> = ({ children, className, inline }) => {
  const [copied, setCopied] = useState(false)
  const language = className?.replace('language-', '') || 'text'
  const codeString = String(children).replace(/\n$/, '')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (inline) {
    return (
      <code className="px-1.5 py-0.5 font-mono text-xs sm:text-sm rounded border bg-muted text-muted-foreground break-words">
        {children}
      </code>
    )
  }

  return (
    <div className="overflow-hidden relative my-2 rounded-lg border shadow-sm sm:my-4 group border-border">
      <div className="flex justify-between items-center px-2 sm:px-4 py-1.5 sm:py-2 border-b bg-muted border-border">
        <span className="font-mono text-xs tracking-wide uppercase text-muted-foreground">
          {language}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="p-0 w-6 h-6 opacity-70 transition-all duration-200 sm:w-7 sm:h-7 hover:opacity-100 hover:bg-muted"
        >
          {copied ? (
            <CheckIcon className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-primary" />
          ) : (
            <CopyIcon className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
          )}
        </Button>
      </div>
      <div className="overflow-x-auto relative">
        <SyntaxHighlighter
          language={language}
          style={oneDark}
          customStyle={{
            margin: 0,
            padding: '0.5rem',
            background: 'hsl(var(--background))',
            fontSize: '0.75rem',
            lineHeight: '1.4',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            color: 'hsl(var(--foreground))',
          }}
          showLineNumbers={false}
          wrapLines={true}
          wrapLongLines={true}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className
}) => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(true);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCode(text);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className={cn('overflow-hidden max-w-none prose prose-slate dark:prose-invert prose-sm sm:prose-base break-words', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Enhanced Headings with better typography and responsive sizing
          h1: ({ children }) => (
            <h1 className="pb-2 mt-4 mb-3 text-lg font-bold leading-tight border-b sm:text-xl text-foreground border-border break-words">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-3 mb-2 text-base font-semibold leading-tight sm:text-lg text-foreground break-words">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-3 mb-2 text-sm font-semibold leading-tight sm:text-base text-foreground break-words">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mt-2 mb-1 text-sm font-medium text-muted-foreground break-words">
              {children}
            </h4>
          ),

          // Enhanced Paragraphs with better spacing and responsive text
          p: ({ children }) => (
            <p className="mb-2 text-sm leading-relaxed break-words sm:text-base text-foreground">
              {children}
            </p>
          ),

          // Enhanced Lists with better styling and responsive spacing
          ul: ({ children }) => (
            <ul className="pl-4 mb-2 space-y-1 text-sm sm:text-base text-foreground break-words">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="pl-4 mb-2 space-y-1 text-sm sm:text-base text-foreground break-words">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="relative pl-1 break-words">
              {children}
            </li>
          ),

          // Code blocks and inline code
          code: ({ children, className, ...props }) => {
            const inline = !className
            return (
              <CodeBlock
                className={className}
                inline={inline}
              >
                {children}
              </CodeBlock>
            )
          },

          // Enhanced Links with better styling
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex gap-1 items-center underline transition-colors duration-200 text-primary hover:text-primary/80 decoration-primary/30 hover:decoration-primary"
            >
              {children}
              <ExternalLink className="w-3 h-3 opacity-70" />
            </a>
          ),

          // Enhanced Blockquotes with responsive spacing
          blockquote: ({ children }) => (
            <blockquote className="py-2 pr-2 pl-3 my-3 rounded-r-lg border-l-4 border-primary bg-muted">
              <div className="text-sm italic font-medium break-words sm:text-base text-muted-foreground">
                {children}
              </div>
            </blockquote>
          ),

          // Enhanced Tables with better mobile handling
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 rounded-lg border shadow-sm border-border">
              <table className="min-w-full text-xs divide-y divide-border sm:text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="px-2 py-2 text-xs font-semibold tracking-wider text-left uppercase sm:px-4 text-muted-foreground">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-2 py-2 text-xs break-words border-t sm:px-4 sm:text-sm text-foreground border-border">
              {children}
            </td>
          ),

          // Enhanced Horizontal rule with responsive spacing
          hr: () => (
            <hr className="my-4 h-px bg-gradient-to-r from-transparent to-transparent border-0 via-border" />
          ),

          // Enhanced Strong and emphasis
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-foreground">
              {children}
            </em>
          ),

          // Enhanced task lists
          input: ({ type, checked, ...props }) => {
            if (type === 'checkbox') {
              return (
                <input
                  type="checkbox"
                  checked={checked}
                  readOnly
                  className="mr-2 rounded text-primary border-border focus:ring-primary"
                  {...props}
                />
              )
            }
            return <input type={type} {...props} />
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownRenderer