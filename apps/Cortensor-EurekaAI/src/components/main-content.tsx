// src/components/main-content.tsx
"use client"

import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import React, { useState, useRef, useEffect } from 'react'
import { Check, Copy, Bot, User, BrainCircuit, MessageSquare, Clock } from 'lucide-react'
import { Button } from './ui/button'
import { Card, CardContent } from "./ui/card"
import { ScrollArea } from "./ui/scroll-area"
import { LoadingIndicator } from "./loading-indicator"
import { ThinkingLoading } from "./thinking-loading"
import { ChainOfThought } from "./chain-of-thought"
import { ThinkingDisplay } from "./thinking-display"
import type { ChatSession, ChatMessage } from "../lib/storage"
import { appConfig } from "../lib/app-config"
import { cn } from "../lib/utils"

const PreBlock = ({ children, ...props }: React.ComponentProps<'pre'>) => {
    const [isCopied, setIsCopied] = useState(false);
    const codeElement = React.Children.toArray(children)[0] as React.ReactElement<{ className?: string; children: React.ReactNode }>;
    const language = codeElement?.props?.className?.replace('language-', '') || 'text';
    const codeString = String(codeElement?.props?.children).replace(/\n$/, '');

    const handleCopy = async () => {
        if (codeString) {
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(codeString);
                } else {
                    // Fallback for non-secure contexts
                    const textArea = document.createElement('textarea');
                    textArea.value = codeString;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-999999px';
                    textArea.style.top = '-999999px';
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    document.execCommand('copy');
                    textArea.remove();
                }
                setIsCopied(true);
                setTimeout(() => setIsCopied(false), 2000);
            } catch (error) {
                console.error('Copy failed:', error);
                // Silently fail - don't show error to user
            }
        }
    };

    return (
        <div className="relative group">
            <Button
                onClick={handleCopy}
                variant="ghost"
                size="sm"
                className="absolute top-2 right-2 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground hover:bg-muted/50"
            >
                {isCopied ? (
                    <Check className="h-3 w-3" />
                ) : (
                    <Copy className="h-3 w-3" />
                )}
            </Button>
            <pre {...props} className={cn("bg-muted/50 border border-border/50 rounded-lg p-3 overflow-x-auto", props.className)}>
                {children}
            </pre>
        </div>
    );
};

