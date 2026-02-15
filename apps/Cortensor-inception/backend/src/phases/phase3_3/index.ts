import type { TrustedInferenceClaim } from "../../adapters/cortensor";
import { DEFAULT_POLICY } from "./agreement.policy";
import { guardPhase3_3 } from "./guard";
import { decide } from "./decision";
import { finalizeDecision } from "./finalize";

export function runPhase3_3(claims: TrustedInferenceClaim[]) {
  guardPhase3_3(claims);

  const base = decide(claims, DEFAULT_POLICY);

  return finalizeDecision(base as any, claims);
}
