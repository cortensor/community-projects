import { v4 as uuidv4 } from 'uuid';
import { ScoredResult, RewardTransaction } from '../models/AgentResult';
import { config } from '../config';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('RewardEngine');

export class RewardEngine {
  private baseReward: number;
  private minScoreThreshold: number;
  private rewardPool: number;

  constructor() {
    this.baseReward = config.reward.baseRewardTokens;
    this.minScoreThreshold = config.reward.minScoreThreshold;
    this.rewardPool = config.reward.rewardPoolSize;
  }

  distributeRewards(scoredResults: ScoredResult[], taskId: string): RewardTransaction[] {
    if (scoredResults.length === 0) return [];

    logger.info('Distributing rewards', {
      taskId,
      agentCount: scoredResults.length,
      pool: this.rewardPool,
    });

    const eligible = scoredResults.filter((r) => r.finalScore >= this.minScoreThreshold);
    const ineligible = scoredResults.filter((r) => r.finalScore < this.minScoreThreshold);

    if (eligible.length === 0) {
      logger.warn('No agents met minimum score threshold', {
        taskId,
        threshold: this.minScoreThreshold,
      });
      return scoredResults.map((r) => this.createTransaction(r, taskId, 0, 'penalty'));
    }

    const totalScore = eligible.reduce((sum, r) => sum + r.finalScore, 0);
    const now = Date.now();

    const transactions: RewardTransaction[] = [];

    for (const result of eligible) {
      const normalizedScore = result.finalScore / totalScore;
      let reward = this.baseReward * normalizedScore * eligible.length;

      if (result.rank === 1) {
        reward *= 1.25;
      } else if (result.rank === 2) {
        reward *= 1.1;
      }

      reward = Math.round(reward * 100) / 100;

      transactions.push(this.createTransaction(result, taskId, reward, 'inference_reward'));
    }

    for (const result of ineligible) {
      transactions.push(this.createTransaction(result, taskId, 0, 'penalty'));
    }

    const totalDistributed = transactions.reduce((sum, t) => sum + t.tokensEarned, 0);
    logger.info('Rewards distributed', {
      taskId,
      totalDistributed,
      eligibleCount: eligible.length,
      ineligibleCount: ineligible.length,
    });

    return transactions;
  }

  private createTransaction(
    result: ScoredResult,
    taskId: string,
    tokens: number,
    type: RewardTransaction['transactionType']
  ): RewardTransaction {
    return {
      id: uuidv4(),
      agentId: result.agentId,
      taskId,
      agentName: `Agent-${result.agentId.slice(0, 8)}`,
      tokensEarned: tokens,
      score: result.finalScore,
      rank: result.rank,
      transactionType: type,
      timestamp: Date.now(),
      x402PaymentId: uuidv4(),
      metadata: {
        confidence: result.confidence,
        computeTimeMs: result.computeTimeMs,
        reliability: result.reliabilityScore,
      },
    };
  }

  getRewardConfig() {
    return {
      baseReward: this.baseReward,
      minScoreThreshold: this.minScoreThreshold,
      rewardPool: this.rewardPool,
    };
  }
}

export const rewardEngine = new RewardEngine();