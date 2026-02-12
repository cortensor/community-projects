import { Task, SwarmSession, ScoredResult, RewardTransaction, SwarmMetrics } from '@/types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function submitTask(data: {
  title: string;
  description: string;
  priority?: string;
  swarmSize?: number;
}): Promise<{ success: boolean; task: Task; message: string }> {
  return fetchJSON('/task', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getTask(
  id: string
): Promise<{ task: Task; session: SwarmSession | null; scoredResults: ScoredResult[] }> {
  return fetchJSON(`/task/${id}`);
}

export async function getAllTasks(): Promise<{ count: number; tasks: Task[] }> {
  return fetchJSON('/tasks');
}

export async function getAgentsForTask(
  taskId: string
): Promise<{ taskId: string; agentCount: number; agents: unknown[]; scoredResults: ScoredResult[] }> {
  return fetchJSON(`/agents/${taskId}`);
}

export async function getLedger(): Promise<{
  transactionCount: number;
  transactions: RewardTransaction[];
  paymentStats: Record<string, number>;
  balances: Record<string, number>;
}> {
  return fetchJSON('/ledger');
}

export async function getMetrics(): Promise<{
  swarm: SwarmMetrics;
  payments: Record<string, number>;
  scoring: { confidence: number; speed: number; reliability: number };
  system: { memoryUsage: Record<string, number>; uptime: number; wsConnections: number };
}> {
  return fetchJSON('/metrics');
}

export async function getSessions(): Promise<{ count: number; sessions: SwarmSession[] }> {
  return fetchJSON('/sessions');
}