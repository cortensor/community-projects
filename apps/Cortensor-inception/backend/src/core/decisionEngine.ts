import type { TrustedInferenceClaim } from "../adapters/cortensor";
import { INVARIANTS } from "./invariants";

export type DecisionResult = {
  decision: "ESCALATE" | "BLOCK" | "RELEASE";
  reason: string;
};

class DecisionEngine {
  private claims: TrustedInferenceClaim[] = [];

  ingestTrustedClaims(claims: TrustedInferenceClaim[]): DecisionResult {
    // Enforce invariants: only authenticated claims allowed and no auto-release
    for (const c of claims) {
      if (c.authenticated !== true) {
        // Do not ingest unauthenticated claims
        return { decision: "BLOCK", reason: "Unauthenticated claim rejected" };
      }
    }

    this.claims.push(...claims);

    if (INVARIANTS.NEVER_AUTO_RELEASE || INVARIANTS.FAIL_CLOSED_ALWAYS) {
      return {
        decision: "ESCALATE",
        reason: "Agreement engine not active",
      };
    }

    // Defensive fallback — should not be reachable with current invariants
    return { decision: "BLOCK", reason: "Fail-closed fallback" };
  }
}

export const decisionEngine = new DecisionEngine();
