import type { DecisionEnvelope } from "../phase3_3/envelope";

export type EvidenceBundle = {
  decisionId: string;
  envelope: DecisionEnvelope;
  provenance: {
    sessionId: number;
    taskIds: number[];
  };
  createdAt: number;
  version?: string;
};

export function buildEvidenceBundle(
  decisionId: string,
  envelope: DecisionEnvelope,
  provenance: { sessionId: number; taskIds: number[] }
): EvidenceBundle {
  return {
    decisionId,
    envelope,
    provenance,
    createdAt: Date.now(),
    version: "v1",
  };
}
