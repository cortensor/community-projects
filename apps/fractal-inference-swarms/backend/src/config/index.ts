import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(__dirname, '../../.env') });

export interface AppConfig {
  server: {
    port: number;
    host: string;
    nodeEnv: string;
    corsOrigin: string;
  };
  websocket: {
    port: number;
    heartbeatInterval: number;
  };
  orchestrator: {
    maxConcurrentAgents: number;
    defaultSwarmSize: number;
    agentTimeoutMs: number;
    taskSplitStrategy: 'semantic' | 'equal' | 'weighted';
  };
  scoring: {
    weightConfidence: number;
    weightSpeed: number;
    weightReliability: number;
  };
  reward: {
    baseRewardTokens: number;
    minScoreThreshold: number;
    rewardPoolSize: number;
  };
  logging: {
    level: string;
    format: string;
  };
}

function parseFloat_(val: string | undefined, fallback: number): number {
  if (!val) return fallback;
  const parsed = parseFloat(val);
  return isNaN(parsed) ? fallback : parsed;
}

function parseInt_(val: string | undefined, fallback: number): number {
  if (!val) return fallback;
  const parsed = parseInt(val, 10);
  return isNaN(parsed) ? fallback : parsed;
}

export const config: AppConfig = {
  server: {
    port: parseInt_(process.env.PORT, 3001),
    host: process.env.HOST || '0.0.0.0',
    nodeEnv: process.env.NODE_ENV || 'development',
    corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  },
  websocket: {
    port: parseInt_(process.env.WS_PORT, 3002),
    heartbeatInterval: parseInt_(process.env.WS_HEARTBEAT_INTERVAL, 30000),
  },
  orchestrator: {
    maxConcurrentAgents: parseInt_(process.env.MAX_CONCURRENT_AGENTS, 20),
    defaultSwarmSize: parseInt_(process.env.DEFAULT_SWARM_SIZE, 5),
    agentTimeoutMs: parseInt_(process.env.AGENT_TIMEOUT_MS, 30000),
    taskSplitStrategy: (process.env.TASK_SPLIT_STRATEGY as AppConfig['orchestrator']['taskSplitStrategy']) || 'semantic',
  },
  scoring: {
    weightConfidence: parseFloat_(process.env.SCORING_WEIGHT_CONFIDENCE, 0.4),
    weightSpeed: parseFloat_(process.env.SCORING_WEIGHT_SPEED, 0.3),
    weightReliability: parseFloat_(process.env.SCORING_WEIGHT_RELIABILITY, 0.3),
  },
  reward: {
    baseRewardTokens: parseFloat_(process.env.BASE_REWARD_TOKENS, 100),
    minScoreThreshold: parseFloat_(process.env.MIN_SCORE_THRESHOLD, 0.3),
    rewardPoolSize: parseFloat_(process.env.REWARD_POOL_SIZE, 1000),
  },
  logging: {
    level: process.env.LOG_LEVEL || 'debug',
    format: process.env.LOG_FORMAT || 'json',
  },
};

export function validateConfig(cfg: AppConfig): void {
  const totalWeight = cfg.scoring.weightConfidence + cfg.scoring.weightSpeed + cfg.scoring.weightReliability;
  if (Math.abs(totalWeight - 1.0) > 0.01) {
    throw new Error(`Scoring weights must sum to 1.0, got ${totalWeight}`);
  }
  if (cfg.orchestrator.maxConcurrentAgents < 1) {
    throw new Error('maxConcurrentAgents must be at least 1');
  }
  if (cfg.reward.minScoreThreshold < 0 || cfg.reward.minScoreThreshold > 1) {
    throw new Error('minScoreThreshold must be between 0 and 1');
  }
}