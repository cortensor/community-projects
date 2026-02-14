/**
 * Challenge Helper
 * Simplified API for creating challenges
 */

import axios from 'axios';
import { EvidenceBundle, VerdictType } from './types/evidence';
 
export interface ChallengeOptions {
  sentinelUrl: string;
  evidence: EvidenceBundle;
  bondAmount: string;
  reason?: string;
}

/**
 * Create a challenge against suspicious output
 */
export async function createChallenge(
  options: ChallengeOptions
): Promise<{
  success: boolean;
  disputeId?: string;
  message: string;
}> {
  try {
    const client = axios.create({
      baseURL: options.sentinelUrl,
      timeout: 30000,
    });

    const response = await client.post('/challenge', {
      evidence: options.evidence,
      bondAmount: options.bondAmount,
    });

    return {
      success: response.data.success,
      disputeId: response.data.disputeId,
      message: response.data.reason || 'Challenge created',
    };
  } catch (error) {
    console.error('Challenge creation failed:', error);
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Monitor for suspicious outputs and auto-challenge
 */
export async function monitorAndChallenge(
  sentinelUrl: string,
  prompt: string,
  evidence: EvidenceBundle,
  bondAmount: string,
  threshold: number = 0.95
): Promise<{
  isSuspicious: boolean;
  challenged: boolean;
  disputeId?: string;
  message: string;
}> {
  try {
    const client = axios.create({
      baseURL: sentinelUrl,
      timeout: 30000,
    });

    // First, monitor
    const monitorResponse = await client.post('/monitor', {
      prompt,
      threshold,
    });

    if (!monitorResponse.data.isSuspicious) {
      return {
        isSuspicious: false,
        challenged: false,
        message: 'Output is safe, no challenge needed',
      };
    }

    // If suspicious, initiate challenge
    const challengeResponse = await client.post('/auto-challenge', {
      evidence,
      minBond: bondAmount,
    });

    return {
      isSuspicious: true,
      challenged: challengeResponse.data.success,
      disputeId: challengeResponse.data.disputeId,
      message: challengeResponse.data.reason,
    };
  } catch (error) {
    console.error('Monitor and challenge failed:', error);
    return {
      isSuspicious: false,
      challenged: false,
      message: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
