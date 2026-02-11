export type AgentStatus = 
  | 'idle'
  | 'initializing'
  | 'running'
  | 'completed'
  | 'failed'
  | 'timeout';

export interface Agent {
  id: string;
  taskId: string;
  subtaskId: string;
  name: string;
  status: AgentStatus;
  spawnedAt: number;
  startedAt: number | null;
  completedAt: number | null;
  computeTimeMs: number;
  memoryUsageMb: number;
  inferenceIterations: number;
}

export interface AgentResult {
  id: string;
  agentId: string;
  taskId: string;
  subtaskId: string;
  output: string;
  confidence: number;
  computeTimeMs: number;
  reliabilityScore: number;
  tokenCount: number;
  inferenceMetadata: InferenceMetadata;
  createdAt: number;
}

export interface InferenceMetadata {
  modelVersion: string;
  temperature: number;
  topP: number;
  iterationsRun: number;
  convergenceReached: boolean;
  intermediateOutputs: string[];
}

export interface ScoredResult extends AgentResult {
  finalScore: number;
  rank: number;
  scoreBreakdown: ScoreBreakdown;
}

export interface ScoreBreakdown {
  confidenceComponent: number;
  speedComponent: number;
  reliabilityComponent: number;
  rawConfidence: number;
  rawSpeedScore: number;
  rawReliability: number;
}

export interface RewardTransaction {
  id: string;
  agentId: string;
  taskId: string;
  agentName: string;
  tokensEarned: number;
  score: number;
  rank: number;
  transactionType: 'inference_reward' | 'bonus' | 'penalty';
  timestamp: number;
  x402PaymentId: string;
  metadata: Record<string, unknown>;
}

export interface SwarmSession {
  id: string;
  taskId: string;
  agents: Agent[];
  results: AgentResult[];
  scoredResults: ScoredResult[];
  rewards: RewardTransaction[];
  status: 'active' | 'scoring' | 'merging' | 'completed' | 'failed';
  startedAt: number;
  completedAt: number | null;
  totalTokensDistributed: number;
}

export interface SwarmMetrics {
  totalSessions: number;
  activeSessions: number;
  totalAgentsSpawned: number;
  totalTasksCompleted: number;
  totalTokensDistributed: number;
  averageSwarmSize: number;
  averageCompletionTimeMs: number;
  averageConfidence: number;
  topAgentId: string | null;
  topAgentScore: number;
  uptimeMs: number;
}