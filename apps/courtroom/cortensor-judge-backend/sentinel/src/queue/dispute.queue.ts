/**
 * Dispute Queue Management (Mock Mode)
 * All operations run in-memory without external dependencies
 * For production use with Redis, implement proper BullMQ integration
 */

import { DisputeStatus, VerdictType } from '../types/evidence';

export interface DisputeJob {
  disputeId: string;
  status: DisputeStatus;
  createdAt: number;
  challengeWindowEndsAt: number;
  retryCount: number;
}

export interface VerdictJob {
  disputeId: string;
  verdict: VerdictType;
  reasoning: string;
  createdAt: number;
}

/**
 * Mock Dispute Queue Service - In-Memory Implementation
 */
export class DisputeQueueService {
  private disputeMap: Map<string, DisputeJob> = new Map();
  private verdictMap: Map<string, VerdictJob> = new Map();
  private completedCallbacks: ((disputeId: string) => void)[] = [];
  private failedCallbacks: ((disputeId: string, error: string) => void)[] = [];

  constructor() {
    console.log('✅ Dispute Queue Service initialized (mock mode - in-memory only)');
  }

  /**
   * Add dispute to queue
   */
  async addDispute(
    disputeId: string,
    challengeWindowDuration: number = 3600000 // 1 hour default
  ): Promise<void> {
    const job: DisputeJob = {
      disputeId,
      status: 'initiated',
      createdAt: Date.now(),
      challengeWindowEndsAt: Date.now() + challengeWindowDuration,
      retryCount: 0,
    };
    this.disputeMap.set(disputeId, job);
    console.log(`⏳ [MOCK] Dispute queued: ${disputeId}`);
  }

  /**
   * Add verdict to queue
   */
  async addVerdict(disputeId: string, verdict: VerdictType, reasoning: string): Promise<void> {
    const job: VerdictJob = {
      disputeId,
      verdict,
      reasoning,
      createdAt: Date.now(),
    };
    this.verdictMap.set(disputeId, job);
    console.log(`⏳ [MOCK] Verdict queued for dispute: ${disputeId}`);
  }

  /**
   * Start dispute worker
   */
  async startDisputeWorker(handler: (job: DisputeJob) => Promise<void>): Promise<void> {
    console.log('👷 Dispute worker started');
    // In mock mode, disputes are processed synchronously
  }

  /**
   * Start verdict worker
   */
  async startVerdictWorker(handler: (job: VerdictJob) => Promise<void>): Promise<void> {
    console.log('👷 Verdict worker started');
    // In mock mode, verdicts are processed synchronously
  }

  /**
   * Start challenge window monitor
   */
  async startChallengeWindowMonitor(handler: (disputeId: string) => Promise<void>): Promise<void> {
    console.log('⏱️  Challenge window monitor started');
    // In mock mode, simulate window closure every 10 seconds
    setInterval(async () => {
      const now = Date.now();
      for (const [disputeId, job] of this.disputeMap.entries()) {
        if (job.challengeWindowEndsAt <= now && job.status !== 'settled') {
          try {
            await handler(disputeId);
            job.status = 'settled';
          } catch (error) {
            console.error(`Error processing challenge window for ${disputeId}:`, error);
          }
        }
      }
    }, 10000);
  }

  /**
   * Get dispute status
   */
  async getDisputeStatus(disputeId: string): Promise<DisputeStatus | null> {
    const job = this.disputeMap.get(disputeId);
    return job?.status || null;
  }

  /**
   * Listen for dispute completion
   */
  onDisputeCompleted(callback: (disputeId: string) => void): void {
    this.completedCallbacks.push(callback);
  }

  /**
   * Listen for dispute failure
   */
  onDisputeFailed(callback: (disputeId: string, error: string) => void): void {
    this.failedCallbacks.push(callback);
  }

  /**
   * Clean old jobs
   */
  async cleanOldJobs(olderThanMs: number = 86400000): Promise<void> {
    const cutoff = Date.now() - olderThanMs;
    for (const [key, job] of this.disputeMap.entries()) {
      if (job.createdAt < cutoff) {
        this.disputeMap.delete(key);
      }
    }
    console.log('🧹 Queue cleanup complete');
  }

  /**
   * Close queue connections (no-op in mock mode)
   */
  async close(): Promise<void> {
    console.log('✅ Queue service closed');
  }
}

// Export singleton
export const disputeQueueService = new DisputeQueueService();
