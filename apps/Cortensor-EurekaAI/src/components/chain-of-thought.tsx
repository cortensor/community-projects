"use client"

import { useState, useEffect, useRef } from "react"
import { BrainCircuit, Lightbulb, Search, Target, CheckCircle, ArrowRight, Zap, Eye, BookOpen, Cpu } from "lucide-react"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "./ui/card"

interface ChainOfThoughtProps {
  className?: string
  isActive?: boolean
  onComplete?: () => void
  modelName?: string
}

// Sophisticated thinking phases like ChatGPT o1
const thinkingPhases = [
  {
    id: "understanding",
    title: "Understanding the question",
    icon: Eye,
    thoughts: [
      "Let me carefully read through this question...",
      "I need to identify the key components here.",
      "What is the user specifically asking for?",
      "Are there any implicit requirements?",
      "Let me break this down systematically."
    ],
    color: "from-blue-500 to-cyan-500",
    duration: 2000
  },
  {
    id: "analysis",
    title: "Analyzing the problem",
    icon: Search,
    thoughts: [
      "Now I'll analyze the different aspects...",
      "What approaches could work here?",
      "Let me consider the constraints and requirements.",
      "I should think about edge cases too.",
      "What information do I need to provide?"
    ],
    color: "from-purple-500 to-pink-500",
    duration: 2500
  },
  {
    id: "reasoning",
    title: "Reasoning through solutions",
    icon: BrainCircuit,
    thoughts: [
      "Let me work through this step by step...",
      "If I apply this logic, then...",
      "Actually, let me reconsider this approach.",
      "There might be a better way to handle this.",
      "I need to ensure this reasoning is sound."
    ],
    color: "from-orange-500 to-red-500",
    duration: 3000
  },
  {
    id: "synthesis",
    title: "Synthesizing the response",
    icon: Target,
    thoughts: [
      "Now I'll bring everything together...",
      "Let me structure this clearly for the user.",
      "I should include practical examples.",
      "Is this comprehensive enough?",
      "Let me double-check this makes sense."
    ],
    color: "from-green-500 to-emerald-500",
    duration: 2000
  },
  {
    id: "verification",
    title: "Verifying accuracy",
    icon: CheckCircle,
    thoughts: [
      "Let me review this response one more time...",
      "Is all the information accurate?",
      "Have I addressed the user's question fully?",
      "Are there any important details missing?",
      "Perfect, I'm confident in this response."
    ],
    color: "from-teal-500 to-blue-500",
    duration: 1500
  }
]

