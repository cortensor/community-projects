"use client"

import { Brain, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface ThinkingLoadingProps {
  className?: string
  variant?: 'default' | 'brain' | 'dots'
}

export function ThinkingLoading({ 
  className, 
  variant = 'brain' 
}: ThinkingLoadingProps) {
  
  if (variant === 'brain') {
    return (
      <div className={cn("flex items-center gap-3 py-3", className)}>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 text-indigo-500 animate-pulse">
            <Brain className="w-full h-full" />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-sm text-muted-foreground font-medium">
              Thinking process
            </span>
            <div className="flex gap-1">
              <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Default dots variant
  return (
    <div className={cn("flex items-center gap-2 py-3", className)}>
      <div className="flex gap-1">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
      <span className="text-sm text-muted-foreground">Thinking...</span>
    </div>
  )
}
