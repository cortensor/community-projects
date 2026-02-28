export interface Incident {
  id: string;
  type: 'high_latency' | 'high_error_rate' | 'validator_score_drop' | 'router_down';
  status: 'detected' | 'analyzing' | 'confirmed' | 'acting' | 'resolved';
  severity: 'low' | 'medium' | 'high' | 'critical';
  detectedAt: number;
  resolvedAt?: number;
  metrics: MetricsSnapshot;
  analysis?: AnalysisResult;
  actions: Action[];
  evidenceBundle?: EvidenceBundle;
}

export interface MetricsSnapshot {
  timestamp: number;
  latency: number;
  errorRate: number;
  validatorScore: number;
  uptime: number;
  requestCount: number;
}

export interface AnalysisResult {
  sessionIds: string[];
  modelOutputs: ModelOutput[];
  consensus: boolean;
  confidence: number;
  validatorScores: number[];
  timestamp: number;
}

export interface ModelOutput {
  model: string;
  output: string;
  isAnomaly: boolean;
  confidence: number;
  validatorScore: number;
}

export interface Action {
  type: 'github_issue' | 'discord_alert' | 'log' | 'escalate';
  status: 'pending' | 'executed' | 'failed';
  timestamp: number;
  result?: any;
  error?: string;
}

export interface EvidenceBundle {
  incidentId: string;
  timestamp: number;
  metrics: MetricsSnapshot;
  analysis: AnalysisResult;
  actions: Action[];
  timeline: TimelineEvent[];
}

export interface TimelineEvent {
  timestamp: number;
  event: string;
  details: any;
}

export interface CortensorSession {
  sessionId: string;
  model: string;
  createdAt: number;
}
