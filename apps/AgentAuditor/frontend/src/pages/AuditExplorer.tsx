import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { 
  Search, 
  Filter, 
  ChevronDown, 
  ChevronUp,
  ExternalLink, 
  Clock, 
  Shield, 
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Copy,
  Check,
  X,
  RefreshCw
} from 'lucide-react'

interface Audit {
  audit_id: string
  agent_id: string
  agent_name?: string
  task_description: string
  confidence_score: number
  poi_similarity: number
  pouw_score: number  // Changed from pouw_mean_score
  ipfs_hash?: string
  created_at: string
  status: string
}

// Update the interface to match the API response
interface AuditListResponse {
  total: number
  audits: Audit[]
}

function Skeleton({ className }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function StatusBadge({ status, score }: { status: string; score: number }) {
  const pct = score * 100
  
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 text-xs font-semibold rounded-full">
        <XCircle className="h-3.5 w-3.5" />
        Failed
      </span>
    )
  }
  
  if (pct >= 80) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs font-semibold rounded-full">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Verified
      </span>
    )
  }
  
  if (pct >= 50) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 text-xs font-semibold rounded-full">
        <AlertTriangle className="h-3.5 w-3.5" />
        Review
      </span>
    )
  }
  
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 text-xs font-semibold rounded-full">
      <XCircle className="h-3.5 w-3.5" />
      Low Trust
    </span>
  )
}

