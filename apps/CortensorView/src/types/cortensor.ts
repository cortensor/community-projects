export interface NetworkStats {
  total_requests?: number;
  active_nodes?: number;
  average_latency?: number;
  success_rate?: number;
  total_inference_time?: number;
  [key: string]: unknown;
}

export interface NodeData {
  id?: string;
  hotkey?: string;
  rank?: number;
  stake?: number;
  emissions?: number;
  performance?: number;
  status?: string;
  [key: string]: unknown;
}

export interface CognitiveSession {
  session_number?: number;
  timestamp?: string;
  status?: string;
  metrics?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TaskData {
  id?: string;
  name?: string;
  status?: string;
  success_rate?: number;
  duration?: number;
  timestamp?: string;
  [key: string]: unknown;
}

export interface HeatmapRank {
  rank?: number;
  value?: number;
  node_id?: string;
  [key: string]: unknown;
}

export interface ConfigData {
  [key: string]: unknown;
}

export interface DashboardData {
  networkStats?: NetworkStats;
  nodes?: NodeData[];
  sessions?: CognitiveSession[];
  tasks?: TaskData[];
  heatmap?: HeatmapRank[];
  config?: ConfigData;
}
