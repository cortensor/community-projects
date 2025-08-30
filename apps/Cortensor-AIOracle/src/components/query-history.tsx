'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Clock, CheckCircle, XCircle, AlertTriangle, ExternalLink, ChevronDown, ChevronUp, Globe, Newspaper, Search } from 'lucide-react'
import { sanitizeModelAnswer, truncateAddress } from '@/lib/utils'

interface QueryHistoryProps {
  queries: Array<{
    id: string
    query: string
    answer: string
    confidence: number
    timestamp: number
    verified: boolean
    minerCount?: number
    minerAddresses?: string[]
  miners?: Array<{ index: number; address: string; response: string; inMajority: boolean }>
  consensus?: { totalMiners: number; respondedMiners: number; agreements: number; disagreements: number; confidenceScore: number }
    modelName?: string
    sources?: Array<{
      title: string
      url: string
      reliability: string
      snippet?: string
  publishedAt?: string
      publisher?: string
    }>
  claim?: string
  verdict?: 'True' | 'False' | 'Uncertain'
  label?: 'Positive' | 'Negative' | 'Disputed'
  lastChecked?: string
  methodology?: string
  recommendation?: string
  confidenceExplanation?: string
  machineReadable?: any
  debug?: any
  }>
}

export function QueryHistory({ queries }: QueryHistoryProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  // Extract inline sources ("Sources:") from answer text so we can render them separately
  const extractSourcesFromAnswer = (text: string) => {
    if (!text) return { clean: text, sources: [] as Array<{ title: string; url: string; reliability: string }> }
    let working = text
    const sources: Array<{ title: string; url: string; reliability: string }> = []

    // Normalize URLs and strip trailing punctuation/utm params for better dedupe
    const normalizeUrl = (raw: string) => {
      let u = raw.trim()
      // Strip trailing ), ., , and quotes
      u = u.replace(/[)\]\.,;:'"\s]+$/g, '')
      try {
        const urlObj = new URL(u)
        // Remove common tracking params
        const toDelete: string[] = []
        urlObj.searchParams.forEach((_, k) => {
          if (/^utm_|^ref$|^fbclid$|^gclid$|^mc_cid$|^mc_eid$/i.test(k)) toDelete.push(k)
        })
        toDelete.forEach(k => urlObj.searchParams.delete(k))
        urlObj.hash = ''
        return urlObj.toString()
      } catch {
        return u
      }
    }

    const matchIdx = working.match(/\bSources?\s*:/i)?.index
    if (matchIdx != null) {
      const block = working.slice(matchIdx)
      // Collect URLs: raw URLs and markdown [title](url)
      const mdLinks = Array.from(block.matchAll(/\[([^\]]{1,120})\]\((https?:\/\/[^)\s]+)\)/gi))
      mdLinks.forEach((m) => {
        const title = m[1].trim()
        const url = normalizeUrl(m[2])
        if (!sources.some(s => s.url === url)) sources.push({ title, url, reliability: 'web search' })
      })

      const urlRegex = /https?:\/\/[^\s)]+/gi
      const urls = Array.from(block.matchAll(urlRegex)).map(m => normalizeUrl(m[0]))
      urls.forEach(u => {
        try {
          const urlObj = new URL(u)
          const host = urlObj.hostname.replace(/^www\./, '')
          // try to find a label before the URL like "Title — https://..." or "Title - https://..."
          const esc = u.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          // Look for label patterns in same line
          const lineMatch = block.split(/\r?\n/).find(ln => ln.includes(u)) || ''
          const labelMatch = lineMatch.match(new RegExp(`(?:^|[•*\-\d\)\.]\s*)([A-Za-z0-9 ,.'”"–—\-()/:]{3,120})\s*(?:[—\-:|]\s*)?${esc}`))
          const rawTitle = labelMatch?.[1]?.trim()
          const title = rawTitle && rawTitle.length > 2 ? rawTitle : host
          if (!sources.some(s => s.url === u)) sources.push({ title, url: u, reliability: 'web search' })
        } catch {
          // ignore
        }
      })
      // remove the sources section from the displayed answer
      working = working.slice(0, matchIdx).trim()
    }

    return { clean: working, sources }
  }

  // Score URLs to prefer deep article links
  const deepScore = (u: string) => {
    try {
      const { pathname } = new URL(u)
      const parts = pathname.split('/').filter(Boolean)
      const depth = parts.length
      const hasSlug = parts.some(p => /[a-z0-9-]{6,}/i.test(p))
      const hasDate = /\/(19|20)\d{2}\/\d{1,2}\//.test(pathname)
      return (depth >= 2 ? 2 : depth >= 1 ? 1 : 0) + (hasSlug ? 1 : 0) + (hasDate ? 1 : 0)
    } catch { return 0 }
  }

  // Identify utility/homepage sources that shouldn't compete with real articles
  const isUtilityHomepage = (u: string) => {
    try {
      const url = new URL(u)
      const host = url.hostname.replace(/^www\./, '')
      const path = url.pathname.replace(/\/+$/, '')
      const shallow = path === '' || path === '/' || path === '/en' || path === '/news'
      const utilityHosts = /(coingecko\.com|x-rates\.com|investing\.com|yahoo\.com|ft\.com)$/i
      return shallow && utilityHosts.test(host)
    } catch { return false }
  }

  // Function to format response text as proper HTML
  const formatResponseAsHTML = (text: string) => {
    if (!text) return text
    // Sanitize CoT (<think>) content, then escape HTML to avoid injection
    const escapeHTML = (s: string) => s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
    let formatted = escapeHTML(sanitizeModelAnswer(text))

    // Handle F1 disclaimers with special formatting
    formatted = formatted.replace(/(⚠️.*?Important.*?:.*?F1.*?official.*?sources.*?\.)/, 
      '<div class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"><div class="flex items-start"><div class="flex-shrink-0"><svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg></div><div class="ml-3"><p class="text-sm text-yellow-800 dark:text-yellow-200 font-medium">$1</p></div></div></div>')

  // Emphasize common labels
  formatted = formatted.replace(/\b(Answer|Key Evidence|Verdict|Claim|Recommendation|Methodology):/gi, '<strong class="font-semibold text-gray-900 dark:text-white">$1:</strong>')

  // Convert **bold text** to <strong>
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-900 dark:text-white">$1</strong>')

    // Handle numbered lists with bold headers
    formatted = formatted.replace(/(\d+)\.\s+(\*\*[^*]+\*\*):?\s*/g, (match, num, boldText) => {
      return `<div class="flex items-start mb-4">
        <span class="inline-flex items-center justify-center w-7 h-7 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm font-bold rounded-full mr-3 mt-0.5 flex-shrink-0">${num}</span>
        <div class="flex-1">
          ${boldText.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-900 dark:text-white">$1</strong>')}: `
    })

    // Close the numbered list items at the end of paragraphs
    formatted = formatted.replace(/(<div class="flex items-start mb-4">.*?<div class="flex-1">.*?)(\n\n|\n(?=\d+\.)|$)/g, '$1</div></div>')

    // Omit inline Sources sections (often unreliable in miner responses); show a short note instead
    const sourcesIdx = formatted.search(/Sources:\s*/i)
    if (sourcesIdx >= 0) {
      const before = formatted.slice(0, sourcesIdx)
      // Replace entire sources block with a short note and drop the original list
      formatted = `${before}<em class="text-gray-500">(Miner-provided sources omitted. See curated Sources below.)</em>`
    }

    // Convert simple markdown-style bullets into list items before paragraph handling
    // 1) Turn lines starting with -, *, or • into <li> items (multiline)
    formatted = formatted.replace(/^(?:\-|\*|•)\s+(.+)$/gm, '<li>$1</li>')
    // 2) Wrap consecutive <li> items into a single <ul>
  formatted = formatted.replace(/(?:<li>[\s\S]*?<\/li>\n?)+/g, (match) => {
      const items = match.replace(/\n/g, '')
      return `<ul class="list-disc pl-6 mb-3">${items}</ul>`
    })

    // Handle regular paragraphs (double newlines become new paragraphs)
    formatted = formatted.replace(/\n\n/g, '</p><p class="mb-3">')
    // Single newlines collapse to a space (lists already wrapped above)
    formatted = formatted.replace(/\n/g, ' ')

    // Wrap in paragraph if not already structured
    if (!formatted.includes('<div class="flex items-start')) {
      formatted = `<p class="mb-3">${formatted}</p>`
    }

    // Add proper paragraph wrapping for any remaining text
    formatted = formatted.replace(/^([^<].*?$)/gm, '<p class="mb-3">$1</p>')

    return formatted
  }

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString()
  }

  const getStatusIcon = (verified: boolean, confidence: number, answer: string) => {
    // Check for negative/positive sentiment in answer
    const negativeKeywords = ['not', "don't", "can't", 'no', 'false', 'incorrect', 'wrong', 'failed', 'error', 'impossible', 'unable', 'deny', 'reject']
    const positiveKeywords = ['yes', 'true', 'correct', 'successful', 'possible', 'able', 'confirm', 'verified', 'accurate', 'valid']
    
    // Safeguard against undefined answer
    const answerLower = answer?.toLowerCase() || ''
    const hasNegative = negativeKeywords.some(keyword => answerLower.includes(keyword))
    const hasPositive = positiveKeywords.some(keyword => answerLower.includes(keyword))
    
    // Check if this is an F1 query with disclaimer
    const hasF1Disclaimer = answerLower.includes('f1 race results may not be') || 
                           answerLower.includes('formula 1 sources')
    
    if (hasF1Disclaimer && confidence <= 0.75) {
      return <AlertTriangle className="h-4 w-4 text-yellow-600" />
    } else if (hasNegative && !hasPositive) {
      return <XCircle className="h-4 w-4 text-red-500" />
    } else if (hasPositive && !hasNegative) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    } else if (verified && confidence > 0.8) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    } else if (confidence > 0.6) {
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />
    } else {
      return <XCircle className="h-4 w-4 text-red-500" />
    }
  }

  const getStatusBadge = (verified: boolean, confidence: number, answer: string) => {
    // Check for negative/positive sentiment in answer
    const negativeKeywords = ['not', "don't", "can't", 'no', 'false', 'incorrect', 'wrong', 'failed', 'error', 'impossible', 'unable', 'deny', 'reject']
    const positiveKeywords = ['yes', 'true', 'correct', 'successful', 'possible', 'able', 'confirm', 'verified', 'accurate', 'valid']
    
    // Safeguard against undefined answer
    const answerLower = answer?.toLowerCase() || ''
    const hasNegative = negativeKeywords.some(keyword => answerLower.includes(keyword))
    const hasPositive = positiveKeywords.some(keyword => answerLower.includes(keyword))
    
    // Check if this is an F1 query with disclaimer
    const hasF1Disclaimer = answerLower.includes('f1 race results may not be') || 
                           answerLower.includes('formula 1 sources')
    
    if (hasF1Disclaimer && confidence <= 0.75) {
      return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">Needs Verification</Badge>
    } else if (hasNegative && !hasPositive) {
      return <Badge variant="destructive" className="bg-red-500">Negative</Badge>
    } else if (hasPositive && !hasNegative) {
      return <Badge variant="default" className="bg-green-500">Positive</Badge>
    } else if (verified && confidence > 0.8) {
      return <Badge variant="default" className="bg-green-500">Verified</Badge>
    } else if (confidence > 0.6) {
      return <Badge variant="secondary">Uncertain</Badge>
    } else {
      return <Badge variant="destructive">Disputed</Badge>
    }
  }

  const hasCredibleSources = (sources?: Array<{ title: string; url: string; reliability: string }>) => {
    if (!sources || sources.length === 0) return false
    const factCheckHosts = /(snopes\.com|politifact\.com|factcheck\.org|fullfact\.org|reuters\.com|apnews\.com|leadstories\.com|turnbackhoax\.id|kominfo\.go\.id)/i
    return sources.some(s => /high/i.test(s.reliability) || factCheckHosts.test(s.url))
  }

  // Infer reliability from URL host for sources without strong labels
  const inferReliabilityFromUrl = (url: string): string => {
    try {
      const host = new URL(url).hostname.replace(/^www\./, '')
      const highSet = /(^|\.)((reuters\.com|apnews\.com|bbc\.com|nytimes\.com|wsj\.com|bloomberg\.com|theguardian\.com|ft\.com|nasa\.gov|\.gov|\.go\.id|kominfo\.go\.id|snopes\.com|politifact\.com|factcheck\.org|fullfact\.org|turnbackhoax\.id))$/i
      if (highSet.test(host)) return 'high'
      const newsSet = /(^|\.)((cnn\.com|cnbc\.com|forbes\.com|coindesk\.com|cointelegraph\.com|espn\.com|theverge\.com|wired\.com|aljazeera\.com))$/i
      if (newsSet.test(host)) return 'news'
      return 'web search'
    } catch {
      return 'web search'
    }
  }

  // Sources display component with show/hide functionality
  const SourcesDisplay = ({ sources, queryId }: { sources?: Array<{title: string, url: string, reliability: string, snippet?: string, publishedAt?: string, publisher?: string}>, queryId: string }) => {
  const [showSources, setShowSources] = useState(false)
    const [expandedSource, setExpandedSource] = useState<string | null>(null)
  const [copied, setCopied] = useState<'list' | 'json' | null>(null)

    if (!sources || sources.length === 0) {
      // Hide the entire Sources section when there are no valid sources
      return null
    }

  const getSourceIcon = (reliability: string) => {
      if (reliability.toLowerCase().includes('news')) return <Newspaper className="h-4 w-4 text-blue-600" />
      if (reliability.toLowerCase().includes('web search')) return <Search className="h-4 w-4 text-purple-600" />
      return <Globe className="h-4 w-4 text-green-600" />
    }

    const getReliabilityColor = (reliability: string) => {
      if (reliability.toLowerCase().includes('high')) return 'bg-green-100 text-green-800 border-green-300'
      if (reliability.toLowerCase().includes('medium')) return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      if (reliability.toLowerCase().includes('web search')) return 'bg-purple-100 text-purple-800 border-purple-300'
      return 'bg-blue-100 text-blue-800 border-blue-300'
    }

    const highlightText = (text: string) => {
      // Remove all HTML tags and decode entities
      const stripTags = (s: string) => s.replace(/<[^>]+>/g, '')
      const decodeEntities = (s: string) => s
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
      const plain = decodeEntities(stripTags(text))
      // Highlight key information with background colors
      return plain
        .replace(/(\$[0-9,]+\.?[0-9]*)/g, '<span class="bg-green-100 text-green-800 px-1 py-0.5 rounded font-semibold">$1</span>')
        .replace(/([0-9]+%)/g, '<span class="bg-blue-100 text-blue-800 px-1 py-0.5 rounded font-semibold">$1</span>')
        .replace(/(won|winner|first place|victory|champion)/gi, '<span class="bg-yellow-100 text-yellow-800 px-1 py-0.5 rounded font-semibold">$1</span>')
        .replace(/(breaking|urgent|alert|important)/gi, '<span class="bg-red-100 text-red-800 px-1 py-0.5 rounded font-semibold">$1</span>')
    }

    const getHost = (url: string) => {
      try { return new URL(url).hostname.replace(/^www\./, '') } catch { return 'source' }
    }

    const snippetText = (s?: string) => {
      if (!s) return ''
      const t = s.replace(/<[^>]+>/g, '')
      return t.length > 160 ? `${t.slice(0, 157)}…` : t
    }

    // Determine if a snippet is too generic/low-quality to show as a preview
    const isLowQualitySnippet = (snippet?: string, title?: string, url?: string) => {
      if (!snippet) return true
      const s = snippet.replace(/<[^>]+>/g, '').trim()
      if (!s) return true
      const t = (title || '').trim()
      const lower = s.toLowerCase()
      const lowerTitle = t.toLowerCase()
      // Generic Google News tagline or aggregator phrasing
      const genericPatterns: RegExp[] = [
        /comprehensive\s+up-to-date\s+news\s+coverage[\s\S]*google\s+news/i,
        /aggregated\s+from\s+sources\s+all\s+over\s+the\s+world/i,
        /^google\s+news$/i
      ]
      if (genericPatterns.some(r => r.test(lower))) return true
      // If snippet equals title or mostly repeats it
      if (t && (lower === lowerTitle || (lower.includes(lowerTitle) && lower.length - lowerTitle.length < 10))) return true
      // Too short or not informative (few words)
      const words = s.split(/\s+/).filter(Boolean)
      if (s.length < 40 || words.length < 8) return true
      // From Google News host – often has generic snippet
      try {
        const host = url ? new URL(url).hostname : ''
        if (/news\.google\.com$/i.test(host) || /(^|\.)news\.google\.com$/i.test(host)) return true
      } catch {}
      return false
    }

    // Dedupe: prefer non-news.google.com when titles duplicate; also remove exact duplicate URLs
    const isGoogleNews = (u: string) => /news\.google\.com/i.test(u)
    const seenUrl = new Set<string>()
    const byTitle = new Map<string, number>()
    const prelim = sources.filter(s => {
      const urlKey = s.url
      if (seenUrl.has(urlKey)) return false
      seenUrl.add(urlKey)
      return true
    })
    const filteredSources = prelim.filter((s) => {
      const key = (s.title || '').trim().toLowerCase()
      if (!key) return true
      const prevIdx = byTitle.get(key)
      if (prevIdx === undefined) { byTitle.set(key, prelim.indexOf(s)); return true }
      const prev = prelim[prevIdx]
      // If one is Google News and the other isn't, drop the Google News one
      if (isGoogleNews(prev.url) && !isGoogleNews(s.url)) {
        byTitle.set(key, prelim.indexOf(s))
        return true
      }
      if (!isGoogleNews(prev.url) && isGoogleNews(s.url)) return false
      // Otherwise keep the first
      return false
    })

    // Rank by reliability + deepness + recency, then cap to 5
    const score = (s: { url: string; reliability?: string; publishedAt?: string }) => {
      const rel = (s.reliability || '').toLowerCase()
      const relW = rel.includes('high') ? 2 : rel.includes('news') ? 1.2 : rel.includes('web search') ? 0.5 : 0.8
      const deepW = deepScore(s.url)
      let recency = 0
      if (s.publishedAt) {
        const t = new Date(s.publishedAt).getTime()
        if (Number.isFinite(t)) {
          const days = Math.max(0, (Date.now() - t) / (1000 * 60 * 60 * 24))
          recency = Math.max(0, 1.2 - Math.log10(1 + days))
        }
      }
      return relW + deepW + recency
    }
    const topSources = [...filteredSources].sort((a, b) => score(b) - score(a)).slice(0, 5)

    return (
      <div className="mt-4 border-t pt-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowSources(!showSources)}
          className="mb-3 text-sm"
        >
          {getSourceIcon('news')}
          <span className="ml-2">
            {showSources ? 'Hide Sources' : `Show Sources (${topSources.length})`}
          </span>
          {showSources ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
        </Button>

        {showSources && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  const text = topSources.map(s => `- ${s.title} — ${s.url}`).join('\n')
                  await navigator.clipboard.writeText(text)
                  setCopied('list')
                  setTimeout(() => setCopied(null), 1500)
                }}
                className="text-xs h-7"
              >
                {copied === 'list' ? 'Copied list' : 'Copy sources (list)'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  const payload = topSources.map(({ title, url, reliability, publishedAt, publisher }) => ({ title, url, reliability, publishedAt, publisher }))
                  await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
                  setCopied('json')
                  setTimeout(() => setCopied(null), 1500)
                }}
                className="text-xs h-7"
              >
                {copied === 'json' ? 'Copied JSON' : 'Copy sources (JSON)'}
              </Button>
            </div>
            {/* Detailed cards */}
              {topSources.map((source, index) => (
              <div key={`${queryId}-source-${index}`} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getSourceIcon(source.reliability)}
                    <a 
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-blue-600 hover:text-blue-800 hover:underline flex items-center max-w-md truncate"
                      title={source.title}
                    >
                      {source.title}
                      <ExternalLink className="h-3 w-3 ml-1 flex-shrink-0" />
                    </a>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${getReliabilityColor(source.reliability)}`}
                  >
                    {source.reliability}
                  </Badge>
                </div>
                  {source.publishedAt && (
                    <div className="text-xs text-gray-500 mb-1">Published: {new Date(source.publishedAt).toLocaleDateString()}</div>
                  )}
                
                {!isLowQualitySnippet(source.snippet, source.title, source.url) && (
                  <div className="mt-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedSource(expandedSource === `${queryId}-${index}` ? null : `${queryId}-${index}`)}
                      className="text-xs text-gray-600 hover:text-gray-800 p-0 h-auto"
                    >
                      {expandedSource === `${queryId}-${index}` ? 'Hide Preview' : 'Show Preview'}
                    </Button>
                    
          {expandedSource === `${queryId}-${index}` && source.snippet && (
                      <div 
                        className="mt-2 p-3 bg-white dark:bg-gray-700 rounded border-l-4 border-blue-500 text-sm text-gray-700 dark:text-gray-300"
            dangerouslySetInnerHTML={{ __html: highlightText(source.snippet || '') }}
                      />
                    )}
                  </div>
                )}
                
                <div className="flex items-center justify-between mt-2">
                  <a className="text-xs text-blue-700 dark:text-blue-300 underline truncate max-w-xs" href={source.url} target="_blank" rel="noopener noreferrer" title={source.url}>
                    {source.url}
                  </a>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(source.url, '_blank')}
                    className="text-xs h-6 px-2"
                  >
                    Visit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      await navigator.clipboard.writeText(`- ${source.title} — ${source.url}`)
                      setCopied('list')
                      setTimeout(() => setCopied(null), 1200)
                    }}
                    className="text-xs h-6 px-2 ml-2"
                  >
                    {copied === 'list' ? 'Copied' : 'Copy'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Miner addresses display with show/hide
  const MinersDisplay = ({ minerAddresses, miners, queryId }: { minerAddresses?: string[], miners?: Array<{ index: number; address: string; response: string; inMajority: boolean }>, queryId: string }) => {
    const [showMiners, setShowMiners] = useState(false)
  const [showResponses, setShowResponses] = useState(false)
    const addresses = minerAddresses && minerAddresses.length > 0
      ? minerAddresses
      : (miners || []).map(m => m.address)

    if (!addresses || addresses.length === 0) return null

    return (
      <div className="mt-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowMiners(!showMiners)}
          className="text-xs"
        >
          {showMiners ? 'Hide Miners' : `Show Miners (${addresses.length})`}
          {showMiners ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
        </Button>
        {showMiners && (
          <ul className="mt-2 text-xs text-gray-600 dark:text-gray-300 list-disc list-inside">
            {addresses.map((addr, i) => {
              const minerMeta = (miners || []).find(m => m.address === addr)
              return (
                <li key={`${queryId}-miner-${i}`}>
                  <span className="font-mono">{truncateAddress(addr)}</span>
                  {minerMeta?.inMajority && (
                    <Badge variant="outline" className="ml-2 bg-green-50 text-green-700 border-green-300">Majority</Badge>
                  )}
                </li>
              )
            })}
          </ul>
        )}
        {showMiners && (miners && miners.length > 0) && (
          <div className="mt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowResponses(!showResponses)}
              className="text-xs p-0 h-auto"
            >
              {showResponses ? 'Hide Miner Responses' : 'Show Miner Responses'}
            </Button>
            {showResponses && (
              <div className="mt-2 space-y-3">
                {miners!.map((m, idx) => (
                  <div key={`${queryId}-miner-resp-${idx}`} className="text-sm">
                    <div className="font-mono text-gray-700 dark:text-gray-200">[{m.index+1}] {truncateAddress(m.address)}</div>
                    {m.inMajority && (
                      <div className="text-xs text-green-700 dark:text-green-300 mb-1">Majority</div>
                    )}
                    <div
                      className="text-gray-800 dark:text-gray-100"
                      dangerouslySetInnerHTML={{ __html: formatResponseAsHTML(m.response) }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <Card className="max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Clock className="h-5 w-5 mr-2" />
          Query History
        </CardTitle>
        <CardDescription>
          Recent queries and their verification results
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {queries.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              No queries yet. Ask the Oracle something!
            </p>
          ) : (
            queries.map((query) => {
              const extracted = extractSourcesFromAnswer(query.answer)
              const mergedSourcesRaw = [
                ...(query.sources || []),
                ...extracted.sources.filter(es => !(query.sources || []).some(s => s.url === es.url))
              ]
              // Prefer deep links; drop shallow utility homepages if any deep articles exist
              const hasDeep = mergedSourcesRaw.some(s => deepScore(s.url) >= 2)
              const filtered = hasDeep
                ? mergedSourcesRaw.filter(s => deepScore(s.url) >= 2 || !isUtilityHomepage(s.url))
                : mergedSourcesRaw
              // Fill or escalate reliability for better badges and sort by deepness
              const mergedSources = filtered.map(s => {
                const rel = s.reliability && !/web search/i.test(s.reliability)
                  ? s.reliability
                  : inferReliabilityFromUrl(s.url)
                return { ...s, reliability: rel }
              }).sort((a, b) => deepScore(b.url) - deepScore(a.url))
              return (
              <div 
                key={query.id}
                className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(query.verified, query.confidence, query.answer)}
                    <span className="font-medium">{query.query}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {hasCredibleSources(mergedSources) && (
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">Credible sources</Badge>
                    )}
                    {getStatusBadge(query.verified, query.confidence, query.answer)}
                    <span className="text-sm text-gray-500">
                      {(query.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div 
                  className="text-sm text-gray-600 dark:text-gray-400 mb-2"
                  dangerouslySetInnerHTML={{ __html: formatResponseAsHTML(extracted.clean) }}
                />

                {/* Transparency bar: claim/verdict/lastChecked */}
                {(query.claim || query.verdict || query.lastChecked) && (
                  <div className="text-xs text-gray-600 dark:text-gray-300 mb-2 flex flex-wrap items-center gap-2">
                    {query.claim && <span><strong>Claim:</strong> “{query.claim}”</span>}
                    {query.verdict && <span>• <strong>Verdict:</strong> {query.verdict}</span>}
                    {query.lastChecked && <span>• <strong>Last checked:</strong> {query.lastChecked}</span>}
                  </div>
                )}

                {query.confidenceExplanation && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    <strong>Confidence metric:</strong> {query.confidenceExplanation}
                  </div>
                )}
                
                {/* Miner Information */}
                {(query.minerCount || query.minerAddresses?.length || query.miners?.length) && (
                  <div className="flex items-center space-x-4 text-xs text-gray-500 mb-2">
                    {query.minerCount && (
                      <span className="flex items-center">
                        <span className="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                        {query.minerCount} miners
                      </span>
                    )}
                    {query.consensus && (
                      <span className="flex items-center">
                        <span className="w-2 h-2 bg-yellow-500 rounded-full mr-1"></span>
                        {query.consensus.agreements}/{query.consensus.respondedMiners} agreements
                      </span>
                    )}
                    {query.minerAddresses && query.minerAddresses.length > 0 && (
                      <span className="flex items-center">
                        <span className="w-2 h-2 bg-blue-500 rounded-full mr-1"></span>
                        {query.minerAddresses.length} addresses
                      </span>
                    )}
                    {query.modelName && (
                      <span className="flex items-center">
                        <span className="w-2 h-2 bg-purple-500 rounded-full mr-1"></span>
                        {query.modelName}
                      </span>
                    )}
                  </div>
                )}
                {/* Miner addresses details toggle */}
                <MinersDisplay minerAddresses={query.minerAddresses} miners={query.miners as any} queryId={query.id} />
                

                {/* Sources Display + Info Note */}
                {mergedSources.length > 0 ? (
                  <>
                    <SourcesDisplay sources={mergedSources} queryId={query.id} />
                    {/* Sources stability disclaimer */}
                    <div className="text-xs text-orange-600 dark:text-orange-400 mt-2 bg-orange-50 dark:bg-orange-900/20 p-2 rounded border border-orange-200 dark:border-orange-800">
                      ⚠️ Note: Sources feature is currently in beta. Results may vary in quality and relevance.
                    </div>
                    {/* If this is a claim/hoax query and sources are shown, add a positive note */}
                    {/(is it true|hoax|myth|fact[- ]?check|claim|klaim|benarkah|apakah benar|visible from space|can you see|seen from space|astronaut)/i.test(query.query) && (
                      <div className="text-xs text-green-700 mt-2">Only credible, contextually relevant sources are shown for this claim.</div>
                    )}
                  </>
                ) : (
                  // If this is a claim/hoax query and no sources are shown, add an info note
                  /is it true|hoax|myth|fact[- ]?check|claim|klaim|benarkah|apakah benar|visible from space|can you see|seen from space|astronaut/i.test(query.query) && (
                    <>
                      <div className="text-xs text-yellow-700 mt-2">No credible sources matched this claim, so none are shown.</div>
                      {/* Sources stability disclaimer even when no sources */}
                      <div className="text-xs text-orange-600 dark:text-orange-400 mt-1 bg-orange-50 dark:bg-orange-900/20 p-2 rounded border border-orange-200 dark:border-orange-800">
                        ⚠️ Note: Sources feature is currently in beta. Results may vary in quality and relevance.
                      </div>
                    </>
                  )
                )}
                
                {/* Machine-readable JSON toggle */}
                {query.machineReadable && (
                  <details className="mt-2">
                    <summary className="text-xs text-blue-600 dark:text-blue-300 cursor-pointer">Show machine-readable JSON</summary>
                    <pre className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded text-xs overflow-auto">{JSON.stringify(query.machineReadable, null, 2)}</pre>
                  </details>
                )}

                <p className="text-xs text-gray-400">
                  {formatTime(query.timestamp)}
                </p>
              </div>
              )
            })
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// Debug section removed as requested
