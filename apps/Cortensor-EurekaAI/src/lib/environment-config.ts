// src/lib/environment-config.ts

export type Environment = 'testnet' | 'devnet6'

export interface EnvironmentConfig {
  name: string
  displayName: string
  cortensorUrl: string
  cortensorApiKey: string
  completionsUrl: string
  defaultSession: string
  deepseekSession: string
  llamaSession: string
  description: string
}

export const environmentConfigs: Record<Environment, EnvironmentConfig> = {
  testnet: {
    name: 'testnet',
    displayName: 'Testnet0',
    cortensorUrl: process.env.CORTENSOR_ROUTER_URL || 'http://205.209.119.106:5010',
    cortensorApiKey: process.env.CORTENSOR_API_KEY || 'f4a2ece1-b7dd-4a70-b71f-d6b9b61c3753',
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || 'http://205.209.119.106:5010/api/v1/completions',
  defaultSession: process.env.NEXT_PUBLIC_LLAVA_SESSION_ID || process.env.NEXT_PUBLIC_LLM_SESSION_ID || '11',
    deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || '21',
    llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || '12',
    description: 'Testnet0 environment for stable testing'
  },
  devnet6: {
    name: 'devnet6',
    displayName: 'Devnet-7',
    cortensorUrl: process.env.CORTENSOR_ROUTER_URL || 'http://173.214.163.250:5010',
    cortensorApiKey: process.env.CORTENSOR_API_KEY || '23695cf5-46af-4ecf-939b-fa7aab0ee1a2',
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || 'http://173.214.163.250:5010/api/v1/completions',
  defaultSession: process.env.NEXT_PUBLIC_LLAVA_SESSION_ID || process.env.NEXT_PUBLIC_LLM_SESSION_ID || '11',
    deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || '21',
    llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || '12',
    description: 'Development environment for new features'
  }
}

// Get active configuration based on current environment
export function getEnvironmentValues(): EnvironmentConfig {
  const env = getCurrentEnvironment()
  return environmentConfigs[env]
}

// Get current environment from localStorage or default to testnet (Testnet0)
export function getCurrentEnvironment(): Environment {
  if (typeof window === 'undefined') return 'testnet'
  
  const stored = localStorage.getItem('chat-environment')
  if (stored && (stored === 'testnet' || stored === 'devnet6')) {
    return stored as Environment
  }
  return 'testnet' // Default to Testnet0
}

// Set current environment in localStorage
export function setCurrentEnvironment(env: Environment): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('chat-environment', env)
}

// Get selected model from localStorage or default to default-model
export function getSelectedModel(): string {
  if (typeof window === 'undefined') return 'llama-3.1-8b-q4'

  const stored = localStorage.getItem('selected-model')
  if (stored) {
    return stored
  }
  return 'llama-3.1-8b-q4' // Default to Meta-Llama 3.1 8B Q4
}

// Set selected model in localStorage
export function setSelectedModel(modelId: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('selected-model', modelId)
}
