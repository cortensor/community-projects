// src/trust/agreement/cluster.ts

import { InferenceResult, NormalizedOutput } from "./types"
import { normalizeOutput } from "./normalize"

export function clusterInferences(
  inferences: InferenceResult[]
): Map<NormalizedOutput, InferenceResult[]> {
  const clusters = new Map<NormalizedOutput, InferenceResult[]>()

  for (const inf of inferences) {
    const normalized = normalizeOutput(inf.output)
    const existing = clusters.get(normalized) ?? []
    existing.push(inf)
    clusters.set(normalized, existing)
  }

  return clusters
}
