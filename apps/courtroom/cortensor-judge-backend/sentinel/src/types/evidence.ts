/**
 * Type definitions for Evidence Bundle and related data structures
 */

export interface LogicTrace {
  step: number;
  description: string;
  reasoning: string;
  confidence: number;
}

export interface EvidenceBundle {
  promptHash: string;           // Hash of original prompt
  minerResult: string;          // The AI output
  logicTrace: LogicTrace[];     // Step-by-step reasoning
  poiHash: string;              // Proof of Inference signature
  ipfsHash: string;             // IPFS hash of full bundle
  modelId: number;              // Model identifier
  modelName: string;            // Model name (e.g., "Llama 3")
  miner: string;                // Miner address
  timestamp: number;            // Unix timestamp
  signature: string;            // Miner's digital signature
}

export interface DisputeData {
  id: string;
  evidence: EvidenceBundle;
  challenger: string;
  challengeBond: number;        // $COR amount
  status: DisputeStatus;
  verdict?: VerdictType;
  judge?: string;
  startTime: number;
  settlementTime?: number;
}

export enum DisputeStatus {
  PENDING = "PENDING",
  CHALLENGED = "CHALLENGED",
  UNDER_REVIEW = "UNDER_REVIEW",
  VERDICT_REACHED = "VERDICT_REACHED",
  SETTLED = "SETTLED",
  DISMISSED = "DISMISSED",
}

export enum VerdictType {
  NONE = "NONE",
  MINER_CORRECT = "MINER_CORRECT",
  MINER_WRONG = "MINER_WRONG",
  INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE",
}

export interface SimilarityResult {
  score: number;                // 0-1 similarity score
  vectorA: number[];            // First output vector
  vectorB: number[];            // Second output vector
  isDifferent: boolean;         // true if score < threshold
}

export interface ValidationResult {
  isValid: boolean;
  score: number;
  reasoning: string;
  recommendations: string[];
}

export interface ChallengePayload {
  evidence: EvidenceBundle;
  comparatorResults: SimilarityResult[];
  validationScore: number;
}

export interface ContractEvent {
  event: string;
  args: Record<string, any>;
  blockNumber: number;
  transactionHash: string;
  logIndex: number;
}
