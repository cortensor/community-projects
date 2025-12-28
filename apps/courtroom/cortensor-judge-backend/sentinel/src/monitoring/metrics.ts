/**
 * Monitoring & Metrics
 * Tracks system health and performance
 */

import { EventEmitter } from 'events';

export interface SystemMetrics {
  disputes: {
    total: number;
    active: number;
    pending: number;
    settled: number;
  };
  verdicts: {
    total: number;
    correct: number;
    incorrect: number;
    accuracy: number;
  };
  performance: {
    avgChallengeTime: number; // seconds
    avgVerdictTime: number;
    queueDepth: number;
  };
  network: {
    requestCount: number;
    errorCount: number;
    errorRate: number;
  };
  validators: {
    count: number;
    avgReputation: number;
  };
}

/**
 * Metrics Collector
 */
export class MetricsCollector extends EventEmitter {
  private metrics: SystemMetrics = {
    disputes: { total: 0, active: 0, pending: 0, settled: 0 },
    verdicts: { total: 0, correct: 0, incorrect: 0, accuracy: 0 },
    performance: { avgChallengeTime: 0, avgVerdictTime: 0, queueDepth: 0 },
    network: { requestCount: 0, errorCount: 0, errorRate: 0 },
    validators: { count: 0, avgReputation: 0 },
  };

  private timers: Map<string, number> = new Map();

  recordDisputeInitiated() {
    this.metrics.disputes.total++;
    this.metrics.disputes.active++;
    this.emit('dispute_initiated');
  }

  recordDisputeSettled(verdictCorrect: boolean) {
    this.metrics.disputes.active--;
    this.metrics.disputes.settled++;
    
    if (verdictCorrect) {
      this.metrics.verdicts.correct++;
    } else {
      this.metrics.verdicts.incorrect++;
    }
    
    this.metrics.verdicts.total++;
    this.updateAccuracy();
    this.emit('dispute_settled');
  }

  startTimer(id: string) {
    this.timers.set(id, Date.now());
  }

  endTimer(id: string, type: 'challenge' | 'verdict') {
    const start = this.timers.get(id);
    if (!start) return;

    const duration = (Date.now() - start) / 1000; // in seconds
    
    if (type === 'challenge') {
      this.metrics.performance.avgChallengeTime =
        (this.metrics.performance.avgChallengeTime + duration) / 2;
    } else {
      this.metrics.performance.avgVerdictTime =
        (this.metrics.performance.avgVerdictTime + duration) / 2;
    }

    this.timers.delete(id);
  }

  recordRequest(success: boolean) {
    this.metrics.network.requestCount++;
    if (!success) {
      this.metrics.network.errorCount++;
    }
    this.updateErrorRate();
  }

  updateQueueDepth(depth: number) {
    this.metrics.performance.queueDepth = depth;
  }

  updateValidatorMetrics(count: number, avgReputation: number) {
    this.metrics.validators.count = count;
    this.metrics.validators.avgReputation = avgReputation;
  }

  private updateAccuracy() {
    if (this.metrics.verdicts.total === 0) return;
    this.metrics.verdicts.accuracy =
      (this.metrics.verdicts.correct / this.metrics.verdicts.total) * 100;
  }

  private updateErrorRate() {
    if (this.metrics.network.requestCount === 0) return;
    this.metrics.network.errorRate =
      (this.metrics.network.errorCount / this.metrics.network.requestCount) * 100;
  }

  getMetrics(): SystemMetrics {
    return { ...this.metrics };
  }

  getHealthStatus(): {
    status: 'healthy' | 'degraded' | 'critical';
    issues: string[];
  } {
    const issues: string[] = [];

    // Check error rate
    if (this.metrics.network.errorRate > 10) {
      issues.push('High error rate');
    }

    // Check queue depth
    if (this.metrics.performance.queueDepth > 1000) {
      issues.push('Queue backlog');
    }

    // Check verdict accuracy
    if (this.metrics.verdicts.accuracy < 70 && this.metrics.verdicts.total > 100) {
      issues.push('Low verdict accuracy');
    }

    // Determine status
    let status: 'healthy' | 'degraded' | 'critical' = 'healthy';
    if (issues.length >= 2) {
      status = 'critical';
    } else if (issues.length === 1) {
      status = 'degraded';
    }

    return { status, issues };
  }

  reset() {
    this.metrics = {
      disputes: { total: 0, active: 0, pending: 0, settled: 0 },
      verdicts: { total: 0, correct: 0, incorrect: 0, accuracy: 0 },
      performance: { avgChallengeTime: 0, avgVerdictTime: 0, queueDepth: 0 },
      network: { requestCount: 0, errorCount: 0, errorRate: 0 },
      validators: { count: 0, avgReputation: 0 },
    };
    this.timers.clear();
  }
}

// Export singleton
export const metricsCollector = new MetricsCollector();
