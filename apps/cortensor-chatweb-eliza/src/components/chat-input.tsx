"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { Send, AlertCircle } from "lucide-react"
import { appConfig } from "../lib/app-config" // <-- PERBAIKAN DI SINI
import { cn } from "../lib/utils"

interface ChatInputProps {
  input: string
  isLoading: boolean
  isPanelOpen: boolean
  isMobile: boolean
  onInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void
}

export function ChatInput({ input, isLoading, isPanelOpen, isMobile, onInputChange, onSubmit }: ChatInputProps) {
  const [showLengthWarning, setShowLengthWarning] = useState(false)
  // FIX: Menggunakan appConfig
  const maxLength = appConfig.chat.maxInputLength

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setShowLengthWarning(value.length > maxLength * 0.9)
    onInputChange(e)
  }

  const isOverLimit = input.length > maxLength
  const remainingChars = maxLength - input.length

  return (
    <div
      className={cn(
        "border-t p-4 bg-background/80 backdrop-blur-md transition-all duration-300 ease-in-out border-border/50",
        isPanelOpen && !isMobile && "ml-80",
      )}
    >
      <div
        className={cn("max-w-4xl mx-auto transition-all duration-300 ease-in-out", isPanelOpen && !isMobile && "ml-16")}
      >
        <form onSubmit={onSubmit}>
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={handleInputChange}
                // FIX: Menggunakan appConfig
                placeholder={`Message ${appConfig.app.assistant}...`}
                className={cn(
                  "flex-1 bg-background/60 backdrop-blur-sm border-border/50 shadow-sm",
                  isOverLimit && "border-destructive focus-visible:ring-destructive",
                )}
                disabled={isLoading}
                maxLength={maxLength + 100}
              />
              <Button
                type="submit"
                disabled={!input.trim() || isLoading || isOverLimit}
                size="icon"
                className="shrink-0 shadow-sm"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

            {(showLengthWarning || isOverLimit) && (
              <div className="flex items-center gap-2 text-xs">
                {isOverLimit && <AlertCircle className="h-3 w-3 text-destructive" />}
                <span
                  className={cn(
                    "text-muted-foreground",
                    isOverLimit && "text-destructive",
                    remainingChars < 100 && remainingChars >= 0 && "text-orange-500",
                  )}
                >
                  {isOverLimit
                    ? `Message is ${Math.abs(remainingChars)} characters too long`
                    : `${remainingChars} characters remaining`}
                </span>
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
