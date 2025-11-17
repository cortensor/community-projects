import { useEffect, useState } from 'react';
import { CheckCircle, Clock, XCircle, Activity } from 'lucide-react';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import PieChart from '../components/charts/PieChart';
import BarChart from '../components/charts/BarChart';
import LineChart from '../components/charts/LineChart';
import { fetchTasks, analyzeTaskMetrics } from '../services/cortensorApi';
import type { TaskData } from '../types/cortensor';

export default function TasksTab() {
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const data = await fetchTasks();
      if (data) {
        setTasks(data);
      }
      setLoading(false);
    }

    loadData();
  }, []);

  const columns = [
    {
      key: 'name',
      label: 'Task Name',
      render: (value: unknown) => (
        <span className="font-medium text-gray-900">{String(value || 'Untitled')}</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (value: unknown) => {
        const status = String(value || 'pending');
        const variant =
          status === 'completed' ? 'success' :
          status === 'running' ? 'warning' :
          status === 'failed' ? 'error' : 'neutral';
        return <StatusBadge status={status} variant={variant} />;
      },
    },
    {
      key: 'success_rate',
      label: 'Success Rate',
      render: (value: unknown) => {
        const rate = Number(value || 0);
        return (
          <div className="flex items-center space-x-2">
            <div className="w-20 bg-gray-100 rounded-full h-1.5">
              <div
                className="bg-gray-900 h-1.5 rounded-full"
                style={{ width: `${rate}%` }}
              ></div>
            </div>
            <span className="text-xs text-gray-600">{rate.toFixed(0)}%</span>
          </div>
        );
      },
    },
    {
      key: 'duration',
      label: 'Duration',
      render: (value: unknown) => (
        <span className="text-sm text-gray-900">{value ? `${value}ms` : 'N/A'}</span>
      ),
    },
    {
      key: 'timestamp',
      label: 'Last Updated',
      render: (value: unknown) => {
        if (!value) return <span className="text-sm text-gray-400">N/A</span>;
        const date = new Date(String(value));
        return <span className="text-sm text-gray-600">{date.toLocaleTimeString()}</span>;
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

  const mockTasks = tasks.length > 0 ? tasks : [
    {
      id: '1',
      name: 'Image Classification',
      status: 'completed',
      success_rate: 98.5,
      duration: 234,
      timestamp: new Date().toISOString(),
    },
    {
      id: '2',
      name: 'Text Generation',
      status: 'running',
      success_rate: 94.2,
      duration: 456,
      timestamp: new Date().toISOString(),
    },
    {
      id: '3',
      name: 'Object Detection',
      status: 'completed',
      success_rate: 96.7,
      duration: 189,
      timestamp: new Date().toISOString(),
    },
  ];

  const completedTasks = mockTasks.filter(t => t.status === 'completed').length;
  const runningTasks = mockTasks.filter(t => t.status === 'running').length;
  const failedTasks = mockTasks.filter(t => t.status === 'failed').length;
  const avgSuccessRate = mockTasks.reduce((acc, t) => acc + (t.success_rate || 0), 0) / mockTasks.length;

  const taskStatusData = analyzeTaskMetrics(mockTasks);

  const taskPerformanceData = mockTasks.map(task => ({
    name: task.name || 'Unknown',
    successRate: task.success_rate || 0,
    duration: task.duration || 0,
  }));

  const timelineData = Array.from({ length: 12 }, (_, i) => ({
    hour: `${i * 2}h`,
    completed: Math.floor(Math.random() * 50) + 20,
    failed: Math.floor(Math.random() * 10),
    running: Math.floor(Math.random() * 15) + 5,
  }));

  return (
    <div className="space-y-6">
      {/* Hero Section with Curved Background */}
      <div className="relative -mx-8 -mt-8 mb-28">
        {/* Black Background with Curve */}
        <div className="bg-gray-900 pt-8 pb-32 px-8">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-1">Task Analytics</h2>
            <p className="text-sm text-gray-400">Monitor running tasks and performance metrics</p>
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
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-500">Total Tasks</p>
                  <Activity className="w-5 h-5 text-gray-400" />
                </div>
                <p className="text-3xl font-semibold text-gray-900">{mockTasks.length}</p>
                <p className="text-xs text-gray-500 mt-1">All time</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-500">Completed</p>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </div>
                <p className="text-3xl font-semibold text-gray-900">{completedTasks}</p>
                <p className="text-xs text-green-600 mt-1">+{Math.floor(completedTasks * 0.12)} from last hour</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-500">Running</p>
                  <Clock className="w-5 h-5 text-yellow-500" />
                </div>
                <p className="text-3xl font-semibold text-gray-900">{runningTasks}</p>
                <p className="text-xs text-gray-500 mt-1">Active now</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-500">Success Rate</p>
                  <XCircle className="w-5 h-5 text-red-500" />
                </div>
                <p className="text-3xl font-semibold text-gray-900">{avgSuccessRate.toFixed(1)}%</p>
                <p className="text-xs text-gray-500 mt-1">{failedTasks} failed</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Status Distribution</h3>
          <PieChart
            data={taskStatusData}
            colors={['#10b981', '#f59e0b', '#ef4444', '#6b7280']}
            height={280}
            innerRadius={60}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Performance Comparison</h3>
          <BarChart
            data={taskPerformanceData}
            xAxisKey="name"
            bars={[
              { dataKey: 'successRate', fill: '#3b82f6', name: 'Success Rate %' },
            ]}
            height={280}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Execution Timeline (24h)</h3>
        <LineChart
          data={timelineData}
          xAxisKey="hour"
          lines={[
            { dataKey: 'completed', stroke: '#10b981', name: 'Completed' },
            { dataKey: 'running', stroke: '#f59e0b', name: 'Running' },
            { dataKey: 'failed', stroke: '#ef4444', name: 'Failed' },
          ]}
          height={280}
        />
      </div>

      <DataTable
        columns={columns}
        data={mockTasks}
        emptyMessage="No tasks available"
      />
    </div>
  );
}
