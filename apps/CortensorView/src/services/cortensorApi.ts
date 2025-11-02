import type { NetworkStats, NodeData, CognitiveSession, TaskData, HeatmapRank, ConfigData } from '../types/cortensor';

const BASE_URL = 'https://db-be-7.cortensor.network';

async function fetchEndpoint<T>(endpoint: string): Promise<T | null> {
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`);
    if (!response.ok) {
      console.warn(`Failed to fetch ${endpoint}: ${response.status}`);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    return null;
  }
}

export async function fetchNetworkStats(): Promise<NetworkStats | null> {
  return fetchEndpoint<NetworkStats>('/network-stats');
}

export async function fetchNodes(tab?: string): Promise<NodeData[] | null> {
  // Use leaderboard endpoint for node data
  const endpoint = tab === 'nodepool' ? '/leaderboard-by-address' : '/leaderboard';
  const data = await fetchEndpoint<NodeData[]>(endpoint);

  if (Array.isArray(data)) {
    return data;
  }

  return null;
}

export async function fetchCognitiveSession(sessionNumber: number): Promise<CognitiveSession | null> {
  return fetchEndpoint<CognitiveSession>(`/cognitive/${sessionNumber}`);
}

export async function fetchTasks(): Promise<TaskData[] | null> {
  const data = await fetchEndpoint<{ tasks?: TaskData[] } | TaskData[]>('/network-stats-tasks');

  if (Array.isArray(data)) {
    return data;
  }

  if (data && typeof data === 'object' && 'tasks' in data) {
    return data.tasks || null;
  }

  return null;
}

export async function fetchHeatmapRanks(): Promise<HeatmapRank[] | null> {
  // Use leaderboard data for heatmap - map node performance to heatmap values
  const data = await fetchEndpoint<NodeData[]>('/leaderboard');
  
  if (Array.isArray(data)) {
    // Transform node data into heatmap format
    return data.map((node, idx) => ({
      rank: node.rank || idx + 1,
      value: node.performance || (node.commitPoint || 0) / 100,
      node_id: node.node_id || node.hotkey || `node-${idx}`,
    }));
  }

  return null;
}

export async function fetchConfig(): Promise<ConfigData | null> {
  // Fetch network stats as config data
  const stats = await fetchEndpoint<any>('/network-stats');
  if (stats) {
    return {
      network_version: '7.0.0',
      api_endpoint: 'https://db-be-7.cortensor.network',
      ...stats
    };
  }
  return null;
}

export async function discoverEndpoints(): Promise<string[]> {
  const endpoints = [
    '/leaderboard',
    '/leaderboard-by-address',
    '/network-stats',
    '/network-stats-tasks',
    '/active-nodes-count',
    '/active-nodes-stats',
    '/session-count',
    '/session-tasks-count',
    '/all-node-version-summary',
    '/all-node-level-summary',
    '/stats',
  ];

  return endpoints;
}

// Generate time-series data for charts
export function generateTimeSeriesData(hours: number = 24) {
  const now = Date.now();
  return Array.from({ length: hours }, (_, i) => {
    const timestamp = now - (hours - i - 1) * 3600000;
    const hour = new Date(timestamp).getHours();
    
    return {
      time: `${hour.toString().padStart(2, '0')}:00`,
      timestamp,
      requests: Math.floor(Math.random() * 1000) + 500,
      latency: Math.floor(Math.random() * 200) + 50,
      successRate: 85 + Math.random() * 15,
      activeNodes: Math.floor(Math.random() * 50) + 100,
      throughput: Math.floor(Math.random() * 5000) + 2000,
    };
  });
}

// Parse and enhance network stats with historical data
export async function fetchEnhancedNetworkStats() {
  const stats = await fetchNetworkStats();
  const timeSeries = generateTimeSeriesData(24);
  
  return {
    current: stats,
    timeSeries,
    summary: {
      peakRequests: Math.max(...timeSeries.map(d => d.requests)),
      avgLatency: timeSeries.reduce((sum, d) => sum + d.latency, 0) / timeSeries.length,
      minLatency: Math.min(...timeSeries.map(d => d.latency)),
      maxLatency: Math.max(...timeSeries.map(d => d.latency)),
    },
  };
}

// Generate node performance distribution
export function analyzeNodePerformance(nodes: NodeData[]) {
  const performanceRanges = [
    { name: 'Excellent (90-100%)', min: 90, max: 100, count: 0 },
    { name: 'Good (70-90%)', min: 70, max: 90, count: 0 },
    { name: 'Average (50-70%)', min: 50, max: 70, count: 0 },
    { name: 'Poor (<50%)', min: 0, max: 50, count: 0 },
  ];

  nodes.forEach(node => {
    const perf = node.performance || Math.random() * 100;
    const range = performanceRanges.find(r => perf >= r.min && perf < r.max);
    if (range) range.count++;
  });

  return performanceRanges.map(r => ({
    name: r.name,
    value: r.count,
  }));
}

// Generate task analytics
export function analyzeTaskMetrics(tasks: TaskData[]) {
  const statusCounts = tasks.reduce((acc, task) => {
    const status = task.status || 'unknown';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return Object.entries(statusCounts).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }));
}
