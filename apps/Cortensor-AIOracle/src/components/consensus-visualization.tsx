'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface ConsensusVisualizationProps {
  minerCount: number
  confidence: number
  isProcessing: boolean
}

export function ConsensusVisualization({ 
  minerCount, 
  confidence, 
  isProcessing 
}: ConsensusVisualizationProps) {
  const [animatedMiners, setAnimatedMiners] = useState<number[]>([])

  useEffect(() => {
    if (isProcessing) {
      // Animate miners coming online
      const miners = Array.from({ length: minerCount }, (_, i) => i)
      miners.forEach((miner, index) => {
        setTimeout(() => {
          setAnimatedMiners(prev => [...prev, miner])
        }, index * 500)
      })
    } else {
      setAnimatedMiners([])
    }
  }, [isProcessing, minerCount])

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'bg-green-500'
    if (conf >= 0.6) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <h3 className="text-lg font-semibold mb-4 text-center">
        Consensus Network
      </h3>
      
      {/* Miners Grid */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {Array.from({ length: Math.max(minerCount, 5) }, (_, i) => (
          <motion.div
            key={i}
            className={`
              w-12 h-12 rounded-full border-2 flex items-center justify-center
              ${animatedMiners.includes(i) || !isProcessing
                ? 'bg-blue-500 border-blue-600 text-white'
                : 'bg-gray-200 border-gray-300 text-gray-500'
              }
            `}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ 
              scale: animatedMiners.includes(i) || !isProcessing ? 1 : 0.5,
              opacity: animatedMiners.includes(i) || !isProcessing ? 1 : 0.3
            }}
            transition={{ duration: 0.3 }}
          >
            <span className="text-xs font-bold">M{i + 1}</span>
          </motion.div>
        ))}
      </div>

      {/* Confidence Bar */}
      {!isProcessing && (
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: '100%' }}
          transition={{ duration: 1, delay: 0.5 }}
          className="space-y-2"
        >
          <div className="flex justify-between text-sm">
            <span>Consensus Confidence</span>
            <span className="font-bold">{(confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <motion.div
              className={`h-3 rounded-full ${getConfidenceColor(confidence)}`}
              initial={{ width: 0 }}
              animate={{ width: `${confidence * 100}%` }}
              transition={{ duration: 1, delay: 1 }}
            />
          </div>
        </motion.div>
      )}

      {/* Processing Animation */}
      {isProcessing && (
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"
          />
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Processing consensus...
          </p>
        </div>
      )}
    </div>
  )
}
