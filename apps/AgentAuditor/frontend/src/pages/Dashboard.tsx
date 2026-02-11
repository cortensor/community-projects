import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { TrendingUp, Award, Activity, ArrowUpRight, Shield, Sparkles, ChevronRight, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

// Skeleton loader component
function Skeleton({ className }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

// Stat card component
function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  trend, 
  color, 
  delay = 0 
}: { 
  icon: any; 
  label: string; 
  value: string; 
  trend?: string; 
  color: string;
  delay?: number;
}) {
  return (
    <div 
      className="glass-card rounded-2xl p-6 hover-lift animate-slide-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        {trend && (
          <div className="flex items-center gap-1 px-2 py-1 bg-emerald-500/10 dark:bg-emerald-500/20 rounded-full">
            <ArrowUpRight className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">{trend}</span>
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
      </div>
    </div>
  )
}

// Loading skeleton for stats
function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {[1, 2, 3].map((i) => (
        <div key={i} className="glass-card rounded-2xl p-6">
          <Skeleton className="h-12 w-12 rounded-xl" />
          <Skeleton className="h-4 w-24 mt-4 rounded" />
          <Skeleton className="h-8 w-32 mt-2 rounded" />
        </div>
      ))}
    </div>
  )
}

// Loading skeleton for table
function TableSkeleton() {
  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="px-6 py-5 border-b border-slate-200/50 dark:border-dark-700/50">
        <Skeleton className="h-6 w-32 rounded" />
      </div>
      <div className="divide-y divide-slate-200/50 dark:divide-dark-700/50">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="px-6 py-4 flex items-center gap-4">
            <Skeleton className="h-10 w-10 rounded-full" />
            <div className="flex-1">
              <Skeleton className="h-4 w-32 rounded" />
              <Skeleton className="h-3 w-24 mt-2 rounded" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-2 w-24 rounded-full" />
            <Skeleton className="h-4 w-12 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

// Confidence bar with animation
function ConfidenceBar({ value }: { value: number }) {
  const percentage = value * 100
  const getColor = () => {
    if (percentage >= 80) return 'from-emerald-500 to-teal-400'
    if (percentage >= 60) return 'from-primary-500 to-cyan-400'
    if (percentage >= 40) return 'from-amber-500 to-yellow-400'
    return 'from-red-500 to-orange-400'
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-slate-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${getColor()} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`text-sm font-semibold min-w-[3rem] text-right ${
        percentage >= 80 ? 'text-emerald-600 dark:text-emerald-400' :
        percentage >= 60 ? 'text-primary-600 dark:text-primary-400' :
        percentage >= 40 ? 'text-amber-600 dark:text-amber-400' :
        'text-red-600 dark:text-red-400'
      }`}>
        {percentage.toFixed(1)}%
      </span>
    </div>
  )
}

// Agent row component
function AgentRow({ agent, index }: { agent: any; index: number }) {
  const rankColors = [
    'from-amber-400 to-yellow-500',
    'from-slate-300 to-slate-400',
    'from-amber-600 to-orange-500',
  ]

  return (
    <Link
      to={`/agents/${agent.agent_id}`}
      className="group flex items-center gap-4 px-6 py-4 hover:bg-slate-50/80 dark:hover:bg-dark-800/50 transition-all duration-200 animate-slide-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Rank */}
      <div className={`
        flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm
        ${index < 3 
          ? `bg-gradient-to-br ${rankColors[index]} text-white shadow-lg` 
          : 'bg-slate-100 dark:bg-dark-700 text-slate-500 dark:text-slate-400'
        }
      `}>
        {index + 1}
      </div>

      {/* Agent Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-900 dark:text-white truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
            {agent.name}
          </h3>
          {index === 0 && (
            <Sparkles className="h-4 w-4 text-amber-500" />
          )}
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 truncate font-mono">
          {agent.agent_id?.slice(0, 16)}...
        </p>
      </div>

      {/* Category Badge */}
      <span className={`
        hidden sm:inline-flex px-3 py-1 text-xs font-semibold rounded-full
        ${agent.category === 'trading' ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300' :
          agent.category === 'coding' ? 'bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300' :
          agent.category === 'research' ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300' :
          'bg-slate-100 dark:bg-slate-500/20 text-slate-700 dark:text-slate-300'
        }
      `}>
        {agent.category || 'general'}
      </span>

      {/* Confidence */}
      <div className="hidden md:block w-40">
        <ConfidenceBar value={agent.overall_confidence} />
      </div>

      {/* Audits Count */}
      <div className="hidden sm:flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
        <Shield className="h-4 w-4" />
        <span className="font-medium">{agent.total_audits}</span>
      </div>

      {/* Arrow */}
      <ChevronRight className="h-5 w-5 text-slate-400 dark:text-slate-500 group-hover:text-primary-500 group-hover:translate-x-1 transition-all" />
    </Link>
  )
}

