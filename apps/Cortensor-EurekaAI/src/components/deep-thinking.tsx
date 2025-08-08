"use client"

import { useState, useEffect, useRef } from "react"
import { Brain, Zap, CheckCircle, Clock, Lightbulb, Search, Cpu, Target } from "lucide-react"
import { cn } from "@/lib/utils"

interface DeepThinkingIndicatorProps {
  className?: string
  isActive?: boolean
  onThinkingComplete?: (result: string) => void
}

// Realistic thinking steps with streaming content
const thinkingSteps = [
  {
    id: 1,
    label: "Initial Analysis",
    icon: Search,
    content: [
      "Parsing user input...",
      "Identifying key concepts...",
      "Understanding context and intent...",
      "Mapping to knowledge domains..."
    ],
    duration: 3000
  },
  {
    id: 2,
    label: "Deep Reasoning",
    icon: Brain,
    content: [
      "Accessing relevant knowledge...",
      "Cross-referencing information...",
      "Exploring multiple perspectives...",
      "Analyzing logical connections...",
      "Considering edge cases..."
    ],
    duration: 4000
  },
  {
    id: 3,
    label: "Solution Generation",
    icon: Lightbulb,
    content: [
      "Generating potential approaches...",
      "Evaluating solution quality...",
      "Optimizing for accuracy...",
      "Structuring comprehensive response..."
    ],
    duration: 2500
  },
  {
    id: 4,
    label: "Validation",
    icon: CheckCircle,
    content: [
      "Fact-checking conclusions...",
      "Verifying logical consistency...",
      "Ensuring completeness...",
      "Finalizing response..."
    ],
    duration: 2000
  }
]

export function DeepThinkingIndicator({ className, isActive = true, onThinkingComplete }: DeepThinkingIndicatorProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [currentContentIndex, setCurrentContentIndex] = useState(0)
  const [displayedText, setDisplayedText] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const typewriterRef = useRef<NodeJS.Timeout | null>(null)

  // Typewriter effect for streaming text
  useEffect(() => {
    if (!isActive) return

    const currentStepData = thinkingSteps[currentStep]
    const currentContent = currentStepData.content[currentContentIndex]

    if (currentContent) {
      setIsTyping(true)
      setDisplayedText("")
      
      let charIndex = 0
      typewriterRef.current = setInterval(() => {
        if (charIndex < currentContent.length) {
          setDisplayedText(currentContent.slice(0, charIndex + 1))
          charIndex++
        } else {
          setIsTyping(false)
          if (typewriterRef.current) {
            clearInterval(typewriterRef.current)
          }
          
          // Move to next content after a short pause
          setTimeout(() => {
            if (currentContentIndex < currentStepData.content.length - 1) {
              setCurrentContentIndex(prev => prev + 1)
            } else {
              // Move to next step
              if (currentStep < thinkingSteps.length - 1) {
                setCurrentStep(prev => prev + 1)
                setCurrentContentIndex(0)
              } else {
                // Thinking complete
                onThinkingComplete?.("Deep thinking process completed")
              }
            }
          }, 800)
        }
      }, 30) // Typing speed
    }

    return () => {
      if (typewriterRef.current) {
        clearInterval(typewriterRef.current)
      }
    }
  }, [isActive, currentStep, currentContentIndex, onThinkingComplete])

  if (!isActive) return null

  const currentStepData = thinkingSteps[currentStep]
  const Icon = currentStepData.icon
  const progress = ((currentStep * thinkingSteps[0].content.length + currentContentIndex + 1) / 
                   (thinkingSteps.length * thinkingSteps[0].content.length)) * 100

  return (
    <div className={cn(
      "p-6 bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50", 
      "dark:from-purple-950/30 dark:via-blue-950/30 dark:to-indigo-950/30",
      "rounded-xl border border-purple-200 dark:border-purple-700/50",
      "shadow-lg backdrop-blur-sm",
      className
    )}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative">
          <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
            <Icon className="w-5 h-5 text-white" />
          </div>
          {/* Pulsing ring */}
          <div className="absolute inset-0 rounded-full border-2 border-purple-400 animate-ping opacity-30" />
        </div>
        
        <div className="flex-1">
          <h3 className="font-semibold text-purple-800 dark:text-purple-200 text-lg">
            🧠 Deep Thinking Mode
          </h3>
          <p className="text-sm text-purple-600 dark:text-purple-300">
            {currentStepData.label}
          </p>
        </div>

        <div className="text-right">
          <div className="text-xs text-purple-500 dark:text-purple-400 font-mono">
            Step {currentStep + 1}/{thinkingSteps.length}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-purple-600 dark:text-purple-300 mb-1">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-purple-200 dark:bg-purple-800 rounded-full h-2 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Streaming Content */}
      <div className="space-y-3">
        {/* Current thinking stream */}
        <div className="bg-white/60 dark:bg-black/20 rounded-lg p-4 border border-purple-100 dark:border-purple-700/30">
          <div className="flex items-start gap-3">
            <Cpu className="w-4 h-4 text-purple-500 mt-0.5 animate-pulse" />
            <div className="flex-1">
              <div className="font-mono text-sm text-purple-800 dark:text-purple-200">
                {displayedText}
                {isTyping && <span className="animate-pulse">▋</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Previous completed steps */}
        {thinkingSteps.slice(0, currentStep).map((step, index) => (
          <div key={step.id} className="flex items-center gap-3 text-sm text-purple-600 dark:text-purple-400 opacity-60">
            <CheckCircle className="w-4 h-4" />
            <span>✓ {step.label} completed</span>
          </div>
        ))}

        {/* Upcoming steps */}
        {thinkingSteps.slice(currentStep + 1).map((step, index) => (
          <div key={step.id} className="flex items-center gap-3 text-sm text-purple-400 dark:text-purple-500 opacity-40">
            <Clock className="w-4 h-4" />
            <span>⏳ {step.label} pending</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-purple-200 dark:border-purple-700/30">
        <div className="flex items-center justify-between text-xs text-purple-500 dark:text-purple-400">
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            Enhanced reasoning active
          </span>
          <span className="font-mono">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  )
}
