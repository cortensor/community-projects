"use client"

import React, { useState, useEffect, useRef } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Search, Brain, Shield, Users, Clock, Copy, ExternalLink, MessageSquare, RefreshCcw, Shuffle } from 'lucide-react'
import { AppLoading } from '../components/app-loading'
import { ModelSelector } from '../components/model-selector'
import { RealtimeLoading } from '../components/realtime-loading'
import { QueryHistory } from '../components/query-history'
import { AVAILABLE_MODELS, ModelConfig } from '../lib/models'
import type { OracleFact } from '../lib/oracle-facts'
import { Skeleton } from '../components/ui/skeleton'

const USER_ID_STORAGE_KEY = 'ai-oracle-user-id'

function generateUserId(): string {
  const cryptoObj = (typeof globalThis !== 'undefined' && (globalThis as { crypto?: Crypto }).crypto) || undefined
  if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
    return `usr-${cryptoObj.randomUUID().replace(/-/g, '').slice(0, 12)}`
  }
  return `usr-${Math.random().toString(36).slice(2, 12)}`
}

interface QueryResult {
  id: string
  query: string
  answer: string
  confidence: number
  minerCount: number
  sources: Array<{
    title: string
    url: string
    reliability: string
    snippet?: string
    publishedAt?: string
    publisher?: string
  }>
  timestamp: number
  verified: boolean
  currentDate?: string
  modelName?: string
  minerAddresses?: string[]
  miners?: Array<{ index: number; address: string; response: string; inMajority: boolean }>
  consensus?: { totalMiners: number; respondedMiners: number; agreements: number; disagreements: number; confidenceScore: number; majorityAnswer?: 'yes' | 'no' | 'uncertain' }
  clientReference?: string
  debug?: {
    promptType: number
    responseQuality: number
    selectedFromResponses: number
    minerCount: number
    consensusInfo: string
    taskId: string
    minerAddresses: string[]
    sessionId?: string
    clientReference?: string
    confidenceBreakdown: {
      baseConfidence: number
      minerBonus: number
      qualityBonus: number
      temporalBonus: number
      finalConfidence: number
    }
  }
}

interface RandomFact {
  title: string
  url: string
  snippet: string
  reliability: 'high' | 'medium' | 'low' | 'unknown'
  publisher?: string
  publishedAt?: string
  source?: string
  verdict: 'Yes' | 'No'
  question?: string
  answer?: string
}