export function ChainOfThought({ 
  className, 
  isActive = true,
  onComplete,
  modelName = "DeepSeek-R1"
}: ChainOfThoughtProps) {
  const [currentPhase, setCurrentPhase] = useState(0)
  const [currentThought, setCurrentThought] = useState(0)
  const [displayedText, setDisplayedText] = useState("")
  const [completedPhases, setCompletedPhases] = useState<number[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [showSummary, setShowSummary] = useState(false)
  
  const typewriterRef = useRef<NodeJS.Timeout | null>(null)
  const phaseTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Reset state when component becomes inactive
  useEffect(() => {
    if (!isActive) {
      setCurrentPhase(0)
      setCurrentThought(0)
      setDisplayedText("")
      setCompletedPhases([])
      setIsTyping(false)
      setShowSummary(false)
      
      if (typewriterRef.current) {
        clearInterval(typewriterRef.current)
        typewriterRef.current = null
      }
      if (phaseTimeoutRef.current) {
        clearTimeout(phaseTimeoutRef.current)
        phaseTimeoutRef.current = null
      }
    }
  }, [isActive])

  // Main thinking process
  useEffect(() => {
    if (!isActive) return

    const runThinkingProcess = () => {
      if (currentPhase >= thinkingPhases.length) {
        // All phases completed, show summary
        setShowSummary(true)
        setTimeout(() => {
          onComplete?.()
        }, 1000)
        return
      }

      const phase = thinkingPhases[currentPhase]
      const thought = phase.thoughts[currentThought]

      // Typewriter effect for current thought
      setIsTyping(true)
      setDisplayedText("")
      
      let charIndex = 0
      typewriterRef.current = setInterval(() => {
        if (charIndex < thought.length) {
          setDisplayedText(thought.slice(0, charIndex + 1))
          charIndex++
        } else {
          clearInterval(typewriterRef.current!)
          setIsTyping(false)
          
          // Move to next thought or phase
          setTimeout(() => {
            if (currentThought < phase.thoughts.length - 1) {
              setCurrentThought(prev => prev + 1)
            } else {
              // Complete current phase
              setCompletedPhases(prev => [...prev, currentPhase])
              setCurrentThought(0)
              setDisplayedText("")
              
              setTimeout(() => {
                setCurrentPhase(prev => prev + 1)
              }, 500)
            }
          }, 800)
        }
      }, 30) // Typing speed
    }

    const timer = setTimeout(runThinkingProcess, 300)
    return () => {
      clearTimeout(timer)
      if (typewriterRef.current) {
        clearInterval(typewriterRef.current)
      }
    }
  }, [currentPhase, currentThought, isActive, onComplete])

  if (!isActive) return null

  const currentPhaseData = thinkingPhases[currentPhase]

  return (
    <Card className={cn("bg-slate-800/30 border-slate-700/30 backdrop-blur-sm", className)}>
      <CardContent className="p-4 md:p-6">
        {/* Header */}
        <div className="flex items-center space-x-3 mb-4 md:mb-6">
          <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
            <BrainCircuit className="w-4 h-4 md:w-5 md:h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="text-base md:text-lg font-semibold text-slate-200 flex items-center space-x-2">
              <span>🧠 Deep Thinking Mode</span>
              <div className="flex space-x-1">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-1 h-1 rounded-full bg-amber-400 animate-bounce",
                      `delay-${i * 150}`
                    )}
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            </div>
            <div className="text-xs md:text-sm text-slate-400">
              {modelName} is thinking step by step...
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4 md:mb-6">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Thinking Progress</span>
            <span>{completedPhases.length}/{thinkingPhases.length} phases</span>
          </div>
          <div className="w-full bg-slate-700/50 rounded-full h-1.5">
            <div 
              className="bg-gradient-to-r from-amber-500 to-orange-500 h-1.5 rounded-full transition-all duration-500 ease-out"
              style={{ 
                width: `${(completedPhases.length + (currentPhaseData ? 0.5 : 0)) / thinkingPhases.length * 100}%` 
              }}
            />
          </div>
        </div>

        {/* Thinking Phases */}
        <div className="space-y-3 md:space-y-4">
          {thinkingPhases.map((phase, index) => {
            const isCompleted = completedPhases.includes(index)
            const isCurrent = currentPhase === index
            const IconComponent = phase.icon

            return (
              <div
                key={phase.id}
                className={cn(
                  "flex items-start space-x-2 md:space-x-3 p-2 md:p-3 rounded-lg transition-all duration-300",
                  isCompleted && "bg-green-500/10 border border-green-500/20",
                  isCurrent && "bg-amber-500/10 border border-amber-500/20",
                  !isCompleted && !isCurrent && "bg-slate-800/20 opacity-50"
                )}
              >
                <div className={cn(
                  "flex-shrink-0 w-5 h-5 md:w-6 md:h-6 rounded-full flex items-center justify-center transition-all duration-300",
                  isCompleted && "bg-green-500",
                  isCurrent && `bg-gradient-to-r ${phase.color}`,
                  !isCompleted && !isCurrent && "bg-slate-600"
                )}>
                  {isCompleted ? (
                    <CheckCircle className="w-2.5 h-2.5 md:w-3 md:h-3 text-white" />
                  ) : (
                    <IconComponent className={cn(
                      "w-2.5 h-2.5 md:w-3 md:h-3 text-white",
                      isCurrent && "animate-pulse"
                    )} />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className={cn(
                    "text-xs md:text-sm font-medium mb-1",
                    isCompleted && "text-green-300",
                    isCurrent && "text-amber-200",
                    !isCompleted && !isCurrent && "text-slate-500"
                  )}>
                    {phase.title}
                  </div>
                  
                  {isCurrent && (
                    <div className="text-xs text-slate-300 leading-relaxed">
                      {displayedText}
                      {isTyping && (
                        <span className="inline-block w-1.5 h-3 md:w-2 md:h-4 bg-amber-400 ml-1 animate-pulse" />
                      )}
                    </div>
                  )}
                  
                  {isCompleted && (
                    <div className="text-xs text-green-400/70">
                      ✓ Completed
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Summary */}
        {showSummary && (
          <div className="mt-6 p-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20 rounded-lg">
            <div className="flex items-center space-x-2 text-green-300 text-sm font-medium mb-2">
              <Zap className="w-4 h-4" />
              <span>Thinking Complete</span>
            </div>
            <div className="text-xs text-green-400/70">
              Analysis finished. Ready to provide comprehensive response.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
