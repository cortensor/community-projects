import type { MetricsSnapshot } from '../types/index.js';
import { metricsMonitor } from '../monitors/metrics.js';

export class Simulator {
  simulateIncident(type: 'high_latency' | 'high_error_rate' | 'validator_score_drop'): MetricsSnapshot {
    const baseMetrics = metricsMonitor.getCurrentMetrics();

    switch (type) {
      case 'high_latency':
        return {
          ...baseMetrics,
          latency: 300 + Math.random() * 100 // 300-400ms (baseline is ~100ms)
        };

      case 'high_error_rate':
        return {
          ...baseMetrics,
          errorRate: 0.08 + Math.random() * 0.04 // 8-12% (baseline is ~1%)
        };

      case 'validator_score_drop':
        return {
          ...baseMetrics,
          validatorScore: 0.5 + Math.random() * 0.1 // 0.5-0.6 (baseline is ~0.9)
        };

      default:
        return baseMetrics;
    }
  }

  generateHealthyMetrics(): MetricsSnapshot {
    return metricsMonitor.getCurrentMetrics();
  }
}

export const simulator = new Simulator();
