import { motion } from 'framer-motion';
import { Link, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useMetrics } from '../hooks/useMetrics';
import { useIncidents } from '../hooks/useIncidents';

export function DashboardContent() {
  const { metrics, isConnected } = useMetrics();
  const { incidents, simulateIncident, isSimulating } = useIncidents();
  const activeIncidents = incidents.filter(i => i.status !== 'resolved');

  const handleSimulate = async (type: string) => {
    toast.loading('Simulating incident...', { id: 'simulate' });
    await simulateIncident(type);
    toast.success('Incident simulated!', { id: 'simulate' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-serif font-bold text-4xl mb-2">Dashboard</h1>
          <p className="text-text-dim">Real-time network monitoring and incident response</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-xl ${isConnected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            <span className="text-sm font-medium">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          label="Latency"
          value={`${metrics?.latency.toFixed(1)}ms`}
          status={metrics && metrics.latency > 200 ? 'critical' : metrics && metrics.latency > 150 ? 'warning' : 'good'}
          icon="⚡"
        />
        <MetricCard
          label="Error Rate"
          value={`${((metrics?.errorRate || 0) * 100).toFixed(2)}%`}
          status={metrics && metrics.errorRate > 0.05 ? 'critical' : metrics && metrics.errorRate > 0.02 ? 'warning' : 'good'}
          icon="🎯"
        />
        <MetricCard
          label="Validator Score"
          value={metrics?.validatorScore.toFixed(3) || '0.000'}
          status={metrics && metrics.validatorScore < 0.7 ? 'critical' : metrics && metrics.validatorScore < 0.85 ? 'warning' : 'good'}
          icon="⭐"
        />
        <MetricCard
          label="Uptime"
          value={`${metrics?.uptime.toFixed(1)}%`}
          status="good"
          icon="📊"
        />
      </div>

      {/* Active Incidents */}
      {activeIncidents.length > 0 && (
        <div className="glass rounded-2xl p-6 border border-app-border">
          <h2 className="font-bold text-xl mb-4">🚨 Active Incidents</h2>
          <div className="space-y-3">
            {activeIncidents.map(incident => (
              <IncidentCard key={incident.id} incident={incident} />
            ))}
          </div>
        </div>
      )}

      {/* Demo Controls */}
      <div className="glass rounded-2xl p-6 border border-app-border">
        <h2 className="font-bold text-xl mb-4">🎬 Demo Mode</h2>
        <p className="text-text-dim mb-4">Simulate incidents to see the full detection and response cycle</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => handleSimulate('high_latency')}
            disabled={isSimulating}
            className="px-4 py-3 bg-orange-50 hover:bg-orange-100 text-orange-700 rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            ⚡ High Latency
          </button>
          <button
            onClick={() => handleSimulate('high_error_rate')}
            disabled={isSimulating}
            className="px-4 py-3 bg-red-50 hover:bg-red-100 text-red-700 rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            🎯 High Error Rate
          </button>
          <button
            onClick={() => handleSimulate('validator_score_drop')}
            disabled={isSimulating}
            className="px-4 py-3 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            ⭐ Validator Drop
          </button>
        </div>
      </div>

      {/* Recent Incidents */}
      <div className="glass rounded-2xl p-6 border border-app-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-xl">Recent Incidents</h2>
          <Link to="/incidents" className="text-accent-indigo hover:underline text-sm font-medium">
            View All →
          </Link>
        </div>
        <div className="space-y-3">
          {incidents.slice(0, 5).map(incident => (
            <IncidentCard key={incident.id} incident={incident} />
          ))}
          {incidents.length === 0 && (
            <p className="text-text-dim text-center py-8">No incidents detected yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, status, icon }: any) {
  const colors = {
    good: 'bg-green-50 border-green-200 text-green-700',
    warning: 'bg-orange-50 border-orange-200 text-orange-700',
    critical: 'bg-red-50 border-red-200 text-red-700'
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass rounded-2xl p-6 border ${colors[status as keyof typeof colors]}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium opacity-70">{label}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </motion.div>
  );
}

function IncidentCard({ incident }: any) {
  const statusColors = {
    detected: 'bg-blue-50 text-blue-700 border-blue-200',
    analyzing: 'bg-purple-50 text-purple-700 border-purple-200',
    confirmed: 'bg-orange-50 text-orange-700 border-orange-200',
    acting: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    resolved: 'bg-green-50 text-green-700 border-green-200'
  };

  const severityIcons = {
    low: '🟢',
    medium: '🟡',
    high: '🟠',
    critical: '🔴'
  };

  return (
    <Link to={`/incidents/${incident.id}`}>
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="glass rounded-xl p-4 border border-app-border hover:border-accent-indigo transition-colors cursor-pointer"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{severityIcons[incident.severity as keyof typeof severityIcons]}</span>
            <div>
              <h3 className="font-medium">{incident.type.replace(/_/g, ' ').toUpperCase()}</h3>
              <p className="text-sm text-text-dim">
                {new Date(incident.detectedAt).toLocaleString()}
              </p>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-lg text-xs font-medium border ${statusColors[incident.status as keyof typeof statusColors]}`}>
            {incident.status}
          </span>
        </div>
      </motion.div>
    </Link>
  );
}

export function IncidentsContent() {
  const { incidents } = useIncidents();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif font-bold text-4xl mb-2">Incidents</h1>
        <p className="text-text-dim">Complete incident history with evidence bundles</p>
      </div>

      <div className="space-y-3">
        {incidents.map(incident => (
          <IncidentCard key={incident.id} incident={incident} />
        ))}
        {incidents.length === 0 && (
          <div className="glass rounded-2xl p-12 border border-app-border text-center">
            <p className="text-text-dim">No incidents recorded yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

export function IncidentDetailContent() {
  const { id } = useParams();
  const { incidents } = useIncidents();
  const incident = incidents.find(i => i.id === id);

  if (!incident) {
    return (
      <div className="glass rounded-2xl p-12 border border-app-border text-center">
        <p className="text-text-dim">Incident not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/incidents" className="text-accent-indigo hover:underline text-sm mb-2 inline-block">
          ← Back to Incidents
        </Link>
        <h1 className="font-serif font-bold text-4xl mb-2">
          {incident.type.replace(/_/g, ' ').toUpperCase()}
        </h1>
        <p className="text-text-dim">{new Date(incident.detectedAt).toLocaleString()}</p>
      </div>

      {/* Metrics Snapshot */}
      <div className="glass rounded-2xl p-6 border border-app-border">
        <h2 className="font-bold text-xl mb-4">📊 Metrics Snapshot</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <p className="text-sm text-text-dim mb-1">Latency</p>
            <p className="text-2xl font-bold">{incident.metrics.latency.toFixed(1)}ms</p>
          </div>
          <div>
            <p className="text-sm text-text-dim mb-1">Error Rate</p>
            <p className="text-2xl font-bold">{(incident.metrics.errorRate * 100).toFixed(2)}%</p>
          </div>
          <div>
            <p className="text-sm text-text-dim mb-1">Validator Score</p>
            <p className="text-2xl font-bold">{incident.metrics.validatorScore.toFixed(3)}</p>
          </div>
          <div>
            <p className="text-sm text-text-dim mb-1">Uptime</p>
            <p className="text-2xl font-bold">{incident.metrics.uptime}%</p>
          </div>
          <div>
            <p className="text-sm text-text-dim mb-1">Requests</p>
            <p className="text-2xl font-bold">{incident.metrics.requestCount}</p>
          </div>
        </div>
      </div>

      {/* Analysis */}
      {incident.analysis && (
        <div className="glass rounded-2xl p-6 border border-app-border">
          <h2 className="font-bold text-xl mb-4">🤖 Cortensor Analysis (PoI)</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-sm text-text-dim">Consensus</p>
                <p className="text-xl font-bold">{incident.analysis.consensus ? '✅ Yes' : '❌ No'}</p>
              </div>
              <div>
                <p className="text-sm text-text-dim">Confidence</p>
                <p className="text-xl font-bold">{(incident.analysis.confidence * 100).toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-sm text-text-dim">Models</p>
                <p className="text-xl font-bold">{incident.analysis.modelOutputs.length}</p>
              </div>
            </div>

            <div>
              <p className="text-sm text-text-dim mb-2">Session IDs</p>
              <div className="flex flex-wrap gap-2">
                {incident.analysis.sessionIds.map((sid: string, i: number) => (
                  <code key={i} className="px-3 py-1 bg-app-hover rounded-lg text-xs font-mono">
                    {sid}
                  </code>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm text-text-dim mb-2">Model Outputs</p>
              <div className="space-y-2">
                {incident.analysis.modelOutputs.map((output: any, i: number) => (
                  <div key={i} className="bg-app-hover rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{output.model}</span>
                      <span className={`px-2 py-1 rounded text-xs ${output.isAnomaly ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                        {output.isAnomaly ? 'Anomaly' : 'Normal'}
                      </span>
                    </div>
                    <p className="text-sm text-text-dim">Confidence: {(output.confidence * 100).toFixed(1)}%</p>
                    <p className="text-sm text-text-dim">Validator Score: {output.validatorScore.toFixed(3)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      {incident.actions.length > 0 && (
        <div className="glass rounded-2xl p-6 border border-app-border">
          <h2 className="font-bold text-xl mb-4">⚡ Actions Taken</h2>
          <div className="space-y-2">
            {incident.actions.map((action: any, i: number) => (
              <div key={i} className="bg-app-hover rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{action.type.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className={`px-2 py-1 rounded text-xs ${action.status === 'executed' ? 'bg-green-100 text-green-700' : action.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
                    {action.status}
                  </span>
                </div>
                <p className="text-sm text-text-dim mt-1">{new Date(action.timestamp).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Bundle */}
      {incident.evidenceBundle && (
        <div className="glass rounded-2xl p-6 border border-app-border">
          <h2 className="font-bold text-xl mb-4">📦 Evidence Bundle</h2>
          <pre className="bg-app-hover rounded-lg p-4 overflow-x-auto text-xs">
            {JSON.stringify(incident.evidenceBundle, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
