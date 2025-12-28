// src/trust/agreement/decide.ts

import { TrustDecision } from "./types"

const POLICY = {
  RELEASE: 0.75,
  ESCALATE: 0.45
}

export function decideTrust(
  aggregatedConfidence: number
): TrustDecision {
  if (aggregatedConfidence >= POLICY.RELEASE) {
    return "RELEASE"
  }

  if (aggregatedConfidence >= POLICY.ESCALATE) {
    return "ESCALATE"
  }

  return "BLOCK"
}