export default function HomePage() {
  const [isAppLoading, setIsAppLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingComplete, setLoadingComplete] = useState(false)
  const [results, setResults] = useState<QueryResult | null>(null)
  const [queryHistory, setQueryHistory] = useState<QueryResult[]>([])
  const [isHistoryHydrated, setIsHistoryHydrated] = useState(false)
  const [randomFact, setRandomFact] = useState<RandomFact | null>(null)
  const [isRandomFactLoading, setIsRandomFactLoading] = useState(false)
  const [randomFactError, setRandomFactError] = useState('')
  const [factTab, setFactTab] = useState<'random' | 'oracle'>('random')
  const [oracleFacts, setOracleFacts] = useState<OracleFact[]>([])
  const [activeOracleFact, setActiveOracleFact] = useState<OracleFact | null>(null)
  const [isOracleFactsLoading, setIsOracleFactsLoading] = useState(false)
  const [oracleFactsError, setOracleFactsError] = useState('')
  const [showSidePanel, setShowSidePanel] = useState(false)
  const [selectedModel, setSelectedModel] = useState<ModelConfig>(AVAILABLE_MODELS[0])
  const [userId, setUserId] = useState('')
  const [copiedUserId, setCopiedUserId] = useState(false)
  const copyFeedbackTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = localStorage.getItem(USER_ID_STORAGE_KEY)
    if (stored && stored.trim()) {
      setUserId(stored)
      return
    }
    const newId = generateUserId()
    localStorage.setItem(USER_ID_STORAGE_KEY, newId)
    setUserId(newId)
  }, [])

  useEffect(() => {
    return () => {
      if (copyFeedbackTimeout.current) {
        clearTimeout(copyFeedbackTimeout.current)
      }
    }
  }, [])

  useEffect(() => {
    fetchRandomFact()
    fetchOracleFacts()
  }, [])

  useEffect(() => {
    const savedHistory = localStorage.getItem('ai-oracle-history')
    if (savedHistory) {
      try {
        const parsedHistory = JSON.parse(savedHistory)
        setQueryHistory(parsedHistory.slice(0, 10))
      } catch (error) {
        console.error('Error loading query history:', error)
      }
    }
    setIsHistoryHydrated(true)
  }, [])

  useEffect(() => {
    if (queryHistory.length > 0) {
      localStorage.setItem('ai-oracle-history', JSON.stringify(queryHistory))
    }
  }, [queryHistory])

  useEffect(() => {
    const hasVisited = localStorage.getItem('ai-oracle-visited')
    if (hasVisited) {
      setIsAppLoading(false)
    } else {
      const timer = setTimeout(() => {
        setIsAppLoading(false)
        localStorage.setItem('ai-oracle-visited', 'true')
      }, 6000)
      return () => clearTimeout(timer)
    }
  }, [])

  const ensureUserId = () => {
    if (typeof window === 'undefined') return ''
    const stored = localStorage.getItem(USER_ID_STORAGE_KEY)
    if (stored && stored.trim()) {
      if (!userId) setUserId(stored)
      return stored
    }
    const newId = generateUserId()
    localStorage.setItem(USER_ID_STORAGE_KEY, newId)
    setUserId(newId)
    return newId
  }

  const handleCopyUserId = async () => {
    if (!userId) return
    try {
      if (!navigator?.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable')
      }
      await navigator.clipboard.writeText(userId)
      setCopiedUserId(true)
      if (copyFeedbackTimeout.current) clearTimeout(copyFeedbackTimeout.current)
      copyFeedbackTimeout.current = setTimeout(() => setCopiedUserId(false), 1600)
    } catch (err) {
      console.error('Failed to copy user id:', err)
    }
  }

  const fetchRandomFact = async () => {
    try {
      setIsRandomFactLoading(true)
      setRandomFactError('')
      const res = await fetch(`/api/random-fact?ts=${Date.now()}`, { cache: 'no-store' })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || 'Failed to fetch random fact')
      }
      const data = await res.json()
      setRandomFact(data)
    } catch (err) {
      console.error('Random fact fetch failed:', err)
      setRandomFact(null)
      setRandomFactError('Unable to fetch a random fact right now. Please try again.')
    } finally {
      setIsRandomFactLoading(false)
    }
  }

  const fetchOracleFacts = async () => {
    try {
      setIsOracleFactsLoading(true)
      setOracleFactsError('')
      const res = await fetch(`/api/oracle-facts?limit=30`, { cache: 'no-store' })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || 'Failed to fetch oracle facts')
      }
      const data = await res.json()
      const facts = data.data || data || []
      setOracleFacts(facts)
      setActiveOracleFact(facts[0] || null)
    } catch (err) {
      console.error('Oracle facts fetch failed:', err)
      setOracleFactsError('Unable to load oracle facts right now.')
      setOracleFacts([])
      setActiveOracleFact(null)
    } finally {
      setIsOracleFactsLoading(false)
    }
  }

  const shuffleOracleFact = () => {
    if (!oracleFacts.length) return
    const idx = Math.floor(Math.random() * oracleFacts.length)
    setActiveOracleFact(oracleFacts[idx])
  }

  const deriveVerdictFromResult = (result: QueryResult): 'Yes' | 'No' | null => {
    const majority = result.consensus?.majorityAnswer
    if (majority === 'yes') return 'Yes'
    if (majority === 'no') return 'No'

    const lower = (result.answer || '').toLowerCase()
    const hasYes = /\byes\b/.test(lower) || /\btrue\b/.test(lower) || /\bcorrect\b/.test(lower)
    const hasNo = /\bno\b/.test(lower) || /\bfalse\b/.test(lower) || /\bnot\b/.test(lower)
    if (hasYes && !hasNo) return 'Yes'
    if (hasNo && !hasYes) return 'No'
    return null
  }

  const persistOracleFact = async (payload: { query: string; answer: string; verdict: 'Yes' | 'No'; confidence?: number; sources?: QueryResult['sources']; modelName?: string; queryId?: string }) => {
    try {
      await fetch('/api/oracle-facts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      await fetchOracleFacts()
    } catch (err) {
      console.error('Persist oracle fact failed:', err)
    }
  }

  const getHost = (url: string) => {
    try {
      return new URL(url).hostname.replace(/^www\./, '')
    } catch {
      return 'source'
    }
  }

  const formatOracleAnswer = (text: string, maxChars = 380) => {
    if (!text) return ''
    // Drop noisy trailing sources lists from miner answers
    const withoutSources = text.replace(/Sources?:[\s\S]*/i, '').trim()
    const singleSpaced = withoutSources.replace(/\s+/g, ' ')
    if (singleSpaced.length > maxChars) return `${singleSpaced.slice(0, maxChars - 1).trim()}…`
    return singleSpaced
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)
    setLoadingComplete(false)
    setResults(null)

    try {
      const readJsonResponse = async (res: Response) => {
        const contentType = res.headers.get('content-type') || ''
        if (contentType.toLowerCase().includes('application/json')) {
          return await res.json()
        }
        const text = await res.text()
        const snippet = text.replace(/\s+/g, ' ').trim().slice(0, 220)
        throw new Error(
          `API returned non-JSON response (status ${res.status}). ` +
            (snippet ? `Body starts with: ${snippet}` : 'Empty response body')
        )
      }

      const activeUserId = ensureUserId()
      const clientReference = activeUserId ? `user-oracle-${activeUserId.replace(/^usr-/, '')}` : undefined
      // Direct submission - no WebSocket wait
      const response = await fetch('/api/oracle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          sessionId: selectedModel.sessionId,
          modelName: selectedModel.name,
          temperature: selectedModel.temperature,
          topK: selectedModel.topK,
          topP: selectedModel.topP,
          clientReference
        }),
        cache: 'no-store'
      })

      const data = await readJsonResponse(response)
      if (!response.ok) {
        const msg = (data && (data.error || data.message)) || response.statusText || 'Request failed'
        throw new Error(msg)
      }

      const responseData = data.data || data
      const effectiveClientReference = responseData.clientReference || clientReference
      
      // Extract taskId from response and fetch REAL task details
      const taskId = responseData.taskId || responseData.debug?.taskId || responseData.provenance?.taskId
      let realMinerData: any = null
      
      if (taskId) {
        try {
          // Wait 5 seconds before fetching task details to ensure miners have finished
          console.log('Waiting 5 seconds before fetching task details...')
          await new Promise(resolve => setTimeout(resolve, 5000))
          
          // Fetch detailed task information using the taskId
          const taskResponse = await fetch(`/api/tasks/${taskId}`)
          if (taskResponse.ok) {
            realMinerData = await readJsonResponse(taskResponse)
            console.log('Task details fetched:', realMinerData)
          }
        } catch (err) {
          console.log('Could not fetch task details:', err)
        }
      }
      
      // Use REAL data from task details if available
      let minerResponses: string[] = []
      let realMinerAddresses: string[] = []
      let realConsensus: any = null
      
      if (realMinerData?.results) {
        // Extract real miner responses from task details
        minerResponses = Array.isArray(realMinerData.results.data) ? realMinerData.results.data : []
        realMinerAddresses = Array.isArray(realMinerData.results.miners) ? realMinerData.results.miners : []
        console.log('Using REAL miner data:', { responses: minerResponses.length, addresses: realMinerAddresses.length })
        
        // Analyze responses for consensus (Yes/No answers)
        const answers: { [key: string]: number } = {}
        let yesCount = 0
        let noCount = 0
        
        minerResponses.forEach(resp => {
          const normalized = resp.toLowerCase()
          // Check for Yes/No in the answer
          if (/answer:\s*yes/i.test(normalized) || /^yes[,\s]/i.test(normalized)) {
            yesCount++
            answers['yes'] = (answers['yes'] || 0) + 1
          } else if (/answer:\s*no/i.test(normalized) || /^no[,\s]/i.test(normalized)) {
            noCount++
            answers['no'] = (answers['no'] || 0) + 1
          }
        })
        
        // Calculate agreements and disagreements
        const totalMiners = realMinerAddresses.length
        const respondedMiners = minerResponses.length
        const maxAgreements = Math.max(yesCount, noCount, 0)
        const disagreements = respondedMiners - maxAgreements
        const majorityAnswer = yesCount > noCount ? 'yes' : 'no'
        
        realConsensus = {
          totalMiners: realMinerData.assigned_miners?.length || totalMiners,
          respondedMiners,
          agreements: maxAgreements,
          disagreements,
          confidenceScore: respondedMiners > 0 ? maxAgreements / respondedMiners : 0,
          breakdown: { yes: yesCount, no: noCount },
          majorityAnswer
        }
        
        console.log('Real consensus calculated:', realConsensus)
      }
      
      // Build miners array with inMajority flag
      const minersWithConsensus = minerResponses.length > 0 ? minerResponses.map((resp, i) => {
        const normalized = resp.toLowerCase()
        let minerAnswer = 'unknown'
        let inMajority = false
        
        if (/answer:\s*yes/i.test(normalized) || /^yes[,\s]/i.test(normalized)) {
          minerAnswer = 'yes'
        } else if (/answer:\s*no/i.test(normalized) || /^no[,\s]/i.test(normalized)) {
          minerAnswer = 'no'
        }
        
        // Check if this miner agrees with majority
        if (realConsensus?.majorityAnswer) {
          inMajority = minerAnswer === realConsensus.majorityAnswer
        }
        
        return {
          index: i,
          address: realMinerAddresses[i] || '0x0000000000000000000000000000000000000000',
          response: resp,
          inMajority
        }
      }) : (responseData.miners || [])
      
      const newResult: QueryResult = {
        id: Date.now().toString(),
        query,
        answer: responseData.answer || responseData.response || 'No response received',
        confidence: responseData.confidence || 0,
        minerCount: realMinerData?.results?.miners?.length || responseData.minerCount || 0,
        sources: responseData.sources || [],
        timestamp: responseData.timestamp || Date.now(),
        verified: (responseData.confidence || 0) > 0.75,
        modelName: responseData.modelName || selectedModel.name,
        minerAddresses: realMinerAddresses.length > 0 ? realMinerAddresses : (responseData.minerAddresses || responseData.debug?.minerAddresses || []),
        miners: minersWithConsensus,
        consensus: realConsensus || responseData.consensus || undefined,
        clientReference: effectiveClientReference,
        debug: {
          ...responseData.debug,
          realTaskData: realMinerData,
          usingRealData: !!realMinerData,
          realConsensus,
          clientReference: effectiveClientReference
        }
      }

      const derivedVerdict = deriveVerdictFromResult(newResult)
      const isErrorAnswer = (newResult.answer || '').toLowerCase().startsWith('error:')
      if (derivedVerdict && !isErrorAnswer) {
        void persistOracleFact({
          query,
          answer: newResult.answer,
          verdict: derivedVerdict,
          confidence: newResult.confidence,
          sources: newResult.sources,
          modelName: newResult.modelName,
          queryId: taskId || newResult.id
        })
      }
      
      const responded = newResult.consensus?.respondedMiners ?? newResult.minerCount
      const total = newResult.consensus?.totalMiners ?? responded
      const needHold = total > 0 && responded < total
      
      const finalize = () => {
        setResults(newResult)
        setQueryHistory(prev => [newResult, ...prev.slice(0, 9)])
        setQuery('')
        setLoadingComplete(true)
        setTimeout(() => { setIsLoading(false); setLoadingComplete(false) }, 1000)
      }
      
      if (needHold) setTimeout(finalize, 4000)
      else finalize()
      
    } catch (error) {
      console.error('Oracle query failed:', error)
      const errorResult: QueryResult = {
        id: Date.now().toString(),
        query,
        answer: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}. Please try again.`,
        confidence: 0,
        minerCount: 0,
        sources: [],
        timestamp: Date.now(),
        verified: false
      }
      setResults(errorResult)
      setLoadingComplete(true)
      setTimeout(() => { setIsLoading(false); setLoadingComplete(false) }, 1000)
    }
  }

  // Show app loading screen on first visit
  if (isAppLoading) {
    return <AppLoading onLoadComplete={() => setIsAppLoading(false)} />
  }

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 lg:px-6 py-8">
        <div className="space-y-8">
          {/* Header */}
          <header className="relative text-center mb-4">
              {userId && (
                <div className="absolute right-0 top-0 flex items-center space-x-2 rounded-full bg-gray-100/90 px-3 py-1 text-xs text-gray-600 shadow-sm backdrop-blur-sm dark:bg-gray-900/70 dark:text-gray-300">
                  <span className="font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">User ID</span>
                  <span className="font-mono text-gray-900 dark:text-gray-100">{userId}</span>
                  <button
                    type="button"
                    onClick={handleCopyUserId}
                    className="flex items-center text-blue-600 transition hover:text-blue-700 focus:outline-none dark:text-blue-400 dark:hover:text-blue-300"
                    aria-label="Copy user ID"
                  >
                    <Copy className="mr-1 h-3.5 w-3.5" />
                    Copy
                  </button>
                  {copiedUserId && (
                    <span className="font-medium text-green-600 dark:text-green-400">Copied!</span>
                  )}
                </div>
              )}
              <div className="flex items-center justify-center mb-4">
                <Brain className="h-12 w-12 text-blue-600 mr-4" />
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
                  AI Oracle
                </h1>
              </div>
              <p className="text-xl text-gray-600 dark:text-gray-300 mb-2">
                The Truth Machine
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Decentralized Truth Verification Powered by Cortensor Network
              </p>
          </header>

          {/* Side panel toggle aligned above form */}
          <div className="flex justify-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowSidePanel(prev => !prev)}
              className="px-4"
            >
              {showSidePanel ? 'Hide Side Panel' : 'Show Side Panel'}
            </Button>
          </div>

          <div className={`grid gap-6 ${showSidePanel ? 'lg:grid-cols-[minmax(0,1fr)_360px]' : ''}`}>
            <div className="space-y-6">
              <Card className="w-full">
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <CardTitle className="flex items-center">
                        <Search className="h-5 w-5 mr-2" />
                        Ask the Oracle
                      </CardTitle>
                      <CardDescription>
                        Submit your query to get verified answers from multiple AI miners
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="flex space-x-2">
                      <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter your question or claim to verify..."
                        className="flex-1"
                        disabled={isLoading}
                      />
                      <Button 
                        type="submit" 
                        disabled={isLoading || !query.trim()}
                        className="px-8 bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        {isLoading ? (
                          <>
                            <Clock className="h-4 w-4 mr-2 animate-spin" />
                            Verifying...
                          </>
                        ) : (
                          'Verify'
                        )}
                      </Button>
                    </div>
                    
                    {/* Model Selector */}
                    <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                      <div className="flex items-center space-x-2">
                        <Brain className="h-4 w-4 text-gray-500" />
                        <span className="text-sm text-gray-600 font-medium">AI Model:</span>
                      </div>
                      <ModelSelector
                        models={AVAILABLE_MODELS}
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                        disabled={isLoading}
                      />
                    </div>
                  </form>
                </CardContent>
              </Card>

              {/* Loading State */}
              {isLoading && (
                <RealtimeLoading 
                  modelName={selectedModel.displayName} 
                  sessionId={selectedModel.sessionId}
                  forceComplete={loadingComplete}
                  onComplete={() => {
                    // Controlled completion; UI will finalize once we decide
                  }}
                />
              )}

              {/* Results */}
              {results && (
                <div className="w-full">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <MessageSquare className="h-5 w-5 mr-2" />
                    Latest Result
                  </h3>
                  <QueryHistory queries={[results]} />
                </div>
              )}

              {/* Query History */}
              <div className="w-full">
                {!isHistoryHydrated ? (
                  <div className="max-w-4xl mx-auto">
                    <div className="border rounded-lg p-4 space-y-3">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-5/6" />
                      <Skeleton className="h-3 w-2/3" />
                    </div>
                  </div>
                ) : queryHistory.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">No queries yet. Ask the Oracle to see history.</p>
                ) : (
                  <QueryHistory queries={queryHistory} />
                )}
              </div>
            </div>

            {showSidePanel && (
              <aside className="space-y-4 lg:sticky lg:top-6">
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle className="text-base">{factTab === 'random' ? 'Random Fact' : 'Oracle Fact'}</CardTitle>
                        <CardDescription>
                          {factTab === 'random'
                            ? 'Powered by Tavily (no verdict badge)'
                            : 'Facts from user oracle results with Yes/No verdicts'}
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="inline-flex rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
                          <Button
                            type="button"
                            variant={factTab === 'random' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setFactTab('random')}
                            className="rounded-none"
                          >
                            Random
                          </Button>
                          <Button
                            type="button"
                            variant={factTab === 'oracle' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => {
                              setFactTab('oracle')
                              if (!oracleFacts.length && !isOracleFactsLoading) fetchOracleFacts()
                            }}
                            className="rounded-none"
                          >
                            Oracle
                          </Button>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={factTab === 'random' ? fetchRandomFact : (oracleFacts.length ? shuffleOracleFact : fetchOracleFacts)}
                          disabled={factTab === 'random' ? isRandomFactLoading : isOracleFactsLoading}
                          className="h-8 w-8"
                          aria-label={factTab === 'random' ? 'Refresh random fact' : 'Shuffle oracle fact'}
                        >
                          {factTab === 'random' ? (
                            <RefreshCcw className={`h-4 w-4 ${isRandomFactLoading ? 'animate-spin text-blue-600' : 'text-gray-600'}`} />
                          ) : (
                            <Shuffle className={`h-4 w-4 ${isOracleFactsLoading ? 'animate-spin text-blue-600' : 'text-gray-600'}`} />
                          )}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {factTab === 'random' ? (
                      <>
                        {isRandomFactLoading && (
                          <div className="space-y-3 animate-pulse">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                          </div>
                        )}

                        {!isRandomFactLoading && randomFact && (
                          <div className="space-y-2">
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-snug">
                              {randomFact.question || randomFact.title}
                            </p>
                            <div className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed space-y-1">
                              <p className="font-semibold">Answer:</p>
                              <p>{randomFact.answer || randomFact.snippet}</p>
                            </div>
                            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                              <span className="truncate pr-2">{randomFact.publisher || getHost(randomFact.url)}</span>
                              {randomFact.reliability !== 'unknown' && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 border text-gray-700 dark:text-gray-200">
                                  {randomFact.reliability.toUpperCase()}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center justify-between pt-1">
                              <a
                                href={randomFact.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-blue-600 dark:text-blue-400 inline-flex items-center hover:underline"
                              >
                                Open source
                                <ExternalLink className="h-3.5 w-3.5 ml-1" />
                              </a>
                              {randomFact.publishedAt && (
                                <span className="text-xs text-gray-400">{new Date(randomFact.publishedAt).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                        )}

                        {!isRandomFactLoading && randomFactError && (
                          <p className="text-sm text-red-600 dark:text-red-400">{randomFactError}</p>
                        )}

                        {!isRandomFactLoading && !randomFact && !randomFactError && (
                          <p className="text-sm text-gray-600 dark:text-gray-300">No fact available.</p>
                        )}
                      </>
                    ) : (
                      <>
                        {isOracleFactsLoading && (
                          <div className="space-y-3 animate-pulse">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                          </div>
                        )}

                        {!isOracleFactsLoading && activeOracleFact && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-snug">
                                {activeOracleFact.query}
                              </p>
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${activeOracleFact.verdict === 'Yes' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                                {activeOracleFact.verdict.toUpperCase()}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed space-y-1">
                              <p className="font-semibold">Answer:</p>
                              <p>{formatOracleAnswer(activeOracleFact.answer)}</p>
                            </div>
                            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                              <span className="truncate pr-2">{activeOracleFact.modelName || 'Oracle network'}</span>
                              <span className="text-xs text-gray-400">{new Date(activeOracleFact.createdAt).toLocaleDateString()}</span>
                            </div>
                            {activeOracleFact.sources?.length ? (
                              <div className="flex items-center justify-between pt-1">
                                <a
                                  href={activeOracleFact.sources[0].url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-600 dark:text-blue-400 inline-flex items-center hover:underline"
                                >
                                  Open source
                                  <ExternalLink className="h-3.5 w-3.5 ml-1" />
                                </a>
                                <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[140px]">
                                  {activeOracleFact.sources[0].title || getHost(activeOracleFact.sources[0].url)}
                                </span>
                              </div>
                            ) : null}
                          </div>
                        )}

                        {!isOracleFactsLoading && oracleFactsError && (
                          <p className="text-sm text-red-600 dark:text-red-400">{oracleFactsError}</p>
                        )}

                        {!isOracleFactsLoading && !activeOracleFact && !oracleFactsError && (
                          <p className="text-sm text-gray-600 dark:text-gray-300">No oracle facts yet.</p>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>
              </aside>
            )}
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
            <Card>
              <CardHeader>
                <Shield className="h-8 w-8 text-blue-600 mb-2" />
                <CardTitle>Consensus Verification</CardTitle>
                <CardDescription>
                  Multiple independent AI miners verify each query for maximum accuracy
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <Users className="h-8 w-8 text-green-600 mb-2" />
                <CardTitle>Decentralized Network</CardTitle>
                <CardDescription>
                  Powered by distributed miners eliminating single points of failure
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <Brain className="h-8 w-8 text-purple-600 mb-2" />
                <CardTitle>AI-Powered Truth</CardTitle>
                <CardDescription>
                  Advanced AI models work together to provide reliable, fact-checked answers
                </CardDescription>
              </CardHeader>
            </Card>
          </div>

          {/* Footer */}
          <footer className="text-center py-8 border-t border-gray-200 dark:border-gray-700 mt-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Powered by <span className="font-semibold text-blue-600 dark:text-blue-400">Cortensor Network</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Decentralized AI consensus • {process.env.MODEL_NAME || 'GPT OSS 20B'} Model
            </p>
          </footer>
        </div>
      </div>
    </>
  )
}
