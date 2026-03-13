import { useEffect, useState } from 'react';
import { Settings, Database, Globe, Zap } from 'lucide-react';
import ApiExplorer from '../components/ApiExplorer';
import { fetchConfig, discoverEndpoints } from '../services/cortensorApi';
import type { ConfigData } from '../types/cortensor';

export default function ConfigTab() {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [endpoints, setEndpoints] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [data, discoveredEndpoints] = await Promise.all([
        fetchConfig(),
        discoverEndpoints(),
      ]);
      
      if (data) setConfig(data);
      setEndpoints(discoveredEndpoints);
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

  const mockConfig = config && Object.keys(config).length > 0 ? config : {
    network_version: '7.0.0',
    chain_endpoint: 'wss://devnet7.cortensor.network',
    block_time: 6000,
    epoch_length: 360,
    max_nodes: 1024,
    min_stake: 1000,
    emission_rate: 0.1,
    consensus_type: 'proof_of_intelligence',
  };

  const renderValue = (value: unknown): string => {
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-1">Network Configuration</h2>
        <p className="text-sm text-gray-500">Current network settings and parameters</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Object.entries(mockConfig).map(([key, value]) => (
          <div key={key} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500 mb-2">
                  {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                </p>
                <p className="text-lg font-semibold text-gray-900 break-all">
                  {renderValue(value)}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Globe className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">API Explorer</h3>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Discover and test Cortensor API endpoints in real-time
        </p>
        <ApiExplorer 
          endpoints={endpoints}
          baseUrl="https://db-be-7.cortensor.network"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Settings className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total Endpoints</p>
              <p className="text-2xl font-semibold text-gray-900">{endpoints.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <Database className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">API Version</p>
              <p className="text-2xl font-semibold text-gray-900">v7.0</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Zap className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Status</p>
              <p className="text-2xl font-semibold text-green-600">Online</p>
            </div>
          </div>
        </div>
      </div>

      {config && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Raw Configuration</h3>
          <pre className="bg-gray-50 rounded-lg p-4 text-xs text-gray-700 overflow-auto max-h-96">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