function AuditRow({ audit, index }: { audit: Audit; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getScoreColor = (score: number) => {
    const pct = score * 100
    if (pct >= 80) return 'text-emerald-600 dark:text-emerald-400'
    if (pct >= 60) return 'text-primary-600 dark:text-primary-400'
    if (pct >= 40) return 'text-amber-600 dark:text-amber-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div 
      className="border-b border-slate-200/50 dark:border-dark-700/50 last:border-0 animate-slide-up"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Main Row */}
      <div 
        className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/80 dark:hover:bg-dark-800/50 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand Icon */}
        <button className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
          {expanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </button>

        {/* Agent Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 dark:text-white truncate">
            {audit.agent_name || audit.agent_id}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 truncate">
            {audit.task_description}
          </p>
        </div>

        {/* Status */}
        <StatusBadge status={audit.status} score={audit.confidence_score} />

        {/* Confidence Score */}
        <div className="hidden sm:block text-right min-w-[80px]">
          <div className={`text-lg font-bold ${getScoreColor(audit.confidence_score)}`}>
            {(audit.confidence_score * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">confidence</div>
        </div>

        {/* Time */}
        <div className="hidden md:flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 min-w-[100px]">
          <Clock className="h-4 w-4" />
          {new Date(audit.created_at).toLocaleDateString()}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-6 pb-6 pt-2 bg-slate-50/50 dark:bg-dark-800/30 animate-slide-down">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Scores */}
            <div className="glass-card rounded-xl p-4">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Validation Scores
              </h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-500 dark:text-slate-400">PoI Similarity</span>
                    <span className={`font-semibold ${getScoreColor(audit.poi_similarity)}`}>
                      {(audit.poi_similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-200 dark:bg-dark-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full bg-gradient-to-r ${
                        audit.poi_similarity >= 0.8 ? 'from-emerald-500 to-teal-400' :
                        audit.poi_similarity >= 0.6 ? 'from-primary-500 to-cyan-400' :
                        'from-amber-500 to-yellow-400'
                      }`}
                      style={{ width: `${audit.poi_similarity * 100}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-500 dark:text-slate-400">PoUW Score</span>
                    <span className={`font-semibold ${getScoreColor(audit.pouw_score || 0)}`}>
                      {((audit.pouw_score || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-200 dark:bg-dark-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full bg-gradient-to-r ${
                        (audit.pouw_score || 0) >= 0.8 ? 'from-emerald-500 to-teal-400' :
                        (audit.pouw_score || 0) >= 0.6 ? 'from-primary-500 to-cyan-400' :
                        'from-amber-500 to-yellow-400'
                      }`}
                      style={{ width: `${(audit.pouw_score || 0) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Audit ID */}
            <div className="glass-card rounded-xl p-4">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Audit Details
              </h4>
              <div className="space-y-2">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Audit ID</div>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-dark-700 px-2 py-1 rounded truncate flex-1">
                      {audit.audit_id}
                    </code>
                    <button
                      onClick={(e) => { e.stopPropagation(); copyToClipboard(audit.audit_id) }}
                      className="p-1.5 hover:bg-slate-200 dark:hover:bg-dark-600 rounded transition-colors"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <Copy className="h-4 w-4 text-slate-400" />
                      )}
                    </button>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Agent ID</div>
                  <code className="text-xs text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-dark-700 px-2 py-1 rounded block truncate">
                    {audit.agent_id}
                  </code>
                </div>
              </div>
            </div>

            {/* IPFS Link */}
            <div className="glass-card rounded-xl p-4">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                Evidence Bundle
              </h4>
              {audit.ipfs_hash ? (
                <a
                  href={`https://gateway.pinata.cloud/ipfs/${audit.ipfs_hash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-2 px-4 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-medium rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors"
                >
                  <FileText className="h-4 w-4" />
                  View on IPFS
                  <ExternalLink className="h-4 w-4 ml-auto" />
                </a>
              ) : (
                <div className="flex items-center gap-2 px-4 py-3 bg-slate-100 dark:bg-dark-700 text-slate-500 dark:text-slate-400 rounded-lg">
                  <Shield className="h-4 w-4" />
                  No evidence bundle
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AuditExplorer() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Update the query to handle the correct response structure
  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['audits'],
    queryFn: async () => {
      const response = await axios.get<AuditListResponse>('/api/v1/audits?limit=50')
      return response.data
    },
    retry: false
  })

  // Extract the audits array
  const audits = data?.audits

  const filteredAudits = audits?.filter((audit: Audit) => {
    const matchesSearch = 
      audit.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      audit.task_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (audit.agent_name?.toLowerCase().includes(searchTerm.toLowerCase()))
    
    const matchesStatus = 
      statusFilter === 'all' ||
      (statusFilter === 'verified' && audit.confidence_score >= 0.8) ||
      (statusFilter === 'review' && audit.confidence_score >= 0.5 && audit.confidence_score < 0.8) ||
      (statusFilter === 'low' && audit.confidence_score < 0.5)

    return matchesSearch && matchesStatus
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
          Audit Explorer
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Browse and search all completed agent audits
        </p>
      </div>

      {/* Search & Filters */}
      <div className="glass-card rounded-2xl p-4 mb-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by agent, task, or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 dark:focus:border-primary-500 outline-none transition-all text-slate-900 dark:text-white placeholder-slate-400"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-200 dark:hover:bg-dark-600 rounded-full transition-colors"
              >
                <X className="h-4 w-4 text-slate-400" />
              </button>
            )}
          </div>

          {/* Filter Button */}
          <div className="relative">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`
                flex items-center gap-2 px-4 py-3 rounded-xl border transition-all
                ${filterOpen || statusFilter !== 'all'
                  ? 'bg-primary-500/10 border-primary-500/50 text-primary-600 dark:text-primary-400'
                  : 'bg-slate-50 dark:bg-dark-800 border-slate-200 dark:border-dark-700 text-slate-700 dark:text-slate-300'
                }
              `}
            >
              <Filter className="h-5 w-5" />
              <span className="font-medium">Filter</span>
              {statusFilter !== 'all' && (
                <span className="w-2 h-2 bg-primary-500 rounded-full" />
              )}
            </button>

            {filterOpen && (
              <div className="absolute right-0 mt-2 w-48 glass-card rounded-xl p-2 shadow-xl z-10 animate-slide-down">
                {['all', 'verified', 'review', 'low'].map((status) => (
                  <button
                    key={status}
                    onClick={() => {
                      setStatusFilter(status)
                      setFilterOpen(false)
                    }}
                    className={`
                      w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors
                      ${statusFilter === status
                        ? 'bg-primary-500/10 text-primary-600 dark:text-primary-400'
                        : 'hover:bg-slate-100 dark:hover:bg-dark-700 text-slate-700 dark:text-slate-300'
                      }
                    `}
                  >
                    {status === 'verified' && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                    {status === 'review' && <AlertTriangle className="h-4 w-4 text-amber-500" />}
                    {status === 'low' && <XCircle className="h-4 w-4 text-red-500" />}
                    {status === 'all' && <Shield className="h-4 w-4" />}
                    <span className="capitalize">{status === 'all' ? 'All Audits' : status}</span>
                    {statusFilter === status && <Check className="h-4 w-4 ml-auto" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="flex items-center gap-2 px-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl hover:bg-slate-100 dark:hover:bg-dark-700 transition-colors text-slate-700 dark:text-slate-300"
          >
            <RefreshCw className={`h-5 w-5 ${isRefetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Audits List */}
      <div className="glass-card rounded-2xl overflow-hidden animate-slide-up" style={{ animationDelay: '200ms' }}>
        {isLoading ? (
          <div className="divide-y divide-slate-200/50 dark:divide-dark-700/50">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-4 px-6 py-4">
                <Skeleton className="h-5 w-5 rounded" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-48 rounded" />
                  <Skeleton className="h-3 w-64 mt-2 rounded" />
                </div>
                <Skeleton className="h-6 w-20 rounded-full" />
                <Skeleton className="h-8 w-16 rounded" />
                <Skeleton className="h-4 w-24 rounded" />
              </div>
            ))}
          </div>
        ) : filteredAudits?.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-slate-100 dark:bg-dark-700 rounded-full mb-4">
              <Search className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              No audits found
            </h3>
            <p className="text-slate-500 dark:text-slate-400">
              {searchTerm ? 'Try adjusting your search terms' : 'No audits have been submitted yet'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200/50 dark:divide-dark-700/50">
            {filteredAudits?.map((audit: Audit, index: number) => (
              <AuditRow key={audit.audit_id} audit={audit} index={index} />
            ))}
          </div>
        )}
      </div>

      {/* Results count */}
      {!isLoading && filteredAudits && (
        <div className="mt-4 text-sm text-slate-500 dark:text-slate-400 text-center">
          Showing {filteredAudits.length} of {data?.total || 0} audits
        </div>
      )}
    </div>
  )
}
