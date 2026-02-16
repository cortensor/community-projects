'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import {
  Send,
  User,
  Loader2,
  Plus,
  Search,
  SearchX,
  Sparkles,
  Zap,
  Square
} from 'lucide-react'
import { SEARCH_MARKER, AI_RESPONSE_CLEANUP_PATTERNS } from '@/lib/constants'
import { CHAT_HISTORY_LIMIT } from '@repo/ai';
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { getApiEndpoint } from '@/lib/api-config'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { useWeb2Chat, type ChatMessage, type ChatHistoryItem } from '../store/useWeb2ChatStore'

interface ChatInterfaceProps {
  className?: string
  userAddress: string
}

// Enhanced Cortensor-themed placeholder texts for AI thinking state
const CORTENSOR_PLACEHOLDER_TEXTS = [
  "🧠 Initializing quantum neural matrices...",
  "⚡ Establishing secure channels to 47 AI nodes...",
  "🔗 Synchronizing with distributed consciousness network...",
  "🌐 Routing through hyperspace data corridors...",
  "🔮 Consulting the collective AI wisdom...",
  "⚙️ Calibrating synaptic response algorithms...",
  "🚀 Launching deep learning protocols...",
  "💫 Weaving thoughts through cosmic data streams...",
  "🔬 Analyzing molecular patterns in your query...",
  "🌟 Harmonizing with stellar computation clusters...",
  "🎯 Targeting optimal response vectors...",
  "🔄 Cycling through infinite possibility matrices...",
  "🛸 Downloading insights from the AI mothership...",
  "⚛️ Splitting atoms of information for precision...",
  "🌊 Surfing waves of pure digital consciousness...",
  "🔥 Igniting fusion reactors of creativity...",
  "💎 Crystallizing thoughts into perfect responses...",
  "🌈 Painting responses with spectrum of knowledge...",
  "⚡ Channeling lightning-fast neural computations...",
  "🎭 Orchestrating symphony of AI collaboration...",
  "🔭 Scanning distant galaxies of information...",
  "🧬 Decoding DNA sequences of your question...",
  "🌀 Spiraling through dimensions of understanding...",
  "💫 Materializing wisdom from quantum foam...",
  "🎪 Performing computational acrobatics...",
  "🔮 Gazing into crystal balls of possibility...",
  "⚗️ Brewing perfect elixir of knowledge...",
  "🎨 Sculpting responses from raw data marble...",
  "🌺 Blooming insights in digital gardens...",
  "🎵 Composing melodies of meaningful answers..."
]

