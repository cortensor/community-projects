'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, Cpu, Network, Zap } from 'lucide-react'

interface NetworkStatusProps {
  className?: string
}

export function NetworkStatus({ className }: NetworkStatusProps) {
  const [networkData, setNetworkData] = useState({
    sessionId: 11,
    activeMiners: 0,
    totalQueries: 0,
    avgConfidence: 0,
    status: 'connecting'
  })

  useEffect(() => {
    // Simulate network status updates with deterministic values
    let counter = 0
    const interval = setInterval(() => {
      counter++
      setNetworkData(prev => ({
        ...prev,
        activeMiners: 3 + (counter % 3), // 3-5 miners in predictable pattern
        totalQueries: prev.totalQueries + (counter % 2),
        avgConfidence: 0.7 + (0.3 * (Math.sin(counter * 0.1) + 1) / 2), // 70-100% using sine wave
        status: 'connected'
      }))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-500'
      case 'connecting': return 'bg-yellow-500'
      case 'disconnected': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center text-lg">
          <Network className="h-5 w-5 mr-2" />
          Network Status
        </CardTitle>
        <CardDescription>
          Cortensor Network
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Connection</span>
          <Badge 
            variant="outline" 
            className={`text-white ${getStatusColor(networkData.status)}`}
          >
            <div className="w-2 h-2 rounded-full bg-current mr-1 animate-pulse" />
            {networkData.status}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <Cpu className="h-4 w-4 text-blue-500" />
            <div>
              <div className="font-medium">{networkData.activeMiners}</div>
              <div className="text-gray-500">Active Miners</div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-green-500" />
            <div>
              <div className="font-medium">{networkData.totalQueries}</div>
              <div className="text-gray-500">Total Queries</div>
            </div>
          </div>

          <div className="flex items-center space-x-2 col-span-2">
            <Zap className="h-4 w-4 text-purple-500" />
            <div>
              <div className="font-medium">
                {(networkData.avgConfidence * 100).toFixed(1)}%
              </div>
              <div className="text-gray-500">Network Confidence</div>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="text-xs text-gray-500 text-center">
            Powered by Cortensor • GPT OSS 20B
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
