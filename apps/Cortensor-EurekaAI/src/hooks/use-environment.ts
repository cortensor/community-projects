// src/hooks/use-environment.ts
"use client"

import { useState, useEffect } from 'react'
import { getCurrentEnvironment, setCurrentEnvironment, type Environment } from '@/lib/environment-config'

export function useEnvironment() {
  const [environment, setEnvironment] = useState<Environment>('testnet')

  useEffect(() => {
    setEnvironment(getCurrentEnvironment())
  }, [])

  const handleEnvironmentChange = (newEnv: Environment) => {
    setEnvironment(newEnv)
    setCurrentEnvironment(newEnv)
  }

  return {
    environment,
    setEnvironment: handleEnvironmentChange
  }
}