export function ChatInterface({ className, userAddress }: ChatInterfaceProps) {
  // Use Zustand store for state management
  const {
    selectedChatId,
    chatHistory,
    currentMessages: messages,
    setUserAddress,
    createNewChat,
    addMessage,
    setMessages,
    updateChatHistory
  } = useWeb2Chat()

  const [currentMessage, setCurrentMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isWebSearchEnabled, setIsWebSearchEnabled] = useState(true)
  const [currentPlaceholder, setCurrentPlaceholder] = useState('')
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  const placeholderIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Character limit for web search messages
  const WEB_SEARCH_CHAR_LIMIT = 390

  // Check if message exceeds character limit
  const isMessageTooLong = isWebSearchEnabled && currentMessage.length > WEB_SEARCH_CHAR_LIMIT
  const remainingChars = WEB_SEARCH_CHAR_LIMIT - currentMessage.length
  const isNearLimit = remainingChars <= 50 && remainingChars > 0
  const isOverLimit = remainingChars < 0

  // Initialize user address in store
  useEffect(() => {
    if (userAddress) {
      setUserAddress(userAddress)
    }
  }, [userAddress, setUserAddress])



  // Rotate placeholder texts while loading
  useEffect(() => {
    if (isLoading) {
      setCurrentPlaceholder(CORTENSOR_PLACEHOLDER_TEXTS[0])
      let index = 0
      placeholderIntervalRef.current = setInterval(() => {
        index = (index + 1) % CORTENSOR_PLACEHOLDER_TEXTS.length
        setCurrentPlaceholder(CORTENSOR_PLACEHOLDER_TEXTS[index])
      }, 2000)
    } else {
      setCurrentPlaceholder('')
      if (placeholderIntervalRef.current) {
        clearInterval(placeholderIntervalRef.current)
      }
    }

    return () => {
      if (placeholderIntervalRef.current) {
        clearInterval(placeholderIntervalRef.current)
      }
    }
  }, [isLoading])

  // Create new chat wrapper (store handles the logic)
  const handleCreateNewChat = useCallback(() => {
    return createNewChat()
  }, [createNewChat])

  // Update chat history wrapper
  const handleUpdateChatHistory = useCallback((message: string) => {
    if (selectedChatId) {
      updateChatHistory(selectedChatId, message, messages.length + 1)
    }
  }, [selectedChatId, updateChatHistory, messages.length])

  const handleCancelRequest = () => {
    if (abortController) {
      abortController.abort()
      setAbortController(null)
      setIsLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return

    let currentChatId = selectedChatId
    if (!currentChatId) {
      currentChatId = handleCreateNewChat()
    }

    // Removed forced auto-scroll to allow user control

    // Truncate message if it exceeds character limit for web search
    let messageToProcess = currentMessage.trim()
    let truncatedWarning = ''
    
    if (isWebSearchEnabled && messageToProcess.length > WEB_SEARCH_CHAR_LIMIT) {
      truncatedWarning = `\n\n⚠️ Message truncated to ${WEB_SEARCH_CHAR_LIMIT} characters for web search.`
      messageToProcess = messageToProcess.substring(0, WEB_SEARCH_CHAR_LIMIT)
    }

    // Prepare the message with search marker if enabled
    const formattedMessage = isWebSearchEnabled
      ? `${SEARCH_MARKER} ${messageToProcess}`
      : messageToProcess

    // Create user message without search marker for display
    const displayMessage = formattedMessage.startsWith(SEARCH_MARKER)
      ? formattedMessage.replace(SEARCH_MARKER, '').trim()
      : formattedMessage

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: displayMessage,
      sender: 'user',
      timestamp: new Date()
    }

    // Add user message to store
    addMessage(currentChatId, userMessage)
    handleUpdateChatHistory(userMessage.content)

    const messageToSend = formattedMessage
    setCurrentMessage('')
    setIsLoading(true)

    // Create new AbortController for this request
    const controller = new AbortController()
    setAbortController(controller)

    try {
      // Get the last N messages for context (including the new user message)
      const allMessages = [...messages, userMessage];
      const recentMessages = allMessages.slice(-CHAT_HISTORY_LIMIT);

      // Format messages for the API
      const formattedMessages = recentMessages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: [{ type: 'text', text: msg.content }]
      }));

      // Override the last message with the formatted message (including search marker if enabled)
      if (formattedMessages.length > 0) {
        formattedMessages[formattedMessages.length - 1] = {
          role: 'user',
          content: [{ type: 'text', text: messageToSend }]
        };
      }

      // Send the message history with chatId for context
      const response = await fetch(getApiEndpoint(`/api/chat?userAddress=${encodeURIComponent(userAddress)}&chatId=${encodeURIComponent(currentChatId)}`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: formattedMessages
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Clean the AI response using cleanup patterns
      let cleanResponse = data.content?.[0]?.text || data.message || "No response"
      AI_RESPONSE_CLEANUP_PATTERNS.forEach(pattern => {
        cleanResponse = cleanResponse.replace(pattern, '')
      })
      cleanResponse = cleanResponse.trim()

      const aiMessage: ChatMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: cleanResponse,
        sender: 'ai',
        timestamp: new Date()
      }

      // Add AI message to store
      addMessage(currentChatId, aiMessage)
      handleUpdateChatHistory(aiMessage.content)

    } catch (error) {
      // Check if the error is due to abort
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request was cancelled by user')
        return
      }

      console.error('Failed to send message:', error)
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: "Sorry, I encountered an error processing your message. Please try again.",
        sender: 'ai',
        timestamp: new Date()
      }
      // Add error message to store
      addMessage(currentChatId, errorMessage)
    } finally {
      setIsLoading(false)
      setAbortController(null)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Create initial chat if none exists
  useEffect(() => {
    if (!selectedChatId && chatHistory.length === 0) {
      createNewChat()
    }
  }, [selectedChatId, chatHistory.length, createNewChat])

  return (
    <TooltipProvider>
      <div className={cn(
        "relative flex flex-col w-full h-full",
        "bg-gradient-to-br from-background via-background to-card/20",
        "backdrop-blur-xl border border-border/30 rounded-2xl",
        "shadow-glass",
        className
      )}>
        {/* Header - Optimized for small screens */}
        <div className="flex-shrink-0 px-3 sm:px-4 md:px-6 py-2 sm:py-3 border-b border-border/30 bg-card/20 backdrop-blur-sm">
          <div className="flex justify-between items-center gap-2">
            <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
              <div className="relative flex-shrink-0">
                <div className="flex justify-center items-center w-8 sm:w-10 h-8 sm:h-10 rounded-2xl bg-gradient-primary shadow-glow-primary">
                  <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 sm:w-5 h-4 sm:h-5" />
                  <div className="absolute -top-0.5 -right-0.5 w-2.5 sm:w-3 h-2.5 sm:h-3 bg-accent rounded-full animate-pulse shadow-glow-accent">
                    <Sparkles className="w-1.5 sm:w-2 h-1.5 sm:h-2 text-background m-0.5" />
                  </div>
                </div>
              </div>
              <div className="min-w-0 flex-1">
                <CardTitle className="text-base sm:text-lg md:text-xl font-bold font-futura bg-gradient-primary bg-clip-text text-transparent gradient-text truncate">
                  cortiGPT
                </CardTitle>
                <p className="text-xs text-muted-foreground font-tech hidden sm:block">
                  Neural Network Intelligence
                </p>
              </div>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={handleCreateNewChat}
                  size="sm"
                  className={cn(
                    "relative overflow-hidden group font-tech flex-shrink-0",
                    "bg-gradient-secondary hover:shadow-glow-secondary",
                    "transition-all duration-300 hover:scale-105",
                    "border border-secondary/20 glow-secondary",
                    "w-8 h-8 p-0 sm:w-auto sm:h-auto sm:px-3 sm:py-2"
                  )}
                >
                  <Plus className="w-4 h-4 sm:mr-2" />
                  <span className="hidden sm:inline">New Chat</span>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Start a new conversation
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Messages Area - with bottom padding for fixed input */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="px-4 sm:px-6 py-4 sm:py-6 pb-32 sm:pb-36">
              {messages.length === 0 && !isLoading ? (
                <div className="flex items-center justify-center h-full min-h-[300px] sm:min-h-[400px]">
                  <div className="text-center space-y-4 sm:space-y-6 max-w-xs sm:max-w-md">
                    <div className="relative">
                      <div className="w-16 sm:w-20 h-16 sm:h-20 mx-auto rounded-3xl bg-gradient-neural shadow-glow-primary animate-pulse flex items-center justify-center">
                        <img src="/cortigpt-4.png" alt="CortiGPT" className="w-20 sm:w-24 h-20 sm:h-24" />
                      </div>
                      <div className="absolute -top-1 sm:-top-2 -right-1 sm:-right-2 w-6 sm:w-8 h-6 sm:h-8 bg-accent rounded-full shadow-glow-accent animate-bounce">
                        <Zap className="w-3 sm:w-4 h-3 sm:h-4 text-background m-1.5 sm:m-2" />
                      </div>
                    </div>
                    <div className="space-y-2 sm:space-y-3">
                      <h3 className="text-lg sm:text-xl font-semibold font-futura text-primary-glow">
                        Welcome to cortiGPT
                      </h3>
                      <p className="text-sm sm:text-base text-muted-foreground leading-relaxed font-tech">
                        Your AI-powered assistant is ready to help. Start a conversation by typing a message below.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1 sm:gap-2 justify-center">
                      <div className="px-2 sm:px-3 py-1 bg-neural-primary/10 rounded-full text-xs text-neural-primary border border-neural-primary/20 glow-primary">
                        Neural Network
                      </div>
                      <div className="px-2 sm:px-3 py-1 bg-neural-secondary/10 rounded-full text-xs text-neural-secondary border border-neural-secondary/20 glow-secondary">
                        Web Search
                      </div>
                      <div className="px-2 sm:px-3 py-1 bg-neural-tertiary/10 rounded-full text-xs text-neural-tertiary border border-neural-tertiary/20 glow-accent">
                        Real-time
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6 sm:space-y-8">
                  {messages.map((message, index) => (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-3 sm:gap-4 group animate-in slide-in-from-bottom-4 duration-500",
                        message.sender === 'user' ? 'justify-end' : 'justify-start'
                      )}
                      style={{ animationDelay: `${index * 100}ms` }}
                    >
                      {message.sender === 'ai' && (
                        <div className="flex-shrink-0">
                          <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-2xl bg-gradient-primary shadow-glow-primary flex items-center justify-center">
                            <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 sm:w-5 h-4 sm:h-5" />
                          </div>
                        </div>
                      )}

                      <div className={cn(
                        "max-w-[85%] sm:max-w-[80%] lg:max-w-[70%]",
                        message.sender === 'user' ? 'order-first' : ''
                      )}>
                        <div className={cn(
                          "rounded-2xl px-4 sm:px-6 py-3 sm:py-4 relative overflow-hidden",
                          "backdrop-blur-sm border transition-all duration-300",
                          "group-hover:shadow-lg group-hover:scale-[1.02]",
                          message.sender === 'user'
                            ? cn(
                              "bg-gradient-primary text-background ml-auto",
                              "shadow-glow-primary/30 border-primary/20",
                              "before:absolute before:inset-0 before:bg-gradient-to-r",
                              "before:from-transparent before:via-white/10 before:to-transparent",
                              "before:-translate-x-full hover:before:translate-x-full",
                              "before:transition-transform before:duration-700"
                            )
                            : cn(
                              "bg-card/40 border-border/30",
                              "shadow-sm hover:shadow-glow-secondary/20"
                            )
                        )}>
                          {message.sender === 'ai' ? (
                            <MarkdownRenderer
                              content={message.content}
                              className="prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 text-foreground text-xs sm:text-sm font-tech"
                            />
                          ) : (
                            <p className="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed font-tech break-words">
                              {message.content}
                            </p>
                          )}
                        </div>

                        <div className={cn(
                          "flex items-center gap-2 mt-1 text-xs text-muted-foreground",
                          message.sender === 'user' ? 'justify-end' : 'justify-start'
                        )}>
                          <span>{formatDistanceToNow(message.timestamp, { addSuffix: true })}</span>
                        </div>
                      </div>

                      {message.sender === 'user' && (
                        <div className="flex-shrink-0">
                          <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-2xl bg-gradient-secondary shadow-glow-secondary flex items-center justify-center">
                            <User className="w-4 sm:w-5 h-4 sm:h-5 text-background" />
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Loading placeholder */}
                  {isLoading && (
                    <div className="flex gap-3 sm:gap-4 justify-start animate-in slide-in-from-bottom-4 duration-500">
                      <div className="flex-shrink-0">
                        <div className="w-8 sm:w-10 h-8 sm:h-10 rounded-2xl bg-gradient-primary shadow-glow-primary flex items-center justify-center animate-pulse">
                          <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 sm:w-5 h-4 sm:h-5" />
                        </div>
                      </div>

                      <div className="max-w-[85%] sm:max-w-[80%] lg:max-w-[70%]">
                        <div className="rounded-2xl px-4 sm:px-6 py-3 sm:py-4 bg-card/40 backdrop-blur-sm border border-border/30">
                          <div className="flex gap-2 items-center">
                            <Loader2 className="w-4 sm:w-5 h-4 sm:h-5 animate-spin text-neural-primary" />
                            <p className="text-xs sm:text-sm italic text-muted-foreground animate-pulse font-tech break-words">
                              {currentPlaceholder}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Removed scroll anchor to allow free scrolling */}
                </div>
              )}
              
              {/* Bottom spacing to allow scrolling past last message */}
              <div className="h-32 sm:h-40" aria-hidden="true" />
            </div>
          </ScrollArea>
        </div>

        {/* Input Area - Absolutely positioned at bottom */}
        <div className="absolute bottom-4 left-0 right-0 border-t border-border/30 bg-background/95 backdrop-blur-md p-3 sm:p-4 space-y-3 sm:space-y-4 rounded-b-2xl glass z-50">
          <div className="flex justify-center">
            <div className="flex gap-2 sm:gap-3 items-end w-full max-w-3xl">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={() => setIsWebSearchEnabled(!isWebSearchEnabled)}
                    variant="outline"
                    size="sm"
                    className={cn(
                      "w-10 h-10 sm:w-12 sm:h-12 p-0 flex-shrink-0",
                      "relative overflow-hidden group transition-all duration-300 font-tech",
                      "border-2 hover:scale-105 glass",
                      isWebSearchEnabled
                        ? "bg-gradient-secondary text-background border-neural-secondary shadow-glow-secondary glow-secondary"
                        : "border-border/50 hover:border-neural-secondary/50 hover:shadow-glow-secondary/20"
                    )}
                  >
                    {isWebSearchEnabled ? (
                      <Search className="w-4 sm:w-5 h-4 sm:h-5" />
                    ) : (
                      <SearchX className="w-4 sm:w-5 h-4 sm:h-5" />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <div className="text-center">
                    <div className="font-medium">
                      Web Search: {isWebSearchEnabled ? "ON" : "OFF"}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {isWebSearchEnabled
                        ? "AI will search the web for current information"
                        : "AI will use only its training data"}
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>

              <div className="flex-1 relative min-w-0">
                <Input
                  placeholder={isWebSearchEnabled ? "🔍 Web search enabled - Type your message..." : "Type your message..."}
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className={cn(
                    "text-base h-10 sm:h-12 px-3 sm:px-4 rounded-2xl border-2 transition-all duration-300 font-tech",
                    "bg-background/50 backdrop-blur-sm glass w-full",
                    "focus:border-neural-primary/50 focus:shadow-glow-primary/20 focus:glow-primary",
                    "placeholder:text-muted-foreground/70",
                    "focus:h-10 sm:focus:h-12",
                    isOverLimit && "border-red-500/50 shadow-glow-accent/20",
                    isNearLimit && "border-amber-500/50 shadow-glow-secondary/20"
                  )}
                />
                {/* Compact web search status and character counter */}
                {isWebSearchEnabled && (
                  <div className="flex items-center justify-between mt-2 px-1">
                    <div className="flex items-center gap-2 text-xs text-neural-secondary/80 font-tech">
                      <Search className="w-3 h-3" />
                      <span>Web search enabled</span>
                    </div>
                    <span className={cn(
                      "text-xs font-tech",
                      remainingChars <= 0 ? "text-red-500" : 
                      remainingChars <= 50 ? "text-amber-500" : 
                      "text-muted-foreground"
                    )}>
                      {remainingChars <= 0 ? `${Math.abs(remainingChars)} over` : `${remainingChars} left`}
                    </span>
                  </div>
                )}
              </div>

              {isLoading ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleCancelRequest}
                      size="sm"
                      className={cn(
                        "relative overflow-hidden group w-10 h-10 sm:w-12 sm:h-12 p-0 flex-shrink-0 font-tech",
                        "bg-red-600 hover:bg-red-700 text-white",
                        "transition-all duration-300 hover:scale-105"
                      )}
                    >
                      <Square className="w-4 sm:w-5 h-4 sm:h-5" />
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Stop generation
                  </TooltipContent>
                </Tooltip>
              ) : (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleSendMessage}
                      disabled={!currentMessage.trim() || (isWebSearchEnabled && isOverLimit)}
                      size="sm"
                      className={cn(
                        "relative overflow-hidden group w-10 h-10 sm:w-12 sm:h-12 p-0 flex-shrink-0 font-tech",
                        "bg-gradient-primary hover:shadow-glow-primary glow-primary",
                        "transition-all duration-300 hover:scale-105",
                        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                      )}
                    >
                      <Send className="w-4 sm:w-5 h-4 sm:h-5" />
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Send message (Enter)
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}