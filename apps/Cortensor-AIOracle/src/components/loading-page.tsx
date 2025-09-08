'use client'

import { Brain, Network, Zap } from 'lucide-react'

interface LoadingPageProps {
  message?: string
  progress?: number
}

export function LoadingPage({ message = "Connecting to Oracle Network...", progress }: LoadingPageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
      <div className="text-center space-y-8 max-w-md mx-auto px-6">
        {/* Animated Logo */}
        <div className="relative">
          <div className="w-24 h-24 mx-auto mb-6 relative">
            <div className="absolute inset-0 rounded-full bg-blue-600 opacity-20 animate-ping"></div>
            <div className="absolute inset-2 rounded-full bg-blue-500 opacity-40 animate-ping animation-delay-75"></div>
            <div className="absolute inset-4 rounded-full bg-blue-600 flex items-center justify-center">
              <Brain className="h-8 w-8 text-white animate-pulse" />
            </div>
          </div>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            AI Oracle
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            The Truth Machine
          </p>
        </div>

        {/* Loading Animation */}
        <div className="space-y-4">
          <div className="flex justify-center space-x-4">
            <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
              <Network className="h-4 w-4 text-blue-500 animate-pulse" />
              <span className="text-sm text-gray-600 dark:text-gray-400">Network</span>
            </div>
            <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
              <Zap className="h-4 w-4 text-green-500 animate-pulse animation-delay-150" />
              <span className="text-sm text-gray-600 dark:text-gray-400">Miners</span>
            </div>
            <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
              <Brain className="h-4 w-4 text-purple-500 animate-pulse animation-delay-300" />
              <span className="text-sm text-gray-600 dark:text-gray-400">AI Models</span>
            </div>
          </div>

          {/* Progress bar if provided */}
          {progress !== undefined && (
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}

          {/* Loading dots */}
          <div className="flex justify-center space-x-1">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce animation-delay-100"></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce animation-delay-200"></div>
          </div>

          {/* Status message */}
          <p className="text-sm text-gray-500 dark:text-gray-400 animate-pulse">
            {message}
          </p>
        </div>

        {/* Footer */}
        <div className="pt-8 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Powered by Cortensor Network
          </p>
        </div>
      </div>
    </div>
  )
}
