'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Search, Brain, Shield, Users, CheckCircle, AlertTriangle, Clock, Network, Zap, Copy, ExternalLink, ChevronDown, ChevronUp, MessageSquare, History } from 'lucide-react'
import { AppLoading } from '../components/app-loading'
import { ModelSelector } from '../components/model-selector'
import { RealtimeLoading } from '../components/realtime-loading'
import { QueryHistory } from '../components/query-history'
import { AVAILABLE_MODELS, getModelConfig, ModelConfig } from '../lib/models'
// Defer WS client import to runtime to keep initial chunk light

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
  consensus?: { totalMiners: number; respondedMiners: number; agreements: number; disagreements: number; confidenceScore: number }
  debug?: {
    promptType: number
    responseQuality: number
    selectedFromResponses: number
    minerCount: number
    consensusInfo: string
    taskId: string
    minerAddresses: string[]
    sessionId?: string
    confidenceBreakdown: {
      baseConfidence: number
      minerBonus: number
      qualityBonus: number
      temporalBonus: number
      finalConfidence: number
    }
  }
}

export default function HomePage() {
  const [isAppLoading, setIsAppLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingComplete, setLoadingComplete] = useState(false)
  const [results, setResults] = useState<QueryResult | null>(null)
  const [queryHistory, setQueryHistory] = useState<QueryResult[]>([])
  const [selectedModel, setSelectedModel] = useState<ModelConfig>(AVAILABLE_MODELS[0])
  const wsUnsubRef = useRef<null | (() => void)>(null)
  const wsFinalizedRef = useRef(false)

  // Helper functions for tooltip content
  // Function to format response text as proper HTML
  // Load query history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('ai-oracle-history')
    if (savedHistory) {
      try {
        const parsedHistory = JSON.parse(savedHistory)
        setQueryHistory(parsedHistory.slice(0, 10)) // Keep only last 10 queries
      } catch (error) {
        console.error('Error loading query history:', error)
      }
    }
  }, [])

  // Save query history to localStorage whenever it changes
  useEffect(() => {
    if (queryHistory.length > 0) {
      localStorage.setItem('ai-oracle-history', JSON.stringify(queryHistory))
    }
  }, [queryHistory])

  // Handle app initialization loading
  useEffect(() => {
    // Check if user has visited before
    const hasVisited = localStorage.getItem('ai-oracle-visited')
    
    if (hasVisited) {
      // Skip loading for returning users
      setIsAppLoading(false)
    } else {
      // Show full loading for new users
      const timer = setTimeout(() => {
        setIsAppLoading(false)
        localStorage.setItem('ai-oracle-visited', 'true')
      }, 6000) // 6 seconds for full loading experience

      return () => clearTimeout(timer)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)
    setLoadingComplete(false)
    setResults(null)

    // WebSocket-first: wait for a WS event for this session to finalize
    wsFinalizedRef.current = false
    if (wsUnsubRef.current) { try { wsUnsubRef.current() } catch {} wsUnsubRef.current = null }

    const finalizeWithOracle = async (payload: any) => {
      if (wsFinalizedRef.current) return
      wsFinalizedRef.current = true
      // Try to extract routerText from event payload; otherwise fetch latest task
      let routerText: string | undefined
      const textCandidates = [payload?.text, payload?.router_text, payload?.routerText, payload?.data, typeof payload === 'string' ? payload : undefined]
      for (const t of textCandidates) { if (typeof t === 'string' && t.length > 0) { routerText = t; break } }
      try {
        if (!routerText) {
          const latest = await fetch('/api/tasks/latest')
          if (latest.ok) {
            const latestData = await latest.json()
            const lt = latestData?.text || latestData?.router_text || latestData?.routerText || JSON.stringify(latestData)
            if (typeof lt === 'string') routerText = lt
          }
        }
      } catch {}

      try {
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
            routerText
          })
        })
        const data = await response.json()
        const responseData = data.data || data
        const newResult: QueryResult = {
          id: Date.now().toString(),
          query,
          answer: responseData.answer || responseData.response || 'No response received',
          confidence: responseData.confidence || 0,
          minerCount: responseData.minerCount || (Array.isArray(responseData.miners) ? responseData.miners.length : 0),
          sources: responseData.sources || [],
          timestamp: responseData.timestamp || Date.now(),
          verified: (responseData.confidence || 0) > 0.75,
          modelName: responseData.modelName || selectedModel.name,
          minerAddresses: responseData.minerAddresses || responseData.debug?.minerAddresses || [],
          miners: responseData.miners || [],
          consensus: responseData.consensus || undefined,
          debug: responseData.debug || undefined
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
        if (needHold) setTimeout(finalize, 4000); else finalize()
      } catch (error) {
        console.error('Oracle WS finalize failed:', error)
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
      } finally {
        if (wsUnsubRef.current) { try { wsUnsubRef.current() } catch {} wsUnsubRef.current = null }
      }
    }

    // Subscribe for a single finalize-worthy event for this session
  // Lazy-load WS client to avoid heavy initial chunk
  const { cortensorService } = await import('@/lib/cortensor')
  wsUnsubRef.current = cortensorService.onTaskEvent((evt) => {
      try {
        // Filter to our session id
  const sidRaw = (evt?.session_id ?? evt?.sessionId ?? evt?.session)
  const sidNum = typeof sidRaw === 'string' ? parseInt(sidRaw, 10) : (typeof sidRaw === 'number' ? sidRaw : NaN)
  const selectedSid = typeof selectedModel.sessionId === 'string' ? parseInt(selectedModel.sessionId as any, 10) : (selectedModel.sessionId as any)
  if (Number.isFinite(sidNum) && Number.isFinite(selectedSid) && selectedSid > 0 && sidNum !== selectedSid) return
        const raw = typeof evt === 'string' ? evt : JSON.stringify(evt)
        // Heuristics: look for miner block cues or a commit event
        const looksFinal = /TaskCommitted|Web3 SDK Response|Address:\s*0x/i.test(raw)
        if (looksFinal) {
          finalizeWithOracle(evt)
        }
      } catch {}
    })

    // Fallback: if no WS event arrives in time, do a single REST finalize
    setTimeout(async () => {
      if (wsFinalizedRef.current) return
      try {
        const response = await fetch('/api/oracle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            sessionId: selectedModel.sessionId,
            modelName: selectedModel.name,
            temperature: selectedModel.temperature,
            topK: selectedModel.topK,
            topP: selectedModel.topP
          })
        })
        if (response.ok) {
          const data = await response.json()
          finalizeWithOracle(data)
        }
      } catch {}
    }, 12000)
  }

  // Show app loading screen on first visit
  if (isAppLoading) {
    return <AppLoading onLoadComplete={() => setIsAppLoading(false)} />
  }

  return (
    <>
      <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <header className="text-center mb-12">
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

      {/* Query Form */}
      <Card className="max-w-4xl mx-auto mb-8">
        <CardHeader>
          <CardTitle className="flex items-center">
            <Search className="h-5 w-5 mr-2" />
            Ask the Oracle
          </CardTitle>
          <CardDescription>
            Submit your query to get verified answers from multiple AI miners
          </CardDescription>
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
        <div className="max-w-4xl mx-auto mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <MessageSquare className="h-5 w-5 mr-2" />
            Latest Result
          </h3>
          <QueryHistory queries={[results]} />
        </div>
      )}

      {/* Query History */}
      {queryHistory.length > 0 && (
        <div className="max-w-4xl mx-auto mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <History className="h-5 w-5 mr-2" />
            Query History ({queryHistory.length})
          </h3>
          <QueryHistory queries={queryHistory} />
        </div>
      )}

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
      <footer className="text-center py-8 border-t border-gray-200 dark:border-gray-700 mt-12">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Powered by <span className="font-semibold text-blue-600 dark:text-blue-400">Cortensor Network</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Decentralized AI consensus • {process.env.MODEL_NAME || 'Eureka'} Model
        </p>
      </footer>
    </div>
    </>
  )
}
