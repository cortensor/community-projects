'use client'

import React, { useState, useEffect } from 'react'
import { Brain, Network, Shield, Zap } from 'lucide-react'

interface AppLoadingProps {
  onLoadComplete?: () => void
}

export function AppLoading({ onLoadComplete }: AppLoadingProps) {
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  
  const loadingSteps = [
    { text: "Initializing AI Oracle...", description: "Starting decentralized verification system" },
    { text: "Connecting to Cortensor Network...", description: "Establishing secure connection to distributed AI miners" },
    { text: "Preparing intelligent workspace...", description: "Setting up consensus algorithms powered by Cortensor" },
    { text: "Ready for queries...", description: "AI Oracle is now ready to verify information via Cortensor" }
  ]

  // Pre-defined particle positions to avoid hydration issues
  const particles = [
    { left: 20.5, top: 15.2, delay: 0.5, duration: 2.8 },
    { left: 75.3, top: 45.7, delay: 1.2, duration: 3.1 },
    { left: 35.8, top: 80.3, delay: 2.1, duration: 2.4 },
    { left: 88.1, top: 25.6, delay: 0.8, duration: 3.5 },
    { left: 12.7, top: 65.9, delay: 1.8, duration: 2.7 },
    { left: 65.4, top: 35.1, delay: 0.3, duration: 3.2 },
    { left: 42.2, top: 70.8, delay: 2.5, duration: 2.9 },
    { left: 78.6, top: 55.4, delay: 1.5, duration: 2.6 },
    { left: 25.9, top: 40.7, delay: 0.9, duration: 3.0 },
    { left: 58.3, top: 18.2, delay: 1.7, duration: 2.5 },
    { left: 8.4, top: 85.6, delay: 2.2, duration: 3.3 },
    { left: 92.1, top: 62.3, delay: 0.6, duration: 2.8 },
    { left: 48.7, top: 28.9, delay: 1.4, duration: 2.7 },
    { left: 15.2, top: 75.1, delay: 2.0, duration: 3.1 },
    { left: 85.5, top: 38.4, delay: 1.1, duration: 2.9 }
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setLoadingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setTimeout(() => {
            onLoadComplete?.()
          }, 500)
          return 100
        }
        return prev + 2
      })
    }, 100)

    return () => clearInterval(interval)
  }, [onLoadComplete])

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= loadingSteps.length - 1) {
          clearInterval(stepInterval)
          return prev
        }
        return prev + 1
      })
    }, 2000)

    return () => clearInterval(stepInterval)
  }, [])

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center z-50">
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {particles.map((particle, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 md:w-2 md:h-2 bg-blue-400 rounded-full opacity-20 animate-pulse"
            style={{
              left: `${particle.left}%`,
              top: `${particle.top}%`,
              animationDelay: `${particle.delay}s`,
              animationDuration: `${particle.duration}s`
            }}
          />
        ))}
      </div>

      <div className="text-center z-10 max-w-sm md:max-w-md mx-auto px-6">
        {/* Logo/Icon */}
        <div className="relative mb-6 md:mb-8">
          <div className="w-20 h-20 md:w-24 md:h-24 mx-auto relative">
            {/* Outer rotating ring */}
            <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full animate-spin" 
                 style={{ animationDuration: '3s' }} />
            
            {/* Middle rotating ring */}
            <div className="absolute inset-2 border-3 border-purple-500/40 rounded-full animate-spin" 
                 style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
            
            {/* Inner icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                <Brain className="w-5 h-5 md:w-6 md:h-6 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
          AI Oracle
        </h1>
        <p className="text-blue-200 text-base md:text-lg mb-6 md:mb-8">
          Truth Machine
        </p>

        {/* Loading dots */}
        <div className="flex justify-center space-x-2 mb-4 md:mb-6">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="w-2.5 h-2.5 md:w-3 md:h-3 bg-blue-400 rounded-full animate-bounce"
              style={{
                animationDelay: `${i * 0.2}s`,
                animationDuration: '1s'
              }}
            />
          ))}
        </div>

        {/* Current step */}
        <div className="mb-4 md:mb-6">
          <p className="text-white text-base md:text-lg font-medium mb-2">
            {loadingSteps[currentStep]?.text}
          </p>
          <p className="text-blue-200 text-xs md:text-sm px-2">
            {loadingSteps[currentStep]?.description}
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-1.5 md:h-2 mb-4 md:mb-6">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-600 h-1.5 md:h-2 rounded-full transition-all duration-300 ease-out shadow-sm"
            style={{ width: `${loadingProgress}%` }}
          />
        </div>

        {/* Loading percentage */}
        <p className="text-blue-200 text-sm md:text-base font-medium mb-6 md:mb-8">
          {loadingProgress}%
        </p>

        {/* Feature icons */}
        <div className="flex justify-center space-x-4 md:space-x-6 opacity-60">
          <div className="flex flex-col items-center">
            <Network className="w-5 h-5 md:w-6 md:h-6 text-blue-400 mb-1" />
            <span className="text-xs text-blue-200">Decentralized</span>
          </div>
          <div className="flex flex-col items-center">
            <Shield className="w-5 h-5 md:w-6 md:h-6 text-purple-400 mb-1" />
            <span className="text-xs text-purple-200">Verified</span>
          </div>
          <div className="flex flex-col items-center">
            <Zap className="w-5 h-5 md:w-6 md:h-6 text-yellow-400 mb-1" />
            <span className="text-xs text-yellow-200">Consensus</span>
          </div>
        </div>

        {/* Cortensor Network Credit */}
        <div className="mt-8 pt-6 border-t border-blue-800/30">
          <div className="flex items-center justify-center space-x-2">
            <Network className="w-4 h-4 text-blue-400/70" />
            <span className="text-xs text-blue-300/70 font-medium">
              Cortensor Network
            </span>
          </div>
          <p className="text-xs text-blue-400/50 mt-1">
            Decentralized AI Infrastructure
          </p>
        </div>
      </div>
    </div>
  )
}
