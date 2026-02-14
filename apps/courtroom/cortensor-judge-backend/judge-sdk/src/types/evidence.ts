/**
 * Evidence Types for Judge SDK
 */

export interface LogicTrace {
  step: number;
  input: any;
  output: any;
  reasoning: string;
  timestamp: number;
}

export interface EvidenceBundle {
  ipfsHash: string;
  evidenceId: string;
  minerOutput: string;
  expectedOutput: string;
  logicTraces: LogicTrace[];
  timestamp: number;
  submittedBy: string;
  dataHash: string;
}

export interface DisputeData {
  id: number;
  evidence: EvidenceBundle;
  challenger: string;
  miner: string;
  bond: bigint;
  status: DisputeStatus;
  verdict?: VerdictType;
  verdictReasoning?: string;
  judge?: string;
  startTime: number;
  settlementTime?: number;
  slashAmount: bigint;
  rewardAmount: bigint;
}

export enum DisputeStatus {
  PENDING = 0,
  UNDER_REVIEW = 1,
  DISPUTE_INITIATED = 2,
  AWAITING_VERDICT = 3,
  VERDICT_SUBMITTED = 4,
  SETTLED = 5,
  APPEALED = 6,
}

export enum VerdictType {
  INVALID_OUTPUT = 0,
  VALID_OUTPUT = 1,
  INCONCLUSIVE = 2,
  TECHNICAL_ERROR = 3,
}

export interface SimilarityResult {
  similarity: number;
  isOutlier: boolean;
  expectedRange: { min: number; max: number };
  deviation: number;
}

export interface ValidationResult {
  isValid: boolean;
  confidence: number;
  reasons: string[];
  timestamp: number;
}

export interface QueueStats {
  active: number;
  delayed: number;
  failed: number;
  completed: number;
}

export interface HealthCheck {
  status: string;
  timestamp: number;
  services: {
    redis: boolean;
    blockchain: boolean;
    ipfs: boolean;
    cortensor: boolean;
  };
  uptime: number;
}
