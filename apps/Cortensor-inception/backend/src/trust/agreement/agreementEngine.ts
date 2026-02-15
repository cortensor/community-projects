// src/trust/agreement/agreementEngine.ts

import {
  InferenceResult,
  TrustAgreementResult,
  NormalizedOutput
} from "./types"

import { clusterInferences } from "./cluster"
import {
  computeAgreementScore,
  computeAggregatedConfidence
} from "./score"

import { decideTrust } from "./decide"

export function runAgreementEngine(
  inferences: InferenceResult[]
): TrustAgreementResult {

  if (inferences.length === 0) {
    return {
      agreementScore: 0,
      aggregatedConfidence: 0,
      majorityOutput: null,
      dissentingOutputs: [],
      decision: "BLOCK",
      explanation: "No inference results provided"
    }
  }

  const clusters = clusterInferences(inferences)

  let majorityOutput: NormalizedOutput | null = null
  let majorityCluster: InferenceResult[] = []

  for (const [output, cluster] of clusters.entries()) {
    if (cluster.length > majorityCluster.length) {
      majorityCluster = cluster
      majorityOutput = output
    }
  }

  const agreementScore = computeAgreementScore(
    majorityCluster.length,
    inferences.length
  )

  const aggregatedConfidence = computeAggregatedConfidence(
    agreementScore,
    majorityCluster
  )

  const decision = decideTrust(aggregatedConfidence)

  const dissentingOutputs = [...clusters.keys()].filter(
    o => o !== majorityOutput
  )

  return {
    agreementScore,
    aggregatedConfidence,
    majorityOutput,
    dissentingOutputs,
    decision,
    explanation: buildExplanation(
      agreementScore,
      aggregatedConfidence,
      decision,
      majorityCluster.length,
      inferences.length
    )
  }
}

function buildExplanation(
  agreement: number,
  confidence: number,
  decision: string,
  majority: number,
  total: number
): string {
  return `Agreement=${agreement.toFixed(2)}, Confidence=${confidence.toFixed(
    2
  )}, Majority=${majority}/${total}, Decision=${decision}`
}
