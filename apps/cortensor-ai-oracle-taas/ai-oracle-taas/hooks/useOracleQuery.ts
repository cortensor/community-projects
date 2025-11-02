"use client"

import { useState, useCallback } from "react"

interface QueryOptions {
  queryType: "fact" | "opinion" | "calculation" | "prediction"
  minerCount: number
  consensusThreshold: number
  timeoutMs: number
}

interface QueryResult {
  queryId: string
  status: "pending" | "processing" | "completed" | "failed"
  consensus?: string
  confidenceScore?: number
  hallucinationRisk?: number
  processingTime?: number
}

interface SubmitQueryResult {
  queryId: string
  status: string
}

export function useOracleQuery() {
  const [isLoading, setIsLoading] = useState(false)
  const [queries, setQueries] = useState<Map<string, QueryResult>>(new Map())
  const [error, setError] = useState<string | null>(null)

  const submitQuery = useCallback(async (query: string, options: QueryOptions): Promise<SubmitQueryResult> => {
    setIsLoading(true)
    setError(null)

    try {
      const res = await fetch("http://localhost:4000/oracle/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          query,
          queryType: options.queryType,
          minerCount: options.minerCount,
          consensusThreshold: options.consensusThreshold,
          timeoutMs: options.timeoutMs,
        }),
      })

      if (!res.ok) {
        // Backend error: mark a synthetic id so the analyzer knows to use direct fallback
        const fallbackId = `direct_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
        setQueries(
          (prev) =>
            new Map(
              prev.set(fallbackId, {
                queryId: fallbackId,
                status: "processing",
              }),
            ),
        )
        return { queryId: fallbackId, status: "submitted" }
      }

      const data = await res.json()
      const queryId = data?.queryId || data?.id || `q_${Date.now()}`

      // Track basic status locally (optional)
      setQueries(
        (prev) =>
          new Map(
            prev.set(queryId, {
              queryId,
              status: "processing",
            }),
          ),
      )

      return { queryId, status: "submitted" }
    } catch (err) {
      const fallbackId = `direct_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      setQueries(
        (prev) =>
          new Map(
            prev.set(fallbackId, {
              queryId: fallbackId,
              status: "processing",
            }),
          ),
      )
      return { queryId: fallbackId, status: "submitted" }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getQueryResult = useCallback(
    (queryId: string): QueryResult | null => {
      return queries.get(queryId) || null
    },
    [queries],
  )

  const getAllQueries = useCallback((): QueryResult[] => {
    return Array.from(queries.values()).sort(
      (a, b) => new Date(b.queryId.split("_")[1]).getTime() - new Date(a.queryId.split("_")[1]).getTime(),
    )
  }, [queries])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const clearQueries = useCallback(() => {
    setQueries(new Map())
  }, [])

  return {
    submitQuery,
    getQueryResult,
    getAllQueries,
    isLoading,
    error,
    clearError,
    clearQueries,
    queryCount: queries.size,
  }
}