// Helper function to detect programming languages in content
const detectProgrammingCode = (content: string): { language: string; code: string } | null => {
    // Language patterns with priority order
    const languagePatterns = [
        // Code blocks with explicit language
        { pattern: /```javascript\s*([\s\S]*?)```/i, language: 'javascript' },
        { pattern: /```js\s*([\s\S]*?)```/i, language: 'javascript' },
        { pattern: /```typescript\s*([\s\S]*?)```/i, language: 'typescript' },
        { pattern: /```ts\s*([\s\S]*?)```/i, language: 'typescript' },
        { pattern: /```python\s*([\s\S]*?)```/i, language: 'python' },
        { pattern: /```py\s*([\s\S]*?)```/i, language: 'python' },
        { pattern: /```html\s*([\s\S]*?)```/i, language: 'html' },
        { pattern: /```css\s*([\s\S]*?)```/i, language: 'css' },
        { pattern: /```java\s*([\s\S]*?)```/i, language: 'java' },
        { pattern: /```cpp\s*([\s\S]*?)```/i, language: 'cpp' },
        { pattern: /```c\+\+\s*([\s\S]*?)```/i, language: 'cpp' },
        
        // Specific language patterns
        { pattern: /console\.log\s*\(|function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=/i, language: 'javascript' },
        { pattern: /print\s*\(|def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import/i, language: 'python' },
        { pattern: /<!DOCTYPE html>|<html>|<head>|<body>|<div>|<p>|<h[1-6]>/i, language: 'html' },
        { pattern: /\{[^}]*\}|\.[\w-]+\s*\{|#[\w-]+\s*\{|@media|:hover|:focus/i, language: 'css' },
        { pattern: /public\s+class|System\.out\.println|public\s+static\s+void\s+main/i, language: 'java' },
        { pattern: /#include\s*<|std::|cout\s*<<|int\s+main\s*\(/i, language: 'cpp' },
        { pattern: /interface\s+\w+|type\s+\w+\s*=|as\s+\w+|<\w+>/i, language: 'typescript' },
    ];
    
    for (const { pattern, language } of languagePatterns) {
        const match = content.match(pattern);
        if (match) {
            // If it's a code block, extract the code
            if (match[1]) {
                return { language, code: match[1].trim() };
            }
            // Otherwise, try to extract the relevant code section
            const lines = content.split('\n');
            const relevantLines = lines.filter(line => 
                line.trim() && !line.trim().startsWith('#') && !line.trim().startsWith('//')
            );
            if (relevantLines.length > 0) {
                return { language, code: relevantLines.join('\n').trim() };
            }
        }
    }
    return null;
};

// Playground functionality completely removed per user request

interface MainContentProps {
  currentSession?: ChatSession;
  messages: ChatMessage[];
  isLoading: boolean;
  isPanelOpen: boolean;
  isMobile: boolean;
  isMemoryMode: boolean;
  selectedModel: string;
  isDeepThinking: boolean;
  isThinkingPhase: boolean;
  environment: 'testnet' | 'devnet6';
  onMemoryModeChange: (enabled: boolean) => void;
    onPrefill?: (text: string) => void;
}

export function MainContent({
    currentSession,
    messages,
    isLoading,
    isPanelOpen,
    isMobile,
    isMemoryMode,
    selectedModel,
    isDeepThinking,
    isThinkingPhase,
    environment = 'testnet',
    onMemoryModeChange,
    onPrefill
}: MainContentProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const scrollAreaRef = useRef<HTMLDivElement>(null);
    
    // Disabled auto scroll as requested
    // useEffect(() => {
    //     if (messagesEndRef.current) {
    //         messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    //     }
    // }, [messages, isLoading, isThinkingPhase]);

    // Disabled auto scroll for thinking phase
    // useEffect(() => {
    //     if (isThinkingPhase && isLoading) {
    //         const timer = setTimeout(() => {
    //             if (messagesEndRef.current) {
    //                 messagesEndRef.current.scrollIntoView({ 
    //                     behavior: 'smooth',
    //                     block: 'end'
    //                 });
    //             }
    //         }, 100);
    //         return () => clearTimeout(timer);
    //     }
    // }, [isThinkingPhase, isLoading]);

    return (
        <div 
            className={cn(
                "flex flex-col transition-all duration-300 ease-in-out",
                "mobile-height ios-scroll-fix", // Mobile optimizations
                isMobile ? "ml-0 h-screen min-h-screen" : isPanelOpen ? "ml-80 h-full" : "ml-16 h-full"
            )}
            style={isMobile ? {
                height: '100dvh', // Use dynamic viewport height
                minHeight: '100dvh'
                // Remove overflow hidden to allow keyboard to overlay naturally
            } : undefined}
        >
            {/* Professional Header - Mobile Optimized */}
            <div className={cn(
                "sticky top-0 z-50 flex items-center justify-between border-b bg-background/95 backdrop-blur-md",
                isMobile ? "p-2.5 min-h-[56px]" : "p-3"
            )}>
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className={cn(
                        "flex-shrink-0 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center",
                        isMobile ? "w-6 h-6" : "w-7 h-7"
                    )}>
                        <MessageSquare className={cn("text-white", isMobile ? "w-3 h-3" : "w-3.5 h-3.5")} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h1 className={cn(
                            "font-semibold text-foreground truncate",
                            isMobile ? "text-sm" : "text-base"
                        )}>
                            {currentSession?.title || "New Chat"}
                        </h1>
                        <div className={cn(
                            "flex items-center space-x-2 text-muted-foreground",
                            isMobile ? "text-xs" : "text-xs"
                        )}>
                                                        <span className="truncate">
                                                                {selectedModel === 'deepseek-r1' 
                                                                    ? 'DeepSeek R1' 
                                                                    : selectedModel === 'llama-3.1-8b-q4' 
                                                                        ? 'Llama 3.1 8B Q4' 
                                                                        : 'Llava 1.5'}
                                                        </span>
                            {!isMobile && (
                                <>
                                    <span>•</span>
                                    <span>{messages.length} messages</span>
                                    <span>•</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                        environment === 'devnet6' 
                                            ? 'bg-orange-900/50 text-orange-300 border border-orange-700/50' 
                                            : 'bg-blue-900/50 text-blue-300 border border-blue-700/50'
                                    }`}>
                                        {environment === 'devnet6' ? 'DEVNET-7' : 'TESTNET0'}
                                    </span>
                                    <span>•</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                        selectedModel === 'deepseek-r1' 
                                            ? 'bg-purple-900/50 text-purple-300 border border-purple-700/50' 
                                            : selectedModel === 'llama-3.1-8b-q4'
                                              ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-700/50'
                                              : 'bg-blue-900/50 text-blue-300 border border-blue-700/50'
                                    }`}>
                                        {selectedModel === 'deepseek-r1' 
                                          ? 'DeepSeek R1' 
                                          : selectedModel === 'llama-3.1-8b-q4'
                                            ? 'Llama 3.1 8B Q4'
                                            : 'Llava 1.5'}
                                    </span>
                                    {isDeepThinking && selectedModel === 'deepseek-r1' && (
                                        <>
                                            <span>•</span>
                                            <span className="text-amber-400">Deep Thinking Mode</span>
                                        </>
                                    )}
                                </>
                            )}
                            {isMobile && isDeepThinking && selectedModel === 'deepseek-r1' && (
                                <>
                                    <span>•</span>
                                    <span className="text-amber-400 text-xs">Deep Mode</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
                {/* Desktop status only */}
                {!isMobile && (
                    <div className="flex items-center space-x-4 text-muted-foreground">
                        <div className="flex items-center space-x-1 text-xs">
                            <Clock className="w-3 h-3" />
                            <span>{new Date().toLocaleTimeString()}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Messages Container with proper scrolling */}
            <ScrollArea className={cn(
                "flex-1",
                isMobile ? "px-2 pb-36 mobile-scroll-safe" : "px-3 pb-40" // Tighter padding ala ChatGPT
            )}>
                <div className={cn(
                    "space-y-4 min-h-0",
                    isMobile ? "py-3 max-w-full overflow-hidden" : "py-3.5"
                )}>
                    {!messages.length && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {[ 
                                { title: 'Code review', body: 'Review this code and suggest fixes.' },
                                { title: 'Summarize', body: 'Summarize the following text in bullet points.' },
                                { title: 'Explain', body: 'Explain this concept in simple terms.' },
                                { title: 'Write test', body: 'Write unit tests for this function.' },
                                { title: 'Blockchain', body: 'Explain this smart contract risk surface.' },
                                { title: 'Optimize', body: 'Optimize this code for readability and performance.' },
                            ].map((card, idx) => (
                                <div key={idx} className="rounded-lg border border-border/50 bg-card/70 p-3 hover:border-primary/50 transition cursor-pointer"
                                    onClick={() => {
                                        onMemoryModeChange(true);
                                        onPrefill?.(card.body);
                                    }}
                                >
                                    <div className="text-sm font-semibold text-foreground mb-1">{card.title}</div>
                                    <div className="text-xs text-muted-foreground leading-5">{card.body}</div>
                                </div>
                            ))}
                        </div>
                    )}
                    {messages.map((message, index) => (
                        <div key={index} className="space-y-4">
                            <div className={`flex items-start ${
                                message.role === 'user' 
                                    ? 'justify-end' 
                                    : 'justify-start'
                            } ${isMobile ? 'space-x-2' : 'space-x-3'}`}>
                                {message.role === 'assistant' && (
                                    <div className={cn(
                                        "flex-shrink-0 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center",
                                        isMobile ? "w-6 h-6" : "w-8 h-8"
                                    )}>
                                        {isDeepThinking && selectedModel === 'deepseek-r1' ? (
                                            <BrainCircuit className={cn("text-white", isMobile ? "w-3 h-3" : "w-4 h-4")} />
                                        ) : (
                                            <Bot className={cn("text-white", isMobile ? "w-3 h-3" : "w-4 h-4")} />
                                        )}
                                    </div>
                                )}
                                
                                <Card className={`chat-bubble ${
                                    isMobile ? 'max-w-[85vw] w-full' : 'max-w-[78%]'
                                } ${
                                    message.role === 'user'
                                        ? 'bg-blue-600/20 border-blue-600/30'
                                        : 'bg-muted/50 border-border/50'
                                }`}>
                                    <CardContent className={cn(
                                        "break-words overflow-wrap-anywhere word-break overflow-hidden",
                                        isMobile ? "p-2.5 text-[13px] leading-6 max-w-full" : "p-3 text-[15px] leading-6"
                                    )}>
                                        {message.role === 'user' ? (
                                            <p className={cn(
                                                "text-foreground whitespace-pre-wrap break-words overflow-hidden max-w-full text-[15px] leading-6",
                                                isMobile && "text-[13px] leading-6"
                                            )}>
                                                {message.content}
                                            </p>
                                        ) : (
                                            <div className={cn(
                                                "prose prose-invert max-w-none break-words overflow-hidden text-[15px] leading-6",
                                                isMobile && "prose-sm text-[13px] leading-6 max-w-full"
                                            )}>
                                                {/* Thinking Process Display for DeepSeek R1 - Always visible */}
                                                {selectedModel.includes('deepseek-r1') && message.thinkingContent && (
                                                    <div className="mb-4">
                                                        <ThinkingDisplay 
                                                            thinkingContent={message.thinkingContent}
                                                            isVisible={true}
                                                        />
                                                    </div>
                                                )}
                                                
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    rehypePlugins={[rehypeHighlight]}
                                                    components={{
                                                        pre: PreBlock,
                                                        code: ({ inline, className, children, ...props }: any) => {
                                                            if (inline) {
                                                                return (
                                                                    <code
                                                                        className="bg-muted text-foreground px-1 py-0.5 rounded text-sm"
                                                                        {...props}
                                                                    >
                                                                        {children}
                                                                    </code>
                                                                );
                                                            }
                                                            return (
                                                                <code className={className} {...props}>
                                                                    {children}
                                                                </code>
                                                            );
                                                        },
                                                        h1: ({ children }) => (
                                                            <h1 className="text-xl font-bold text-foreground mb-4 mt-6">
                                                                {children}
                                                            </h1>
                                                        ),
                                                        h2: ({ children }) => (
                                                            <h2 className="text-lg font-semibold text-foreground mb-3 mt-5">
                                                                {children}
                                                            </h2>
                                                        ),
                                                        h3: ({ children }) => (
                                                            <h3 className="text-base font-medium text-foreground/90 mb-2 mt-4">
                                                                {children}
                                                            </h3>
                                                        ),
                                                        p: ({ children }) => (
                                                            <p className="text-foreground/80 mb-4 leading-relaxed">
                                                                {children}
                                                            </p>
                                                        ),
                                                        ul: ({ children }) => (
                                                            <ul className="text-foreground/80 mb-4 pl-6 space-y-1">
                                                                {children}
                                                            </ul>
                                                        ),
                                                        ol: ({ children }) => (
                                                            <ol className="text-foreground/80 mb-4 pl-6 space-y-1">
                                                                {children}
                                                            </ol>
                                                        ),
                                                        li: ({ children }) => (
                                                            <li className="text-foreground/80">
                                                                {children}
                                                            </li>
                                                        ),
                                                        blockquote: ({ children }) => (
                                                            <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground my-4">
                                                                {children}
                                                            </blockquote>
                                                        ),
                                                        a: ({ href, children }) => (
                                                            <a
                                                                href={href}
                                                                className="text-blue-400 hover:text-blue-300 underline"
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            >
                                                                {children}
                                                            </a>
                                                        ),
                                                        table: ({ children }) => (
                                                            <div className="overflow-x-auto my-4">
                                                                <table className="min-w-full border border-slate-700">
                                                                    {children}
                                                                </table>
                                                            </div>
                                                        ),
                                                        th: ({ children }) => (
                                                            <th className="border border-slate-700 bg-slate-800 px-3 py-2 text-left text-slate-200 font-medium">
                                                                {children}
                                                            </th>
                                                        ),
                                                        td: ({ children }) => (
                                                            <td className="border border-slate-700 px-3 py-2 text-slate-300">
                                                                {children}
                                                            </td>
                                                        ),
                                                    }}
                                                >
                                                    {message.content}
                                                </ReactMarkdown>
                                                
                                                {/* Code Playground Suggestion - COMPLETELY DISABLED */}
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {message.role === 'user' && (
                                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center">
                                        <User className="w-4 h-4 text-white" />
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Advanced Loading Indicator - Chain of Thought for DeepSeek */}
                    {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
                        <div className="space-y-4">
                            {/* Deep Thinking Mode - only for DeepSeek R1 */}
                            {isDeepThinking && selectedModel === 'deepseek-r1' ? (
                                <ChainOfThought 
                                    isActive={true}
                                    className="mb-6"
                                    modelName={'Deep Thinking Mode'}
                                    onComplete={() => {
                                        // Deep thinking completed
                                    }}
                                />
                            ) : (
                                <div className="flex items-start space-x-3 justify-start">
                                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                                        <Bot className="w-4 h-4 text-white" />
                                    </div>
                                    <Card className="chat-bubble chat-bubble-assistant bg-slate-800/50 border-slate-700/50">
                                        <CardContent className="p-4">
                                            {selectedModel.includes('deepseek-r1') ? (
                                                <ThinkingLoading variant="brain" />
                                            ) : (
                                                <LoadingIndicator variant="spinning" />
                                            )}
                                        </CardContent>
                                    </Card>
                                </div>
                            )}
                        </div>
                    )}

                    <div ref={messagesEndRef} className="h-4" />
                </div>
            </ScrollArea>
        </div>
    );
}
