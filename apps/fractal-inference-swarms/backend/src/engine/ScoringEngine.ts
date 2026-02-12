import { AgentResult, ScoredResult, ScoreBreakdown } from '../models/AgentResult';
import { config } from '../config';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('ScoringEngine');

export interface ScoringWeights {
  confidence: number;
  speed: number;
  reliability: number;
}

export class ScoringEngine {
  private weights: ScoringWeights;

  constructor(weights?: Partial<ScoringWeights>) {
    this.weights = {
      confidence: weights?.confidence ?? config.scoring.weightConfidence,
      speed: weights?.speed ?? config.scoring.weightSpeed,
      reliability: weights?.reliability ?? config.scoring.weightReliability,
    };

    const total = this.weights.confidence + this.weights.speed + this.weights.reliability;
    if (Math.abs(total - 1.0) > 0.01) {
      logger.warn('Scoring weights do not sum to 1.0, normalizing', { total });
      this.weights.confidence /= total;
      this.weights.speed /= total;
      this.weights.reliability /= total;
    }
  }

  scoreResults(results: AgentResult[]): ScoredResult[] {
    if (results.length === 0) return [];

    logger.info('Scoring agent results', { count: results.length });

    const maxComputeTime = Math.max(...results.map((r) => r.computeTimeMs));
    const minComputeTime = Math.min(...results.map((r) => r.computeTimeMs));
    const computeRange = maxComputeTime - minComputeTime || 1;

    const scored: ScoredResult[] = results.map((result) => {
      const rawConfidence = Math.max(0, Math.min(1, result.confidence));
      const rawSpeedScore = 1 - (result.computeTimeMs - minComputeTime) / computeRange;
      const rawReliability = Math.max(0, Math.min(1, result.reliabilityScore));

      const confidenceComponent = this.weights.confidence * rawConfidence;
      const speedComponent = this.weights.speed * rawSpeedScore;
      const reliabilityComponent = this.weights.reliability * rawReliability;

      const finalScore = confidenceComponent + speedComponent + reliabilityComponent;

      const breakdown: ScoreBreakdown = {
        confidenceComponent,
        speedComponent,
        reliabilityComponent,
        rawConfidence,
        rawSpeedScore,
        rawReliability,
      };

      return {
        ...result,
        finalScore: Math.round(finalScore * 10000) / 10000,
        rank: 0,
        scoreBreakdown: breakdown,
      };
    });

    scored.sort((a, b) => b.finalScore - a.finalScore);
    scored.forEach((s, i) => {
      s.rank = i + 1;
    });

    logger.info('Scoring complete', {
      topScore: scored[0]?.finalScore,
      bottomScore: scored[scored.length - 1]?.finalScore,
      spread: scored[0]?.finalScore - scored[scored.length - 1]?.finalScore,
    });

    return scored;
  }

  getWeights(): ScoringWeights {
    return { ...this.weights };
  }

  updateWeights(newWeights: Partial<ScoringWeights>): void {
    if (newWeights.confidence !== undefined) this.weights.confidence = newWeights.confidence;
    if (newWeights.speed !== undefined) this.weights.speed = newWeights.speed;
    if (newWeights.reliability !== undefined) this.weights.reliability = newWeights.reliability;

    const total = this.weights.confidence + this.weights.speed + this.weights.reliability;
    this.weights.confidence /= total;
    this.weights.speed /= total;
    this.weights.reliability /= total;

    logger.info('Scoring weights updated', this.weights);
  }
}

export const scoringEngine = new ScoringEngine();