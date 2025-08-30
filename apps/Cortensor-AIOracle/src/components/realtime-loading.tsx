'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Brain, Network, Users, CheckCircle, Clock, Zap, Search } from 'lucide-react'

interface RealtimeLoadingProps {
  modelName: string
  sessionId: string
  onComplete?: () => void
  forceComplete?: boolean
  respondedMiners?: number
  totalMiners?: number
}

interface LoadingStep {
  id: string
  title: string
  description: string
  icon: React.ComponentType<any>
  duration: number
  completed: boolean
}

export function RealtimeLoading({ modelName, sessionId, onComplete, forceComplete = false, respondedMiners, totalMiners }: RealtimeLoadingProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [steps, setSteps] = useState<LoadingStep[]>([
    {
      id: 'connect',
      title: 'Connecting to Network',
      description: `Establishing connection to ${modelName}...`,
      icon: Network,
      duration: 1000,
      completed: false
    },
    {
      id: 'route',
      title: 'Routing to AI Miners',
      description: `Finding available miners...`,
      icon: Search,
      duration: 1500,
      completed: false
    },
    {
      id: 'auth',
      title: 'Authenticating Request',
      description: 'Verifying API credentials and permissions...',
      icon: CheckCircle,
      duration: 1000,
      completed: false
    },
    {
      id: 'process',
      title: 'Processing Query',
      description: `Analyzing query with ${modelName}...`,
      icon: Brain,
      duration: 2000,
      completed: false
    },
    {
      id: 'miners',
      title: 'Waiting for Miners',
      description: 'Collecting responses from multiple AI miners...',
      icon: Users,
      duration: 8000,
      completed: false
    },
    {
      id: 'additional',
      title: 'Additional Confirmations',
      description: 'Gathering extra miner confirmations for accuracy...',
      icon: Zap,
      duration: 8000,
      completed: false
    },
    {
      id: 'consensus',
      title: 'Building Consensus',
      description: 'Finalizing consensus from miners...',
      icon: CheckCircle,
      duration: 10000,
      completed: false
    }
  ])

  // Handle force completion effect
  useEffect(() => {
    if (forceComplete) {
      setProgress(100)
      setCurrentStep(steps.length)
      setSteps(prev => prev.map(step => ({ ...step, completed: true })))
    }
  }, [forceComplete, steps.length])

  // Handle progress calculation
  useEffect(() => {
    if (forceComplete) return

    const maxProgress = currentStep >= steps.length ? 99 : 99
    const calculatedProgress = Math.min((currentStep / steps.length) * 100, maxProgress)
    setProgress(calculatedProgress)
  }, [currentStep, steps.length, forceComplete])

  // Handle step progression
  useEffect(() => {
    if (forceComplete || currentStep >= steps.length) {
      return
    }

    const timer = setTimeout(() => {
      setSteps(prev => prev.map((step, index) => 
        index === currentStep ? { ...step, completed: true } : step
      ))
      setCurrentStep(prev => prev + 1)
    }, steps[currentStep].duration)

    return () => clearTimeout(timer)
  }, [currentStep, forceComplete, steps])

  return (
    <Card className="max-w-2xl mx-auto">
      <CardContent className="p-6">
        <div className="text-center mb-6">
          <Brain className="h-12 w-12 text-blue-600 mx-auto mb-4 animate-pulse" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Processing Oracle Query
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Please wait while we gather responses from the AI network...
          </p>
          {(typeof respondedMiners === 'number' && typeof totalMiners === 'number' && totalMiners > 0) && (
            <p className="mt-2 text-sm text-blue-600 dark:text-blue-400 font-medium">
              Miners: {Math.min(respondedMiners, totalMiners)} / {totalMiners}
            </p>
          )}
        </div>

        <div className="space-y-4">
          {steps.map((step, index) => {
            const Icon = step.icon
            const isActive = index === currentStep
            const isCompleted = step.completed
            const isPending = index > currentStep

            return (
              <div 
                key={step.id}
                className={`flex items-center space-x-3 p-3 rounded-lg transition-all duration-300 ${
                  isActive 
                    ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' 
                    : isCompleted 
                    ? 'bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500'
                    : 'bg-gray-50 dark:bg-gray-800/50'
                }`}
              >
                <div className={`p-2 rounded-full ${
                  isCompleted 
                    ? 'bg-green-500 text-white' 
                    : isActive 
                    ? 'bg-blue-500 text-white animate-pulse' 
                    : 'bg-gray-300 dark:bg-gray-600 text-gray-500'
                }`}>
                  <Icon className="h-4 w-4" />
                </div>
                
                <div className="flex-1">
                  <div className={`font-medium ${
                    isCompleted 
                      ? 'text-green-700 dark:text-green-400' 
                      : isActive 
                      ? 'text-blue-700 dark:text-blue-400' 
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {step.title}
                  </div>
                  <div className={`text-sm ${
                    isCompleted || isActive 
                      ? 'text-gray-600 dark:text-gray-300' 
                      : 'text-gray-400 dark:text-gray-500'
                  }`}>
                    {step.description}
                  </div>
                </div>

                {isCompleted && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                {isActive && (
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-6">
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all duration-500 ease-out relative overflow-hidden ${
                forceComplete 
                  ? 'bg-gradient-to-r from-green-500 to-emerald-500' 
                  : 'bg-gradient-to-r from-blue-500 to-purple-500'
              }`}
              style={{ width: `${progress}%` }}
            >
              {progress < 100 && !forceComplete && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse" />
              )}
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
            <span>Step {Math.min(currentStep + 1, steps.length)} of {steps.length}</span>
            <span className={`font-medium ${forceComplete ? 'text-green-600 dark:text-green-400' : ''}`}>
              {Math.round(progress)}% Complete
            </span>
          </div>
          {progress >= 99 && currentStep >= steps.length && (
            <div className="text-center mt-3">
              <div className="inline-flex items-center space-x-2 text-sm text-blue-600 dark:text-blue-400">
                {forceComplete ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-green-600 dark:text-green-400 font-medium">Response ready!</span>
                  </>
                ) : (
                  <>
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span>Finalizing response...</span>
                  </>
                )}
              </div>
              {!forceComplete && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Processing in queue... This may take 1-2 minutes during high traffic. Please wait for completion.
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
