'use client';

import React, { useState } from 'react';
import { Activity, Database, Layers, Terminal, AlertCircle, Network, Home } from 'lucide-react';
import Link from 'next/link';
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
    <div className="min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden">
      
      {/* Animated Background */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#111_1px,transparent_1px),linear-gradient(to_bottom,#111_1px,transparent_1px)] bg-[size:3rem_3rem] opacity-10 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 pointer-events-none" />
      
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/90 backdrop-blur-xl">
        <div className="h-16 max-w-[2000px] mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30 group-hover:shadow-blue-500/50 transition-all duration-300">
                <Network className="w-5 h-5 text-white" />
              </div>
              <h1 className="font-bold text-xl text-white group-hover:text-blue-400 transition-colors">Fractal Console</h1>
            </Link>
            <div className="h-8 w-px bg-white/20" />
            <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20">
              <span className="text-xs font-mono text-blue-400 font-bold">ORD</span>
              <span className="text-xs font-mono text-gray-400">MAINNET</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2.5 text-xs px-4 py-2 rounded-full border font-mono font-semibold transition-all ${connected ? 'border-green-500/30 bg-green-500/10 text-green-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span>{connected ? 'SYSTEM ONLINE' : 'DISCONNECTED'}</span>
            </div>
            <Link href="/" className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all text-sm font-medium text-gray-300 hover:text-white">
              <Home className="w-4 h-4" />
              <span className="hidden md:inline">Home</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-[2000px] mx-auto px-6 py-6">
        
        {/* Error State */}
        {swarmData.error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-2xl p-5 flex items-center justify-between">
            <div className="flex items-center gap-3 text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm font-medium">Connection Failure: {swarmData.error}</span>
            </div>
            <button onClick={swarmData.refresh} className="text-xs px-5 py-2.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl transition-all font-mono font-semibold whitespace-nowrap">
              RECONNECT
            </button>
          </div>
        )}

        {/* Metrics Panel - Full Width */}
        <div className="mb-6">
          <MetricsPanel metrics={swarmData.metrics} connected={connected} />
        </div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Task Registry */}
          <div className="lg:col-span-3 order-1">
            <div className="bg-gradient-to-br from-white/[0.07] to-white/[0.03] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[600px] flex flex-col">
              <div className="p-5 border-b border-white/10 bg-white/5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-blue-500/20 rounded-xl">
                      <Layers className="w-4 h-4 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white">Task Queue</h3>
                      <p className="text-xs text-gray-500 font-mono mt-0.5">Active threads</p>
                    </div>
                  </div>
                  <div className="px-3 py-1.5 rounded-full bg-blue-500/20 border border-blue-500/30">
                    <span className="text-xs font-mono text-blue-400 font-bold">{swarmData.tasks.length}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
                {swarmData.loading && swarmData.tasks.length === 0 ? (
                  <div className="p-6 text-center">
                    <div className="inline-flex items-center gap-2 text-blue-400/70 text-xs font-mono">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
                      LOADING_REGISTRY...
                    </div>
                  </div>
                ) : swarmData.tasks.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-gray-600 p-8 text-center">
                    <Database className="w-16 h-16 mb-4 opacity-20" />
                    <span className="text-sm font-semibold text-gray-500">No active threads</span>
                    <span className="text-xs text-gray-600 mt-2 font-mono">Deploy a swarm to begin</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {swarmData.tasks.map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onSelect={setSelectedTaskId}
                        isSelected={selectedTaskId === task.id}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Center Column: Main Visualizer */}
          <div className="lg:col-span-6 order-2 space-y-6">
            {/* Main Swarm View */}
            <div className="bg-gradient-to-br from-white/[0.07] to-white/[0.03] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[400px] relative">
              {selectedTaskId ? (
                <AgentSwarmView taskId={selectedTaskId} />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5" />
                  <Activity className="w-24 h-24 mb-6 stroke-[0.5] text-white/10" />
                  <h3 className="text-2xl font-bold text-gray-600 mb-3">Awaiting Selection</h3>
                  <div className="px-5 py-2.5 rounded-xl bg-white/5 border border-white/10">
                    <p className="text-sm font-mono text-gray-500">SELECT_TASK_ID FROM REGISTRY</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* System Logs */}
            <div className="bg-gradient-to-br from-white/[0.07] to-white/[0.03] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[250px] flex flex-col">
              <div className="px-5 py-3.5 border-b border-white/10 bg-white/5 flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Terminal className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">System Logs</h3>
                  <p className="text-[10px] text-gray-500 font-mono mt-0.5">Real-time event stream</p>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <EventFeed events={events} />
              </div>
            </div>

            {/* Submit Task Form - Moved Below */}
            <div>
              <TaskSubmitForm onSubmitted={swarmData.refresh} />
            </div>
          </div>

          {/* Right Column: Stats */}
          <div className="lg:col-span-3 order-3 space-y-6">
            {/* Leaderboard */}
            <div className="bg-gradient-to-br from-white/[0.07] to-white/[0.03] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[500px] flex flex-col">
              <div className="p-5 border-b border-white/10 bg-white/5">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-yellow-500/20 rounded-xl">
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-400"></div>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">Leaderboard</h3>
                    <p className="text-xs text-gray-500 font-mono mt-0.5">Top performers</p>
                  </div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                <Leaderboard ledger={swarmData.ledger} />
              </div>
            </div>

            {/* x402 Ledger */}
            <div className="bg-gradient-to-br from-white/[0.07] to-white/[0.03] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-2xl h-[420px] flex flex-col">
              <div className="p-5 border-b border-white/10 bg-white/5">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-green-500/20 rounded-xl">
                    <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">x402 Ledger</h3>
                    <p className="text-xs text-gray-500 font-mono mt-0.5">Transaction history</p>
                  </div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                <LedgerHistory transactions={swarmData.ledger} />
              </div>
            </div>
          </div>

        </div>
      </main>

      {/* Custom Scrollbar Styles */}
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.03);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(96, 165, 250, 0.3);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(96, 165, 250, 0.5);
        }
        
        /* Prevent text overflow */
        * {
          word-wrap: break-word;
          overflow-wrap: break-word;
        }
      `}</style>
    </div>
  );
}