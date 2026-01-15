import { useEffect, useState } from 'react';
import { Activity, Zap, Server, TrendingUp, Network, Cpu, Database } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import AreaChart from '../components/charts/AreaChart';
import LineChart from '../components/charts/LineChart';
import PieChart from '../components/charts/PieChart';
import NetworkTopology from '../components/NetworkTopology';
import { fetchEnhancedNetworkStats, fetchNodes, analyzeNodePerformance } from '../services/cortensorApi';
import type { NodeData } from '../types/cortensor';

export default function OverviewTab() {
  const [timeSeriesData, setTimeSeriesData] = useState<any[]>([]);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentStats, setCurrentStats] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [enhancedStats, nodesData] = await Promise.all([
        fetchEnhancedNetworkStats(),
        fetchNodes(),
      ]);

      if (enhancedStats) {
        setTimeSeriesData(enhancedStats.timeSeries);
        setCurrentStats(enhancedStats.current);
      }
      
      if (nodesData) {
        setNodes(nodesData);
        setPerformanceData(analyzeNodePerformance(nodesData));
      }
      
      setLoading(false);
    }

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const activeNodes = nodes.filter(n => n.status === 'active').length || nodes.length;
  const totalRequests = currentStats?.total_requests ?? timeSeriesData[timeSeriesData.length - 1]?.requests ?? 0;
  const avgLatency = currentStats?.average_latency ?? timeSeriesData[timeSeriesData.length - 1]?.latency ?? 0;
  const successRate = currentStats?.success_rate ?? timeSeriesData[timeSeriesData.length - 1]?.successRate ?? 0;

  const requestDistribution = [
    { name: 'Inference', value: 68 },
    { name: 'Query', value: 22 },
    { name: 'System', value: 10 },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Section with Curved Background */}
      <div className="relative -mx-8 -mt-8 mb-28">
        {/* Black Background with Curve */}
        <div className="bg-gray-900 pt-8 pb-32 px-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-1">Network Overview</h2>
            <p className="text-sm text-gray-400">Real-time insights into the Cortensor inference network</p>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="shadow-xl">
                <MetricCard
                  title="Active Nodes"
                  value={activeNodes.toLocaleString()}
                  icon={Server}
                  change={5}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Total Requests"
                  value={totalRequests.toLocaleString()}
                  icon={Activity}
                  change={12}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Avg Latency"
                  value={`${avgLatency.toFixed(0)}ms`}
                  icon={Zap}
                  subtitle="Response time"
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Success Rate"
                  value={`${successRate.toFixed(1)}%`}
                  icon={TrendingUp}
                  change={2}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Network Activity (24h)</h3>
            <Activity className="w-5 h-5 text-gray-400" />
          </div>
          <AreaChart
            data={timeSeriesData}
            xAxisKey="time"
            areas={[
              { dataKey: 'requests', fill: '#3b82f6', stroke: '#2563eb', name: 'Requests' },
            ]}
            height={250}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Latency Trends</h3>
            <Zap className="w-5 h-5 text-gray-400" />
          </div>
          <LineChart
            data={timeSeriesData}
            xAxisKey="time"
            lines={[
              { dataKey: 'latency', stroke: '#10b981', name: 'Latency (ms)' },
            ]}
            height={250}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Request Distribution</h3>
            <Database className="w-5 h-5 text-gray-400" />
          </div>
          <PieChart
            data={requestDistribution}
            colors={['#3b82f6', '#10b981', '#f59e0b']}
            height={260}
            innerRadius={50}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Node Performance</h3>
            <Cpu className="w-5 h-5 text-gray-400" />
          </div>
          <PieChart
            data={performanceData}
            colors={['#10b981', '#3b82f6', '#f59e0b', '#ef4444']}
            height={260}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Network Health</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Inference Capacity</span>
                <span className="font-medium text-gray-900">87%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500" style={{ width: '87%' }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Network Load</span>
                <span className="font-medium text-gray-900">64%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-gradient-to-r from-green-500 to-green-600 h-2 rounded-full transition-all duration-500" style={{ width: '64%' }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Node Availability</span>
                <span className="font-medium text-gray-900">92%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-500" style={{ width: '92%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Network Topology</h3>
          <Network className="w-5 h-5 text-gray-400" />
        </div>
        <NetworkTopology nodes={nodes} height={400} />
      </div>
    </div>
  );
}
