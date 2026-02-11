'use client';

import React, { useState } from 'react';
import MetricsPanel from '@/components/MetricsPanel';
import TaskSubmitForm from '@/components/TaskSubmitForm';
import TaskCard from '@/components/TaskCard';
import AgentSwarmView from '@/components/AgentSwarmView';
import Leaderboard from '@/components/Leaderboard';
import LedgerHistory from '@/components/LedgerHistory';
import EventFeed from '@/components/EventFeed';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSwarmData } from '@/hooks/useSwarmData';

export default function DashboardPage() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const { connected, events } = useWebSocket(() => {
    swarmData.refresh();
  });
  const swarmData = useSwarmData(2500);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-swarm-border bg-swarm-surface/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-swarm-accent to-swarm-purple rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold text-swarm-text tracking-tight">Fractal Inference Swarms</h1>
              <p className="text-[10px] text-swarm-muted font-mono tracking-wider uppercase">AI Orchestration Control Plane</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span className="text-swarm-muted font-mono">{connected ? 'WS LIVE' : 'WS DOWN'}</span>
            </div>
            <div className="text-xs text-swarm-muted font-mono hidden md:block">
              v1.0.0 | x402 Protocol
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 py-4 space-y-4">
        {/* Error Banner */}
        {swarmData.error && (
          <div className="bg-red-900/20 border border-red-800/40 rounded-xl p-3 text-red-400 text-sm flex items-center justify-between">
            <span>Backend connection error: {swarmData.error}</span>
            <button onClick={swarmData.refresh} className="text-xs px-3 py-1 bg-red-800/30 rounded-lg hover:bg-red-800/50 transition-colors">
              Retry
            </button>
          </div>
        )}

        {/* Metrics */}
        <MetricsPanel metrics={swarmData.metrics} connected={connected} />

        {/* Task Submit */}
        <TaskSubmitForm onSubmitted={swarmData.refresh} />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Task List */}
          <div className="lg:col-span-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-swarm-text">
                Swarm Sessions
                {swarmData.tasks.length > 0 && (
                  <span className="text-swarm-muted ml-2 font-normal">({swarmData.tasks.length})</span>
                )}
              </h2>
            </div>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {swarmData.loading && swarmData.tasks.length === 0 ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="bg-swarm-card border border-swarm-border rounded-xl p-4 animate-pulse">
                      <div className="h-4 bg-swarm-border rounded w-3/4 mb-2" />
                      <div className="h-3 bg-swarm-border rounded w-full mb-3" />
                      <div className="h-2 bg-swarm-border rounded w-full" />
                    </div>
                  ))}
                </div>
              ) : swarmData.tasks.length === 0 ? (
                <div className="bg-swarm-card border border-swarm-border rounded-xl p-8 text-center">
                  <div className="text-3xl mb-2">&#x1F9E0;</div>
                  <div className="text-swarm-muted text-sm">No tasks yet</div>
                  <div className="text-swarm-muted text-xs mt-1">Submit a task above to deploy a swarm</div>
                </div>
              ) : (
                swarmData.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onSelect={setSelectedTaskId}
                    isSelected={selectedTaskId === task.id}
                  />
                ))
              )}
            </div>
          </div>

          {/* Detail View */}
          <div className="lg:col-span-8 space-y-4">
            {selectedTaskId ? (
              <AgentSwarmView taskId={selectedTaskId} />
            ) : (
              <div className="bg-swarm-card border border-swarm-border rounded-xl p-12 text-center">
                <div className="text-4xl mb-3 opacity-50">&#x1F50D;</div>
                <div className="text-swarm-muted text-sm">Select a task to view swarm details</div>
                <div className="text-swarm-muted text-xs mt-1">Agent status, scoring, merge output, and reward distribution</div>
              </div>
            )}

            {/* Bottom panels: Leaderboard + Event Feed */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Leaderboard ledger={swarmData.ledger} />
              <EventFeed events={events} />
            </div>

            {/* Ledger History */}
            <LedgerHistory transactions={swarmData.ledger} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-swarm-border mt-8 py-4">
        <div className="max-w-[1600px] mx-auto px-4 flex items-center justify-between text-xs text-swarm-muted font-mono">
          <span>Fractal Inference Swarms v1.0.0</span>
          <span>x402 Micropayment Protocol | WebSocket Real-Time | Modular Agent Architecture</span>
        </div>
      </footer>
    </div>
  );
}