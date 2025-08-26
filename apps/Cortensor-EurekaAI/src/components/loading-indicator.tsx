"use client"

import { Bot, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { SpinningTextLoader, TypewriterLoader } from "./spinning-text-loader"

interface LoadingIndicatorProps {
  className?: string
  message?: string
  variant?: 'default' | 'simple' | 'elegant' | 'spinning' | 'typewriter'
}

export function LoadingIndicator({ 
  className, 
  message = "Just a sec...", 
  variant = 'spinning' 
}: LoadingIndicatorProps) {
  
  // Spinning text variant - rotating loading messages
  if (variant === 'spinning') {
    return (
      <div className={cn("py-3", className)}>
        <SpinningTextLoader />
      </div>
    )
  }
  
  // Typewriter variant - typing effect
  if (variant === 'typewriter') {
    return (
      <div className={cn("py-3", className)}>
        <TypewriterLoader />
      </div>
    )
  }
  
  // Elegant variant - spinning circle with text
  if (variant === 'elegant') {
    return (
      <div className={cn("flex items-center justify-center py-4", className)}>
        {/* Spinning text loader */}
        <div className="flex items-center gap-3">
          {/* Rotating text spinner */}
          <div className="relative">
            <div className="w-6 h-6 text-blue-500 animate-spin">
              <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
                <circle 
                  cx="12" 
                  cy="12" 
                  r="10" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeDasharray="60 40"
                  className="opacity-75"
                />
              </svg>
            </div>
          </div>
          
          {/* Animated message with typewriter effect */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">{message}</span>
            
            {/* Blinking cursor */}
            <span className="inline-block w-0.5 h-4 bg-blue-500 animate-pulse" />
          </div>
        </div>
      </div>
    )
  }
  
  // Simple variant
  if (variant === 'simple') {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite]" />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.2s]" />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.4s]" />
        </div>
        <span className="text-sm text-muted-foreground">{message}</span>
      </div>
    )
  }
  
  // Default variant - original design
  return (
    <div className={cn("flex items-center gap-3 p-4", className)}>
      <div className="flex-shrink-0 relative">
        <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center animate-[breathing_2s_ease-in-out_infinite]">
          <Bot className="h-4 w-4 text-primary animate-pulse" />
        </div>
        {/* Enhanced breathing ring animation */}
        <div className="absolute inset-0 rounded-full border-2 border-primary/30 animate-[pulse-ring_2s_ease-out_infinite]" />
      </div>
      
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">{message}</span>
          
          {/* Enhanced typing dots animation */}
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite]" />
            <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.2s]" />
            <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.4s]" />
          </div>
        </div>
        
        {/* Enhanced progress bar animation */}
        <div className="mt-2 h-1 bg-primary/10 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-primary/50 via-primary to-primary/50 rounded-full animate-[slide-progress_3s_ease-in-out_infinite] w-1/3" />
        </div>
      </div>
    </div>
  )
}

export function ThinkingBubble({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3 text-sm font-medium text-muted-foreground", className)}>
      <div className="relative w-5 h-5">
        {/* Brain/thinking icon with sparkle effect */}
        <svg 
          className="absolute inset-0 m-auto animate-[sparkle_1.5s_ease-in-out_infinite]" 
          width="12" 
          height="12" 
          viewBox="0 0 24 24" 
          fill="currentColor" 
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M12 2L14.09 8.26L20.5 9.27L15.91 13.91L17.18 20.42L12 17.27L6.82 20.42L8.09 13.91L3.5 9.27L9.91 8.26L12 2Z" />
        </svg>
        <svg 
          className="animate-[spin_1.5s_linear_infinite]" 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      </div>
      <span>Processing your request...</span>
    </div>
  )
}
