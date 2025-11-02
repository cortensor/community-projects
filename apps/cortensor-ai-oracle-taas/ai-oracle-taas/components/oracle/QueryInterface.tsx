"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Send, Settings, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface QueryInterfaceProps {
  onSubmitQuery: (query: string, options: QueryOptions) => void
  isLoading: boolean
  value?: string
  onChangeQuery?: (text: string) => void
}

interface QueryOptions {
  queryType: "fact" | "opinion" | "calculation" | "prediction"
  minerCount: number
  consensusThreshold: number
  timeoutMs: number
}

export function QueryInterface({ onSubmitQuery, isLoading, value, onChangeQuery }: QueryInterfaceProps) {
  const [internalQuery, setInternalQuery] = useState(value ?? "")
  const [options, setOptions] = useState<QueryOptions>({
    queryType: "fact",
    minerCount: 3,
    consensusThreshold: 0.8,
    timeoutMs: 30000,
  })
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    if (value !== undefined) {
      setInternalQuery(value)
    }
  }, [value])

  const handleSubmit = () => {
    const current = (value !== undefined ? value : internalQuery).trim()
    if (current && !isLoading) {
      onSubmitQuery(current, options)
    }
  }

  const queryTypeDescriptions = {
    fact: "Objective, verifiable information",
    opinion: "Subjective viewpoints and preferences",
    calculation: "Mathematical computations",
    prediction: "Future forecasts and trends",
  }

  return (
    <Card className="bg-white/5 backdrop-blur-sm border-white/10">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 animate-pulse" />
          Truth Query Interface
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Query Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-white">Your Question</label>
          <Textarea
            placeholder="Ask anything... e.g., 'What is the current population of Tokyo?' or 'Explain quantum computing'"
            value={value !== undefined ? value : internalQuery}
            onChange={(e) => (onChangeQuery ? onChangeQuery(e.target.value) : setInternalQuery(e.target.value))}
            className="min-h-[120px] bg-white/5 border-white/10 text-white placeholder-white/50 focus:border-fuchsia-400 focus:ring-0 resize-none"
            maxLength={1000}
          />
          <div className="flex justify-between text-xs text-white/60">
            <span>Be specific for better results</span>
            <span>{value !== undefined ? value.length : internalQuery.length}/1000</span>
          </div>
        </div>

        {/* Query Type */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-white">Query Type</label>
          <Select
            value={options.queryType}
            onValueChange={(value: any) => setOptions({ ...options, queryType: value })}
          >
            <SelectTrigger className="bg-white/5 border-white/10 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-white/5 border-white/10">
              {Object.entries(queryTypeDescriptions).map(([type, description]) => (
                <SelectItem key={type} value={type} className="text-white hover:bg-white/10">
                  <div className="flex flex-col items-start">
                    <span className="capitalize font-medium">{type}</span>
                    <span className="text-xs text-white/60">{description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Advanced Settings */}
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between text-white/60 hover:text-white hover:bg-white/10">
              <span className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-white" />
                Advanced Settings
              </span>
              <motion.div animate={{ rotate: showAdvanced ? 180 : 0 }} transition={{ duration: 0.2 }}>
                ▼
              </motion.div>
            </Button>
          </CollapsibleTrigger>

          <CollapsibleContent className="space-y-4 pt-4">
            {/* Miner Count */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-white">Miners to Query</label>
                <Badge variant="outline" className="border-white/10 text-white">
                  {options.minerCount}
                </Badge>
              </div>
              <Slider
                value={[options.minerCount]}
                onValueChange={([value]) => setOptions({ ...options, minerCount: value })}
                min={1}
                max={10}
                step={1}
                className="w-full"
              />
              <p className="text-xs text-white/60">More miners = higher accuracy but slower response</p>
            </div>

            {/* Consensus Threshold */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-white">Consensus Threshold</label>
                <Badge variant="outline" className="border-white/10 text-white">
                  {Math.round(options.consensusThreshold * 100)}%
                </Badge>
              </div>
              <Slider
                value={[options.consensusThreshold]}
                onValueChange={([value]) => setOptions({ ...options, consensusThreshold: value })}
                min={0.5}
                max={1.0}
                step={0.05}
                className="w-full"
              />
              <p className="text-xs text-white/60">Higher threshold = stricter consensus requirements</p>
            </div>

            {/* Timeout */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-white">Timeout</label>
                <Badge variant="outline" className="border-white/10 text-white">
                  {options.timeoutMs / 1000}s
                </Badge>
              </div>
              <Slider
                value={[options.timeoutMs]}
                onValueChange={([value]) => setOptions({ ...options, timeoutMs: value })}
                min={5000}
                max={60000}
                step={5000}
                className="w-full"
              />
              <p className="text-xs text-white/60">Maximum time to wait for miner responses</p>
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!(value !== undefined ? value : internalQuery).trim() || isLoading}
          className="w-full text-white bg-gradient-to-r from-blue-600 via-fuchsia-600 to-pink-600 hover:opacity-90"
          size="lg"
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing Query...
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Send className="w-4 h-4 text-white" />
              Submit to Oracle Network
            </div>
          )}
        </Button>

        {/* Info */}
        <div className="flex items-start gap-2 p-3 bg-white/5 border border-white/10 rounded-lg">
          <Info className="w-4 h-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-fuchsia-400 to-pink-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-white">
            <p className="font-medium mb-1">How it works:</p>
            <p className="text-white/80">
              Your query is sent to multiple AI miners in the Cortensor network. Their responses are analyzed for
              consensus, and hallucinations are detected and filtered out.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
