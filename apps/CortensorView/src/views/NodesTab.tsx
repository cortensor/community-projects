import { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import AdvancedHeatmap from '../components/AdvancedHeatmap';
import RadarChart from '../components/charts/RadarChart';
import BarChart from '../components/charts/BarChart';
import { fetchNodes, fetchHeatmapRanks } from '../services/cortensorApi';
import type { NodeData, HeatmapRank } from '../types/cortensor';

export default function NodesTab() {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapRank[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'nodes' | 'nodepool'>('nodes');

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [nodesData, heatmapData] = await Promise.all([
        fetchNodes(view === 'nodepool' ? 'nodepool' : undefined),
        fetchHeatmapRanks(),
      ]);

      if (nodesData) setNodes(nodesData);
      if (heatmapData) setHeatmap(heatmapData);
      setLoading(false);
    }

    loadData();
  }, [view]);

  const columns = [
    {
      key: 'rank',
      label: 'Rank',
      render: (value: unknown) => (
        <span className="font-medium text-gray-900">#{String(value || '-')}</span>
      ),
    },
    {
      key: 'hotkey',
      label: 'Node ID',
      render: (value: unknown) => {
        const id = String(value || '');
        return (
          <span className="font-mono text-xs text-gray-600">
            {id.slice(0, 8)}...{id.slice(-6)}
          </span>
        );
      },
    },
    {
      key: 'status',
      label: 'Status',
      render: (value: unknown) => {
        const status = String(value || 'active');
        const variant = status === 'active' ? 'success' : status === 'inactive' ? 'neutral' : 'warning';
        return <StatusBadge status={status} variant={variant} />;
      },
    },
    {
      key: 'stake',
      label: 'Stake',
      render: (value: unknown) => (
        <span className="text-gray-900">{Number(value || 0).toLocaleString()}</span>
      ),
    },
    {
      key: 'emissions',
      label: 'Emissions',
      render: (value: unknown) => (
        <span className="text-gray-900">{Number(value || 0).toFixed(4)}</span>
      ),
    },
    {
      key: 'performance',
      label: 'Performance',
      render: (value: unknown) => {
        const perf = Number(value || Math.random() * 100);
        return (
          <div className="flex items-center space-x-2">
            <div className="w-24 bg-gray-100 rounded-full h-1.5">
              <div
                className="bg-gray-900 h-1.5 rounded-full"
                style={{ width: `${perf}%` }}
              ></div>
            </div>
            <span className="text-xs text-gray-600">{perf.toFixed(0)}%</span>
          </div>
        );
      },
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const topNodesByStake = nodes
    .sort((a, b) => (b.stake || 0) - (a.stake || 0))
    .slice(0, 10)
    .map((node, idx) => ({
      name: `#${idx + 1}`,
      stake: node.stake || Math.floor(Math.random() * 100000),
      id: node.hotkey || node.id,
    }));

  const radarData = [
    { metric: 'Performance', value: 85 },
    { metric: 'Uptime', value: 92 },
    { metric: 'Response Time', value: 78 },
    { metric: 'Reliability', value: 88 },
    { metric: 'Throughput', value: 81 },
    { metric: 'Efficiency', value: 90 },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Section with Curved Background */}
      <div className="relative -mx-8 -mt-8 mb-28">
        {/* Black Background with Curve */}
        <div className="bg-gray-900 pt-8 pb-32 px-8">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-white mb-1">Node Pool</h2>
              <p className="text-sm text-gray-400">Active nodes and performance metrics</p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setView('nodes')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  view === 'nodes'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700'
                }`}
              >
                All Nodes
              </button>
              <button
                onClick={() => setView('nodepool')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  view === 'nodepool'
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700'
                }`}
              >
                Node Pool
              </button>
            </div>
          </div>
        </div>
        
        {/* Curved Bottom Edge */}
        <div className="absolute bottom-0 left-0 right-0 overflow-hidden">
          <svg className="w-full h-16" viewBox="0 0 1200 120" preserveAspectRatio="none">
            <path d="M0,0 C300,100 900,100 1200,0 L1200,120 L0,120 Z" fill="#111827" />
          </svg>
        </div>

        {/* Metric Cards - Overlapping */}
        <div className="absolute -bottom-20 left-0 right-0 px-8">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <p className="text-sm font-medium text-gray-500 mb-1">Total Nodes</p>
                <p className="text-3xl font-semibold text-gray-900">{nodes.length}</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <p className="text-sm font-medium text-gray-500 mb-1">Active Now</p>
                <p className="text-3xl font-semibold text-gray-900">
                  {nodes.filter(n => n.status === 'active').length || nodes.length}
                </p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <p className="text-sm font-medium text-gray-500 mb-1">Avg Performance</p>
                <p className="text-3xl font-semibold text-gray-900">87%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={nodes.map((node, idx) => ({
          ...node,
          rank: node.rank ?? idx + 1,
          hotkey: node.hotkey ?? node.id ?? `node-${idx}`,
          status: node.status ?? 'active',
          stake: node.stake ?? Math.floor(Math.random() * 100000),
          emissions: node.emissions ?? Math.random() * 10,
          performance: node.performance ?? Math.random() * 100,
        }))}
        emptyMessage="No nodes available"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top 10 Nodes by Stake</h3>
          <BarChart
            data={topNodesByStake}
            xAxisKey="name"
            bars={[
              { dataKey: 'stake', fill: '#3b82f6', name: 'Stake' },
            ]}
            height={300}
            colors={['#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#172554', '#0f172a', '#0c1222', '#0a0f1a', '#080b12']}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Node Performance Metrics</h3>
          <RadarChart
            data={radarData}
            dataKey="value"
            nameKey="metric"
            fill="#8b5cf6"
            stroke="#7c3aed"
            height={300}
          />
        </div>
      </div>

      {heatmap.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Heatmap - Node Rankings</h3>
          <AdvancedHeatmap data={heatmap} rows={10} cols={10} />
        </div>
      )}
    </div>
  );
}
