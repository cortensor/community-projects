import { useState } from 'react';
import { Code, Eye, RefreshCw } from 'lucide-react';
import { analyzeEndpointResponse } from '../utils/dataParser';

interface ApiExplorerProps {
  endpoints: string[];
  baseUrl: string;
}

export default function ApiExplorer({ endpoints, baseUrl }: ApiExplorerProps) {
  const [selectedEndpoint, setSelectedEndpoint] = useState(endpoints[0]);
  const [response, setResponse] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchEndpoint = async (endpoint: string) => {
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${baseUrl}${endpoint}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      setResponse(data);
      
      const analyzed = analyzeEndpointResponse(endpoint, data);
      setAnalysis(analyzed);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch endpoint');
      setResponse(null);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-3">
        <select
          value={selectedEndpoint}
          onChange={(e) => setSelectedEndpoint(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          {endpoints.map((endpoint) => (
            <option key={endpoint} value={endpoint}>
              {endpoint}
            </option>
          ))}
        </select>
        
        <button
          onClick={() => fetchEndpoint(selectedEndpoint)}
          disabled={loading}
          className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Fetch</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {analysis && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Eye className="w-4 h-4 text-gray-600" />
            <h4 className="font-semibold text-gray-900">Analysis</h4>
          </div>
          
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Data Type:</span>
              <span className="font-mono text-gray-900">{analysis.dataType}</span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Fields:</span>
              <span className="font-mono text-gray-900">{analysis.fields.length}</span>
            </div>
            
            {analysis.insights.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-gray-600 mb-2">Insights:</p>
                <ul className="space-y-1">
                  {analysis.insights.map((insight: string, idx: number) => (
                    <li key={idx} className="text-gray-700 text-xs">• {insight}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {response && (
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Code className="w-4 h-4 text-gray-400" />
            <h4 className="font-semibold text-white">Response</h4>
          </div>
          
          <pre className="text-xs text-gray-300 overflow-auto max-h-96">
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
