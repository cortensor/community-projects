import { listenForTrustedClaims } from "../adapters/cortensor/events";
import { guardPhase3_2 } from "./phase3_2.guard";
import { decisionEngine } from "../core/decisionEngine";

export function startPhase3_2() {
  listenForTrustedClaims((claims) => {
    guardPhase3_2(claims);

    // 🔒 END OF PHASE 3.2 — claims are ingested but do not trigger actions here.
    decisionEngine.ingestTrustedClaims(claims);
  });
}
