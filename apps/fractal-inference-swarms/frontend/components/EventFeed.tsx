'use client';

import React from 'react';
import { SwarmEvent } from '@/types';

interface EventFeedProps {
  events: SwarmEvent[];
}

const EVENT_ICONS: Record<string, string> = {
  'task:created': '\u{1F4CB}',
  'task:splitting': '\u2702\uFE0F',
  'task:subtasks_ready': '\u{1F9E9}',
  'task:agents_spawning': '\u{1F680}',
  'task:inference_started': '\u{1F9E0}',
  'task:inference_complete': '\u2705',
  'task:scoring_started': '\u{1F4CA}',
  'task:scoring_complete': '\u{1F3AF}',
  'task:merging_started': '\u{1F500}',
  'task:merge_complete': '\u{1F4E6}',
  'task:validation_complete': '\u{1F6E1}\uFE0F',
  'task:rewards_distributed': '\u{1FA99}',
  'task:completed': '\u{1F389}',
  'task:failed': '\u274C',
  'agent:spawned': '\u{1F916}',
  'agent:started': '\u25B6\uFE0F',
  'agent:progress': '\u{1F504}',
  'agent:completed': '\u{1F7E2}',
  'agent:failed': '\u{1F534}',
  'reward:distributed': '\u{1F4B0}',
  'metrics:updated': '\u{1F4C8}',
};

const EVENT_COLORS: Record<string, string> = {
  'task:created': 'text-blue-400',
  'task:completed': 'text-green-400',
  'task:failed': 'text-red-400',
  'agent:spawned': 'text-purple-400',
  'agent:completed': 'text-emerald-400',
  'agent:failed': 'text-red-400',
  'task:rewards_distributed': 'text-yellow-400',
  'task:merge_complete': 'text-indigo-400',
  'task:validation_complete': 'text-teal-400',
};

export default function EventFeed({ events }: EventFeedProps) {
  const displayed = events.filter((e) => e.event !== 'agent:progress' && e.event !== 'metrics:updated').slice(0, 40);

  return (
    <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-swarm-text">Live Event Feed</h3>
        <span className="text-[10px] text-swarm-muted font-mono">{events.length} events</span>
      </div>
      <div className="space-y-1 max-h-80 overflow-y-auto pr-1">
        {displayed.length === 0 ? (
          <div className="text-swarm-muted text-sm text-center py-4">Waiting for events...</div>
        ) : (
          displayed.map((event, i) => (
            <div
              key={`${event.timestamp}-${i}`}
              className="flex items-center gap-2 py-1 px-2 rounded hover:bg-swarm-surface/50 transition-colors animate-slide-in text-xs"
            >
              <span className="text-sm flex-shrink-0">{EVENT_ICONS[event.event] || '\u26AA'}</span>
              <span className="font-mono text-swarm-muted text-[10px] flex-shrink-0 w-16">
                {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`font-mono flex-shrink-0 ${EVENT_COLORS[event.event] || 'text-swarm-text'}`}>
                {event.event}
              </span>
              <span className="text-swarm-muted text-[10px] truncate font-mono">
                {event.taskId.slice(0, 8)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}