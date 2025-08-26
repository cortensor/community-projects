"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"

interface SpinningTextLoaderProps {
  className?: string
  speed?: number // milliseconds between text changes
}

const loadingTexts = [
  "Processing your request...",
  "Analyzing your input...",
  "Gathering information...", 
  "Thinking deeply...",
  "Almost ready...",
  "Just a sec...",
  "Working on it...",
  "Getting smart response...",
  "Connecting neurons...",
  "Crafting the perfect answer..."
]

export function SpinningTextLoader({ className, speed = 800 }: SpinningTextLoaderProps) {
  const [currentTextIndex, setCurrentTextIndex] = useState(0)
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setIsVisible(false)
      
      setTimeout(() => {
        setCurrentTextIndex((prev) => (prev + 1) % loadingTexts.length)
        setIsVisible(true)
      }, 150) // Quick fade out/in
      
    }, speed)

    return () => clearInterval(interval)
  }, [speed])

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Spinning circle loader */}
      <div className="relative">
        <div className="w-5 h-5 text-blue-500 animate-spin">
          <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
            <circle 
              cx="12" 
              cy="12" 
              r="10" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeDasharray="31.416 31.416"
              strokeDashoffset="31.416"
              className="animate-spin"
              style={{
                animation: 'spin 1s linear infinite, dash 2s ease-in-out infinite'
              }}
            />
          </svg>
        </div>
      </div>
      
      {/* Rotating text with fade transition */}
      <div className="relative overflow-hidden">
        <span 
          className={cn(
            "text-sm font-medium text-muted-foreground transition-opacity duration-150",
            isVisible ? "opacity-100" : "opacity-0"
          )}
        >
          {loadingTexts[currentTextIndex]}
        </span>
      </div>
      
      {/* Animated dots */}
      <div className="flex gap-1">
        <div className="w-1 h-1 bg-blue-500/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite]" />
        <div className="w-1 h-1 bg-blue-500/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.2s]" />
        <div className="w-1 h-1 bg-blue-500/60 rounded-full animate-[wave-dots_1.4s_ease-in-out_infinite_0.4s]" />
      </div>
    </div>
  )
}

// Alternative version with typewriter effect
export function TypewriterLoader({ className, speed = 100 }: SpinningTextLoaderProps) {
  const [currentText, setCurrentText] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)
  const [charIndex, setCharIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const currentFullText = loadingTexts[currentIndex]
    
    const timeout = setTimeout(() => {
      if (!isDeleting) {
        // Typing
        if (charIndex < currentFullText.length) {
          setCurrentText(currentFullText.substring(0, charIndex + 1))
          setCharIndex(charIndex + 1)
        } else {
          // Wait before deleting
          setTimeout(() => setIsDeleting(true), 1500)
        }
      } else {
        // Deleting
        if (charIndex > 0) {
          setCurrentText(currentFullText.substring(0, charIndex - 1))
          setCharIndex(charIndex - 1)
        } else {
          setIsDeleting(false)
          setCurrentIndex((currentIndex + 1) % loadingTexts.length)
        }
      }
    }, isDeleting ? speed / 2 : speed)

    return () => clearTimeout(timeout)
  }, [currentText, currentIndex, charIndex, isDeleting, speed])

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Pulsing loader */}
      <div className="w-5 h-5 text-blue-500">
        <div className="w-full h-full bg-blue-500 rounded-full animate-pulse" />
      </div>
      
      {/* Typewriter text */}
      <div className="flex items-center">
        <span className="text-sm font-medium text-muted-foreground">
          {currentText}
        </span>
        <span className="inline-block w-0.5 h-4 bg-blue-500 ml-1 animate-pulse" />
      </div>
    </div>
  )
}
