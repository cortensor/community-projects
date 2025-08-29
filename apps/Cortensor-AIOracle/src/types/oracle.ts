export interface OracleQuery {
  id: string
  query: string
  timestamp: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  consensus: OracleConsensus
  responses: MinerResponse[]
  finalAnswer: string | null
  confidence: number
  sources: string[]
}

export interface QueryResult {
  id: string
  query: string
  answer: string
  confidence: number
  minerCount: number
  sources: Array<{
    title: string
    url: string
    reliability: string
    snippet?: string
  }>
  timestamp: number
  verified: boolean
  modelName: string
  minerAddresses?: string[]
  debug?: any
}

export interface OracleConsensus {
  totalMiners: number
  respondedMiners: number
  agreements: number
  disagreements: number
  confidenceScore: number
  verifiedAt?: number
}

export interface MinerResponse {
  minerId: string
  response: string
  confidence: number
  timestamp: number
  verified: boolean
  stake?: number
}

export interface SessionInfo {
  id: number
  name: string
  status: 'active' | 'inactive'
  minerCount: number
  lastActivity: number
}

export interface CortensorApiResponse {
  success: boolean
  data?: any
  error?: string
  timestamp: number
}

export interface OracleConfig {
  minConsensus: number
  confidenceThreshold: number
  timeout: number
  sessionId: number
}
