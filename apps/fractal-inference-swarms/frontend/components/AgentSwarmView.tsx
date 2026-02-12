'use client';

import React, { useEffect, useState } from 'react';
import { Task, ScoredResult, SwarmSession } from '@/types';
import { getTask } from '@/lib/api';
import StatusBadge from './StatusBadge';

interface AgentSwarmViewProps {
  taskId: string;
}

export default function AgentSwarmView({ taskId }: AgentSwarmViewProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [session, setSession] = useState<SwarmSession | null>(null);
  const [scored, setScored] = useState<ScoredResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const data = await getTask(taskId);
        if (mounted) {
          setTask(data.task);
          setSession(data.session);
          setScored(data.scoredResults);
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [taskId]);

  if (loading) {
    return (
      <div className="bg-swarm-card border border-swarm-border rounded-xl p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-5 bg-swarm-border rounded w-48" />
          <div className="h-4 bg-swarm-border rounded w-full" />
          <div className="grid grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-24 bg-swarm-border rounded-lg" />)}
          </div>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="bg-swarm-card border border-swarm-border rounded-xl p-6 text-swarm-muted text-center">
        Task not found
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Task Detail Header */}
      <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-lg font-bold text-swarm-text">{task.title}</h2>
            <p className="text-sm text-swarm-muted mt-1">{task.description}</p>
          </div>
          <StatusBadge status={task.status} size="md" />
        </div>
        <div className="flex gap-4 text-xs text-swarm-muted font-mono">
          <span>ID: {task.id.slice(0, 12)}</span>
          <span>Agents: {task.swarmSize}</span>
          <span>Subtasks: {task.subtasks.length}</span>
          {task.totalComputeTimeMs > 0 && <span>Total: {(task.totalComputeTimeMs / 1000).toFixed(2)}s</span>}
        </div>
      </div>

      {/* Agent Grid */}
      {session && session.agents.length > 0 && (
        <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-swarm-text mb-3">Swarm Agents</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {session.agents.map((agent, i) => {
              const agentScore = scored.find((s) => s.agentId === agent.id);
              const reward = session.rewards.find((r) => r.agentId === agent.id);

              return (
                <div
                  key={agent.id}
                  className={`bg-swarm-surface border border-swarm-border rounded-lg p-3 transition-all duration-500 ${
                    agent.status === 'running' ? 'animate-glow' : ''
                  } ${agent.status === 'completed' ? 'animate-spawn' : ''}`}
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-mono font-semibold text-swarm-text">{agent.name}</span>
                    <StatusBadge status={agent.status} />
                  </div>
                  <div className="space-y-1 text-xs text-swarm-muted font-mono">
                    <div className="flex justify-between">
                      <span>Compute</span>
                      <span>{agent.computeTimeMs > 0 ? `${(agent.computeTimeMs / 1000).toFixed(2)}s` : '...'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Iterations</span>
                      <span>{agent.inferenceIterations}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Memory</span>
                      <span>{agent.memoryUsageMb > 0 ? `${agent.memoryUsageMb.toFixed(0)}MB` : '...'}</span>
                    </div>
                    {agentScore && (
                      <>
                        <div className="border-t border-swarm-border/50 pt-1 mt-1" />
                        <div className="flex justify-between text-swarm-accent">
                          <span>Score</span>
                          <span>{(agentScore.finalScore * 100).toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Rank</span>
                          <span className={agentScore.rank <= 3 ? 'text-swarm-warning' : ''}>
                            #{agentScore.rank}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Confidence</span>
                          <span>{(agentScore.confidence * 100).toFixed(1)}%</span>
                        </div>
                      </>
                    )}
                    {reward && (
                      <div className="flex justify-between text-swarm-success font-semibold">
                        <span>Reward</span>
                        <span>{reward.tokensEarned.toFixed(2)} tokens</span>
                      </div>
                    )}
                  </div>
                  {agentScore && (
                    <div className="mt-2">
                      <div className="w-full bg-swarm-border rounded-full h-1.5">
                        <div
                          className="bg-gradient-to-r from-swarm-accent to-swarm-cyan h-1.5 rounded-full transition-all duration-1000"
                          style={{ width: `${agentScore.finalScore * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Merged Output */}
      {task.mergedOutput && (
        <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-swarm-text">Merged Output</h3>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full ${task.mergedOutput.validationPassed ? 'bg-green-900/30 text-green-400 border border-green-700/40' : 'bg-amber-900/30 text-amber-400 border border-amber-700/40'}`}>
                {task.mergedOutput.validationPassed ? 'VALIDATED' : 'VALIDATION ISSUES'}
              </span>
              <span className="text-xs text-swarm-muted font-mono">
                {(task.mergedOutput.validationScore * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Validation Details */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
            {task.mergedOutput.validationDetails.map((detail, i) => (
              <div key={i} className="bg-swarm-surface border border-swarm-border rounded-lg p-2">
                <div className="text-[10px] text-swarm-muted uppercase tracking-wider">{detail.criterion.replace(/_/g, ' ')}</div>
                <div className={`text-sm font-mono font-semibold ${detail.passed ? 'text-green-400' : 'text-amber-400'}`}>
                  {(detail.score * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>

          <div className="bg-swarm-bg border border-swarm-border rounded-lg p-4 max-h-64 overflow-y-auto">
            <pre className="text-xs text-swarm-text/80 whitespace-pre-wrap font-mono leading-relaxed">
              {task.mergedOutput.finalOutput}
            </pre>
          </div>
          <div className="flex gap-3 mt-2 text-xs text-swarm-muted">
            <span>Strategy: {task.mergedOutput.mergeStrategy.replace(/_/g, ' ')}</span>
            <span>Contributing: {task.mergedOutput.contributingAgents.length} agents</span>
            <span>Merged: {new Date(task.mergedOutput.mergedAt).toLocaleTimeString()}</span>
          </div>
        </div>
      )}

      {/* Score Breakdown */}
      {scored.length > 0 && (
        <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-swarm-text mb-3">Score Breakdown</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-swarm-muted border-b border-swarm-border">
                  <th className="text-left py-2 px-2">Rank</th>
                  <th className="text-left py-2 px-2">Agent</th>
                  <th className="text-right py-2 px-2">Confidence</th>
                  <th className="text-right py-2 px-2">Speed</th>
                  <th className="text-right py-2 px-2">Reliability</th>
                  <th className="text-right py-2 px-2">Final Score</th>
                </tr>
              </thead>
              <tbody>
                {scored.map((s) => (
                  <tr key={s.id} className="border-b border-swarm-border/30 hover:bg-swarm-surface/50">
                    <td className="py-2 px-2">
                      <span className={`font-mono font-bold ${s.rank <= 3 ? 'text-swarm-warning' : 'text-swarm-muted'}`}>
                        #{s.rank}
                      </span>
                    </td>
                    <td className="py-2 px-2 font-mono text-swarm-text">{s.agentId.slice(0, 10)}</td>
                    <td className="py-2 px-2 text-right font-mono text-swarm-cyan">
                      {(s.scoreBreakdown.rawConfidence * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2 text-right font-mono text-swarm-purple">
                      {(s.scoreBreakdown.rawSpeedScore * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2 text-right font-mono text-swarm-success">
                      {(s.scoreBreakdown.rawReliability * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2 text-right font-mono font-bold text-swarm-accent">
                      {(s.finalScore * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}