// src/trust/agreement/types.ts

export type InferenceResult = {
  inferenceId: string
  modelId: string
  output: unknown
  confidence?: number        // Optional, untrusted
  poiHash?: string
  validatorId?: string
}

export type NormalizedOutput = string

export type TrustDecision = "RELEASE" | "ESCALATE" | "BLOCK"

export type TrustAgreementResult = {
  agreementScore: number
  aggregatedConfidence: number
  majorityOutput: NormalizedOutput | null
  dissentingOutputs: NormalizedOutput[]
  decision: TrustDecision
  explanation: string
}
