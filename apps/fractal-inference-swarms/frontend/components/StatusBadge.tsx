'use client';

import React from 'react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-600 text-gray-200',
  splitting: 'bg-blue-600/30 text-blue-300 border border-blue-500/50',
  spawning_agents: 'bg-purple-600/30 text-purple-300 border border-purple-500/50 animate-pulse',
  inference_running: 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 animate-pulse',
  scoring: 'bg-amber-600/30 text-amber-300 border border-amber-500/50',
  merging: 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 animate-pulse',
  validating: 'bg-teal-600/30 text-teal-300 border border-teal-500/50',
  distributing_rewards: 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/50',
  completed: 'bg-green-600/30 text-green-300 border border-green-500/50',
  failed: 'bg-red-600/30 text-red-300 border border-red-500/50',
  active: 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 animate-pulse',
  idle: 'bg-gray-600/30 text-gray-300',
  initializing: 'bg-blue-600/30 text-blue-300 animate-pulse',
  running: 'bg-cyan-600/30 text-cyan-300 animate-pulse',
  timeout: 'bg-orange-600/30 text-orange-300',
};

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-600 text-gray-200';
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span className={`inline-flex items-center rounded-full font-mono font-medium ${colorClass} ${sizeClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${status === 'completed' ? 'bg-green-400' : status === 'failed' ? 'bg-red-400' : 'bg-current'}`} />
      {status.replace(/_/g, ' ')}
    </span>
  );
}