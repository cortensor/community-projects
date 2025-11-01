'use client'

import { Brain, Network, Zap, Shield, Eye, Cpu } from 'lucide-react'
import { useEffect, useState } from 'react'

interface OracleLoadingProps {
  message?: string
  progress?: number
}

export function OracleLoading({ message = "Connecting to Oracle Network...", progress }: OracleLoadingProps) {
  const [dots, setDots] = useState('')
  const [currentStep, setCurrentStep] = useState(0)

  const steps = [
    { icon: Network, label: "Connecting to Cortensor Network", color: "text-blue-500", bg: "bg-blue-500" },
    { icon: Shield, label: "Authenticating with AI Miners", color: "text-green-500", bg: "bg-green-500" },
  { icon: Cpu, label: "Processing with Eureka", color: "text-purple-500", bg: "bg-purple-500" },
    { icon: Eye, label: "Analyzing responses", color: "text-orange-500", bg: "bg-orange-500" },
    { icon: Brain, label: "Calculating consensus", color: "text-indigo-500", bg: "bg-indigo-500" }
  ]

  useEffect(() => {
    const dotsInterval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.')
    }, 500)

    const stepInterval = setInterval(() => {
      setCurrentStep(prev => (prev + 1) % steps.length)
    }, 2000)

    return () => {
      clearInterval(dotsInterval)
      clearInterval(stepInterval)
    }
  }, [])

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-blue-900/95 via-purple-900/95 to-indigo-900/95 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="text-center space-y-8 max-w-lg mx-auto px-6">
        
        {/* Main Oracle Animation */}
        <div className="relative">
          {/* Outer ring */}
          <div className="w-32 h-32 mx-auto relative">
            <div className="absolute inset-0 rounded-full border-4 border-blue-500/30 animate-spin" style={{ animationDuration: '3s' }}></div>
            <div className="absolute inset-2 rounded-full border-4 border-purple-500/40 animate-spin" style={{ animationDuration: '2s', animationDirection: 'reverse' }}></div>
            <div className="absolute inset-4 rounded-full border-4 border-indigo-500/50 animate-spin" style={{ animationDuration: '1.5s' }}></div>
            
            {/* Center Oracle Eye */}
            <div className="absolute inset-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-600 flex items-center justify-center shadow-2xl shadow-blue-500/30">
              <Brain className="h-8 w-8 text-white animate-pulse" />
            </div>
            
            {/* Floating particles */}
            <div className="absolute -inset-4">
              {[...Array(8)].map((_, i) => (
                <div
                  key={i}
                  className={`absolute w-2 h-2 bg-blue-400 rounded-full animate-ping opacity-60`}
                  style={{
                    top: `${50 + 40 * Math.sin((i * Math.PI) / 4)}%`,
                    left: `${50 + 40 * Math.cos((i * Math.PI) / 4)}%`,
                    animationDelay: `${i * 0.2}s`,
                    animationDuration: '2s'
                  }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-4xl font-bold text-white mb-2 tracking-wide">
            AI Oracle
          </h1>
          <p className="text-xl text-blue-200 mb-1">
            The Truth Machine
          </p>
          <p className="text-sm text-blue-300/80">
            Powered by Cortensor Network
          </p>
        </div>

        {/* Progress Steps */}
        <div className="space-y-4">
          <div className="text-white text-lg font-medium">
            {message}{dots}
          </div>
          
          {/* Step Indicators */}
          <div className="flex justify-center space-x-2 mb-6">
            {steps.map((step, index) => {
              const StepIcon = step.icon
              const isActive = index === currentStep
              const isCompleted = index < currentStep
              
              return (
                <div
                  key={index}
                  className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all duration-500 ${
                    isActive 
                      ? `${step.bg} border-white shadow-lg shadow-${step.color}/50 scale-110` 
                      : isCompleted
                      ? 'bg-green-500 border-green-400'
                      : 'bg-gray-700 border-gray-500'
                  }`}
                >
                  <StepIcon 
                    className={`h-5 w-5 ${
                      isActive || isCompleted ? 'text-white' : 'text-gray-400'
                    } ${isActive ? 'animate-pulse' : ''}`} 
                  />
                </div>
              )
            })}
          </div>

          {/* Current Step Label */}
          <div className="text-center">
            <p className="text-blue-200 text-sm font-medium">
              {steps[currentStep].label}
            </p>
          </div>

          {/* Progress bar if provided */}
          {progress !== undefined && (
            <div className="w-full bg-gray-700/50 rounded-full h-2 backdrop-blur-sm">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300 ease-out shadow-lg shadow-blue-500/30"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}

          {/* Network Status */}
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
              <Network className="h-5 w-5 text-blue-400 mx-auto mb-1 animate-pulse" />
              <div className="text-xs text-blue-200">Network</div>
              <div className="text-xs text-green-400">Connected</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
              <Cpu className="h-5 w-5 text-purple-400 mx-auto mb-1 animate-pulse animation-delay-100" />
              <div className="text-xs text-purple-200">Miners</div>
              <div className="text-xs text-green-400">5 Active</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
              <Brain className="h-5 w-5 text-indigo-400 mx-auto mb-1 animate-pulse animation-delay-200" />
              <div className="text-xs text-indigo-200">AI Model</div>
              <div className="text-xs text-green-400">Eureka</div>
            </div>
          </div>
        </div>

        {/* Loading Animation */}
        <div className="flex justify-center space-x-1">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="w-3 h-3 bg-blue-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.1}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
