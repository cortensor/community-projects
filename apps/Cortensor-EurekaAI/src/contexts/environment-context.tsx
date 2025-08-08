// src/contexts/environment-context.tsx
"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getCurrentEnvironment, setCurrentEnvironment, type Environment } from '@/lib/environment-config'

interface EnvironmentContextType {
  environment: Environment
  setEnvironment: (env: Environment) => void
  isLoading: boolean
}

const EnvironmentContext = createContext<EnvironmentContextType | undefined>(undefined)

interface EnvironmentProviderProps {
  children: ReactNode
}

export function EnvironmentProvider({ children }: EnvironmentProviderProps) {
  const [environment, setEnvironmentState] = useState<Environment>('devnet6')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setEnvironmentState(getCurrentEnvironment())
    setIsLoading(false)
  }, [])

  const handleEnvironmentChange = (newEnv: Environment) => {
    setCurrentEnvironment(newEnv)
    setEnvironmentState(newEnv) // Update local state as well
    
    // Force reload app config yang mungkin cached
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('environment-changed', { detail: { environment: newEnv } }))
    }, 100)
  }

  return (
    <EnvironmentContext.Provider value={{ 
      environment, 
      setEnvironment: handleEnvironmentChange,
      isLoading 
    }}>
      {children}
    </EnvironmentContext.Provider>
  )
}

export function useEnvironment() {
  const context = useContext(EnvironmentContext)
  if (context === undefined) {
    throw new Error('useEnvironment must be used within an EnvironmentProvider')
  }
  return context
}
