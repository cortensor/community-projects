'use client';

import { useState, useEffect, useCallback } from 'react';
import { Task, SwarmMetrics, RewardTransaction, SwarmSession } from '@/types';
import * as api from '@/lib/api';

export function useSwarmData(refreshInterval = 3000) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [metrics, setMetrics] = useState<SwarmMetrics | null>(null);
  const [ledger, setLedger] = useState<RewardTransaction[]>([]);
  const [sessions, setSessions] = useState<SwarmSession[]>([]);
  const [paymentStats, setPaymentStats] = useState<Record<string, number>>({});
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [tasksRes, metricsRes, ledgerRes, sessionsRes] = await Promise.all([
        api.getAllTasks(),
        api.getMetrics(),
        api.getLedger(),
        api.getSessions(),
      ]);

      setTasks(tasksRes.tasks);
      setMetrics(metricsRes.swarm);
      setLedger(ledgerRes.transactions);
      setPaymentStats(ledgerRes.paymentStats);
      setBalances(ledgerRes.balances);
      setSessions(sessionsRes.sessions);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [refresh, refreshInterval]);

  return {
    tasks,
    metrics,
    ledger,
    sessions,
    paymentStats,
    balances,
    loading,
    error,
    refresh,
  };
}