'use client';

import React from 'react';
import { SwarmMetrics } from '@/types';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  color: string;
  icon: string;
}

function MetricCard({ label, value, subtext, color, icon }: MetricCardProps) {
  return (
    <div className="bg-swarm-card border border-swarm-border rounded-xl p-4 hover:border-swarm-accent/40 transition-all duration-300">
      <div className="flex items-center justify-between mb-2">
        <span className="text-swarm-muted text-xs font-medium uppercase tracking-wider">{label}</span>
        <span className="text-lg">{icon}</span>
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
      {subtext && <div className="text-swarm-muted text-xs mt-1">{subtext}</div>}
    </div>
  );
}

interface MetricsPanelProps {
  metrics: SwarmMetrics | null;
  connected: boolean;
}

export default function MetricsPanel({ metrics, connected }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-swarm-card border border-swarm-border rounded-xl p-4 animate-pulse">
            <div className="h-3 bg-swarm-border rounded w-20 mb-3" />
            <div className="h-7 bg-swarm-border rounded w-16" />
          </div>
        ))}
      </div>
    );
  }

  const uptimeHours = (metrics.uptimeMs / 3600000).toFixed(1);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <MetricCard
        label="Active Sessions"
        value={metrics.activeSessions}
        subtext={`${metrics.totalSessions} total`}
        color="text-swarm-cyan"
        icon={connected ? '\u26A1' : '\u26AA'}
      />
      <MetricCard
        label="Agents Spawned"
        value={metrics.totalAgentsSpawned}
        subtext={`avg ${metrics.averageSwarmSize}/swarm`}
        color="text-swarm-purple"
        icon="\u{1F916}"
      />
      <MetricCard
        label="Tasks Complete"
        value={metrics.totalTasksCompleted}
        subtext={`${metrics.averageCompletionTimeMs > 0 ? (metrics.averageCompletionTimeMs / 1000).toFixed(1) + 's avg' : 'n/a'}`}
        color="text-swarm-success"
        icon="\u2705"
      />
      <MetricCard
        label="Tokens Paid"
        value={metrics.totalTokensDistributed.toFixed(1)}
        subtext="x402 protocol"
        color="text-swarm-warning"
        icon="\u{1FA99}"
      />
      <MetricCard
        label="Avg Confidence"
        value={`${(metrics.averageConfidence * 100).toFixed(1)}%`}
        subtext={metrics.topAgentId ? `top: ${(metrics.topAgentScore * 100).toFixed(1)}%` : 'no data'}
        color="text-swarm-accent"
        icon="\u{1F3AF}"
      />
      <MetricCard
        label="Uptime"
        value={`${uptimeHours}h`}
        subtext={connected ? 'ws: connected' : 'ws: disconnected'}
        color={connected ? 'text-swarm-success' : 'text-swarm-danger'}
        icon="\u{1F4E1}"
      />
    </div>
  );
}