'use client';

import React from 'react';
import { RewardTransaction } from '@/types';

interface LeaderboardProps {
  ledger: RewardTransaction[];
}

interface AgentAggregate {
  agentId: string;
  agentName: string;
  totalTokens: number;
  taskCount: number;
  avgScore: number;
  bestRank: number;
}

export default function Leaderboard({ ledger }: LeaderboardProps) {
  const aggregated = new Map<string, AgentAggregate>();

  for (const tx of ledger) {
    const existing = aggregated.get(tx.agentId);
    if (existing) {
      existing.totalTokens += tx.tokensEarned;
      existing.taskCount++;
      existing.avgScore = (existing.avgScore * (existing.taskCount - 1) + tx.score) / existing.taskCount;
      existing.bestRank = Math.min(existing.bestRank, tx.rank);
    } else {
      aggregated.set(tx.agentId, {
        agentId: tx.agentId,
        agentName: tx.agentName,
        totalTokens: tx.tokensEarned,
        taskCount: 1,
        avgScore: tx.score,
        bestRank: tx.rank,
      });
    }
  }

  const sorted = Array.from(aggregated.values())
    .filter((a) => a.totalTokens > 0)
    .sort((a, b) => b.totalTokens - a.totalTokens)
    .slice(0, 15);

  const maxTokens = sorted[0]?.totalTokens || 1;

  if (sorted.length === 0) {
    return (
      <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-swarm-text mb-3">Agent Leaderboard</h3>
        <div className="text-swarm-muted text-sm text-center py-6">No agent data yet. Submit a task to populate the leaderboard.</div>
      </div>
    );
  }

  return (
    <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-swarm-text mb-4">Agent Leaderboard</h3>
      <div className="space-y-2">
        {sorted.map((agent, i) => {
          const barWidth = (agent.totalTokens / maxTokens) * 100;
          const medal = i === 0 ? '\u{1F947}' : i === 1 ? '\u{1F948}' : i === 2 ? '\u{1F949}' : '';

          return (
            <div
              key={agent.agentId}
              className="relative bg-swarm-surface border border-swarm-border rounded-lg p-3 overflow-hidden animate-slide-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div
                className="absolute inset-0 bg-gradient-to-r from-swarm-accent/10 to-transparent transition-all duration-1000"
                style={{ width: `${barWidth}%` }}
              />
              <div className="relative flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg w-8 text-center">
                    {medal || <span className="text-xs text-swarm-muted font-mono">#{i + 1}</span>}
                  </span>
                  <div>
                    <div className="text-sm font-mono font-semibold text-swarm-text">{agent.agentName}</div>
                    <div className="text-[10px] text-swarm-muted">
                      {agent.taskCount} tasks | avg score: {(agent.avgScore * 100).toFixed(1)}% | best: #{agent.bestRank}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold font-mono text-swarm-warning">{agent.totalTokens.toFixed(2)}</div>
                  <div className="text-[10px] text-swarm-muted">tokens</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}