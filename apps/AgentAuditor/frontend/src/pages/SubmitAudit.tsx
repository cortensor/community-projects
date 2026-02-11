import { useState } from 'react'
import axios from 'axios'
import { 
  Send, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  Bot, 
  FileText, 
  Tag, 
  Sparkles,
  Shield,
  ExternalLink,
  Copy,
  Check,
  ArrowRight,
  Zap
} from 'lucide-react'

interface AuditResult {
  audit_id: string
  agent_id: string
  status: string
  confidence_score: number | null
  poi_similarity: number | null
  pouw_mean_score: number | null
  ipfs_hash: string | null
  error?: string
}

const categories = [
  { value: 'general', label: 'General', icon: '🤖', desc: 'General purpose AI tasks' },
  { value: 'code', label: 'Code', icon: '💻', desc: 'Programming & development' },
  { value: 'content', label: 'Content', icon: '📝', desc: 'Writing & content creation' },
  { value: 'reasoning', label: 'Reasoning', icon: '🧠', desc: 'Logic & problem solving' },
]

function ScoreBar({ label, value, color }: { label: string; value: number | null; color: string }) {
  const percentage = (value || 0) * 100
  const displayValue = isNaN(percentage) ? 0 : percentage
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-slate-700 dark:text-slate-300">{label}</span>
        <span className={`font-bold ${color}`}>{displayValue.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-slate-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-1000 ease-out bg-gradient-to-r ${
            displayValue >= 80 ? 'from-emerald-500 to-teal-400' :
            displayValue >= 60 ? 'from-primary-500 to-cyan-400' :
            displayValue >= 40 ? 'from-amber-500 to-yellow-400' :
            'from-red-500 to-orange-400'
          }`}
          style={{ width: `${displayValue}%` }}
        />
      </div>
    </div>
  )
}

export default function SubmitAudit() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AuditResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [step, setStep] = useState(0)
  const [formData, setFormData] = useState({
    agent_id: '',
    agent_name: '',
    task_description: '',
    task_input: '',
    category: 'general'
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    setStep(1)

    // Simulate progress steps
    const stepInterval = setInterval(() => {
      setStep(prev => prev < 4 ? prev + 1 : prev)
    }, 2000)

    try {
      const response = await axios.post('/api/v1/audit', formData, {
        timeout: 600000 // 10 minute timeout
      })
      
      const data = response.data
      
      // Check if audit failed
      if (data.status === 'failed' || data.error) {
        throw new Error(data.error || 'Audit failed')
      }
      
      setResult(data)
      setStep(5)
    } catch (err: any) {
      console.error('Audit failed:', err)
      const errorMessage = err.response?.data?.error || err.response?.data?.detail || err.message || 'Audit failed. Please try again.'
      setError(errorMessage)
      setStep(0)
    } finally {
      clearInterval(stepInterval)
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const steps = [
    { label: 'Initializing', icon: Zap },
    { label: 'Running PoI Validation', icon: Shield },
    { label: 'Running PoUW Scoring', icon: Sparkles },
    { label: 'Generating Evidence', icon: FileText },
    { label: 'Complete', icon: CheckCircle2 },
  ]

  const getScoreColor = (score: number | null) => {
    if (score === null || isNaN(score)) return 'text-slate-400'
    const pct = score * 100
    if (pct >= 80) return 'text-emerald-600 dark:text-emerald-400'
    if (pct >= 60) return 'text-primary-600 dark:text-primary-400'
    if (pct >= 40) return 'text-amber-600 dark:text-amber-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
          Submit New Audit
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Validate an AI agent's output using Proof of Inference and Proof of Useful Work
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="glass-card rounded-2xl p-6 space-y-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
            {/* Agent ID */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                <Bot className="h-4 w-4 text-primary-500" />
                Agent ID
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.agent_id}
                onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 dark:focus:border-primary-500 outline-none transition-all text-slate-900 dark:text-white placeholder-slate-400"
                placeholder="agent-code-assistant"
              />
            </div>

            {/* Agent Name */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                <Tag className="h-4 w-4 text-primary-500" />
                Agent Name
              </label>
              <input
                type="text"
                value={formData.agent_name}
                onChange={(e) => setFormData({ ...formData, agent_name: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 dark:focus:border-primary-500 outline-none transition-all text-slate-900 dark:text-white placeholder-slate-400"
                placeholder="Code Assistant"
              />
            </div>

            {/* Task Description */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                <FileText className="h-4 w-4 text-primary-500" />
                Task Description
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.task_description}
                onChange={(e) => setFormData({ ...formData, task_description: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 dark:focus:border-primary-500 outline-none transition-all text-slate-900 dark:text-white placeholder-slate-400"
                placeholder="Write ONLY a Python function named is_prime(n)"
              />
            </div>

            {/* Task Input */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                <Sparkles className="h-4 w-4 text-primary-500" />
                Task Input
                <span className="text-red-500">*</span>
              </label>
              <textarea
                required
                rows={5}
                value={formData.task_input}
                onChange={(e) => setFormData({ ...formData, task_input: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-dark-800 border border-slate-200 dark:border-dark-700 rounded-xl focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 dark:focus:border-primary-500 outline-none transition-all text-slate-900 dark:text-white placeholder-slate-400 resize-none"
                placeholder="17"
              />
            </div>

            {/* Category */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Category
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {categories.map((cat) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, category: cat.value })}
                    className={`
                      relative p-4 rounded-xl border-2 transition-all duration-200
                      ${formData.category === cat.value
                        ? 'border-primary-500 bg-primary-500/10 dark:bg-primary-500/20'
                        : 'border-slate-200 dark:border-dark-700 hover:border-slate-300 dark:hover:border-dark-600 bg-slate-50 dark:bg-dark-800'
                      }
                    `}
                  >
                    <div className="text-2xl mb-2">{cat.icon}</div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">
                      {cat.label}
                    </div>
                    {formData.category === cat.value && (
                      <div className="absolute top-2 right-2">
                        <Check className="h-4 w-4 text-primary-500" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl animate-slide-up">
                <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-red-700 dark:text-red-400">Audit Failed</h4>
                  <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-primary-500 to-purple-600 text-white font-semibold rounded-xl shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-lg transition-all duration-200"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Processing Audit...
                </>
              ) : (
                <>
                  <Send className="h-5 w-5" />
                  Submit Audit
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Sidebar - Progress / Result */}
        <div className="lg:col-span-1">
          {/* Progress Steps */}
          {loading && (
            <div className="glass-card rounded-2xl p-6 animate-slide-up">
              <h3 className="font-semibold text-slate-900 dark:text-white mb-6">
                Audit Progress
              </h3>
              <div className="space-y-4">
                {steps.map((s, index) => {
                  const Icon = s.icon
                  const isActive = index + 1 === step
                  const isComplete = index + 1 < step
                  return (
                    <div key={index} className="flex items-center gap-3">
                      <div className={`
                        flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300
                        ${isComplete 
                          ? 'bg-emerald-500 text-white' 
                          : isActive 
                            ? 'bg-primary-500 text-white animate-pulse' 
                            : 'bg-slate-200 dark:bg-dark-700 text-slate-400'
                        }
                      `}>
                        {isComplete ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </div>
                      <span className={`
                        text-sm font-medium transition-colors
                        ${isComplete || isActive ? 'text-slate-900 dark:text-white' : 'text-slate-400 dark:text-slate-500'}
                      `}>
                        {s.label}
                      </span>
                      {isActive && (
                        <Loader2 className="h-4 w-4 text-primary-500 animate-spin ml-auto" />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Result */}
          {result && result.status === 'completed' && (
            <div className="glass-card rounded-2xl p-6 animate-slide-up">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-emerald-500/10 dark:bg-emerald-500/20 rounded-lg">
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 dark:text-white">
                    Audit Complete!
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Verification successful
                  </p>
                </div>
              </div>

              {/* Overall Score */}
              <div className="mb-6 p-4 bg-gradient-to-br from-primary-500/10 to-purple-500/10 dark:from-primary-500/20 dark:to-purple-500/20 rounded-xl border border-primary-500/20">
                <div className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">
                  Confidence Score
                </div>
                <div className={`text-4xl font-bold ${getScoreColor(result.confidence_score)}`}>
                  {((result.confidence_score || 0) * 100).toFixed(1)}%
                </div>
              </div>

              {/* Detailed Scores */}
              <div className="space-y-4 mb-6">
                <ScoreBar 
                  label="PoI Similarity" 
                  value={result.poi_similarity}
                  color={getScoreColor(result.poi_similarity)}
                />
                <ScoreBar 
                  label="PoUW Score" 
                  value={result.pouw_mean_score}
                  color={getScoreColor(result.pouw_mean_score)}
                />
              </div>

              {/* Audit ID */}
              <div className="p-3 bg-slate-50 dark:bg-dark-800 rounded-lg mb-3">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Audit ID
                </div>
                <div className="flex items-center justify-between gap-2">
                  <code className="text-xs text-slate-700 dark:text-slate-300 truncate">
                    {result.audit_id}
                  </code>
                  <button
                    onClick={() => copyToClipboard(result.audit_id)}
                    className="p-1.5 hover:bg-slate-200 dark:hover:bg-dark-700 rounded transition-colors"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Copy className="h-4 w-4 text-slate-400" />
                    )}
                  </button>
                </div>
              </div>

              {/* IPFS Link */}
              {result.ipfs_hash && (
                <a
                  href={`https://gateway.pinata.cloud/ipfs/${result.ipfs_hash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full p-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-medium rounded-xl hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  View on IPFS
                </a>
              )}
            </div>
          )}

          {/* Info Card */}
          {!loading && !result && (
            <div className="glass-card rounded-2xl p-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
                How it works
              </h3>
              <ul className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
                <li className="flex items-start gap-2">
                  <Shield className="h-4 w-4 text-primary-500 mt-0.5 flex-shrink-0" />
                  <span><strong className="text-slate-900 dark:text-white">PoI:</strong> Validates inference by comparing outputs from multiple nodes</span>
                </li>
                <li className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" />
                  <span><strong className="text-slate-900 dark:text-white">PoUW:</strong> Scores output quality using validator models</span>
                </li>
                <li className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span><strong className="text-slate-900 dark:text-white">Evidence:</strong> Cryptographically signed and stored on IPFS</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
