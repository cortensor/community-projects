import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  ArrowLeft,
  Shield,
  Award,
  Activity,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  FileText,
  Copy,
  Check,
  Sparkles,
  Bot,
  BarChart3
} from 'lucide-react'
import { useState } from 'react'

function Skeleton({ className }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  subValue, 
  color,
  trend 
}: { 
  icon: any; 
  label: string; 
  value: string; 
  subValue?: string;
  color: string;
  trend?: 'up' | 'down';
}) {
  return (
    <div className="glass-card rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className={`p-2.5 rounded-lg bg-gradient-to-br ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 ${trend === 'up' ? 'text-emerald-500' : 'text-red-500'}`}>
            {trend === 'up' ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          </div>
        )}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
        <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
        {subValue && (
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{subValue}</p>
        )}
      </div>
    </div>
  )
}

function ConfidenceGauge({ value }: { value: number }) {
  const percentage = value * 100
  const circumference = 2 * Math.PI * 45
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  const getColor = () => {
    if (percentage >= 80) return { stroke: '#10b981', text: 'text-emerald-500' }
    if (percentage >= 60) return { stroke: '#0ea5e9', text: 'text-primary-500' }
    if (percentage >= 40) return { stroke: '#f59e0b', text: 'text-amber-500' }
    return { stroke: '#ef4444', text: 'text-red-500' }
  }

  const colors = getColor()

  return (
    <div className="relative w-32 h-32">
      <svg className="w-32 h-32 transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          className="text-slate-200 dark:text-dark-700"
        />
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke={colors.stroke}
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${colors.text}`}>
          {percentage.toFixed(0)}%
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400">confidence</span>
      </div>
    </div>
  )
}

function ReputationChart({ data }: { data: Array<{ date: string; score: number }> }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-500 dark:text-slate-400">
        <div className="text-center">
          <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No reputation history yet</p>
        </div>
      </div>
    )
  }

  const maxScore = Math.max(...data.map(d => d.score))
  const minScore = Math.min(...data.map(d => d.score))
  const range = maxScore - minScore || 1

  return (
    <div className="h-48 flex items-end gap-1">
      {data.map((point, index) => {
        const height = ((point.score - minScore) / range) * 100
        const getBarColor = () => {
          const pct = point.score * 100
          if (pct >= 80) return 'from-emerald-500 to-teal-400'
          if (pct >= 60) return 'from-primary-500 to-cyan-400'
          if (pct >= 40) return 'from-amber-500 to-yellow-400'
          return 'from-red-500 to-orange-400'
        }
        
        return (
          <div 
            key={index} 
            className="flex-1 group relative"
            style={{ minWidth: '8px' }}
          >
            <div
              className={`w-full bg-gradient-to-t ${getBarColor()} rounded-t transition-all duration-500`}
              style={{ 
                height: `${Math.max(height, 10)}%`,
                animationDelay: `${index * 50}ms`
              }}
            />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              {(point.score * 100).toFixed(1)}%
            </div>
          </div>
        )
      })}
    </div>
  )
}

function AuditHistoryItem({ audit, index }: { audit: any; index: number }) {
  const [copied, setCopied] = useState(false)
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getStatusIcon = (score: number) => {
    const pct = score * 100
    if (pct >= 80) return <CheckCircle2 className="h-5 w-5 text-emerald-500" />
    if (pct >= 50) return <AlertTriangle className="h-5 w-5 text-amber-500" />
    return <AlertTriangle className="h-5 w-5 text-red-500" />
  }

  return (
    <div 
      className="flex items-center gap-4 p-4 hover:bg-slate-50/80 dark:hover:bg-dark-800/50 rounded-xl transition-colors animate-slide-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {getStatusIcon(audit.confidence_score)}
      
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 dark:text-white truncate">
          {audit.task_description}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <Clock className="h-3 w-3 text-slate-400" />
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {new Date(audit.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      <div className="text-right">
        <div className={`font-bold ${
          audit.confidence_score >= 0.8 ? 'text-emerald-600 dark:text-emerald-400' :
          audit.confidence_score >= 0.6 ? 'text-primary-600 dark:text-primary-400' :
          'text-amber-600 dark:text-amber-400'
        }`}>
          {(audit.confidence_score * 100).toFixed(1)}%
        </div>
      </div>

      {audit.ipfs_hash && (
        <a
          href={`https://gateway.pinata.cloud/ipfs/${audit.ipfs_hash}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 hover:bg-slate-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
        >
          <ExternalLink className="h-4 w-4 text-slate-400 hover:text-primary-500" />
        </a>
      )}
    </div>
  )
}

