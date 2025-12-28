/**
 * Submit Evidence Helper
 * Simplified API for submitting evidence to the Judge
 */

import axios from 'axios';
import { EvidenceBundle } from './types/evidence';

export interface SubmitEvidenceOptions {
  sentinelUrl: string;
  evidence: EvidenceBundle;
  bondAmount: string;
  autoChallenge?: boolean;
}

/**
 * Submit evidence directly to Sentinel service
 */
export async function submitEvidence(
  options: SubmitEvidenceOptions
): Promise<{
  success: boolean;
  disputeId?: string;
  transactionHash?: string;
  error?: string;
}> {
  try {
    const client = axios.create({
      baseURL: options.sentinelUrl,
      timeout: 30000,
    });

    const endpoint = options.autoChallenge ? '/auto-challenge' : '/challenge';

    const response = await client.post(endpoint, {
      evidence: options.evidence,
      bondAmount: options.bondAmount,
    });

    return response.data;
  } catch (error) {
    console.error('Evidence submission failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Batch submit multiple evidence bundles
 */
export async function submitEvidenceBatch(
  sentinelUrl: string,
  evidences: Array<{
    bundle: EvidenceBundle;
    bondAmount: string;
  }>
): Promise<Array<{
  success: boolean;
  disputeId?: string;
  error?: string;
}>> {
  return Promise.all(
    evidences.map((item) =>
      submitEvidence({
        sentinelUrl,
        evidence: item.bundle,
        bondAmount: item.bondAmount,
      })
    )
  );
}
