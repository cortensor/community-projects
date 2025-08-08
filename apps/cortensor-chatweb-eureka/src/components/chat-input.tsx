// src/components/chat-input.tsx
"use client"

import React, { useState, useRef, useEffect, type KeyboardEvent } from "react"
import { Button } from "./ui/button"
import { Textarea } from "./ui/textarea"
import { Send, AlertCircle } from "lucide-react"
import { appConfig } from "../lib/app-config"
import { cn } from "../lib/utils"

interface ChatInputProps {
  input: string
  isLoading: boolean
  isPanelOpen: boolean
  isMobile: boolean
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  disabled?: boolean
}

export function ChatInput({ 
  input, 
  isLoading, 
  onInputChange, 
  onSubmit, 
  disabled = false 
}: ChatInputProps) {
  const [showLengthWarning, setShowLengthWarning] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const maxLength = appConfig.chat?.maxInputLength || 4000;

  // Auto-resize the textarea based on its content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 200; // Max height for the textarea
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [input]);

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
    <div className="border-t p-4 bg-background/80 backdrop-blur-md">
      <div className="max-w-4xl mx-auto">
        <form onSubmit={onSubmit} className="relative">
          <div className="flex flex-col w-full">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={onInputChange}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${appConfig.app.assistant}... (Ctrl+Enter to send)`}
              className="flex-1 bg-background/60 backdrop-blur-sm border-border/50 shadow-sm resize-none pr-14 py-3"
              disabled={isLoading || disabled}
              maxLength={maxLength + 100}
              rows={1}
            />
            <Button
              type="submit"
              disabled={!input.trim() || isLoading || isOverLimit || disabled}
              size="icon"
              className="absolute right-2 bottom-2 h-9 w-9 shrink-0 shadow-sm"
            >
              <Send className="h-4 w-4" />
            </Button>
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
      </div>
    </div>
  )
}
