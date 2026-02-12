'use client';

import React from 'react';
import { RewardTransaction } from '@/types';

interface LedgerHistoryProps {
  transactions: RewardTransaction[];
}

export default function LedgerHistory({ transactions }: LedgerHistoryProps) {
  const recent = transactions.slice(0, 30);

  if (recent.length === 0) {
    return (
      <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-swarm-text mb-3">x402 Payment Ledger</h3>
        <div className="text-swarm-muted text-sm text-center py-6">No transactions recorded yet.</div>
      </div>
    );
  }

  return (
    <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-swarm-text">x402 Payment Ledger</h3>
        <span className="text-xs text-swarm-muted font-mono">{transactions.length} total transactions</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-swarm-muted border-b border-swarm-border">
              <th className="text-left py-2 px-2">Time</th>
              <th className="text-left py-2 px-2">Agent</th>
              <th className="text-left py-2 px-2">Type</th>
              <th className="text-right py-2 px-2">Score</th>
              <th className="text-right py-2 px-2">Rank</th>
              <th className="text-right py-2 px-2">Tokens</th>
              <th className="text-left py-2 px-2">Payment ID</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((tx) => (
              <tr key={tx.id} className="border-b border-swarm-border/20 hover:bg-swarm-surface/50 transition-colors">
                <td className="py-1.5 px-2 font-mono text-swarm-muted">
                  {new Date(tx.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-1.5 px-2 font-mono text-swarm-text">{tx.agentName}</td>
                <td className="py-1.5 px-2">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      tx.transactionType === 'inference_reward'
                        ? 'bg-green-900/30 text-green-400'
                        : tx.transactionType === 'bonus'
                        ? 'bg-blue-900/30 text-blue-400'
                        : 'bg-red-900/30 text-red-400'
                    }`}
                  >
                    {tx.transactionType.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="py-1.5 px-2 text-right font-mono text-swarm-accent">
                  {(tx.score * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 px-2 text-right font-mono">
                  <span className={tx.rank <= 3 ? 'text-swarm-warning' : 'text-swarm-muted'}>#{tx.rank}</span>
                </td>
                <td className={`py-1.5 px-2 text-right font-mono font-semibold ${tx.tokensEarned > 0 ? 'text-swarm-success' : 'text-swarm-danger'}`}>
                  {tx.tokensEarned > 0 ? '+' : ''}{tx.tokensEarned.toFixed(2)}
                </td>
                <td className="py-1.5 px-2 font-mono text-swarm-muted text-[10px]">
                  {tx.x402PaymentId.slice(0, 12)}...
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}