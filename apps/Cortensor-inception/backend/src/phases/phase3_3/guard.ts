import type { TrustedInferenceClaim } from "../../adapters/cortensor";
import { INVARIANTS } from "../../core/invariants";

export function guardPhase3_3(claims: TrustedInferenceClaim[]) {
  if (!INVARIANTS.NEVER_TRUST_INFERENCE) throw new Error("Invariant violation: trust inference");

  for (const c of claims) {
    if (c.authenticated !== true) throw new Error("Unauthenticated claim rejected");
  }

  return true;
}