export default function AgentProfile() {
  const { agentId } = useParams<{ agentId: string }>()
  const [copied, setCopied] = useState(false)

  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/agents/${agentId}`)
      return response.data
    },
    enabled: !!agentId
  })

  const { data: history } = useQuery({
    queryKey: ['agent-history', agentId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/agents/${agentId}/history`)
      return response.data
    },
    enabled: !!agentId
  })

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (agentLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Skeleton className="h-8 w-48 rounded mb-8" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="glass-card rounded-2xl p-6">
              <Skeleton className="h-32 w-32 rounded-full mx-auto" />
              <Skeleton className="h-6 w-48 mx-auto mt-4 rounded" />
              <Skeleton className="h-4 w-32 mx-auto mt-2 rounded" />
            </div>
          </div>
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="glass-card rounded-xl p-5">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <Skeleton className="h-6 w-16 mt-3 rounded" />
                  <Skeleton className="h-4 w-24 mt-1 rounded" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-slate-100 dark:bg-dark-700 rounded-full mb-4">
            <Bot className="h-8 w-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            Agent Not Found
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            The agent you're looking for doesn't exist or hasn't been audited yet.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white font-medium rounded-lg hover:bg-primary-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const mockReputationData = Array.from({ length: 14 }, (_, i) => ({
    date: new Date(Date.now() - (13 - i) * 24 * 60 * 60 * 1000).toISOString(),
    score: 0.7 + Math.random() * 0.25
  }))

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 mb-6 transition-colors animate-slide-up"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Agent Card */}
        <div className="lg:col-span-1">
          <div className="glass-card rounded-2xl p-6 text-center animate-slide-up" style={{ animationDelay: '100ms' }}>
            {/* Avatar */}
            <div className="relative inline-block">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center shadow-xl shadow-primary-500/25">
                <Bot className="h-12 w-12 text-white" />
              </div>
              {agent.overall_confidence >= 0.8 && (
                <div className="absolute -top-2 -right-2 p-1.5 bg-amber-400 rounded-full shadow-lg">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
              )}
            </div>

            {/* Name */}
            <h1 className="text-xl font-bold text-slate-900 dark:text-white mt-4">
              {agent.name || 'Unnamed Agent'}
            </h1>
            
            {/* Category */}
            <span className={`
              inline-flex px-3 py-1 mt-2 text-xs font-semibold rounded-full
              ${agent.category === 'trading' ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300' :
                agent.category === 'coding' ? 'bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300' :
                agent.category === 'research' ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300' :
                'bg-slate-100 dark:bg-slate-500/20 text-slate-700 dark:text-slate-300'
              }
            `}>
              {agent.category || 'general'}
            </span>

            {/* Agent ID */}
            <div className="mt-4 p-3 bg-slate-50 dark:bg-dark-800 rounded-lg">
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Agent ID</div>
              <div className="flex items-center justify-center gap-2">
                <code className="text-xs text-slate-700 dark:text-slate-300 truncate max-w-[120px]">
                  {agentId}
                </code>
                <button
                  onClick={() => copyToClipboard(agentId || '')}
                  className="p-1 hover:bg-slate-200 dark:hover:bg-dark-700 rounded transition-colors"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-emerald-500" />
                  ) : (
                    <Copy className="h-3 w-3 text-slate-400" />
                  )}
                </button>
              </div>
            </div>

            {/* Confidence Gauge */}
            <div className="mt-6 flex justify-center">
              <ConfidenceGauge value={agent.overall_confidence} />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-4 animate-slide-up" style={{ animationDelay: '200ms' }}>
            <StatCard
              icon={Shield}
              label="Total Audits"
              value={agent.total_audits?.toString() || '0'}
              color="from-primary-500 to-cyan-500"
              trend="up"
            />
            <StatCard
              icon={Activity}
              label="Avg PoI Score"
              value={`${((agent.avg_poi_score || 0) * 100).toFixed(1)}%`}
              color="from-emerald-500 to-teal-500"
            />
            <StatCard
              icon={Award}
              label="Avg PoUW Score"
              value={`${((agent.avg_pouw_score || 0) * 100).toFixed(1)}%`}
              color="from-purple-500 to-pink-500"
            />
            <StatCard
              icon={TrendingUp}
              label="Success Rate"
              value={`${((agent.success_rate || 0.6) * 100).toFixed(0)}%`}
              subValue="last 30 days"
              color="from-amber-500 to-orange-500"
              trend="up"
            />
          </div>

          {/* Reputation History */}
          <div className="glass-card rounded-2xl p-6 animate-slide-up" style={{ animationDelay: '300ms' }}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-500/10 dark:bg-primary-500/20 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Reputation History
                </h2>
              </div>
              <span className="text-sm text-slate-500 dark:text-slate-400">Last 14 days</span>
            </div>
            <ReputationChart data={history || mockReputationData} />
          </div>

          {/* Recent Audits */}
          <div className="glass-card rounded-2xl overflow-hidden animate-slide-up" style={{ animationDelay: '400ms' }}>
            <div className="px-6 py-5 border-b border-slate-200/50 dark:border-dark-700/50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/10 dark:bg-emerald-500/20 rounded-lg">
                  <FileText className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Recent Audits
                </h2>
              </div>
            </div>
            
            <div className="p-2">
              {agent.recent_audits?.length > 0 ? (
                agent.recent_audits.map((audit: any, index: number) => (
                  <AuditHistoryItem key={audit.audit_id} audit={audit} index={index} />
                ))
              ) : (
                <div className="py-8 text-center text-slate-500 dark:text-slate-400">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No audits found for this agent</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
