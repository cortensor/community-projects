// src/trust/agreement/score.ts

import { InferenceResult } from "./types"

export function computeAgreementScore(
  majorityCount: number,
  total: number
): number {
  if (total === 0) return 0
  return majorityCount / total
}

export function computeAggregatedConfidence(
  agreementScore: number,
  majorityCluster: InferenceResult[]
): number {
  const confidences = majorityCluster.map(
    r => r.confidence ?? 0.5 // default safe value
  )

  const avgConfidence =
    confidences.reduce((a, b) => a + b, 0) / confidences.length

  // Blend agreement and confidence so that partial agreement with reasonable
  // confidence escalates rather than blocks. We compute the mean of agreement
  // ratio and average confidence to produce a more intuitive aggregate.
  return (agreementScore + avgConfidence) / 2
}
