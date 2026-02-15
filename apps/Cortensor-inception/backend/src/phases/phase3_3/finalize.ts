import { deriveState } from "./state";
import { replayHash } from "./replay";
import type { TrustedInferenceClaim } from "../../adapters/cortensor";
import type { DecisionEnvelope } from "./envelope";

export function finalizeDecision(
  base: Omit<DecisionEnvelope, "agreementState" | "evidence"> & { evidence: { groupCount: number } },
  claims: TrustedInferenceClaim[]
): DecisionEnvelope {
  return {
    ...base,
    agreementState: deriveState(base.decision),
    evidence: {
      totalClaims: claims.length,
      groupCount: base.evidence.groupCount,
      distinctMiners: new Set(claims.map((c) => c.miner)).size,
      replayHash: replayHash(claims),
    },
  };
}
