// src/components/chat-input.tsx
"use client"

import React, { useState, useRef, useEffect, type KeyboardEvent } from "react"
import { Button } from "./ui/button"
import { Textarea } from "./ui/textarea"
import { Switch } from "./ui/switch"
import { Label } from "./ui/label"
import { Send, AlertCircle, Loader2, Zap, Shield, Globe, ChevronUp, ChevronDown } from "lucide-react"
import { ModelSelector } from "./model-selector"
import { DeepThinkingToggle } from "./deep-thinking-toggle"
import { appConfig } from "../lib/app-config"
import { cn } from "../lib/utils"
import { useKeyboard } from "../hooks/use-keyboard"

interface ChatInputProps {
  input: string
  isLoading: boolean
  isPanelOpen: boolean
  isMobile: boolean
  selectedModel: string
  isDeepThinking: boolean
  isMemoryMode: boolean
  onModelChange: (modelId: string, modelName: string) => void
  onDeepThinkingChange: (enabled: boolean) => void
  onMemoryModeChange: (checked: boolean) => void
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  disabled?: boolean
}

export function ChatInput({ 
  input, 
  isLoading, 
  onInputChange, 
  onSubmit, 
  disabled = false,
  isPanelOpen,
  isMobile,
  selectedModel,
  isDeepThinking,
  isMemoryMode,
  onModelChange,
  onDeepThinkingChange,
  onMemoryModeChange
}: ChatInputProps) {
  const [showLengthWarning, setShowLengthWarning] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const maxLength = appConfig.chat?.maxInputLength || 400000;
  
  // Professional keyboard handling
  const keyboard = useKeyboard()

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const scrollHeight = textareaRef.current.scrollHeight
      const maxHeight = isMobile ? 120 : 200
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`
    }
  }, [input, isMobile])

  // Auto-resize the textarea based on its content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = isMobile ? 120 : 200; // Smaller max height on mobile
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [input, isMobile]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !isLoading && input.trim()) {
      e.preventDefault();
      // Directly submit the form
      const form = e.currentTarget.closest('form');
      form?.requestSubmit();
    }
  };

  const isOverLimit = input.length > maxLength
  const remainingChars = maxLength - input.length

  return (
    <div 
      className={cn(
        "border-t bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/60",
        // Mobile positioning - STABLE fixed at bottom, no transforms
        isMobile && "mobile-chat-input fixed bottom-0 left-0 right-0 z-50 w-full", 
        isMobile && "pb-4 pt-3", // Consistent padding regardless of keyboard state
        // Desktop positioning and spacing  
        !isMobile && "p-4 fixed bottom-0 left-0 right-0 z-40",
        !isMobile && isPanelOpen && "ml-80", 
        !isMobile && !isPanelOpen && "ml-16"
      )}
      // Remove all dynamic styles that cause jumping
      style={undefined}
    >
      <div className="max-w-4xl mx-auto px-4">
        <form onSubmit={onSubmit} className="relative">
          <div className="flex flex-col w-full space-y-3">
            
            {/* Mobile Controls - Always visible with full controls */}
            {isMobile && (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-wrap gap-y-2">
                    <div className="flex items-center space-x-2">
                      <div className="text-xs text-muted-foreground">Model</div>
                      <ModelSelector 
                        selectedModel={selectedModel}
                        onModelChange={onModelChange}
                      />
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="memory-mode-mobile"
                        checked={isMemoryMode}
                        onCheckedChange={onMemoryModeChange}
                        className="data-[state=checked]:bg-blue-600 scale-90"
                      />
                      <Label htmlFor="memory-mode-mobile" className="text-xs text-muted-foreground">
                        Memory
                      </Label>
                    </div>
                  </div>
                </div>
                
                <DeepThinkingToggle
                  modelId={selectedModel}
                  enabled={isDeepThinking}
                  onToggle={onDeepThinkingChange}
                  disabled={isLoading}
                  collapsible={false} // Don't make it collapsible on mobile
                />
              </>
            )}
            
            {/* Desktop Controls */}
            {!isMobile && (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 lg:space-x-6">
                    <div className="flex items-center space-x-2">
                      <div className="text-sm text-muted-foreground">Model</div>
                      <ModelSelector 
                        selectedModel={selectedModel}
                        onModelChange={onModelChange}
                      />
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="memory-mode"
                        checked={isMemoryMode}
                        onCheckedChange={onMemoryModeChange}
                        className="data-[state=checked]:bg-blue-600"
                      />
                      <Label htmlFor="memory-mode" className="text-sm text-muted-foreground">
                        Memory Mode
                      </Label>
                    </div>
                  </div>
                </div>
                
                <DeepThinkingToggle
                  modelId={selectedModel}
                  enabled={isDeepThinking}
                  onToggle={onDeepThinkingChange}
                  disabled={isLoading}
                />
              </>
            )}
            
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={onInputChange}
                onKeyDown={handleKeyDown}
                placeholder={isMobile 
                  ? `Message ${appConfig.app.assistant}...` 
                  : `Message ${appConfig.app.assistant}... (Ctrl+Enter to send)`
                }
                className={cn(
                  "flex-1 bg-card/60 backdrop-blur-sm border-border/50 shadow-sm resize-none transition-all",
                  "focus:ring-2 focus:ring-primary/20 focus:border-primary/50",
                  "focus:outline-none", // Remove default outline
                  isMobile && "text-base leading-relaxed pr-12 py-3 rounded-lg min-h-[48px]", // Better mobile UX
                  !isMobile && "pr-14 py-3 rounded-lg",
                  isLoading && "animate-pulse cursor-not-allowed",
                  // Professional styling
                  "placeholder:text-muted-foreground/60",
                  "selection:bg-primary/20"
                )}
                disabled={isLoading || disabled}
                maxLength={maxLength + 100}
                rows={1}
                style={{ 
                  minHeight: isMobile ? '48px' : '40px', // Larger touch target on mobile
                  maxHeight: isMobile ? '120px' : '200px'
                }}
              />
              
              {/* Professional send button */}
              <Button
                type="submit"
                disabled={!input.trim() || isLoading || isOverLimit || disabled}
                size="icon"
                className={cn(
                  "absolute bottom-2 shrink-0 shadow-sm transition-all rounded-lg",
                  isMobile ? "right-2 h-10 w-10" : "right-2 h-9 w-9", // Larger touch target on mobile
                  isLoading 
                    ? "bg-primary/80 cursor-not-allowed" 
                    : "bg-primary hover:bg-primary/90 active:scale-95",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  // Professional hover effects
                  "hover:shadow-md active:shadow-sm",
                  !input.trim() && "opacity-40"
                )}
              >
                {isLoading ? (
                  <Loader2 className={cn("animate-spin", isMobile ? "h-4 w-4" : "h-4 w-4")} />
                ) : (
                  <Send className={cn(isMobile ? "h-4 w-4" : "h-4 w-4")} />
                )}
              </Button>
            </div>
          </div>

          {(!disabled && (showLengthWarning || isOverLimit)) && (
            <div className="flex items-center gap-2 text-xs mt-2">
              {isOverLimit && <AlertCircle className="h-3 w-3 text-destructive" />}
              <span
                className={cn(
                  "text-muted-foreground",
                  remainingChars < 100 && remainingChars >= 0 && "text-orange-500",
                  isOverLimit && "text-destructive"
                )}
              >
                {isOverLimit
                  ? `Message is ${Math.abs(remainingChars)} characters too long`
                  : `${remainingChars} characters remaining`}
              </span>
            </div>
          )}
        </form>
        
        {/* Professional Footer */}
        <div className="mt-2 pt-2 border-t border-border/50">
          <div className="text-center text-xs text-muted-foreground">
            <div className="flex justify-center items-center space-x-3 mb-1">
              <div className="flex items-center space-x-1">
                <Zap className="w-3 h-3" />
                <span>Cortensor AI</span>
              </div>
              <div className="flex items-center space-x-1">
                <Shield className="w-3 h-3" />
                <span>Secure</span>
              </div>
              <div className="flex items-center space-x-1">
                <Globe className="w-3 h-3" />
                <span>v{appConfig.app.version || '1.0.0'}</span>
              </div>
            </div>
            <div className="text-muted-foreground/70 text-xs">
              © 2025 Eureka - Advanced AI Assistant
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
