import { INVARIANTS } from "../core/invariants";
import { TrustedInferenceClaim } from "../adapters/cortensor/types";

export function guardPhase3_2(claims: TrustedInferenceClaim[]) {
  if (!INVARIANTS.NEVER_TRUST_INFERENCE) throw new Error("Invariant violation");

  for (const c of claims) {
    if (c.authenticated !== true) throw new Error("Unauthenticated claim rejected");
  }

  return true;
}
