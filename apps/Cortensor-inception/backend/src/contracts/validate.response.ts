export type TrustDecision = "RELEASE" | "BLOCK" | "ESCALATE";

export interface ValidateResponse {
  decision: TrustDecision;
  confidence: number;
  reason: string;
  evidence: { hash: string; cid: string | null };
  stats: {
    validatorsUsed: number;
    agreementScore: number;
    policyScore: number;
    latencyMs: number;
  };
}