export default function Dashboard() {
  const { data: agents, isLoading, isError } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/agents?limit=10')
      return response.data
    }
  })

  const totalAgents = agents?.length || 0
  const totalAudits = agents?.reduce((sum: number, a: any) => sum + (a.total_audits || 0), 0) || 0
  const avgConfidence = agents?.length 
    ? ((agents.reduce((sum: number, a: any) => sum + (a.overall_confidence || 0), 0) / agents.length) * 100).toFixed(1) + '%'
    : '0%'

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
              Trust Dashboard
            </h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              Monitor and verify AI agent performance across the Cortensor network
            </p>
          </div>
          <Link
            to="/submit"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-purple-600 text-white font-semibold rounded-xl shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 hover:-translate-y-0.5 transition-all duration-200"
          >
            <Zap className="h-5 w-5" />
            New Audit
          </Link>
        </div>
      </div>

      {/* Stats Overview */}
      {isLoading ? (
        <StatsSkeleton />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard
            icon={Award}
            label="Total Agents"
            value={totalAgents.toString()}
            trend="+12%"
            color="from-primary-500 to-cyan-500"
            delay={0}
          />
          <StatCard
            icon={Activity}
            label="Audits Completed"
            value={totalAudits.toString()}
            trend="+24%"
            color="from-emerald-500 to-teal-500"
            delay={100}
          />
          <StatCard
            icon={TrendingUp}
            label="Avg Confidence"
            value={avgConfidence}
            trend="+5%"
            color="from-purple-500 to-pink-500"
            delay={200}
          />
        </div>
      )}

      {/* Agent Leaderboard */}
      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-500/20 rounded-full mb-4">
            <Shield className="h-8 w-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            Failed to load agents
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            Please check your connection and try again
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-slate-100 dark:bg-dark-700 text-slate-700 dark:text-slate-300 font-medium rounded-lg hover:bg-slate-200 dark:hover:bg-dark-600 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="glass-card rounded-2xl overflow-hidden animate-slide-up" style={{ animationDelay: '300ms' }}>
          <div className="px-6 py-5 border-b border-slate-200/50 dark:border-dark-700/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-500/10 dark:bg-primary-500/20 rounded-lg">
                <Award className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Top Agents
              </h2>
            </div>
            <Link
              to="/agents"
              className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
            >
              View All
            </Link>
          </div>
          
          {agents?.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-slate-100 dark:bg-dark-700 rounded-full mb-4">
                <Shield className="h-8 w-8 text-slate-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                No agents yet
              </h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                Submit your first audit to get started
              </p>
              <Link
                to="/submit"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white font-medium rounded-lg hover:bg-primary-600 transition-colors"
              >
                <Zap className="h-4 w-4" />
                Submit Audit
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-200/50 dark:divide-dark-700/50">
              {agents?.map((agent: any, index: number) => (
                <AgentRow key={agent.agent_id} agent={agent} index={index} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
