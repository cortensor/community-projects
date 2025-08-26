"use client"

import { Bot } from "lucide-react"
import { cn } from "@/lib/utils"
import { useState, useEffect } from "react"

const loadingMessages = [
  "Initializing AI systems...",
  "Loading neural networks...", 
  "Preparing intelligent responses...",
  "Connecting to knowledge base...",
  "Optimizing user experience...",
  "Starting conversation engine..."
]

export function PageLoadingSkeleton() {
  return (
    <div className="h-screen bg-background flex animate-[fade-in-up_0.6s_ease-out]">
      {/* Sidebar skeleton */}
      <div className="w-72 bg-muted/30 border-r p-4 space-y-4">
        {/* Header skeleton */}
        <div className="space-y-2">
          <div className="h-6 bg-gradient-to-r from-muted/50 via-muted/30 to-muted/50 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
               style={{ backgroundSize: '200px 100%' }} />
          <div className="h-4 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-2/3" 
               style={{ backgroundSize: '200px 100%', animationDelay: '0.1s' }} />
        </div>
        
        {/* New chat button skeleton */}
        <div className="h-10 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded-lg animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
             style={{ backgroundSize: '200px 100%', animationDelay: '0.2s' }} />
        
        {/* Chat history skeleton */}
        <div className="space-y-2">
          <div className="h-4 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-1/2" 
               style={{ backgroundSize: '200px 100%', animationDelay: '0.3s' }} />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-8 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                 style={{
                   backgroundSize: '200px 100%',
                   animationDelay: `${0.4 + i * 0.1}s`
                 }} />
          ))}
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col">
        {/* Header skeleton */}
        <div className="h-16 border-b p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gradient-to-r from-muted/50 via-muted/30 to-muted/50 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                 style={{ backgroundSize: '200px 100%' }} />
            <div className="h-6 bg-gradient-to-r from-muted/50 via-muted/30 to-muted/50 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-20" 
                 style={{ backgroundSize: '200px 100%', animationDelay: '0.1s' }} />
          </div>
          <div className="flex items-center gap-4">
            <div className="h-8 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-24" 
                 style={{ backgroundSize: '200px 100%', animationDelay: '0.2s' }} />
            <div className="w-8 h-8 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                 style={{ backgroundSize: '200px 100%', animationDelay: '0.3s' }} />
          </div>
        </div>

        {/* Chat area skeleton */}
        <div className="flex-1 p-4 space-y-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Welcome card skeleton */}
            <div className="p-8 bg-muted/20 rounded-lg border text-center space-y-4 animate-[scale-in_0.8s_ease-out_0.3s_both]">
              <div className="w-12 h-12 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded-full mx-auto animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                   style={{ backgroundSize: '200px 100%' }} />
              <div className="h-6 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-48 mx-auto" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.1s' }} />
              <div className="h-4 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-32 mx-auto" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.2s' }} />
              <div className="h-4 bg-gradient-to-r from-muted/20 via-muted/10 to-muted/20 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-64 mx-auto" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.3s' }} />
            </div>
          </div>
        </div>

        {/* Input area skeleton */}
        <div className="border-t p-4">
          <div className="max-w-4xl mx-auto space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-4 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-12" 
                   style={{ backgroundSize: '200px 100%' }} />
              <div className="h-8 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite] w-32" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.1s' }} />
            </div>
            <div className="relative">
              <div className="h-12 bg-gradient-to-r from-muted/30 via-muted/20 to-muted/30 rounded-lg animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.2s' }} />
              <div className="absolute right-2 top-2 w-8 h-8 bg-gradient-to-r from-muted/40 via-muted/30 to-muted/40 rounded animate-[skeleton-loading_1.5s_ease-in-out_infinite]" 
                   style={{ backgroundSize: '200px 100%', animationDelay: '0.3s' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function AppLoadingScreen() {
  const [currentMessage, setCurrentMessage] = useState(0)
  
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessage(prev => (prev + 1) % loadingMessages.length)
    }, 1000)
    
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="h-screen bg-background flex items-center justify-center overflow-hidden relative">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/5" />
      
      <div className="text-center space-y-8 relative z-10">
        {/* Enhanced Logo with multiple animation layers */}
        <div className="relative">
          {/* Main logo container */}
          <div className="w-20 h-20 mx-auto relative">
            <Bot className="w-full h-full text-primary animate-[logo-pulse_2s_ease-in-out_infinite]" />
          </div>
          
          {/* Multiple ripple effects */}
          <div className="absolute inset-0 w-20 h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-2 border-primary/40 animate-[ripple_2s_ease-out_infinite]" />
            <div className="absolute inset-1 rounded-full border border-primary/30 animate-[ripple_2s_ease-out_infinite]" style={{ animationDelay: '0.3s' }} />
            <div className="absolute inset-3 rounded-full border border-primary/20 animate-[ripple_2s_ease-out_infinite]" style={{ animationDelay: '0.6s' }} />
          </div>
          
          {/* Rotating ring */}
          <div className="absolute inset-0 w-20 h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary/60 animate-spin" />
          </div>
        </div>

        {/* Enhanced App name with better gradient */}
        <div className="space-y-3">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent animate-[text-shimmer_3s_ease-in-out_infinite]">
            Eureka
          </h1>
          <p className="text-lg text-muted-foreground animate-[fade-in-out_2s_ease-in-out_infinite]">
            AI Assistant
          </p>
        </div>

        {/* Enhanced loading dots with wave animation */}
        <div className="flex items-center justify-center space-x-3">
          <div className="w-3 h-3 bg-gradient-to-r from-primary to-primary/60 rounded-full animate-[wave_1.5s_ease-in-out_infinite]" />
          <div className="w-3 h-3 bg-gradient-to-r from-primary to-primary/60 rounded-full animate-[wave_1.5s_ease-in-out_infinite]" style={{ animationDelay: '0.2s' }} />
          <div className="w-3 h-3 bg-gradient-to-r from-primary to-primary/60 rounded-full animate-[wave_1.5s_ease-in-out_infinite]" style={{ animationDelay: '0.4s' }} />
        </div>

        {/* Dynamic loading text with rotation */}
        <div className="space-y-2 h-12 flex flex-col justify-center">
          <p className="text-sm text-muted-foreground transition-all duration-500 animate-[typing_3s_steps(20)_infinite]">
            {loadingMessages[currentMessage]}
          </p>
          <p className="text-xs text-muted-foreground/70 animate-pulse">
            Preparing your intelligent workspace
          </p>
        </div>

        {/* Enhanced progress bar with gradient animation */}
        <div className="w-80 h-2 bg-muted/20 rounded-full overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/20 via-primary to-primary/20 rounded-full animate-[progress-slide_2s_ease-in-out_infinite]" 
               style={{ width: '40%' }} />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent rounded-full animate-[shine_2s_ease-in-out_infinite]" />
        </div>
      </div>
    </div>
  )
}
