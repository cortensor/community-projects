export interface MinerResponse {
  minerId: string
  response: string
  confidence: number
  responseTime: number
  reputation: number
  sources?: string[]
  metadata?: any
}

export interface QueryOptions {
  minerCount?: number
  consensusThreshold?: number
  timeoutMs?: number
  maxTokens?: number
  temperature?: number
  categories?: string[]
}

export interface Miner {
  id: string
  name: string
  endpoint: string
  reputation: number
  specializations: string[]
  isActive: boolean
  averageResponseTime?: number
  totalQueries?: number
  successfulQueries?: number
}

export interface ConsensusResult {
  consensusAnswer: string
  consensusScore: number
  confidenceLevel: number
  algorithmResults: AlgorithmResult[]
  consensusReached: boolean
  participatingMiners: number
  outliers: string[]
  metadata: any
}

export interface AlgorithmResult {
  name: string
  score: number
  answer: string
}

export interface ConsensusAlgorithm {
  name: string
  weight: number
  calculate(responses: MinerResponse[]): Promise<any>
}

export interface Query {
  id: string
  userId?: string
  queryText: string
  queryType: "fact" | "opinion" | "calculation" | "prediction"
  status: "pending" | "processing" | "completed" | "failed"
  minerCount: number
  consensusThreshold: number
  timeoutMs: number
  createdAt: Date
  completedAt?: Date
  metadata?: any
}

export interface TruthRecord {
  id: string
  queryId: string
  consensusAnswer: string
  truthScore: number
  consensusAlgorithm: string
  minerCount: number
  verificationStatus: "verified" | "disputed" | "pending"
  blockchainHash?: string
  consensusDetails: any
  createdAt: Date
}

export interface User {
  id: string
  email?: string
  walletAddress?: string
  username?: string
  subscriptionTier: string
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

export interface SystemMetrics {
  queryVolume: number
  averageConsensusScore: number
  hallucinationDetectionRate: number
  averageResponseTime: number
  minerParticipationRate: number
  consensusAccuracy: number
}
