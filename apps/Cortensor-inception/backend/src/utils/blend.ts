import type { EvidenceBundle } from "../phases/phase3_4/schema";
import type { Decision } from "../phases/phase3_3/envelope";

export type BlendedBundle = {
  id: string;
  sources: { path: string; bundle: EvidenceBundle }[];
  blended: {
    decision: Decision | "ESCALATE";
    agreementState: string;
    rationale: string;
    evidence: {
      totalClaims: number;
      groupCount: number;
      distinctMiners: number;
      replayHash: string[];
    };
    diffs: string[];
  };
  createdAt: number;
};

export function blendBundles(aPath: string, a: EvidenceBundle, bPath: string, b: EvidenceBundle): BlendedBundle {
  const diffs: string[] = [];

  if (a.envelope.decision !== b.envelope.decision) diffs.push("decision");
  if (a.envelope.rationale !== b.envelope.rationale) diffs.push("rationale");
  if (a.envelope.agreementState !== b.envelope.agreementState) diffs.push("agreementState");
  if (a.envelope.evidence.replayHash !== b.envelope.evidence.replayHash) diffs.push("replayHash");

  // Simple rule set:
  // - identical decisions => keep it
  // - different decisions => ESCALATE
  let blendedDecision: Decision | "ESCALATE" = a.envelope.decision;
  if (a.envelope.decision !== b.envelope.decision) blendedDecision = "ESCALATE";

  const rationale = `Source A (${a.decisionId}): ${a.envelope.rationale}\nSource B (${b.decisionId}): ${b.envelope.rationale}`;

  const evidence = {
    totalClaims: (a.envelope.evidence.totalClaims || 0) + (b.envelope.evidence.totalClaims || 0),
    groupCount: (a.envelope.evidence.groupCount || 0) + (b.envelope.evidence.groupCount || 0),
    distinctMiners: (a.envelope.evidence.distinctMiners || 0) + (b.envelope.evidence.distinctMiners || 0),
    replayHash: [a.envelope.evidence.replayHash, b.envelope.evidence.replayHash].filter(Boolean),
  };

  const agreementState = a.envelope.agreementState === b.envelope.agreementState ? a.envelope.agreementState : "ESCALATED";

  return {
    id: `blended-${Date.now()}`,
    sources: [ { path: aPath, bundle: a }, { path: bPath, bundle: b } ],
    blended: {
      decision: blendedDecision,
      agreementState,
      rationale,
      evidence,
      diffs,
    },
    createdAt: Date.now(),
  };
}
