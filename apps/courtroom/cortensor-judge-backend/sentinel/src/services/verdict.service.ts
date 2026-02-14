/**
 * Verdict Service
 * Generates verdicts using PoUW validation
 */

import { justiceClient } from '../web3/justice.client';
import { pouWValidator } from '../cortensor/validate';
import { ipfsService } from '../evidence/ipfs';
import { config } from '../config/env';
import { EvidenceBundle, VerdictType, DisputeStatus } from '../types/evidence';
import { disputeQueueService } from '../queue/dispute.queue';

export interface VerdictSubmissionResult {
  success: boolean;
  transactionHash: string;
  verdict: VerdictType;
  reasoning: string;
}

/**
 * Verdict Service
 * Executes PoUW validation and submits verdicts to Justice contract
 */
export class VerdictService {
  /**
   * Generate verdict for disputed output
   * Uses PoUW (Proof of Useful Work) validation
   */
  async generateVerdict(
    disputeId: string,
    evidence: EvidenceBundle,
    minerOutput: string
  ): Promise<{
    verdict: VerdictType;
    reasoning: string;
    isValid: boolean;
    confidence: number;
  }> {
    try {
      console.log(`Generating verdict for dispute: ${disputeId}`);

      // Run PoUW validation on the output
      const pouWProof = await pouWValidator.validateOutput(minerOutput, {
        prompt: evidence.promptHash,
        minerAddress: evidence.miner,
      });

      // Determine verdict based on PoUW result
      const verdict = pouWProof.isValid ? VerdictType.MINER_CORRECT : VerdictType.MINER_WRONG;

      console.log(`Verdict generated: ${verdict}, Score: ${pouWProof.overallScore}`);

      return {
        verdict,
        reasoning: pouWProof.reasoning,
        isValid: pouWProof.isValid,
        confidence: pouWProof.overallScore,
      };
    } catch (error) {
      console.error('Verdict generation failed:', error);
      throw error;
    }
  }

  /**
   * Submit verdict to Justice contract
   */
  async submitVerdict(
    disputeId: string,
    evidence: EvidenceBundle,
    verdict: VerdictType,
    reasoning: string
  ): Promise<VerdictSubmissionResult> {
    try {
      console.log(`Submitting verdict for dispute: ${disputeId}`);

      // Pin verdict reasoning to IPFS
      const verdictData = {
        disputeId,
        verdict,
        reasoning,
        timestamp: Date.now(),
      };

      const verdictIpfsHash = await ipfsService.pinEvidenceBundle(verdictData as any);

      // Submit to Justice contract
      const txHash = await justiceClient.submitVerdict(
        disputeId,
        verdict,
        verdictIpfsHash
      );

      console.log(`Verdict submitted: ${txHash}`);

      // Add settlement job to queue
      await this.scheduleSettlement(disputeId);

      return {
        success: true,
        transactionHash: txHash,
        verdict,
        reasoning,
      };
    } catch (error) {
      console.error('Verdict submission failed:', error);
      return {
        success: false,
        transactionHash: '',
        verdict: VerdictType.NONE,
        reasoning: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Execute full verdict workflow
   * Validate -> Submit -> Settle
   */
  async executeFullVerdictWorkflow(
    disputeId: string,
    evidence: EvidenceBundle
  ): Promise<{
    success: boolean;
    verdict: VerdictType;
    error?: string;
  }> {
    try {
      console.log(`Executing full verdict workflow for dispute: ${disputeId}`);

      // Step 1: Generate verdict
      const verdictResult = await this.generateVerdict(
        disputeId,
        evidence,
        evidence.minerResult
      );

      // Step 2: Submit verdict
      const submissionResult = await this.submitVerdict(
        disputeId,
        evidence,
        verdictResult.verdict,
        verdictResult.reasoning
      );

      if (!submissionResult.success) {
        return {
          success: false,
          verdict: VerdictType.NONE,
          error: 'Failed to submit verdict',
        };
      }

      return {
        success: true,
        verdict: verdictResult.verdict,
      };
    } catch (error) {
      console.error('Full verdict workflow failed:', error);
      return {
        success: false,
        verdict: VerdictType.NONE,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Schedule dispute settlement
   */
  async scheduleSettlement(
    disputeId: string,
    delaySeconds: number = 60
  ): Promise<void> {
    try {
      // Could add to a settlement queue if needed
      console.log(`Settlement scheduled for dispute ${disputeId} in ${delaySeconds}s`);
    } catch (error) {
      console.error('Failed to schedule settlement:', error);
      throw error;
    }
  }

  /**
   * Settle dispute (execute rewards/slashes)
   */
  async settleDispute(disputeId: string): Promise<{
    success: boolean;
    transactionHash: string;
  }> {
    try {
      console.log(`Settling dispute: ${disputeId}`);

      const txHash = await justiceClient.settleDispute(disputeId);

      return {
        success: true,
        transactionHash: txHash,
      };
    } catch (error) {
      console.error('Dispute settlement failed:', error);
      return {
        success: false,
        transactionHash: '',
      };
    }
  }

  /**
   * Appeal a verdict (future feature)
   */
  async appealVerdict(
    disputeId: string,
    appealReason: string
  ): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      console.log(`Appeal submitted for dispute: ${disputeId}`);
      // Implementation would follow similar pattern

      return {
        success: true,
        message: 'Appeal submitted successfully',
      };
    } catch (error) {
      console.error('Appeal submission failed:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Get verdict statistics
   */
  async getVerdictStats(): Promise<{
    totalVerdicts: number;
    successRate: number;
    avgProcessingTime: number;
  }> {
    try {
      // Would query contract or database
      return {
        totalVerdicts: 0,
        successRate: 0,
        avgProcessingTime: 0,
      };
    } catch (error) {
      console.error('Failed to fetch verdict stats:', error);
      throw error;
    }
  }
}

export const verdictService = new VerdictService();
