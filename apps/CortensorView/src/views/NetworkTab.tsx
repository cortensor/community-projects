import { useEffect, useState } from 'react';
import { Activity, Clock, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import AreaChart from '../components/charts/AreaChart';
import BarChart from '../components/charts/BarChart';
import LineChart from '../components/charts/LineChart';
import { fetchEnhancedNetworkStats } from '../services/cortensorApi';
import type { NetworkStats } from '../types/cortensor';

export default function NetworkTab() {
  const [stats, setStats] = useState<NetworkStats | null>(null);
  const [timeSeriesData, setTimeSeriesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const enhancedStats = await fetchEnhancedNetworkStats();
      if (enhancedStats) {
        setStats(enhancedStats.current);
        setTimeSeriesData(enhancedStats.timeSeries);
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

  const totalRequests = stats?.total_requests ?? timeSeriesData[timeSeriesData.length - 1]?.requests ?? 0;
  const avgLatency = stats?.average_latency ?? timeSeriesData[timeSeriesData.length - 1]?.latency ?? 0;
  const successRate = stats?.success_rate ?? timeSeriesData[timeSeriesData.length - 1]?.successRate ?? 0;
  const inferenceTime = stats?.total_inference_time ?? 0;
  const throughput = timeSeriesData[timeSeriesData.length - 1]?.throughput ?? 0;

  const hourlyData = timeSeriesData.slice(-12).map(d => ({
    hour: d.time,
    requests: d.requests,
    success: Math.floor(d.requests * (d.successRate / 100)),
    failed: Math.floor(d.requests * (1 - d.successRate / 100)),
  }));

  return (
    <div className="space-y-6">
      {/* Hero Section with Curved Background */}
      <div className="relative -mx-8 -mt-8 mb-28">
        {/* Black Background with Curve */}
        <div className="bg-gray-900 pt-8 pb-32 px-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-1">Network Statistics</h2>
            <p className="text-sm text-gray-400">Detailed network performance and health metrics</p>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
              <div className="shadow-xl">
                <MetricCard
                  title="Total Requests"
                  value={totalRequests.toLocaleString()}
                  icon={Activity}
                  change={8}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Success Rate"
                  value={`${successRate.toFixed(1)}%`}
                  icon={CheckCircle}
                  change={3}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Avg Latency"
                  value={`${avgLatency.toFixed(0)}ms`}
                  icon={Clock}
                  change={-2}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Throughput"
                  value={`${(throughput / 1000).toFixed(1)}k/s`}
                  icon={TrendingUp}
                  change={5}
                />
              </div>
              <div className="shadow-xl">
                <MetricCard
                  title="Inference Time"
                  value={`${(inferenceTime / 1000).toFixed(1)}s`}
                  icon={AlertCircle}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Request Distribution</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Inference Requests</span>
              <span className="text-sm font-medium text-gray-900">68%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-gray-900 h-2 rounded-full" style={{ width: '68%' }}></div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Query Requests</span>
              <span className="text-sm font-medium text-gray-900">22%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-gray-700 h-2 rounded-full" style={{ width: '22%' }}></div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">System Requests</span>
              <span className="text-sm font-medium text-gray-900">10%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-gray-500 h-2 rounded-full" style={{ width: '10%' }}></div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time Breakdown</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">Fast (&lt;100ms)</p>
                <p className="text-xs text-gray-500">Optimal response time</p>
              </div>
              <span className="text-lg font-semibold text-gray-900">45%</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">Normal (100-300ms)</p>
                <p className="text-xs text-gray-500">Acceptable range</p>
              </div>
              <span className="text-lg font-semibold text-gray-900">42%</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">Slow (&gt;300ms)</p>
                <p className="text-xs text-gray-500">Needs optimization</p>
              </div>
              <span className="text-lg font-semibold text-gray-900">13%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Request Success vs Failure (12h)</h3>
        <BarChart
          data={hourlyData}
          xAxisKey="hour"
          bars={[
            { dataKey: 'success', fill: '#10b981', name: 'Successful' },
            { dataKey: 'failed', fill: '#ef4444', name: 'Failed' },
          ]}
          height={280}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Multi-Metric Performance</h3>
          <AreaChart
            data={timeSeriesData}
            xAxisKey="time"
            areas={[
              { dataKey: 'successRate', fill: '#10b981', stroke: '#059669', name: 'Success Rate %' },
              { dataKey: 'activeNodes', fill: '#3b82f6', stroke: '#2563eb', name: 'Active Nodes' },
            ]}
            height={280}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Throughput Analysis</h3>
          <LineChart
            data={timeSeriesData}
            xAxisKey="time"
            lines={[
              { dataKey: 'throughput', stroke: '#8b5cf6', name: 'Throughput' },
            ]}
            height={280}
          />
        </div>
      </div>
    </div>
  );
}
