/**
 * Advanced data parsing utilities for Cortensor API endpoints
 * Handles various response formats and extracts meaningful insights
 */

export interface ParsedEndpointData {
  endpoint: string;
  dataType: string;
  structure: any;
  sampleData: any;
  fields: string[];
  insights: string[];
}

/**
 * Intelligently parse and analyze API response structure
 */
export function analyzeEndpointResponse(endpoint: string, data: any): ParsedEndpointData {
  const insights: string[] = [];
  let dataType = 'unknown';
  let fields: string[] = [];

  if (Array.isArray(data)) {
    dataType = 'array';
    if (data.length > 0) {
      fields = Object.keys(data[0]);
      insights.push(`Array of ${data.length} items`);
      insights.push(`Each item has ${fields.length} fields`);
    }
  } else if (typeof data === 'object' && data !== null) {
    dataType = 'object';
    fields = Object.keys(data);
    insights.push(`Object with ${fields.length} top-level fields`);
    
    // Check for nested arrays
    fields.forEach(field => {
      if (Array.isArray(data[field])) {
        insights.push(`Field '${field}' contains array of ${data[field].length} items`);
      }
    });
  }

  return {
    endpoint,
    dataType,
    structure: getDataStructure(data),
    sampleData: getSampleData(data),
    fields,
    insights,
  };
}

/**
 * Extract data structure recursively
 */
function getDataStructure(data: any, depth: number = 0): any {
  if (depth > 3) return '...'; // Limit recursion depth

  if (Array.isArray(data)) {
    if (data.length === 0) return [];
    return [getDataStructure(data[0], depth + 1)];
  }

  if (typeof data === 'object' && data !== null) {
    const structure: any = {};
    Object.keys(data).slice(0, 10).forEach(key => {
      structure[key] = typeof data[key];
      if (typeof data[key] === 'object') {
        structure[key] = getDataStructure(data[key], depth + 1);
      }
    });
    return structure;
  }

  return typeof data;
}

/**
 * Get sample data for preview
 */
function getSampleData(data: any): any {
  if (Array.isArray(data)) {
    return data.slice(0, 3);
  }
  if (typeof data === 'object' && data !== null) {
    const sample: any = {};
    Object.keys(data).slice(0, 5).forEach(key => {
      sample[key] = data[key];
    });
    return sample;
  }
  return data;
}

/**
 * Parse network statistics with enhanced metrics
 */
export function parseNetworkStats(data: any) {
  const stats = {
    totalRequests: extractNumber(data, ['total_requests', 'requests', 'totalRequests']),
    activeNodes: extractNumber(data, ['active_nodes', 'nodes', 'activeNodes']),
    averageLatency: extractNumber(data, ['average_latency', 'latency', 'avgLatency']),
    successRate: extractNumber(data, ['success_rate', 'successRate', 'success']),
    throughput: extractNumber(data, ['throughput', 'tps', 'requestsPerSecond']),
    uptime: extractNumber(data, ['uptime', 'availability']),
  };

  return stats;
}

/**
 * Parse node data with performance metrics
 */
export function parseNodeData(data: any) {
  if (!Array.isArray(data)) {
    if (data.nodes && Array.isArray(data.nodes)) {
      data = data.nodes;
    } else {
      return [];
    }
  }

  return data.map((node: any, idx: number) => ({
    id: node.id || node.hotkey || node.node_id || `node-${idx}`,
    hotkey: node.hotkey || node.id || node.address,
    rank: node.rank ?? idx + 1,
    stake: extractNumber(node, ['stake', 'staked', 'balance']),
    emissions: extractNumber(node, ['emissions', 'rewards', 'earned']),
    performance: extractNumber(node, ['performance', 'score', 'rating']),
    status: node.status || (node.active ? 'active' : 'inactive'),
    uptime: extractNumber(node, ['uptime', 'availability']),
    latency: extractNumber(node, ['latency', 'responseTime']),
  }));
}

/**
 * Parse task data with analytics
 */
