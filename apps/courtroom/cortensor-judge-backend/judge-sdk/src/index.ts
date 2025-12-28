/**
 * Judge SDK - Main Entry Point
 * Provides a simple interface for developers to integrate with Cortensor Judge
 */

export { submitEvidence } from './submitEvidence';
export { createChallenge } from './challenge';
export { JudgeClient } from './client';
export type { EvidenceBundle, DisputeStatus, VerdictType, LogicTrace, DisputeData, ValidationResult, QueueStats, HealthCheck } from './types/evidence';
