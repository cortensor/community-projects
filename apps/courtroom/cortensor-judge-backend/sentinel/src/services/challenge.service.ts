/**
 * Challenge Service
 * Handles challenge initiation and adversarial detection
 */

import { justiceClient } from '../web3/justice.client';
import { cortensorRouter } from '../cortensor/router';
import { ipfsService } from '../evidence/ipfs';
import { EvidenceBundleService } from '../evidence/bundle';
import { detectOutliers, MockEmbedding } from '../similarity/cosine';
import { config } from '../config/env';
import { EvidenceBundle, DisputeStatus } from '../types/evidence';
import { disputeQueueService } from '../queue/dispute.queue';

export interface ChallengeResult {
  disputeId: string;
  success: boolean;
  transactionHash: string;
  reason: string;
}

/**
 * Challenge Service
 */
export class ChallengeService {
  private embeddingModel = new MockEmbedding(); // In production, use Pinecone

  /**
   * Initiate a challenge against suspicious miner output
   */
  async initiateChallenge(
    evidence: EvidenceBundle,
    bondAmount: string
  ): Promise<ChallengeResult> {
    try {
      console.log(`Initiating challenge against miner: ${evidence.miner}`);

      // Validate evidence
      const validation = EvidenceBundleService.validateBundle(evidence);
      if (!validation.isValid) {
        return {
          disputeId: '',
          success: false,
          transactionHash: '',
          reason: `Invalid evidence: ${validation.errors.join(', ')}`,
        };
      }

      // Pin evidence to IPFS
      const ipfsHash = await ipfsService.pinEvidenceBundle(evidence);
      evidence.ipfsHash = ipfsHash;

      // Submit challenge to Justice contract
      const disputeId = await justiceClient.initiateChallenge(evidence, bondAmount);

      // Add to dispute queue
      await disputeQueueService.addDispute(disputeId, config.CHALLENGE_WINDOW_DURATION);

      console.log(`Challenge initiated: Dispute ID ${disputeId}`);

      return {
        disputeId,
        success: true,
        transactionHash: '', // Would be filled from tx receipt
        reason: 'Challenge initiated successfully',
      };
    } catch (error) {
      console.error('Challenge initiation failed:', error);
      return {
        disputeId: '',
        success: false,
        transactionHash: '',
        reason: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Monitor network for suspicious outputs
   * Uses Cortensor /validate to detect deviations
   */
  async monitorForSuspiciousOutputs(
    prompt: string,
    threshold: number = config.MIN_SIMILARITY_THRESHOLD
  ): Promise<{
    isSuspicious: boolean;
    outlierMiners: string[];
    consensusScore: number;
  }> {
    try {
      console.log(`Monitoring prompt for suspicious outputs`);

      // Get Cortensor consensus results
      const validationResult = await cortensorRouter.validateInference({
        prompt,
        validators: 3,
      });

      // Extract miner outputs
      const minerOutputs = new Map<string, string>();
      for (const result of validationResult.results) {
        minerOutputs.set(result.minerAddress, result.result);
      }

      // Detect outliers using cosine similarity
      const outlierAnalysis = await detectOutliers(
        minerOutputs,
        this.embeddingModel,
        threshold
      );

      const isSuspicious = outlierAnalysis.outliers.length > 0;

      console.log(`Monitoring result: ${isSuspicious ? 'SUSPICIOUS' : 'SAFE'}`, {
        outliers: outlierAnalysis.outliers,
        consensus: validationResult.consensusScore,
      });

      return {
        isSuspicious,
        outlierMiners: outlierAnalysis.outliers,
        consensusScore: validationResult.consensusScore,
      };
    } catch (error) {
      console.error('Suspicious output monitoring failed:', error);
      return {
        isSuspicious: false,
        outlierMiners: [],
        consensusScore: 0,
      };
    }
  }

  /**
   * Auto-challenge suspicious outputs
   */
  async autoChallengeIfSuspicious(
    evidence: EvidenceBundle,
    minBond: string = config.MIN_BOND_AMOUNT,
    maxBond: string = config.MAX_BOND_AMOUNT
  ): Promise<ChallengeResult> {
    try {
      // Monitor for suspicious activity
      const monitoring = await this.monitorForSuspiciousOutputs(
        '',
        config.MIN_SIMILARITY_THRESHOLD
      );

      if (!monitoring.isSuspicious) {
        return {
          disputeId: '',
          success: false,
          transactionHash: '',
          reason: 'Output is not suspicious, no challenge initiated',
        };
      }

      // If output is suspicious, determine bond amount
      const bondAmount = this.calculateBondAmount(monitoring.consensusScore, minBond, maxBond);

      // Initiate challenge
      return this.initiateChallenge(evidence, bondAmount);
    } catch (error) {
      console.error('Auto-challenge failed:', error);
      return {
        disputeId: '',
        success: false,
        transactionHash: '',
        reason: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Calculate appropriate bond amount based on risk
   * Higher risk -> higher bond
   */
  private calculateBondAmount(
    consensusScore: number,
    minBond: string,
    maxBond: string
  ): string {
    const min = BigInt(minBond);
    const max = BigInt(maxBond);

    // Risk score from 0-1 (inverse of consensus)
    const riskScore = 1 - consensusScore;

    // Calculate bond as: min + (max - min) * riskScore
    const range = max - min;
    const bondBigInt = min + (range * BigInt(Math.floor(riskScore * 100))) / BigInt(100);

    return bondBigInt.toString();
  }

  /**
   * Get miner's challenge history
   */
  async getMinerChallengeHistory(minerAddress: string): Promise<{
    totalChallenges: number;
    successfulChallenges: number;
    trustScore: number;
  }> {
    try {
      const trustScore = await justiceClient.getMinerTrustScore(minerAddress);

      return {
        totalChallenges: 0, // Would need to query contract
        successfulChallenges: 0,
        trustScore,
      };
    } catch (error) {
      console.error('Failed to fetch miner challenge history:', error);
      throw error;
    }
  }
}

export const challengeService = new ChallengeService();
