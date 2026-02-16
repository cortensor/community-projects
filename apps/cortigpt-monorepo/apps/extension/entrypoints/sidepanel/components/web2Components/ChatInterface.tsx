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
  X,
  Square
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { getApiEndpoint } from '@/lib/api-config'
import { SEARCH_MARKER, AI_RESPONSE_CLEANUP_PATTERNS, CHAT_HISTORY_LIMIT } from '@/lib/constants'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import {
  SelectedTextPreview,
  ClearSelectedTextMessage,
  TextSelectionUpdateMessage,
  GetSelectedTextMessage,
  MessageResponse
} from '@/types/messaging'
import { useWeb2Chat, ChatMessage } from '@/stores/useWeb2ChatStore'
import type { TextSelectionData } from '@/types/messaging'

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
  const [currentMessage, setCurrentMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentPlaceholder, setCurrentPlaceholder] = useState('')
  const [selectedTextPreview, setSelectedTextPreview] = useState<SelectedTextPreview | null>(null)
  const [isWebSearchEnabled, setIsWebSearchEnabled] = useState(true)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  const placeholderIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Character limit for web search messages
  const WEB_SEARCH_CHAR_LIMIT = 390

  // Check if message exceeds character limit
  const isMessageTooLong = isWebSearchEnabled && currentMessage.length > WEB_SEARCH_CHAR_LIMIT
  const remainingChars = WEB_SEARCH_CHAR_LIMIT - currentMessage.length
  const isNearLimit = remainingChars <= 50 && remainingChars > 0
  const isOverLimit = remainingChars < 0

  // Use Web2 Zustand store
  const {
    currentMessages: messages,
    chatHistory,
    selectedChatId,
    setUserAddress,
    createNewChat,
    addMessage,
    updateChatHistory
  } = useWeb2Chat()

  // Initialize user address in store
  useEffect(() => {
    if (userAddress) {
      setUserAddress(userAddress)
    }
  }, [userAddress, setUserAddress])

  // Utility function to truncate text to two lines
  const truncateToTwoLines = (text: string, maxLength: number = 100): string => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }



  // Removed scroll management to allow free scrolling during loading



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

  // Listen for text selection and website content messages from background script
  useEffect(() => {
    const handleMessage = (message: any, sender: any, sendResponse: any) => {
      if (message.type === 'TEXT_SELECTION_UPDATE') {
        const textSelectionMessage = message as TextSelectionUpdateMessage
        if (textSelectionMessage.data) {
          const preview: SelectedTextPreview = {
            originalText: textSelectionMessage.data.text,
            truncatedText: truncateToTwoLines(textSelectionMessage.data.text),
            url: textSelectionMessage.data.url,
            timestamp: textSelectionMessage.data.timestamp,
            isVisible: true
          }
          setSelectedTextPreview(preview)
        } else {
          setSelectedTextPreview(null)
        }
      }
      return true
    }

    // Listen for messages from background script
    if (typeof browser !== 'undefined' && browser?.runtime?.onMessage) {
      browser.runtime.onMessage.addListener(handleMessage);
    } else if (typeof chrome !== 'undefined' && chrome?.runtime?.onMessage) {
      chrome.runtime.onMessage.addListener(handleMessage);
    }

    // Request any existing selected text when component mounts
    const getSelectedTextMessage: GetSelectedTextMessage = { type: 'GET_SELECTED_TEXT' };
    const runtimeAPI = typeof browser !== 'undefined' ? browser : chrome;
    if (runtimeAPI?.runtime?.sendMessage) {
      runtimeAPI.runtime.sendMessage(getSelectedTextMessage)
      .then((response: MessageResponse) => {
        if (response.success && response.data && 'text' in response.data) {
          const textData = response.data as TextSelectionData;
          const preview: SelectedTextPreview = {
            originalText: textData.text,
            truncatedText: truncateToTwoLines(textData.text),
            url: textData.url,
            timestamp: textData.timestamp,
            isVisible: true
          };
          setSelectedTextPreview(preview);
        }
      })
      .catch(() => {
        // Background script might not be ready yet
        console.log('Could not get selected text on mount');
      });
    }

    return () => {
      if (typeof browser !== 'undefined' && browser?.runtime?.onMessage) {
        browser.runtime.onMessage.removeListener(handleMessage);
      } else if (typeof chrome !== 'undefined' && chrome?.runtime?.onMessage) {
        chrome.runtime.onMessage.removeListener(handleMessage);
      }
    };
  }, []);

  // Wrapper function for creating new chat
  const handleCreateNewChat = () => {
    createNewChat()
  }

  const clearSelectedText = () => {
    setSelectedTextPreview(null)
    const clearMessage: ClearSelectedTextMessage = { type: 'CLEAR_SELECTED_TEXT' }
    const runtimeAPI = typeof browser !== 'undefined' ? browser : chrome;
    if (runtimeAPI?.runtime?.sendMessage) {
      runtimeAPI.runtime.sendMessage(clearMessage)
    }
  }

  const handleCancelRequest = () => {
    if (abortController) {
      abortController.abort()
      setAbortController(null)
      setIsLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!currentMessage.trim() && !selectedTextPreview) return
    if (isLoading) return

    // Allow free scrolling - no forced focus

    let messageContent = currentMessage.trim()

    // Truncate message if it exceeds character limit for web search
    let truncatedWarning = ''
    if (isWebSearchEnabled && messageContent.length > WEB_SEARCH_CHAR_LIMIT) {
      truncatedWarning = `\n\n⚠️ Message truncated to ${WEB_SEARCH_CHAR_LIMIT} characters for web search.`
      messageContent = messageContent.substring(0, WEB_SEARCH_CHAR_LIMIT)
    }

    // Store the selected text for display above the message
    let selectedTextForDisplay: SelectedTextPreview | null = null
    if (selectedTextPreview) {
      selectedTextForDisplay = { ...selectedTextPreview }
      const contextMessage = `Context from ${new URL(selectedTextPreview.url).hostname}:\n\n"${selectedTextPreview.originalText}"\n\nUser question: ${messageContent || 'Please analyze this text.'}`
      messageContent = contextMessage
    }

    // If no chat is selected, create a new one
    let currentChatId = selectedChatId
    if (!currentChatId) {
      currentChatId = createNewChat()
    }

    // Prepare the message with search marker if enabled
    const formattedMessage = isWebSearchEnabled
      ? `${SEARCH_MARKER} ${messageContent}`
      : messageContent

    // Create user message without search marker for display
    const displayMessage = selectedTextPreview
      ? (currentMessage.trim() || 'Please analyze this text.')
      : (formattedMessage.startsWith(SEARCH_MARKER)
        ? formattedMessage.replace(SEARCH_MARKER, '').trim()
        : formattedMessage)

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: displayMessage,
      sender: 'user',
      timestamp: new Date(),
      selectedText: selectedTextForDisplay ? {
        text: selectedTextForDisplay.originalText,
        url: selectedTextForDisplay.url,
        timestamp: selectedTextForDisplay.timestamp
      } : undefined
    }

    // Add message to store
    addMessage(currentChatId, userMessage)
    updateChatHistory(currentChatId, userMessage.content, messages.length + 1)

    const messageToSend = formattedMessage
    setCurrentMessage('')
    setSelectedTextPreview(null)
    setIsLoading(true)

    // Clear selected text from background
    const clearMessage: ClearSelectedTextMessage = { type: 'CLEAR_SELECTED_TEXT' }
    const runtimeAPI = typeof browser !== 'undefined' ? browser : chrome;
    if (runtimeAPI?.runtime?.sendMessage) {
      runtimeAPI.runtime.sendMessage(clearMessage)
    }

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

      // Add AI response to store
      addMessage(currentChatId, aiMessage)
      updateChatHistory(currentChatId, aiMessage.content, messages.length + 2)

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

  const canSend = (currentMessage.trim() || selectedTextPreview) && !isLoading && !(isWebSearchEnabled && isOverLimit)

  return (
    <TooltipProvider>
      <div className={cn(
        "relative flex flex-col w-full h-full",
        "bg-gradient-to-br from-background via-background to-card/20",
        "backdrop-blur-xl border border-border/30 rounded-2xl",
        "shadow-glass",
        "w-full max-w-full",
        className
      )}>
        {/* Header - Optimized for small screens */}
        <div className="flex-shrink-0 px-2 sm:px-4 py-1.5 sm:py-2 border-b border-border/30 bg-card/20 backdrop-blur-sm">
          <div className="flex justify-between items-center gap-2">
            <div className="flex items-center space-x-2 min-w-0 flex-1">
              <div className="relative flex-shrink-0">
                <div className="flex justify-center items-center w-8 sm:w-10 h-8 sm:h-10 rounded-2xl bg-gradient-primary shadow-glow-primary">
                  <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 sm:w-5 h-4 sm:h-5" />
                  <div className="absolute -top-0.5 -right-0.5 w-2.5 sm:w-3 h-2.5 sm:h-3 bg-accent rounded-full animate-pulse shadow-glow-accent">
                    <Sparkles className="w-1.5 sm:w-2 h-1.5 sm:h-2 text-background m-0.5" />
                  </div>
                </div>
              </div>
              <div className="min-w-0 flex-1">
                <CardTitle className="text-sm sm:text-lg font-bold bg-gradient-primary bg-clip-text text-transparent truncate">
                  cortiGPT
                </CardTitle>
                <p className="text-xs text-muted-foreground truncate hidden sm:block">
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
                    "relative overflow-hidden group flex-shrink-0",
                    "bg-gradient-secondary hover:shadow-glow-secondary",
                    "transition-all duration-300 hover:scale-105",
                    "border border-secondary/20 p-1.5 sm:p-2 w-7 sm:w-8 h-7 sm:h-8"
                  )}
                >
                  <Plus className="w-3 sm:w-4 h-3 sm:h-4" />
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Start new chat
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="w-full h-full max-h-full">
            <div className="px-2 sm:px-4 py-2 sm:py-4">
              {messages.length === 0 && !isLoading ? (
                <div className="flex items-center justify-center h-full min-h-[300px]">
                  <div className="text-center space-y-4 max-w-xs">
                    <div className="relative">
                      <div className="w-16 h-16 mx-auto rounded-3xl bg-gradient-neural shadow-glow-primary animate-pulse">
                        <img src="/cortigpt-4.png" alt="CortiGPT" className="w-20 h-20 m-3" />
                      </div>
                      <div className="absolute -top-1 -right-1 w-6 h-6 bg-accent rounded-full shadow-glow-accent animate-bounce">
                        <Zap className="w-3 h-3 text-background m-1.5" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold text-foreground">
                        Welcome to cortiGPT
                      </h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Your AI assistant is ready. Start a conversation or select text on the page to analyze.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1 justify-center">
                      <div className="px-2 py-1 bg-primary/10 rounded-full text-xs text-primary border border-primary/20">
                        Neural
                      </div>
                      <div className="px-2 py-1 bg-secondary/10 rounded-full text-xs text-secondary border border-secondary/20">
                        Web Search
                      </div>
                      <div className="px-2 py-1 bg-accent/10 rounded-full text-xs text-accent border border-accent/20">
                        Real-time
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 sm:space-y-4">
                  {messages.map((message: ChatMessage, index) => (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-3 group animate-in slide-in-from-bottom-4 duration-500",
                        message.sender === 'user' ? 'justify-end' : 'justify-start'
                      )}
                      style={{ animationDelay: `${index * 100}ms` }}
                    >
                      {message.sender === 'ai' && (
                        <div className="flex-shrink-0">
                          <div className="w-8 h-8 rounded-2xl bg-gradient-primary shadow-glow-primary flex items-center justify-center">
                            <img src="/cortigpt-4.png" alt="CortiGPT" className="w-8 h-8" />
                          </div>
                        </div>
                      )}

                      <div className={cn(
                        "max-w-[85%]",
                        message.sender === 'user' ? 'order-first' : ''
                      )}>
                        {/* Selected text preview for user messages */}
                        {message.sender === 'user' && message.selectedText && (
                          <div className="mb-2 p-2 rounded-lg bg-accent/10 border border-accent/20 backdrop-blur-sm">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-accent text-xs">📄</span>
                              <span className="text-xs text-muted-foreground">
                                Context from {new URL(message.selectedText.url).hostname}
                              </span>
                            </div>
                            <p className="text-xs text-foreground/80 italic leading-relaxed break-words">
                              "{message.selectedText.text.length > 150 
                                ? message.selectedText.text.substring(0, 150) + '...' 
                                : message.selectedText.text}"
                            </p>
                          </div>
                        )}

                        <div className={cn(
                          "rounded-2xl px-4 py-3 relative overflow-hidden",
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
                              className="prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 text-foreground text-xs"
                            />
                          ) : (
                            <p className="text-xs whitespace-pre-wrap leading-relaxed break-words">
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
                          <div className="w-8 h-8 rounded-2xl bg-gradient-secondary shadow-glow-secondary flex items-center justify-center">
                            <User className="w-4 h-4 text-background" />
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Loading placeholder */}
                  {isLoading && (
                    <div className="flex gap-3 justify-start animate-in slide-in-from-bottom-4 duration-500">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-2xl bg-gradient-primary shadow-glow-primary flex items-center justify-center animate-pulse">
                          <img src="/cortigpt-4.png" alt="CortiGPT" className="w-4 h-4" />
                        </div>
                      </div>

                      <div className="max-w-[85%]">
                        <div className="rounded-2xl px-4 py-3 bg-card/40 backdrop-blur-sm border border-border/30">
                          <div className="flex gap-2 items-center">
                            <Loader2 className="w-4 h-4 animate-spin text-primary" />
                            <p className="text-xs italic text-muted-foreground animate-pulse break-words">
                              {currentPlaceholder}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Bottom spacing for scrolling past last message */}
                  <div className="h-16 sm:h-24"></div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Input Area - Fixed at bottom */}
        <div className="absolute bottom-2 sm:bottom-4 left-0 right-0 p-2 sm:p-4 border-t border-border/30 bg-background/95 backdrop-blur-md rounded-b-2xl w-full z-50">
          {/* Web Search Status Indicator */}
          {isWebSearchEnabled && (
            <div className={cn(
              "flex gap-2 items-center px-2 sm:px-3 py-1.5 sm:py-2 mb-1.5 sm:mb-2 rounded-xl",
              "bg-gradient-to-r from-secondary/10 to-accent/10",
              "border border-secondary/20 backdrop-blur-sm",
              "animate-in slide-in-from-bottom-2 duration-300"
            )}>
              <div className="w-5 sm:w-6 h-5 sm:h-6 bg-secondary/20 rounded-full flex items-center justify-center">
                <Search className="w-2.5 sm:w-3 h-2.5 sm:h-3 text-secondary" />
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-secondary">
                  Web search enabled
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-secondary/80">
                    {currentMessage.length}/{WEB_SEARCH_CHAR_LIMIT}
                  </span>
                  {isNearLimit && (
                    <span className="text-xs text-amber-500 animate-pulse">
                      ⚠️
                    </span>
                  )}
                  {isOverLimit && (
                    <span className="text-xs text-red-500 animate-pulse">
                      ❌
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Selected Text Preview */}
          {selectedTextPreview && selectedTextPreview.isVisible && (
            <div className={cn(
              "p-2 sm:p-3 mb-2 sm:mb-3 rounded-xl border backdrop-blur-sm",
              "bg-gradient-to-r from-accent/10 to-primary/10",
              "border-accent/20 animate-in slide-in-from-bottom-2 duration-300"
            )}>
              <div className="flex gap-2 justify-between items-start mb-2">
                <div className="flex gap-2 items-center text-xs text-muted-foreground">
                  <span className="text-accent">📄</span>
                  <span>Selected from {new URL(selectedTextPreview.url).hostname}</span>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={clearSelectedText}
                      variant="ghost"
                      size="sm"
                      className="p-1 h-6 w-6 hover:bg-destructive/20 hover:text-destructive"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Clear selected text
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-xs text-foreground/80 leading-relaxed break-words">
                "{selectedTextPreview.truncatedText}"
              </p>
            </div>
          )}

          <div className="flex gap-1.5 sm:gap-2 items-stretch min-h-[40px] sm:min-h-[48px] w-full max-w-full">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={() => setIsWebSearchEnabled(!isWebSearchEnabled)}
                  variant="outline"
                  size="sm"
                  className={cn(
                    "relative overflow-hidden group transition-all duration-300 flex-shrink-0",
                    "border-2 hover:scale-105 px-2 sm:px-3 h-10 sm:h-12",
                    isWebSearchEnabled
                      ? "bg-gradient-secondary text-background border-secondary shadow-glow-secondary"
                      : "border-border/50 hover:border-secondary/50 hover:shadow-glow-secondary/20"
                  )}
                >
                  {isWebSearchEnabled ? (
                    <Search className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                  ) : (
                    <SearchX className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <div className="text-center">
                  <div className="font-medium">
                    {isWebSearchEnabled ? "Web Search: ON" : "Web Search: OFF"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {isWebSearchEnabled
                      ? "AI will search the web for current information"
                      : "AI will use only its training data"}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>

            <div className="flex-1 min-w-0 relative">
              <Input
                placeholder={selectedTextPreview
                  ? "Ask about the selected text..."
                  : (isWebSearchEnabled ? "🔍 Web search enabled - Type your message..." : "Type your message...")}
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                className={cn(
                  "text-base h-10 sm:h-12 px-3 sm:px-4 rounded-2xl border-2 transition-all duration-300 w-full",
                  "bg-background/50 backdrop-blur-sm resize-none",
                  "focus:border-primary/50 focus:shadow-glow-primary/20",
                  "placeholder:text-muted-foreground/70",
                  "focus:h-10 sm:focus:h-12",
                  isOverLimit && "border-red-500/50",
                  isNearLimit && "border-amber-500/50"
                )}
              />
              {/* Character counter overlay */}
              {isWebSearchEnabled && (
                <div className="absolute -bottom-5 right-0 text-xs text-muted-foreground">
                  <span className={cn(
                    remainingChars <= 0 ? "text-red-500" : 
                    remainingChars <= 50 ? "text-amber-500" : 
                    "text-muted-foreground"
                  )}>
                    {remainingChars <= 0 ? `${Math.abs(remainingChars)} over` : `${remainingChars} left`}
                  </span>
                </div>
              )}
            </div>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={isLoading ? handleCancelRequest : handleSendMessage}
                  disabled={!canSend && !isLoading}
                  size="sm"
                  className={cn(
                    "relative overflow-hidden group h-10 sm:h-12 px-3 sm:px-4 flex-shrink-0",
                    isLoading
                      ? "bg-destructive hover:bg-destructive/90 hover:shadow-glow-destructive"
                      : "bg-gradient-primary hover:shadow-glow-primary",
                    "transition-all duration-300 hover:scale-105",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  )}
                >
                  {isLoading ? (
                    <Square className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                  ) : (
                    <Send className="w-3.5 sm:w-4 h-3.5 sm:h-4" />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                {isLoading ? "Cancel request" : "Send message (Enter)"}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}