import type { TrustedInferenceClaim } from "../../adapters/cortensor";
import { DEFAULT_POLICY } from "./agreement.policy";
import type { Decision } from "./envelope";

export function decide(claims: TrustedInferenceClaim[], policy = DEFAULT_POLICY): { decision: Decision; rationale: string; evidence: { groupCount: number } } {
  if (claims.length === 0) {
    return { decision: "BLOCK", rationale: "no claims", evidence: { groupCount: 0 } };
  }

  const groups = new Map<string, TrustedInferenceClaim[]>();

  for (const c of claims) {
    const key = String(c.output);
    groups.set(key, (groups.get(key) || []).concat(c));
  }

  let majorityKey: string | null = null;
  let majoritySize = 0;

  for (const [k, g] of groups.entries()) {
    if (g.length > majoritySize) {
      majoritySize = g.length;
      majorityKey = k;
    }
  }

  const agreementScore = majoritySize / claims.length;

  if (agreementScore >= policy.releaseThreshold) {
    return {
      decision: "RELEASE",
      rationale: `majority ${majoritySize}/${claims.length} >= ${policy.releaseThreshold}` ,
      evidence: { groupCount: groups.size },
    };
  }

  if (agreementScore >= policy.escalateThreshold) {
    return {
      decision: "ESCALATE",
      rationale: `partial agreement ${majoritySize}/${claims.length}` ,
      evidence: { groupCount: groups.size },
    };
  }

  return {
    decision: "BLOCK",
    rationale: `conflict ${majoritySize}/${claims.length}` ,
    evidence: { groupCount: groups.size },
  };
}
