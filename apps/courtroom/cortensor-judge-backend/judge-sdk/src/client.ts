/**
 * Judge Client SDK
 * Complete client for interacting with Cortensor Judge
 */

import axios, { AxiosInstance } from 'axios';
import { EvidenceBundle, DisputeStatus, VerdictType } from './types/evidence';

export class JudgeClient {
  private client: AxiosInstance;

  constructor(sentinelUrl: string) {
    this.client = axios.create({
      baseURL: sentinelUrl,
      timeout: 30000,
    });
  }

  /**
   * Submit evidence and create dispute
   */
  async submitEvidence(evidence: EvidenceBundle, bondAmount: string) {
    const response = await this.client.post('/challenge', {
      evidence,
      bondAmount,
    });
    return response.data;
  }

  /**
   * Monitor output for suspicious activity
   */
  async monitorOutput(prompt: string, threshold: number = 0.95) {
    const response = await this.client.post('/monitor', {
      prompt,
      threshold,
    });
    return response.data;
  }

  /**
   * Auto-challenge if output is suspicious
   */
  async autoChallenge(
    evidence: EvidenceBundle,
    minBond: string,
    maxBond: string
  ) {
    const response = await this.client.post('/auto-challenge', {
      evidence,
      minBond,
      maxBond,
    });
    return response.data;
  }

  /**
   * Generate verdict for disputed output
   */
  async generateVerdict(
    disputeId: string,
    evidence: EvidenceBundle,
    minerOutput: string
  ) {
    const response = await this.client.post('/verdict/generate', {
      disputeId,
      evidence,
      minerOutput,
    });
    return response.data;
  }

  /**
   * Submit verdict to blockchain
   */
  async submitVerdict(
    disputeId: string,
    evidence: EvidenceBundle,
    verdict: VerdictType,
    reasoning: string
  ) {
    const response = await this.client.post('/verdict/submit', {
      disputeId,
      evidence,
      verdict,
      reasoning,
    });
    return response.data;
  }

  /**
   * Execute full verdict workflow
   */
  async executeVerdict(disputeId: string, evidence: EvidenceBundle) {
    const response = await this.client.post('/verdict/execute', {
      disputeId,
      evidence,
    });
    return response.data;
  }

  /**
   * Settle dispute
   */
  async settleDispute(disputeId: string) {
    const response = await this.client.post('/dispute/settle', {
      disputeId,
    });
    return response.data;
  }

  /**
   * Get dispute details
   */
  async getDispute(disputeId: string) {
    const response = await this.client.get(`/dispute/${disputeId}`);
    return response.data;
  }

  /**
   * Get miner trust score
   */
  async getMinerTrustScore(minerAddress: string) {
    const response = await this.client.get(`/miner/${minerAddress}/trust-score`);
    return response.data;
  }

  /**
   * Get queue statistics
   */
  async getQueueStats() {
    const response = await this.client.get('/queue/stats');
    return response.data;
  }

  /**
   * Health check
   */
  async health() {
    const response = await this.client.get('/health');
    return response.data;
  }
}
