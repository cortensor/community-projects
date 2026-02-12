'use client';

import React, { useState } from 'react';
import { Task } from '@/types';
import StatusBadge from './StatusBadge';

interface TaskCardProps {
  task: Task;
  onSelect: (taskId: string) => void;
  isSelected: boolean;
}

const PIPELINE_STAGES: Array<{ key: string; label: string }> = [
  { key: 'pending', label: 'Queued' },
  { key: 'splitting', label: 'Split' },
  { key: 'spawning_agents', label: 'Spawn' },
  { key: 'inference_running', label: 'Infer' },
  { key: 'scoring', label: 'Score' },
  { key: 'merging', label: 'Merge' },
  { key: 'distributing_rewards', label: 'Reward' },
  { key: 'completed', label: 'Done' },
];

function getStageIndex(status: string): number {
  const idx = PIPELINE_STAGES.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : 0;
}

export default function TaskCard({ task, onSelect, isSelected }: TaskCardProps) {
  const stageIdx = getStageIndex(task.status);
  const elapsed = task.completedAt
    ? ((task.completedAt - task.createdAt) / 1000).toFixed(1)
    : ((Date.now() - task.createdAt) / 1000).toFixed(0);

  return (
    <div
      onClick={() => onSelect(task.id)}
      className={`bg-swarm-card border rounded-xl p-4 cursor-pointer transition-all duration-300 animate-fade-in ${
        isSelected
          ? 'border-swarm-accent/60 ring-1 ring-swarm-accent/20 shadow-lg shadow-blue-900/20'
          : 'border-swarm-border hover:border-swarm-accent/30'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-swarm-text truncate">{task.title}</h3>
          <p className="text-xs text-swarm-muted mt-0.5 truncate">{task.description}</p>
        </div>
        <StatusBadge status={task.status} />
      </div>

      {/* Pipeline progress bar */}
      <div className="flex items-center gap-0.5 my-3">
        {PIPELINE_STAGES.map((stage, i) => {
          const isActive = i === stageIdx && task.status !== 'completed' && task.status !== 'failed';
          const isComplete = i < stageIdx || task.status === 'completed';
          const isFailed = task.status === 'failed';

          return (
            <div key={stage.key} className="flex-1 flex flex-col items-center">
              <div
                className={`w-full h-1.5 rounded-full transition-all duration-500 ${
                  isFailed && i <= stageIdx
                    ? 'bg-red-500/60'
                    : isComplete
                    ? 'bg-swarm-accent'
                    : isActive
                    ? 'bg-swarm-accent/60 animate-pulse'
                    : 'bg-swarm-border'
                }`}
              />
              <span className={`text-[9px] mt-1 ${isComplete || isActive ? 'text-swarm-accent' : 'text-swarm-muted/50'}`}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-xs text-swarm-muted">
        <div className="flex gap-3">
          <span>{task.swarmSize} agents</span>
          <span>{task.subtasks.length} subtasks</span>
        </div>
        <span className="font-mono">{elapsed}s</span>
      </div>

      {task.mergedOutput && (
        <div className={`mt-2 flex items-center gap-2 text-xs ${task.mergedOutput.validationPassed ? 'text-green-400' : 'text-amber-400'}`}>
          <span>{task.mergedOutput.validationPassed ? '\u2713 Validated' : '\u26A0 Validation issues'}</span>
          <span className="text-swarm-muted">score: {(task.mergedOutput.validationScore * 100).toFixed(1)}%</span>
          <span className="text-swarm-muted">strategy: {task.mergedOutput.mergeStrategy.replace(/_/g, ' ')}</span>
        </div>
      )}
    </div>
  );
}