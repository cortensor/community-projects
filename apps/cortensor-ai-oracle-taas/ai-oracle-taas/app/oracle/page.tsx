"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { QueryInterface } from "@/components/oracle/QueryInterface"
import { ResponseAnalyzer } from "@/components/oracle/ResponseAnalyzer"
import { TruthDashboard } from "@/components/oracle/TruthDashboard"
import { useOracleQuery } from "@/hooks/useOracleQuery"

export default function OraclePage() {
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null)
  const [lastQueryText, setLastQueryText] = useState<string>("")
  const [prompt, setPrompt] = useState<string>("") // new controlled prompt
  const { submitQuery, getQueryResult, isLoading } = useOracleQuery()

  const handleSubmitQuery = async (query: string, options: any) => {
    try {
      // Ensure we capture the submitted text as the prompt used for analysis
      setLastQueryText(query) // use submitted query as source of truth
      const result = await submitQuery(query, options)
      setActiveQueryId(result.queryId)
    } catch (error) {
      console.error("Failed to submit query:", error)
    }
  }

  return (
    <div className="min-h-screen relative bg-gradient-to-br from-blue-950 via-fuchsia-950 to-pink-950">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-24 -left-24 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute top-1/3 -right-24 h-72 w-72 rounded-full bg-fuchsia-500/20 blur-3xl" />
        <div className="absolute -bottom-24 left-1/4 h-72 w-72 rounded-full bg-pink-500/20 blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6 text-balance">
            AI Oracle{" "}
            <span className="bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent">
              Interface
            </span>
          </h1>
          <p className="text-xl text-white/70 max-w-3xl mx-auto text-pretty">
            Submit your queries to the decentralized truth verification network. Get consensus-based answers from
            multiple AI miners.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Query Interface */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <QueryInterface
              onSubmitQuery={handleSubmitQuery}
              isLoading={isLoading}
              value={prompt} // controlled prompt value
              onChangeQuery={setPrompt} // keep parent in sync
            />
          </motion.div>

          {/* Response Analyzer */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            {activeQueryId ? (
              <ResponseAnalyzer queryId={activeQueryId} queryText={lastQueryText} />
            ) : (
              <div className="h-full flex items-center justify-center bg-card rounded-2xl border border-border">
                <div className="text-center text-muted-foreground">
                  <div className="text-6xl mb-4">🤖</div>
                  <p>Submit a query to see real-time analysis</p>
                </div>
              </div>
            )}
          </motion.div>
        </div>

        {/* Truth Dashboard */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="mt-12"
        >
          <TruthDashboard />
        </motion.div>
      </div>
    </div>
  )
}