export function parseTaskData(data: any) {
  if (!Array.isArray(data)) {
    if (data.tasks && Array.isArray(data.tasks)) {
      data = data.tasks;
    } else {
      return [];
    }
  }

  return data.map((task: any, idx: number) => ({
    id: task.id || task.task_id || `task-${idx}`,
    name: task.name || task.type || task.task_name || 'Unknown Task',
    status: task.status || 'pending',
    successRate: extractNumber(task, ['success_rate', 'successRate', 'accuracy']),
    duration: extractNumber(task, ['duration', 'time', 'elapsed']),
    timestamp: task.timestamp || task.created_at || task.updated_at,
    priority: task.priority || 'normal',
    retries: extractNumber(task, ['retries', 'attempts']),
  }));
}

/**
 * Parse heatmap/ranking data
 */
export function parseHeatmapData(data: any) {
  if (!Array.isArray(data)) {
    if (data.ranks && Array.isArray(data.ranks)) {
      data = data.ranks;
    } else if (data.heatmap && Array.isArray(data.heatmap)) {
      data = data.heatmap;
    } else {
      return [];
    }
  }

  return data.map((item: any, idx: number) => ({
    rank: item.rank ?? idx + 1,
    value: extractNumber(item, ['value', 'score', 'performance']),
    nodeId: item.node_id || item.id || item.hotkey || `node-${idx}`,
    metric: item.metric || 'performance',
  }));
}

/**
 * Parse cognitive session data
 */
export function parseCognitiveSession(data: any) {
  return {
    sessionNumber: data.session_number || data.id || data.sessionId,
    timestamp: data.timestamp || data.created_at || data.startTime,
    status: data.status || 'unknown',
    metrics: data.metrics || {},
    requests: extractNumber(data, ['requests', 'totalRequests', 'count']),
    duration: extractNumber(data, ['duration', 'elapsed', 'time']),
    successRate: extractNumber(data, ['success_rate', 'successRate']),
    nodes: data.nodes || [],
  };
}

/**
 * Helper: Extract number from various possible field names
 */
function extractNumber(obj: any, possibleKeys: string[]): number {
  for (const key of possibleKeys) {
    if (obj[key] !== undefined && obj[key] !== null) {
      const num = Number(obj[key]);
      if (!isNaN(num)) return num;
    }
  }
  return 0;
}

/**
 * Generate mock data when real data is unavailable
 */
export function generateMockData(type: 'network' | 'nodes' | 'tasks' | 'heatmap') {
  switch (type) {
    case 'network':
      return {
        total_requests: Math.floor(Math.random() * 10000) + 5000,
        active_nodes: Math.floor(Math.random() * 100) + 50,
        average_latency: Math.floor(Math.random() * 100) + 50,
        success_rate: 85 + Math.random() * 15,
        throughput: Math.floor(Math.random() * 5000) + 2000,
      };

    case 'nodes':
      return Array.from({ length: 20 }, (_, i) => ({
        id: `node-${i}`,
        hotkey: `0x${Math.random().toString(16).substr(2, 40)}`,
        rank: i + 1,
        stake: Math.floor(Math.random() * 100000),
        emissions: Math.random() * 10,
        performance: Math.random() * 100,
        status: Math.random() > 0.2 ? 'active' : 'inactive',
      }));

    case 'tasks':
      return Array.from({ length: 10 }, (_, i) => ({
        id: `task-${i}`,
        name: ['Image Classification', 'Text Generation', 'Object Detection', 'Sentiment Analysis'][i % 4],
        status: ['completed', 'running', 'pending'][Math.floor(Math.random() * 3)],
        success_rate: 85 + Math.random() * 15,
        duration: Math.floor(Math.random() * 500) + 100,
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
      }));

    case 'heatmap':
      return Array.from({ length: 100 }, (_, i) => ({
        rank: i + 1,
        value: Math.random() * 100,
        node_id: `node-${i}`,
      }));

    default:
      return null;
  }
}
