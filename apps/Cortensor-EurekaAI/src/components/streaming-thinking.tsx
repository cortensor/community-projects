"use client"

import { useState, useEffect, useRef } from "react"
import { Brain, Zap, CheckCircle, Clock, Lightbulb, Search, Cpu, Target, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface StreamingThinkingProps {
  className?: string
  isActive?: boolean
  onComplete?: () => void
}

// Real-time thinking thoughts with progressive complexity
const thinkingPhases = [
  {
    phase: "analysis",
    title: "🔍 Analyzing Input",
    thoughts: [
      "Let me break down this question...",
      "I need to understand the core concepts here.",
      "What's the user really asking for?",
      "Are there any ambiguities I should clarify?",
      "Let me identify the key components..."
    ],
    color: "from-blue-500 to-cyan-500"
  },
  {
    phase: "exploration",
    title: "🧭 Exploring Knowledge",
    thoughts: [
      "Searching through relevant information...",
      "Cross-referencing multiple sources...",
      "Hmm, there are several approaches to consider.",
      "Let me think about different perspectives...",
      "What are the best practices here?",
      "I should consider edge cases too..."
    ],
    color: "from-purple-500 to-pink-500"
  },
  {
    phase: "reasoning",
    title: "⚡ Deep Reasoning",
    thoughts: [
      "Now let me connect these concepts logically...",
      "If I apply this principle, then...",
      "Wait, let me double-check this reasoning...",
      "Actually, there's a better way to approach this.",
      "The implications of this are...",
      "I need to ensure this is accurate and helpful."
    ],
    color: "from-orange-500 to-red-500"
  },
  {
    phase: "synthesis",
    title: "✨ Synthesis & Validation",
    thoughts: [
      "Bringing everything together now...",
      "Let me structure this response clearly...",
      "Is this explanation comprehensive enough?",
      "I should add some practical examples...",
      "Final check for accuracy and completeness...",
      "Perfect, I'm ready to respond!"
    ],
    color: "from-green-500 to-emerald-500"
  }
]

export function StreamingThinking({ 
  className, 
  isActive = true,
  onComplete 
}: StreamingThinkingProps) {
  const [currentPhase, setCurrentPhase] = useState(0)
  const [currentThought, setCurrentThought] = useState(0)
  const [displayedText, setDisplayedText] = useState("")
  const [completedThoughts, setCompletedThoughts] = useState<string[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const typewriterRef = useRef<NodeJS.Timeout | null>(null)
  const phaseTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Reset state when component unmounts or becomes inactive
  useEffect(() => {
    if (!isActive) {
      setCurrentPhase(0)
      setCurrentThought(0)
      setDisplayedText("")
      setCompletedThoughts([])
      setIsTyping(false)
      
      // Clear any running timers
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

  useEffect(() => {
    if (!isActive) return

    const currentPhaseData = thinkingPhases[currentPhase]
    const currentThoughtText = currentPhaseData.thoughts[currentThought]

    if (currentThoughtText) {
      setIsTyping(true)
      setDisplayedText("")
      
      let charIndex = 0
      typewriterRef.current = setInterval(() => {
        if (charIndex < currentThoughtText.length) {
          setDisplayedText(currentThoughtText.slice(0, charIndex + 1))
          charIndex++
        } else {
          setIsTyping(false)
          if (typewriterRef.current) {
            clearInterval(typewriterRef.current)
          }
          
          // Add completed thought after typing finishes
          setCompletedThoughts(prev => [...prev, currentThoughtText])
          
          // Move to next thought after pause (random delay for realism)
          const pauseDelay = 1000 + Math.random() * 800 // 1-1.8 seconds
          phaseTimeoutRef.current = setTimeout(() => {
            if (currentThought < currentPhaseData.thoughts.length - 1) {
              setCurrentThought(prev => prev + 1)
            } else {
              // Move to next phase
              if (currentPhase < thinkingPhases.length - 1) {
                setCurrentPhase(prev => prev + 1)
                setCurrentThought(0)
                setCompletedThoughts([]) // Reset for new phase
              } else {
                // All thinking complete
                onComplete?.()
              }
            }
          }, pauseDelay)
        }
      }, 30 + Math.random() * 20) // Variable typing speed: 30-50ms
    }

    return () => {
      if (typewriterRef.current) {
        clearInterval(typewriterRef.current)
      }
      if (phaseTimeoutRef.current) {
        clearTimeout(phaseTimeoutRef.current)
      }
    }
  }, [isActive, currentPhase, currentThought, onComplete])

  if (!isActive) return null

  const currentPhaseData = thinkingPhases[currentPhase]
  const overallProgress = ((currentPhase * 6 + currentThought + 1) / (thinkingPhases.length * 6)) * 100

  return (
    <div className={cn(
      "w-full p-6 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50",
      "dark:from-slate-900/50 dark:via-blue-950/30 dark:to-indigo-950/30",
      "rounded-2xl border border-slate-200 dark:border-slate-700/50",
      "shadow-xl backdrop-blur-sm overflow-hidden",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className={cn(
              "w-12 h-12 rounded-full bg-gradient-to-r flex items-center justify-center",
              currentPhaseData.color
            )}>
              <Brain className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div className="absolute inset-0 rounded-full border-2 border-current animate-ping opacity-20" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">
              Deep Thinking Mode
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {currentPhaseData.title}
            </p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            Phase {currentPhase + 1}/{thinkingPhases.length}
          </div>
          <div className="text-xs text-slate-400 dark:text-slate-500">
            {Math.round(overallProgress)}% complete
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
          <div 
            className={cn(
              "h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r",
              currentPhaseData.color
            )}
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Current Thinking Stream */}
      <div className="space-y-4">
        {/* Active thinking bubble */}
        <div className="bg-white/80 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-600/30 shadow-sm relative overflow-hidden">
          {/* Thinking wave animation background */}
          <div className="absolute inset-0 opacity-10">
            <div className={cn(
              "absolute inset-0 bg-gradient-to-r animate-pulse",
              currentPhaseData.color
            )} />
          </div>
          
          <div className="flex items-start gap-3 relative z-10">
            <div className={cn(
              "w-2 h-2 rounded-full mt-2 bg-gradient-to-r animate-pulse",
              currentPhaseData.color
            )} />
            <div className="flex-1">
              <div className="text-slate-700 dark:text-slate-300 leading-relaxed">
                {displayedText}
                {isTyping && (
                  <span className="inline-flex items-center ml-1">
                    <span className={cn(
                      "inline-block w-0.5 h-5 animate-pulse bg-gradient-to-r",
                      currentPhaseData.color
                    )}>|</span>
                    {/* Typing dots */}
                    <span className="ml-2 flex gap-1">
                      <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" />
                      <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </span>
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Recent completed thoughts (show last 2) */}
        {completedThoughts.slice(-2).map((thought, index) => (
          <div key={index} className="bg-slate-100/50 dark:bg-slate-800/30 rounded-lg p-3 border border-slate-200/50 dark:border-slate-600/20">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-slate-600 dark:text-slate-400 opacity-75">
                {thought}
              </div>
            </div>
          </div>
        ))}

        {/* Phase indicators */}
        <div className="flex items-center justify-center gap-2 pt-4">
          {thinkingPhases.map((phase, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className={cn(
                "w-2 h-2 rounded-full transition-all duration-300",
                index < currentPhase ? "bg-green-500" :
                index === currentPhase ? cn("bg-gradient-to-r animate-pulse", phase.color) :
                "bg-slate-300 dark:bg-slate-600"
              )} />
              {index < thinkingPhases.length - 1 && (
                <ArrowRight className="w-3 h-3 text-slate-400" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700/50">
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            Enhanced reasoning engine active
          </span>
          <span className="font-mono">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  )
}
