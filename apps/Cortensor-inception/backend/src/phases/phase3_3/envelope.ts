export type Decision = "BLOCK" | "ESCALATE" | "RELEASE";

export type DecisionEnvelope = {
  decision: Decision;
  rationale: string;
  winningHash?: string;

  agreementState: "AGREED" | "ESCALATED" | "CONFLICT_DETECTED";

  evidence: {
    totalClaims: number;
    groupCount: number;
    distinctMiners: number;
    replayHash: string;
  };
};
