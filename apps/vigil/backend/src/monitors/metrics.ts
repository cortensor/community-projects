import type { MetricsSnapshot } from '../types/index.js';
import db from '../db/index.js';

export class MetricsMonitor {
  private baselineLatency = 100;
  private baselineErrorRate = 0.01;
  private baselineValidatorScore = 0.9;

  getCurrentMetrics(): MetricsSnapshot {
    const metrics: MetricsSnapshot = {
      timestamp: Date.now(),
      latency: this.baselineLatency + (Math.random() - 0.5) * 20,
      errorRate: this.baselineErrorRate + (Math.random() - 0.5) * 0.005,
      validatorScore: this.baselineValidatorScore + (Math.random() - 0.5) * 0.05,
      uptime: 99.9,
      requestCount: Math.floor(1000 + Math.random() * 100)
    };

    this.saveMetrics(metrics);
    return metrics;
  }

  detectAnomalies(metrics: MetricsSnapshot): {
    hasAnomaly: boolean;
    type?: string;
    severity?: string;
  } {
    // High latency detection
    if (metrics.latency > this.baselineLatency * 2) {
      return {
        hasAnomaly: true,
        type: 'high_latency',
        severity: metrics.latency > this.baselineLatency * 3 ? 'critical' : 'high'
      };
    }

    // High error rate detection
    if (metrics.errorRate > this.baselineErrorRate * 5) {
      return {
        hasAnomaly: true,
        type: 'high_error_rate',
        severity: metrics.errorRate > this.baselineErrorRate * 10 ? 'critical' : 'high'
      };
    }

    // Validator score drop
    if (metrics.validatorScore < this.baselineValidatorScore * 0.8) {
      return {
        hasAnomaly: true,
        type: 'validator_score_drop',
        severity: metrics.validatorScore < this.baselineValidatorScore * 0.6 ? 'critical' : 'medium'
      };
    }

    return { hasAnomaly: false };
  }

  private saveMetrics(metrics: MetricsSnapshot) {
    const stmt = db.prepare(`
      INSERT INTO metrics_history (timestamp, latency, error_rate, validator_score, uptime, request_count)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    
    stmt.run(
      metrics.timestamp,
      metrics.latency,
      metrics.errorRate,
      metrics.validatorScore,
      metrics.uptime,
      metrics.requestCount
    );
  }

  getMetricsHistory(limit = 100): MetricsSnapshot[] {
    const stmt = db.prepare(`
      SELECT * FROM metrics_history
      ORDER BY timestamp DESC
      LIMIT ?
    `);
    
    const rows = stmt.all(limit) as any[];
    return rows.map(row => ({
      timestamp: row.timestamp,
      latency: row.latency,
      errorRate: row.error_rate,
      validatorScore: row.validator_score,
      uptime: row.uptime,
      requestCount: row.request_count
    }));
  }
}

export const metricsMonitor = new MetricsMonitor();
