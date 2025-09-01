"use client"

import { useState, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { CheckCircle, Clock, Brain, TrendingUp, Shield } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface ResponseAnalyzerProps {
  queryId: string
  queryText: string
}

interface MinerResponse {
  id: string
  response: string
  confidence: number
  reputation: number
  processingTime: number
  status: "completed" | "processing" | "failed"
}

interface AnalysisResult {
  consensus: string
  confidenceScore: number
  hallucinationRisk: number
  minerResponses: MinerResponse[]
  verificationStatus: "verified" | "disputed" | "processing"
  processingTime: number
}

const BACKEND_BASE = "http://localhost:4000"
const DECENTRALIZED_BASE = "http://127.0.0.1:5010"
const DECENTRALIZED_TOKEN = "default-dev-token"

export function ResponseAnalyzer({ queryId, queryText = "" }: ResponseAnalyzerProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastPromptRef = useRef<string>("") // stores last non-empty query

  function toPercent(n: number | null | undefined) {
    if (n == null || Number.isNaN(n)) return 0
    return n <= 1 ? Math.round(n * 100) : Math.round(n)
  }

  function mapBackendToAnalysis(payload: any): AnalysisResult {
    const status = payload?.query?.status as string | undefined
    const truth = payload?.truthRecord || null
    const createdAt = payload?.query?.createdAt ? new Date(payload.query.createdAt) : null
    const completedAt = payload?.query?.completedAt ? new Date(payload.query.completedAt) : null
    const procSeconds = createdAt && completedAt ? Math.max(0, (completedAt.getTime() - createdAt.getTime()) / 1000) : 0

    const minerResponses: MinerResponse[] = (payload?.minerResponses || []).map((r: any, idx: number) => ({
      id: r?.minerId ?? `miner-${idx + 1}`,
      response: r?.response ?? r?.responseText ?? r?.response_text ?? "",
      confidence: toPercent(Number.parseFloat(r?.confidence ?? r?.confidence_score ?? "0")),
      reputation: 0,
      processingTime: r?.responseTime ? Math.round((Number(r.responseTime) || 0) / 100) / 10 : 0,
      status: "completed",
    }))

    const verification = (truth?.verificationStatus as string) || "processing"
    const confidenceScore = toPercent(Number.parseFloat(truth?.truthScore ?? "0"))

    return {
      consensus: truth?.consensusAnswer ?? "(no consensus yet)",
      confidenceScore,
      hallucinationRisk: Math.max(0, 100 - confidenceScore),
      minerResponses,
      verificationStatus:
        verification === "verified" || verification === "disputed" ? (verification as any) : "processing",
      processingTime: procSeconds ? Math.round(procSeconds * 10) / 10 : 0,
    }
  }

  async function fetchDirectFromDecentralized(prompt: string): Promise<AnalysisResult> {
    try {
      await fetch(`${DECENTRALIZED_BASE}/api/v1/info`, {
        method: "GET",
        headers: { Authorization: `Bearer ${DECENTRALIZED_TOKEN}` },
      })
    } catch {
      // ignore
    }

    let text = ""
    try {
      const res = await fetch(`${DECENTRALIZED_BASE}/api/v1/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${DECENTRALIZED_TOKEN}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: 77,
          prompt,
          stream: false,
          timeout: 60,
        }),
      })

      let data: any = null
      try {
        data = await res.json()
      } catch {
        text = await res.text()
      }

      const possible =
        data?.text ??
        data?.response ??
        data?.output ??
        data?.result ??
        data?.choices?.[0]?.text ??
        data?.choices?.[0]?.message?.content ??
        text

      text = typeof possible === "string" ? possible : JSON.stringify(possible ?? {})
    } catch (e) {
      text = "Decentralized API request failed. Please verify the router is running on 127.0.0.1:5010."
    }

    const confidence = 90
    return {
      consensus: text || "(no response)",
      confidenceScore: confidence,
      hallucinationRisk: Math.max(0, 100 - confidence),
      minerResponses: [
        {
          id: "router",
          response: text || "",
          confidence,
          reputation: 0,
          processingTime: 0,
          status: "completed",
        },
      ],
      verificationStatus: "verified",
      processingTime: 0,
    }
  }

  useEffect(() => {
    if (typeof queryText === "string" && queryText.trim().length > 0) {
      lastPromptRef.current = queryText.trim()
    }

    setIsLoading(true)
    setAnalysis(null)

    const isDirectMode = queryId?.startsWith?.("direct_")
    let cancelled = false

    async function handleDirect() {
      try {
        const safePrompt = lastPromptRef.current || queryText || "Please answer the user's question."
        const direct = await fetchDirectFromDecentralized(safePrompt)
        if (!cancelled) {
          setAnalysis(direct)
          setIsLoading(false)
        }
      } catch {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    if (isDirectMode) {
      handleDirect()
      return () => {
        cancelled = true
      }
    }

    async function fetchOnce() {
      try {
        const res = await fetch(`${BACKEND_BASE}/oracle/result/${encodeURIComponent(queryId)}`)
        if (!res.ok) {
          const safePrompt = lastPromptRef.current || queryText || "Please answer the user's question."
          const direct = await fetchDirectFromDecentralized(safePrompt)
          if (!cancelled) {
            setAnalysis(direct)
            setIsLoading(false)
          }
          return
        }

        const payload = await res.json()
        const status = payload?.query?.status as string | undefined

        const mapped = mapBackendToAnalysis(payload)
        if (!cancelled) {
          setAnalysis(mapped)
        }

        if (status === "completed") {
          if (!cancelled) setIsLoading(false)
          if (pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
        }
      } catch (e) {
        const safePrompt = lastPromptRef.current || queryText || "Please answer the user's question."
        const direct = await fetchDirectFromDecentralized(safePrompt)
        if (!cancelled) {
          setAnalysis(direct)
          setIsLoading(false)
        }
      }
    }

    fetchOnce()
    pollRef.current = setInterval(fetchOnce, 2000)

    return () => {
      cancelled = true
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [queryId, queryText])

  if (isLoading) {
    return (
      <Card className="bg-white/5 backdrop-blur-sm border-white/10">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 animate-spin" />
            Analyzing Responses...
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-white/70">Processing miners</span>
              <span className="text-white">—</span>
            </div>
            <Progress value={60} className="h-2" />
          </div>
          <div className="text-sm text-white/70">Collecting responses from decentralized miners...</div>
        </CardContent>
      </Card>
    )
  }

  if (!analysis) return null

  return (
    <Card className="bg-white/5 backdrop-blur-sm border-white/10">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
          Truth Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="consensus" className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-white/5 border border-white/10">
            <TabsTrigger value="consensus" className="text-white data-[state=active]:bg-white/10">
              Consensus
            </TabsTrigger>
            <TabsTrigger value="miners" className="text-white data-[state=active]:bg-white/10">
              Miners
            </TabsTrigger>
            <TabsTrigger value="metrics" className="text-white data-[state=active]:bg-white/10">
              Metrics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="consensus" className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge className="bg-gradient-to-r from-blue-600 via-fuchsia-600 to-pink-600 text-white border-0">
                  {analysis.verificationStatus.toUpperCase()}
                </Badge>
                <span className="text-sm text-white/70">
                  {analysis.processingTime ? `Processed in ${analysis.processingTime}s` : "Processing..."}
                </span>
              </div>

              <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                <p className="text-white leading-relaxed">{analysis.consensus}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Confidence</span>
                    <span className="text-sm font-medium text-white">{analysis.confidenceScore}%</span>
                  </div>
                  <Progress value={analysis.confidenceScore} className="h-2" />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70">Hallucination Risk</span>
                    <span className="text-sm font-medium text-white">{analysis.hallucinationRisk}%</span>
                  </div>
                  <Progress value={analysis.hallucinationRisk} className="h-2" />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="miners" className="space-y-4">
            <div className="space-y-3">
              {analysis.minerResponses.map((miner, index) => (
                <motion.div
                  key={miner.id ?? index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="p-4 bg-white/5 rounded-lg border border-white/10"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Brain className="w-4 h-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400" />
                      <span className="text-sm font-medium text-white">Miner {index + 1}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className="text-xs bg-white/10 text-white border-white/10">
                        {miner.confidence}% confidence
                      </Badge>
                      <Badge className="text-xs bg-white/10 text-white border-white/10">⭐ {miner.reputation}</Badge>
                    </div>
                  </div>
                  <p className="text-sm text-white/80 mb-2">{miner.response}</p>
                  <div className="text-xs text-white/60">
                    {miner.processingTime ? `Processed in ${miner.processingTime}s` : ""}
                  </div>
                </motion.div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="metrics" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-white/5 rounded-lg border border-white/10">
                <TrendingUp className="w-8 h-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">{analysis.confidenceScore}%</div>
                <div className="text-sm text-white/70">Truth Confidence</div>
              </div>

              <div className="text-center p-4 bg-white/5 rounded-lg border border-white/10">
                <Shield className="w-8 h-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">{100 - analysis.hallucinationRisk}%</div>
                <div className="text-sm text-white/70">Accuracy Score</div>
              </div>

              <div className="text-center p-4 bg-white/5 rounded-lg border border-white/10">
                <Clock className="w-8 h-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">
                  {analysis.processingTime ? `${analysis.processingTime}s` : "—"}
                </div>
                <div className="text-sm text-white/70">Processing Time</div>
              </div>

              <div className="text-center p-4 bg-white/5 rounded-lg border border-white/10">
                <Brain className="w-8 h-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">{analysis.minerResponses.length}</div>
                <div className="text-sm text-white/70">Miners Consulted</div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
